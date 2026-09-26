# -*- coding: utf-8 -*-
"""Unit tests for BOM aggregation and CSV export (no FreeCAD needed)."""

import csv
import os
import sys
import tempfile
import unittest

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))

from freecad.AlumFrame.bom import export_bom_csv, get_bom_summary, hole_note


BEAMS = [
    {'part': u'X-横梁', 'profile': '20x20 方管', 'length': 560, 'qty': 2},
    {'part': u'Y-纵梁', 'profile': '20x20 方管', 'length': 360, 'qty': 2},
    {'part': u'Z-立柱', 'profile': '20x20 方管', 'length': 500, 'qty': 4},
]


class TestBomSummary(unittest.TestCase):
    def test_aggregates_total_qty_and_length(self):
        s = get_bom_summary(BEAMS)
        self.assertEqual(s[u'X-横梁 (20x20 方管)']['qty'], 2)
        self.assertEqual(s[u'X-横梁 (20x20 方管)']['length'], 1120)


class TestCsvExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_export_roundtrip(self):
        path = os.path.join(self.tmp, 'bom.csv')
        export_bom_csv(
            BEAMS, path,
            material='Aluminum 6061',
            hole_spec={'beam_cross': 'M5', 'post_tap': 'M6'},
            profile_size=20,
            z_layers=1,
            z_layer_positions=[0, 480])
        self.assertTrue(os.path.exists(path))

        with open(path, encoding='utf-8-sig') as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[0][0], u'序号')
        self.assertEqual(rows[0][1], u'部件')
        # 3 part rows + header + total row
        self.assertEqual(len(rows), 5)
        # total length 2*560 + 2*360 + 4*500 = 3840
        total_row = rows[-1]
        self.assertIn('3840', total_row)

    def test_export_contains_hole_notes(self):
        path = os.path.join(self.tmp, 'bom.csv')
        export_bom_csv(
            BEAMS, path,
            hole_spec={'beam_cross': 'M5', 'post_tap': 'M6'},
            profile_size=20, z_layers=1)
        with open(path, encoding='utf-8-sig') as f:
            content = f.read()
        self.assertIn('M6', content)
        self.assertIn(u'十字通孔', content)

    def test_export_without_hole_spec(self):
        path = os.path.join(self.tmp, 'bom.csv')
        export_bom_csv(BEAMS, path)
        with open(path, encoding='utf-8-sig') as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[0][0], u'序号')


class TestHoleNote(unittest.TestCase):
    def test_empty_without_spec(self):
        self.assertEqual(hole_note(u'X-横梁', 560), '')

    def test_x_beam_note(self):
        note = hole_note(u'X-横梁', 560,
                         {'beam_cross': 'M5', 'post_tap': 'M6'}, 20)
        self.assertIn(u'距端面0mm', note)
        self.assertIn(u'距端面560mm', note)

    def test_z_post_note_uses_real_specs(self):
        # 40x40 uses M8 cross holes / M10 taps — must not be hard-coded M5/M6
        note = hole_note(u'Z-立柱', 500,
                         {'beam_cross': 'M8', 'post_tap': 'M10'}, 40)
        self.assertIn('M8', note)
        self.assertIn('M10', note)
        self.assertNotIn('M5', note)
        self.assertNotIn('M6', note)


if __name__ == '__main__':
    unittest.main()
