# -*- coding: utf-8 -*-
"""Unit tests for the connection method registry (no FreeCAD needed)."""

import os
import sys
import unittest

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))

from freecad.AlumFrame import connections as c


class TestConnectionMethods(unittest.TestCase):
    def test_order_matches_methods(self):
        for mid in c.METHOD_ORDER:
            self.assertIn(mid, c.METHODS, mid)

    def test_expected_methods_present(self):
        for mid in ('bracket', 'end_tap', 'hidden', 'through_tap', 'anchor',
                    'straight', 'base_plate'):
            self.assertIn(mid, c.METHODS, mid)

    def test_labels_and_hardware(self):
        for mid, meta in c.METHODS.items():
            self.assertTrue(meta.get('label'), mid)
            self.assertIn('hardware', meta, mid)
            self.assertIn('machining', meta, mid)

    def test_joint_hardware_and_params(self):
        hw = c.joint_hardware('bracket')
        self.assertTrue(any(u'\u89d2\u7801' == n for n, _ in hw))
        self.assertEqual(c.joint_hardware('straight'),
                         [(u'\u8fde\u63a5\u68d2', 1)])
        self.assertEqual(c.method_params('hidden')['side_offset'], 18.0)
        self.assertEqual(c.method_params('nonexistent'), {})

    def test_method_label_fallback(self):
        self.assertEqual(c.method_label('nonexistent'), 'nonexistent')


if __name__ == '__main__':
    unittest.main()
