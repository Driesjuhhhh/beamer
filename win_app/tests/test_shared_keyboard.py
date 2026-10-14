from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import capture_win
from kvm_bridge_win import WindowsApplication
from links_rig import Rig
from core.tests import test_shared_input as fixtures
A, B = fixtures.A, fixtures.B


class SharedKeyboardShortcutTests(unittest.TestCase):
    def setUp(self):
        fixtures.SharedFocusTests.setUp(self)

    def test_physical_switch_key_on_keyboard_pc_does_not_take_mouse_ownership(self):
        rig = Rig()
        keyboard = self.focus[B]
        rig.sender.keyboard_follow = keyboard.route_keyboard
        rig.sender.keyboard_is_away = lambda: keyboard.keyboard_away
        shell = SimpleNamespace(sender=rig.sender, _trigger=capture_win.Trigger('shift_r'), _shared_input=keyboard)
        self.focus[A].claim_pointer(B)
        for down in (True, False, True, False):
            WindowsApplication._on_hook_key(shell, 'shift_r', down, 0xA1, None)
        self.assertEqual(self.focus[A].state['driver'], A)
        self.assertEqual(self.focus[A].state['target'], A)
        self.assertFalse(rig.sender.redirecting)
        self.assertTrue(WindowsApplication._on_hook_key(shell, 'a', True, 0x41, 'a'))
        self.assertTrue(WindowsApplication._on_hook_key(shell, 'a', False, 0x41, 'a'))
        self.assertEqual([message['key'] for message in self.keys[A]], ['a', 'a'])
        self.focus[A].move_pointer(B)
        self.assertFalse(WindowsApplication._on_hook_key(shell, 'a', True, 0x41, 'a'))
        self.assertFalse(WindowsApplication._on_hook_key(shell, 'a', False, 0x41, 'a'))

    def test_composed_text_and_dead_keys_follow_without_an_owner_take(self):
        rig = Rig()
        rig.sender.keyboard_follow = self.focus[B].route_keyboard
        rig.sender.keyboard_is_away = lambda: self.focus[B].keyboard_away
        self.focus[A].claim_pointer(A)
        self.assertTrue(rig.sender.on_dead_key(0xDE))
        self.assertTrue(rig.sender.on_text('é', 0x45))
        self.assertEqual(self.keys[A][-1]['text'], 'é')
