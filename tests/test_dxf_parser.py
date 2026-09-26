# -*- coding: utf-8 -*-
"""Unit tests for the DXF contour parser (no FreeCAD needed)."""

import os
import sys
import unittest

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))

from freecad.AlumFrame.profiles import dxf_parser as dp


DXF_DIR = dp.default_dxf_dir()


class TestPortability(unittest.TestCase):
    def test_default_dir_is_package_relative(self):
        self.assertTrue(os.path.isabs(DXF_DIR))
        self.assertTrue(DXF_DIR.endswith(os.path.join('profiles', 'dxf')))
        self.assertTrue(os.path.isdir(DXF_DIR))

    def test_no_hardcoded_home_path_in_config(self):
        config_path = os.path.join(
            os.path.dirname(_here), 'freecad', 'AlumFrame', 'config.py')
        with open(config_path, encoding='utf-8') as f:
            self.assertNotIn('/home/', f.read())


class TestChaining(unittest.TestCase):
    def test_loops_are_closed(self):
        path = os.path.join(DXF_DIR, 'hfs8-4040.dxf')
        entities = dp.extract_entities(dp.parse_dxf_tokens(path))
        loops, circles = dp.chain_loops(entities)
        self.assertTrue(loops)
        for loop in loops:
            start = loop[0]['p0']
            end = loop[-1]['p1']
            self.assertAlmostEqual(start[0], end[0], places=4)
            self.assertAlmostEqual(start[1], end[1], places=4)

    def test_circles_detected(self):
        path = os.path.join(DXF_DIR, 'nfs5-2020.dxf')
        entities = dp.extract_entities(dp.parse_dxf_tokens(path))
        loops, circles = dp.chain_loops(entities)
        self.assertTrue(circles)
        self.assertTrue(any(r > 0 for _, _, r in circles))


class TestContours(unittest.TestCase):
    def test_square_profile_20x20(self):
        c = dp.get_contours(os.path.join(DXF_DIR, 'nfs5-2020.dxf'))
        self.assertIsNotNone(c)
        self.assertAlmostEqual(c['width'], 20.0, delta=0.2)
        self.assertAlmostEqual(c['height'], 20.0, delta=0.2)
        self.assertGreater(len(c['circles']), 0)

    def test_square_profile_40x40_with_cavities(self):
        c = dp.get_contours(os.path.join(DXF_DIR, 'hfs8-4040.dxf'))
        self.assertIsNotNone(c)
        self.assertAlmostEqual(c['width'], 40.0, delta=0.2)
        self.assertAlmostEqual(c['height'], 40.0, delta=0.2)
        self.assertGreater(len(c['outer']), 20)
        self.assertGreaterEqual(len(c['holes']), 4)

    def test_centered_on_origin(self):
        c = dp.get_contours(os.path.join(DXF_DIR, 'hfs8-4040.dxf'))
        pts = dp.loop_points(c['outer'])
        cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2.0
        cy = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2.0
        self.assertAlmostEqual(cx, 0.0, places=3)
        self.assertAlmostEqual(cy, 0.0, places=3)

    def test_annotation_rectangle_rejected(self):
        # LCF8-3030 stores its real geometry in a REGION proxy; only the
        # annotation rectangle is made of LINEs, which must not be accepted.
        self.assertIsNone(
            dp.get_contours(os.path.join(DXF_DIR, 'LCF8-3030.dxf')))

    def test_holes_inside_outer(self):
        c = dp.get_contours(os.path.join(DXF_DIR, 'nefs8-4040.dxf'))
        self.assertIsNotNone(c)
        poly = dp.loop_points(c['outer'])
        for hole in c['holes']:
            self.assertTrue(dp.point_in_polygon(hole[0]['p0'], poly))
        for cx, cy, _ in c['circles']:
            self.assertTrue(dp.point_in_polygon((cx, cy), poly))


class TestProfileLookup(unittest.TestCase):
    def test_known_sizes(self):
        p20 = dp.get_profile_for_size('20x20')
        p40 = dp.get_profile_for_size('40x40')
        self.assertAlmostEqual(p20['width'], 20.0, delta=0.2)
        self.assertAlmostEqual(p40['width'], 40.0, delta=0.2)
        self.assertTrue(os.path.exists(p40['dxf_file']))

    def test_proxy_only_size_returns_none(self):
        self.assertIsNone(dp.get_profile_for_size('30x30'))

    def test_get_all_profiles_has_core_sizes(self):
        profiles = dp.get_all_profiles()
        sizes = {p['profile'] for p in profiles}
        self.assertIn('20x20', sizes)
        self.assertIn('40x40', sizes)


if __name__ == '__main__':
    unittest.main()
