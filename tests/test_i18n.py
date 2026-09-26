# -*- coding: utf-8 -*-
"""Unit tests for the runtime i18n helper."""

import io
import os
import re
import sys
import unittest

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))

from freecad.AlumFrame import i18n
from freecad.AlumFrame.config import PROFILES


class TestI18n(unittest.TestCase):

    def setUp(self):
        i18n.set_language(None)

    def tearDown(self):
        i18n.set_language(None)

    def test_chinese_is_identity(self):
        i18n.set_language('zh')
        self.assertEqual(i18n.tr(u'新建框架'), u'新建框架')
        self.assertEqual(i18n.tr('plain'), 'plain')

    def test_english_translation(self):
        i18n.set_language('en')
        self.assertEqual(i18n.tr(u'新建框架'), 'New Frame')
        self.assertEqual(i18n.tr(u'铝型材框架'), 'Aluminum Frame')
        # unknown strings fall back to the source
        self.assertEqual(i18n.tr(u'未收录'), u'未收录')

    def test_profile_names_covered(self):
        i18n.set_language('en')
        for key in PROFILES:
            if not any(u'\u4e00' <= ch <= u'\u9fff' for ch in key):
                continue  # ASCII names (E series) need no translation
            self.assertIn(key, i18n._EN)
            self.assertNotEqual(i18n.tr(key), key,
                                'no English name for %s' % key)

    def test_all_tr_sources_are_translated(self):
        i18n.set_language('en')
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pattern = re.compile(r"tr\(\s*u?['\"]([^'\"]+)['\"]\s*\)")
        for name in ('gui.py', 'init_gui.py', 'connections.py', 'bom.py',
                     'frame_builder.py', 'techdraw_bom.py'):
            text = io.open(os.path.join(root, 'freecad', 'AlumFrame', name),
                           encoding='utf-8').read()
            for match in pattern.finditer(text):
                src = match.group(1).replace('\\n', '\n')
                self.assertIn(src, i18n._EN,
                              '%s: missing translation for %r' % (name, src))


if __name__ == '__main__':
    unittest.main()
