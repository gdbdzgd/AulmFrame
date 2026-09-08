# -*- coding: utf-8 -*-
"""Unit tests for position calculations and BOM hole notes (no FreeCAD needed)."""

import os
import sys
import unittest

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_here)))

from AulmFrame.position_calculator import FramePositionCalculator
from AulmFrame.config import PROFILES, HOLE_SPECS
from AulmFrame.bom import hole_note, get_bom_summary


class TestAnchorAndPosts(unittest.TestCase):
    def setUp(self):
        self.c = FramePositionCalculator(600, 400, 500, 40)

    def test_anchor_corner(self):
        self.assertAlmostEqual(self.c.z_post_anchor_x, -300.0)
        self.assertAlmostEqual(self.c.z_post_anchor_y, -200.0)
        self.assertEqual(self.c.z_post_anchor_z, 0)

    def test_post_positions_four_corners(self):
        pos = self.c.get_z_post_positions()
        self.assertEqual(len(pos), 4)
        self.assertIn((-300.0, -200.0), pos)
        self.assertIn((260.0, -200.0), pos)
        self.assertIn((-300.0, 160.0), pos)
        self.assertIn((260.0, 160.0), pos)

    def test_post_spacing(self):
        self.assertEqual(self.c.get_z_post_spacing(), (560, 360))


class TestBeams(unittest.TestCase):
    def setUp(self):
        self.c = FramePositionCalculator(600, 400, 500, 40)

    def test_beam_lengths(self):
        self.assertEqual(self.c.get_x_beam_length(), 520)
        self.assertEqual(self.c.get_y_beam_length(), 320)

    def test_beam_placements_flush_with_posts(self):
        x_y = self.c.get_x_beam_placement()[1]
        y_x = self.c.get_y_beam_placement()[0]
        self.assertAlmostEqual(x_y, -180.0)
        self.assertAlmostEqual(y_x, -280.0)

    def test_beam_spacings(self):
        self.assertEqual(self.c.get_x_beam_spacing(), 360)
        self.assertEqual(self.c.get_y_beam_spacing(), 560)


class TestZLayers(unittest.TestCase):
    def test_two_layers(self):
        c = FramePositionCalculator(600, 400, 500, 40)
        self.assertAlmostEqual(c.get_z_layer_spacing(2), 230.0)
        self.assertEqual(c.get_z_layer_positions(2), [0.0, 230.0, 460.0])

    def test_one_layer(self):
        c = FramePositionCalculator(600, 400, 500, 40)
        self.assertAlmostEqual(c.get_z_layer_spacing(1), 460.0)
        self.assertEqual(c.get_z_layer_positions(1), [0.0, 460.0])

    def test_zero_layers_clamped(self):
        c = FramePositionCalculator(600, 400, 500, 40)
        self.assertAlmostEqual(c.get_z_layer_spacing(0), 460.0)


class TestAllProfiles(unittest.TestCase):
    def test_every_profile_gives_valid_geometry(self):
        for name, p in PROFILES.items():
            ps = p['w']
            c = FramePositionCalculator(600, 400, 500, ps)
            self.assertGreater(c.get_x_beam_length(), 0, name)
            self.assertGreater(c.get_y_beam_length(), 0, name)
            self.assertAlmostEqual(
                2 * ps + c.get_x_beam_length(), 600, msg=name)
            self.assertAlmostEqual(
                2 * ps + c.get_y_beam_length(), 400, msg=name)
            self.assertAlmostEqual(
                c.get_z_layer_spacing(2), (500 - ps) / 2, msg=name)


