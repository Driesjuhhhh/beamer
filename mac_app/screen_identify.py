"""Temporary screen numbers without taking keyboard focus or intercepting clicks."""
import AppKit
from PyObjCTools import AppHelper
from core import ways
import desktop_mac


class ScreenIdentifier:
    def __init__(self):
        self.windows = []
        self.generation = 0

    def clear(self):
        for window in self.windows:
            window.orderOut_(None)
            window.close()
        self.windows = []

    def show(self, tile, name):
        self.clear()
        self.generation += 1
        generation = self.generation
        ids = desktop_mac.display_ids()
        screens = {int(screen.deviceDescription()['NSScreenNumber']): screen for screen in AppKit.NSScreen.screens()}
        for number, frame in enumerate(ways._display_frames(tile), 1):
            display = frame['display']
            index = int(display) if display and display.isdigit() else number-1
            screen = screens.get(int(ids[index])) if index < len(ids) else None
            if screen is None:
                continue
            bounds = screen.frame()
            rect = AppKit.NSMakeRect(bounds.origin.x+(bounds.size.width-360)/2,
                                    bounds.origin.y+(bounds.size.height-160)/2, 360, 160)
            panel = AppKit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                rect, AppKit.NSWindowStyleMaskBorderless | AppKit.NSWindowStyleMaskNonactivatingPanel,
                AppKit.NSBackingStoreBuffered, False)
            panel.setReleasedWhenClosed_(False)
            panel.setLevel_(AppKit.NSFloatingWindowLevel)
            panel.setIgnoresMouseEvents_(True)
            panel.setCollectionBehavior_(AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
                                         AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary)
            panel.setBackgroundColor_(AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(.09, .10, .12, 1))
            text = AppKit.NSTextField.labelWithString_(f"{name}\nScreen {number}")
            text.setFrame_(AppKit.NSMakeRect(16, 24, 328, 112))
            text.setFont_(AppKit.NSFont.boldSystemFontOfSize_(36))
            text.setTextColor_(AppKit.NSColor.whiteColor())
            text.setAlignment_(AppKit.NSTextAlignmentCenter)
            text.cell().setUsesSingleLineMode_(False)
            text.cell().setWraps_(True)
            panel.contentView().addSubview_(text)
            panel.orderFrontRegardless()
            self.windows.append(panel)
        AppHelper.callLater(4, lambda: self.clear() if generation == self.generation else None)
