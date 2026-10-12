import ctypes
import sys
from pathlib import Path
from ctypes.wintypes import MSG
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication
from scroll_sink import ScrollSink


class ScrollSinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_direct_precision_messages_forward_fractional_deltas_and_are_consumed(self):
        send = Mock(return_value=True)
        sink = ScrollSink(send)
        for message, delta, expected in [(0x020A, 1, (1/120, 0)),
                                         (0x020E, -40, (0, -1/3)),
                                         (0x024E, -1, (-1/120, 0)),
                                         (0x024F, 40, (0, 1/3))]:
            native = MSG()
            native.message = message
            native.wParam = (delta & 0xffff) << 16
            with patch.object(sink, 'isVisible', return_value=True), patch('scroll_sink.injected_message', return_value=False):
                self.assertEqual(sink.nativeEvent(b'windows_generic_MSG', ctypes.addressof(native)), (True, 0))
            send.assert_called_with(*expected)
        sink.close()

    def test_beamers_own_injected_scroll_is_not_forwarded_again(self):
        send = Mock()
        sink = ScrollSink(send)
        native = MSG()
        native.message = 0x020A
        native.wParam = 120 << 16
        with patch.object(sink, 'isVisible', return_value=True), patch('scroll_sink.injected_message', return_value=True):
            self.assertEqual(sink.nativeEvent(b'windows_generic_MSG', ctypes.addressof(native)), (True, 0))
        send.assert_not_called()
        sink.close()

    def test_returning_home_removes_capture_window_and_timer(self):
        sink = ScrollSink(Mock())
        sink._timer.start()
        sink.set_redirecting(False)
        self.assertFalse(sink.isVisible())
        self.assertFalse(sink._timer.isActive())
        sink.close()

    def test_redirect_signal_activates_capture_and_return_signal_releases_it(self):
        from kvm_bridge_win import WindowsApplication
        window = SimpleNamespace(sender=SimpleNamespace(on_wheel=Mock(), owner='peer', status='Local'),
                                 _label_of=lambda _: 'Other PC', _refresh_tray_state=Mock())
        with patch('scroll_sink.ScrollSink') as factory:
            WindowsApplication._on_redirecting(window, True)
            factory.assert_called_once_with(window.sender.on_wheel, window)
            factory.return_value.set_redirecting.assert_called_with(True)
            WindowsApplication._on_redirecting(window, False)
            factory.return_value.set_redirecting.assert_called_with(False)
