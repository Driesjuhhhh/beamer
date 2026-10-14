import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from core import protocol, receiver
from core.shared_input import SharedInput

A, B = [protocol.id_text(bytes([n]) * 16) for n in (1, 2)]


class SharedFocusTests(unittest.TestCase):
    def setUp(self):
        self.keys = {A: [], B: []}
        self.focus = {}
        self.known = {A, B}

        def send(source, target, data):
            remote = self.focus[target]
            if 'shared_keyboard' in data:
                read = remote.read_keyboard(source, data['shared_keyboard'], self.known)
                if read:
                    self.keys[target].append(read)
            elif 'shared_shortcut' in data:
                request = data['shared_shortcut']
                if request['focus'] == remote.state and remote.state['driver'] == target:
                    self.focus[A].move_pointer(A if self.focus[A].state['target'] == B else B)
            return True

        def announce(source, data):
            for target, remote in self.focus.items():
                if target != source:
                    remote.accept_focus(source, data['shared_focus'], self.known)

        for own in (A, B):
            self.focus[own] = SharedInput(own, lambda target, data, own=own: send(own, target, data),
                                          lambda data, own=own: announce(own, data), Mock())
        self.focus[A].hello(B, self.focus[B].session)
        self.focus[B].hello(A, self.focus[A].session)

    def test_pointer_pc_restart_can_replace_old_focus_with_a_fresh_revision(self):
        mouse, keyboard = self.focus[A], self.focus[B]
        mouse.claim_pointer(A)
        mouse.move_pointer(B)
        fresh_session = 'a' * 32
        self.assertTrue(keyboard.hello(A, fresh_session))
        self.assertIsNone(keyboard.state)
        self.assertTrue(keyboard.accept_focus(A, dict(driver=A, target=A, revision=1,
                                                    session=fresh_session), self.known))

    def test_keyboard_on_other_pc_follows_crossing_shortcut_and_next_crossing(self):
        mouse, keyboard = self.focus[A], self.focus[B]
        mouse.claim_pointer(A)
        key_down = {'type': 'keydown', 'data': {'key': 'a'}}
        key_up = {'type': 'keyup', 'data': {'key': 'a'}}
        self.assertTrue(keyboard.route_keyboard(key_down))
        self.assertTrue(keyboard.route_keyboard(key_up))
        self.assertEqual([k['type'] for k in self.keys[A]], ['keydown', 'keyup'])
        mouse.move_pointer(B)
        self.assertFalse(keyboard.route_keyboard(key_down))
        self.assertTrue(keyboard.shortcut('toggle'))
        self.assertEqual(mouse.state['driver'], A)
        self.assertEqual(mouse.state['target'], A)
        self.assertTrue(keyboard.route_keyboard(key_down))
        self.assertTrue(keyboard.route_keyboard(key_up))
        mouse.move_pointer(B)
        self.assertFalse(keyboard.route_keyboard(key_down))
        self.assertEqual(len(self.keys[A]), 4)

    def test_held_key_is_released_at_old_target_and_not_replayed_at_new_target(self):
        mouse, keyboard = self.focus[A], self.focus[B]
        mouse.claim_pointer(A)
        keyboard.route_keyboard({'type': 'keydown', 'data': {'key': 'cmd'}})
        mouse.move_pointer(B)
        self.assertTrue(keyboard.route_keyboard({'type': 'keydown', 'data': {'key': 'cmd'}}))
        self.assertTrue(keyboard.route_keyboard({'type': 'keyup', 'data': {'key': 'cmd'}}))
        self.assertEqual(len(self.keys[A]), 1)  # Old-focus key-up was already handled by release().
        self.focus[A].release.assert_called()

    def test_rejects_spoofed_focus_and_malformed_keyboard_messages(self):
        mouse, keyboard = self.focus[A], self.focus[B]
        mouse.claim_pointer(A)
        self.assertFalse(keyboard.accept_focus(B, mouse.state, self.known))
        for message in ({'type': 'mousemove', 'data': {'dx': 1, 'dy': 1}},
                        {'type': 'keydown', 'data': []}):
            self.assertIsNone(mouse.read_keyboard(B, {'focus': mouse.state, 'message': message}, self.known))
        self.assertIsNone(mouse.read_keyboard('unknown', {'focus': mouse.state}, self.known))


class KeyboardFollowerInjectionTests(unittest.TestCase):
    def setUp(self):
        self.server = receiver.LinkResponder.__new__(receiver.LinkResponder)
        self.server._lock = threading.RLock()
        self.server._owner = None
        self.server._unlock = None
        self.server._unlocking = threading.Event()
        self.peer = {'id': B, 'allow_drive': True}
        self.server._settings_now = lambda: ([self.peer], [])
        self.injector = Mock()
        self.server._injector_module = lambda: self.injector

    def test_follower_injects_without_claiming_pointer_and_releases_held_keys(self):
        read = protocol.read_input({'type': 'keydown', 'data': {'key': 'cmd', 'seq': 1}})
        self.server.follow_keyboard(B, read)
        self.assertIsNone(self.server._owner)
        self.injector.inject_key.assert_called_with('cmd', down=True, us=None)
        self.server.release_follow_keyboards()
        self.injector.inject_key.assert_called_with('cmd', down=False, us=None)

    def test_disallowed_or_locked_keyboard_is_not_injected(self):
        read = protocol.read_input({'type': 'keydown', 'data': {'key': 'a', 'seq': 1}})
        self.peer['allow_drive'] = False
        self.server.follow_keyboard(B, read)
        self.peer['allow_drive'] = True
        self.server._unlock = SimpleNamespace(is_locked=lambda: True)
        self.server.follow_keyboard(B, read)
        self.injector.inject_key.assert_not_called()
