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
    def test_labels_use_native_rectangles_even_when_qt_screen_order_differs(self):
        app = QApplication.instance() or QApplication([])
        identifier = ScreenIdentifier()
        self.addCleanup(identifier.clear)
        tile = dict(x=0,y=0,w=200,h=100,displays={
            '0':dict(x=1080,y=789,w=1920,h=1080),
            '1':dict(x=0,y=0,w=1080,h=2560)})
        with patch('screen_identify.QApplication.screens', return_value=[FakeScreen(),FakeScreen()]), \
                patch('screen_identify.QApplication.platformName', return_value='windows'), \
                patch('win32gui.GetWindowRect', return_value=(0,0,360,160)), \
                patch('win32gui.SetWindowPos') as position:
            identifier.show(tile,'Studio','A')
        self.assertEqual([(call.args[2],call.args[3]) for call in position.call_args_list],
                         [(1860,1249),(360,1200)])

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
