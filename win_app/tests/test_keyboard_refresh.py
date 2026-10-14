import unittest
from unittest.mock import Mock, patch

import capture_win


class KeyboardRefreshTests(unittest.TestCase):
    def test_refresh_is_queued_on_the_hook_thread(self):
        hooks = capture_win.Hooks(Mock(), Mock(), Mock())
        hooks._thread_id = 42
        with patch.object(capture_win, 'user32') as user32:
            hooks.refresh_keyboard()
            user32.PostThreadMessageW.assert_called_once_with(42, capture_win.WM_REFRESH_KEYBOARD, 0, 0)
            user32.SetWindowsHookExW.assert_not_called()

    def test_repair_replaces_only_the_keyboard_hook_and_preserves_held_keys(self):
        hooks = capture_win.Hooks(Mock(), Mock(), Mock())
        hooks._handles = [10, 20]
        keyboard_callback = Mock()
        hooks._callbacks = [keyboard_callback, Mock()]
        hooks._text_keyups_swallowed.add(65)
        with patch.object(capture_win, 'user32') as user32:
            user32.SetWindowsHookExW.return_value = 30
            hooks._refresh_keyboard()
            user32.SetWindowsHookExW.assert_called_once_with(capture_win.WH_KEYBOARD_LL, keyboard_callback, None, 0)
            user32.UnhookWindowsHookEx.assert_called_once_with(10)
        self.assertEqual(hooks._handles, [30, 20])
        self.assertEqual(hooks._text_keyups_swallowed, {65})

    def test_failed_repair_retains_existing_capture(self):
        hooks = capture_win.Hooks(Mock(), Mock(), Mock())
        hooks._handles = [10, 20]
        hooks._callbacks = [Mock(), Mock()]
        with patch.object(capture_win, 'user32') as user32:
            user32.SetWindowsHookExW.return_value = 0
            with self.assertLogs(capture_win.LOGGER, level='ERROR'):
                hooks._refresh_keyboard()
            user32.UnhookWindowsHookEx.assert_not_called()
        self.assertEqual(hooks._handles, [10, 20])
