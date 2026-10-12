"""Catch directly delivered Precision Touchpad scrolling while input is away.

The mouse hook consumes ordinary wheel events. Precision scrolling can instead
be delivered to the hit-tested window, so place a non-activating window at the
pinned pointer and forward only the wheel messages that actually reach it.
"""
import ctypes
from ctypes.wintypes import MSG

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter
from PySide6.QtWidgets import QWidget
from input_injector import INJECTED_MARK

WHEEL_MESSAGES = (0x020A, 0x020E, 0x024E, 0x024F)


def injected_message():
    get_info = ctypes.windll.user32.GetMessageExtraInfo
    get_info.restype = ctypes.c_size_t
    return get_info() == INJECTED_MARK


def wheel_delta(message, wparam):
    delta = ctypes.c_short((int(wparam) >> 16) & 0xffff).value / 120.0
    return (delta, 0.0) if message in (0x020A, 0x024E) else (0.0, delta)


class ScrollSink(QWidget):
    def __init__(self, on_wheel, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self._on_wheel = on_wheel
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet('background-color: rgba(0, 0, 0, 1);')
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._follow_pin)

    def _follow_pin(self):
        point = QCursor.pos()
        self.setGeometry(point.x() - 32, point.y() - 32, 64, 64)

    def set_redirecting(self, away):
        if away:
            self._follow_pin()
            self.show()
            self.raise_()
            self._timer.start()
        else:
            self._timer.stop()
            self.hide()

    def nativeEvent(self, event_type, message):
        if self.isVisible():
            event = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
            if event.message in WHEEL_MESSAGES:
                if injected_message():
                    return True, 0
                self._on_wheel(*wheel_delta(event.message, event.wParam))
                return True, 0
        return super().nativeEvent(event_type, message)

    def paintEvent(self, event):
        # Alpha zero would remove the layered window from Windows hit testing.
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))

    def wheelEvent(self, event):
        # Qt fallback for platforms/drivers that translate before nativeEvent.
        delta = event.angleDelta()
        self._on_wheel(delta.y() / 120.0, delta.x() / 120.0)
        event.accept()
