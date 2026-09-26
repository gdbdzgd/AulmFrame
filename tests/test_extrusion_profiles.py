# -*- coding: utf-8 -*-
"""Unit tests for the parametric extrusion profile table (no FreeCAD needed)."""

import os
import sys
import unittest

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))

from freecad.AlumFrame.profiles import extrusion_profiles as ep


class TestExtrusionTable(unittest.TestCase):
    def test_expected_series_present(self):
        for name in ('E2020', 'E2040', 'E3030', 'E3060', 'E4040', 'E4080'):
            self.assertIn(name, ep.EXTRUSIONS, name)

    def test_dimensions(self):
        self.assertEqual(ep.dimensions('E2020'), (20, 20))
        self.assertEqual(ep.dimensions('E2040'), (20, 40))
        self.assertEqual(ep.dimensions('E4040'), (40, 40))
        self.assertEqual(ep.dimensions('E4080'), (40, 80))
        self.assertEqual(ep.dimensions('E3060'), (30, 60))

    def test_square_classification(self):
        self.assertTrue(ep.is_square('E2020'))
        self.assertTrue(ep.is_square('E4040'))
        self.assertFalse(ep.is_square('E2040'))
        self.assertFalse(ep.is_square('E4080'))

    def test_tuple_layout(self):
        # 11 fields: W,H,d1,d2,sq,cw,cwi,t,st,f,recess
        for name, entry in ep.EXTRUSIONS.items():
            self.assertEqual(len(entry), 11, name)


class TestTapSizing(unittest.TestCase):
    def test_taps_follow_centre_bore(self):
        from freecad.AlumFrame.config import tap_for_center_bore
        self.assertEqual(tap_for_center_bore(4.2)[0], 'M5')
        self.assertEqual(tap_for_center_bore(5.0)[0], 'M6')
        self.assertEqual(tap_for_center_bore(6.8)[0], 'M8')
        self.assertEqual(tap_for_center_bore(10.2)[0], 'M12')
        self.assertIsNone(tap_for_center_bore(None))
        self.assertIsNone(tap_for_center_bore(0))

    def test_clearance_is_larger_than_tap(self):
        from freecad.AlumFrame.config import tap_for_center_bore
        for bore in (4.2, 5.0, 6.8, 10.2):
            name, pilot, clearance = tap_for_center_bore(bore)
            nominal = float(name[1:])
            self.assertGreater(clearance, nominal)

    def test_profile_specs_for_parametric(self):
        from freecad.AlumFrame.config import hole_specs_for_profile
        sp = hole_specs_for_profile('40x40 E4040')
        self.assertEqual(sp['tap'], 'M12')      # bore 10.5
        self.assertAlmostEqual(sp['center_bore'], 10.5, places=3)
        sp20 = hole_specs_for_profile('20x20 E2020')
        self.assertEqual(sp20['tap'], 'M5')     # bore 4.2


if __name__ == '__main__':
    unittest.main()
