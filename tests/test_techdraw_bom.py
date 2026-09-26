# -*- coding: utf-8 -*-
"""Unit tests for the TechDraw helper module (no FreeCAD needed)."""

import os
import sys
import unittest

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_here)))

from AulmFrame import techdraw_bom as td


A2 = (594.0, 420.0)
A4 = (297.0, 210.0)
LENGTHS = [200, 300, 500, 800, 1000, 1500, 2000, 3000, 4000, 6000,
           8000, 10000, 15000, 20000]


class TestTechDrawHelpers(unittest.TestCase):
    def test_prefix(self):
        self.assertEqual(td.PAGE_PREFIX, 'TD_')

    def test_remove_drawings_none_is_safe(self):
        self.assertIsNone(td.remove_drawings(None))

    def test_module_importable_without_freecad(self):
        self.assertTrue(hasattr(td, 'create_techdraw_bom'))


class TestPlanLayout(unittest.TestCase):
    def _check(self, page, lengths, cross=40.0):
        items = [(float(L), cross) for L in lengths]
        page_w, page_h = page
        plan = td.plan_layout(items, page_w, page_h)
        draw_w = page_w - 2 * td.MARGIN - td.END_BOX - 10.0
        self.assertGreater(plan['scale'], 0)
        for (length, _cm), row in zip(items, plan['rows']):
            drawn = length * plan['scale']
            # never wider than the available drawing width
            self.assertLessEqual(drawn, draw_w + 1e-6,
                                 'length %s overflows' % length)
            # one-end aligned: every member starts at the same left edge
            self.assertAlmostEqual(row['x_left'], td.MARGIN, places=6)
            self.assertAlmostEqual(row['x_center'] - drawn / 2.0,
                                   td.MARGIN, places=6)
        # longest member uses the full available width (unless row-limited)
        longest = max(L for L, _ in items)
        self.assertLessEqual(longest * plan['scale'], draw_w + 1e-6)

    def test_a2_all_lengths(self):
        self._check(A2, LENGTHS)

    def test_a4_all_lengths(self):
        self._check(A4, LENGTHS)

    def test_short_members_not_scaled_up(self):
        plan = td.plan_layout([(200.0, 40.0), (300.0, 40.0)], *A2)
        self.assertLessEqual(plan['scale'], 1.0)

    def test_common_scale_for_all_rows(self):
        plan = td.plan_layout([(200.0, 40.0), (6000.0, 40.0)], *A2)
        drawn_short = 200.0 * plan['scale']
        drawn_long = 6000.0 * plan['scale']
        self.assertAlmostEqual(drawn_long / drawn_short, 30.0, places=6)
        self.assertLessEqual(drawn_long,
                             A2[0] - 2 * td.MARGIN - td.END_BOX - 10.0 + 1e-6)

    def test_template_keepout_parsed(self):
        tpl = os.path.join(os.path.dirname(os.path.dirname(_here)),
                           'AulmFrame', 'templates', 'A2_Landscape.svg')
        ko = td._template_keepout(tpl, *A2)
        self.assertIsNotNone(ko)
        # title block sits in the lower-right corner of the sheet
        self.assertLess(ko[1], A2[1] * 0.5)
        self.assertGreater(ko[2], A2[0] * 0.5)

    def test_layout_avoids_titleblock(self):
        tpl = os.path.join(os.path.dirname(os.path.dirname(_here)),
                           'AulmFrame', 'templates', 'A2_Landscape.svg')
        ko = td._template_keepout(tpl, *A2)
        plan = td.plan_layout([(6000.0, 40.0)] * 3, *A2, keepout=ko)
        for row in plan['rows']:
            band_bottom = row['y_center'] - row['row_h'] / 2.0
            # whole row (incl. end view / annotation) stays above keep-out
            self.assertGreaterEqual(band_bottom, ko[3] - 1e-6)
            self.assertLessEqual(row['end_x'] + td.END_BOX / 2.0, A2[0] - td.MARGIN)
            self.assertGreaterEqual(row['x_left'], td.MARGIN)

    def test_rows_within_sheet(self):
        cross = 40.0
        plan = td.plan_layout([(200.0, cross)] * 3, *A2)
        half = cross / 2.0 * plan['scale']
        for row in plan['rows']:
            self.assertLessEqual(row['y_center'] + half, A2[1] - td.MARGIN + 1e-6)
            self.assertGreaterEqual(row['y_center'] - half, td.MARGIN - 1e-6)
        # end view box stays inside the sheet as well
        for row in plan['rows']:
            self.assertLessEqual(row['end_x'] + td.END_BOX / 2.0,
                                 A2[0] - td.MARGIN + 1e-6)


if __name__ == '__main__':
    unittest.main()
