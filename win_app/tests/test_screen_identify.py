import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication
from screen_identify import ScreenIdentifier


class FakeScreen:
    def name(self):
        return 'test'

    def geometry(self):
        return QRect(0, 0, 1920, 1080)


class IdentifyTests(unittest.TestCase):
    def test_repeated_identification_replaces_labels_and_keeps_screen_numbering(self):
        app = QApplication.instance() or QApplication([])
        identifier = ScreenIdentifier()
        self.addCleanup(identifier.clear)
        tile = dict(x=0, y=0, w=200, h=100, displays={
            '0': dict(x=1920, y=0, w=1920, h=1080),
            '1': dict(x=0, y=0, w=1920, h=1080)})
        with patch('screen_identify.QApplication.screens', return_value=[FakeScreen(), FakeScreen()]):
            identifier.show(tile, 'Studio')
            self.assertEqual([w.text() for w in identifier.windows], ['Studio\nScreen 1', 'Studio\nScreen 2'])
            self.assertTrue(all(w.windowFlags() & Qt.WindowType.WindowTransparentForInput for w in identifier.windows))
            self.assertEqual(identifier.timer.interval(), 4000)
            identifier.show(tile, 'Studio')
            self.assertEqual(len(identifier.windows), 2)
        identifier.clear()
        self.assertEqual(identifier.windows, [])
