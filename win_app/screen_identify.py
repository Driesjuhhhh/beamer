"""Temporary, non-activating screen numbers matching the Crossing cards."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel
from core import ways
import theme


class ScreenIdentifier:
    def __init__(self, parent=None):
        self.windows = []
        self.timer = QTimer(parent)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.clear)

    def clear(self):
        for window in self.windows:
            window.close()
            window.deleteLater()
        self.windows = []

    def show(self, tile, name):
        self.clear()
        screens = QApplication.screens()
        devices = {}
        try:
            import win32api
            for handle, _dc, rect in win32api.EnumDisplayMonitors():
                devices[tuple(rect)] = win32api.GetMonitorInfo(handle)['Device']
        except ImportError:
            pass
        for number, frame in enumerate(ways._display_frames(tile), 1):
            display = frame['display']
            native = tile.get('displays', {}).get(display)
            target = None
            if native:
                device = devices.get((native['x'], native['y'], native['x']+native['w'], native['y']+native['h']))
                target = next((screen for screen in screens if screen.name() == device), None)
            if target is None:
                index = int(display) if display and display.isdigit() else number-1
                target = screens[index] if index < len(screens) else None
            if target is None:
                continue
            label = QLabel(f"{name}\nScreen {number}")
            label.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                                 Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus |
                                 Qt.WindowType.WindowTransparentForInput)
            label.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFont(theme.font(36, 650))
            label.setStyleSheet('background: #171a20; color: white; border: 2px solid #65d6b2; border-radius: 12px; padding: 20px;')
            label.resize(360, 160)
            center = target.geometry().center()
            label.move(center.x()-180, center.y()-80)
            label.show()
            self.windows.append(label)
        self.timer.start(4000)