class TestHoleNotes(unittest.TestCase):
    def test_x_beam_tap_at_end_faces(self):
        note = hole_note(u'X-横梁', 560,
                         {'beam_cross': 'M5', 'post_tap': 'M6'}, 20)
        self.assertIn('M6', note)
        self.assertIn('端1: M6距端面0mm', note)
        self.assertIn('端2: M6距端面560mm', note)

    def test_x_beam_coordinates(self):
        note = hole_note(u'X-横梁', 560,
                         {'beam_cross': 'M5', 'post_tap': 'M6'}, 20)
        self.assertIn('(x=0, y=10, z=10)', note)
        self.assertIn('(x=560, y=10, z=10)', note)

    def test_y_beam_tap_at_end_faces(self):
        note = hole_note(u'Y-纵梁', 360,
                         {'beam_cross': 'M5', 'post_tap': 'M6'}, 20)
        self.assertIn('M6', note)
        self.assertIn('端1: M6距端面0mm', note)
        self.assertIn('端2: M6距端面360mm', note)

    def test_y_beam_coordinates(self):
        note = hole_note(u'Y-纵梁', 360,
                         {'beam_cross': 'M5', 'post_tap': 'M6'}, 20)
        self.assertIn('(x=10, y=0, z=10)', note)
        self.assertIn('(x=10, y=360, z=10)', note)

    def test_z_post_top_bottom_tap(self):
        note = hole_note(u'Z-立柱', 500,
                         {'beam_cross': 'M5', 'post_tap': 'M6'}, 20)
        self.assertIn('M6', note)
        self.assertIn('底部: M5十字通孔 + M6攻丝', note)
        self.assertIn('顶部: M5十字通孔 + M6攻丝', note)

    def test_z_post_default_coordinates(self):
        note = hole_note(u'Z-立柱', 500,
                         {'beam_cross': 'M5', 'post_tap': 'M6'}, 20)
        self.assertIn('(x=10, y=10, z=10)', note)
        self.assertIn('(x=10, y=10, z=490)', note)

    def test_z_post_multi_layer_cross_holes(self):
        calc = FramePositionCalculator(600, 400, 500, 20)
        positions = calc.get_z_layer_positions(2)
        note = hole_note(u'Z-立柱', 500,
                         {'beam_cross': 'M5', 'post_tap': 'M6'}, 20,
                         z_layers=2, z_layer_positions=positions)
        self.assertIn('M5十字通孔', note)
        self.assertIn('第2层: M5十字通孔', note)
        self.assertIn('底部: M5十字通孔 + M6攻丝', note)
        self.assertIn('顶部: M5十字通孔 + M6攻丝', note)
        self.assertIn('z=0)', note)
        self.assertIn('z=240)', note)
        self.assertIn('z=480)', note)

    def test_z_post_single_layer(self):
        calc = FramePositionCalculator(600, 400, 500, 20)
        positions = calc.get_z_layer_positions(1)
        note = hole_note(u'Z-立柱', 500,
                         {'beam_cross': 'M5', 'post_tap': 'M6'}, 20,
                         z_layers=1, z_layer_positions=positions)
        self.assertIn('底部: M5十字通孔 + M6攻丝', note)
        self.assertIn('顶部: M5十字通孔 + M6攻丝', note)
        self.assertNotIn('第', note)

    def test_no_spec_returns_empty(self):
        self.assertEqual(hole_note(u'X-横梁', 560), '')
        self.assertEqual(hole_note(u'X-横梁', 560, {'beam_cross': 'M5'}, 0), '')

    def test_every_core_profile_has_hole_spec(self):
        # Only test core profiles (not DXF-based ones)
        core_profiles = ['20x20', '30x30', '40x40', '60x60']
        for name in core_profiles:
            self.assertIn(name + ' 方管', HOLE_SPECS, name + ' 方管')


class TestBomSummary(unittest.TestCase):
    def test_summary_aggregation(self):
        beams = [
            {'part': 'X', 'profile': '20x20', 'length': 500, 'qty': 2},
            {'part': 'X', 'profile': '20x20', 'length': 500, 'qty': 2},
        ]
        s = get_bom_summary(beams)
        self.assertEqual(s['X (20x20)']['qty'], 4)
        self.assertEqual(s['X (20x20)']['length'], 2000)


if __name__ == '__main__':
    unittest.main()