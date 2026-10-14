"""One pointer destination for keyboards attached to other paired PCs.

Focus and keyboard messages travel on authenticated settings links. Keyboard
followers never take mouse ownership, so they cannot send the pointer home.
"""
import threading
import uuid

from core import protocol


class SharedInput:
    def __init__(self, own, send, announce, release):
        self.own, self.send, self.announce, self.release = own, send, announce, release
        self.state = None
        self.session = uuid.uuid4().hex
        self._sessions = {own: self.session}
        self._revision = 0
        self._held = {}
        self._lock = threading.RLock()

    def claim_pointer(self, target):
        state = self.state
        if state and state['driver'] == self.own and state['target'] == target:
            return
        with self._lock:
            if self.state and self.state['driver'] == self.own and self.state['target'] == target:
                return
            self._revision += 1
            self.state = dict(driver=self.own, target=target, revision=self._revision, session=self.session)
            self.release()
            self.announce({'shared_focus': dict(self.state)})

    def move_pointer(self, target):
        with self._lock:
            if self.state and self.state['driver'] == self.own:
                self.claim_pointer(target)

    def accept_focus(self, peer, state, known):
        if (not isinstance(state, dict) or state.get('driver') != peer or peer not in known
                or not isinstance(state.get('target'), str) or state.get('target') not in known or type(state.get('revision')) is not int
                or not 1 <= state['revision'] <= protocol.MAX_SAFE_INTEGER
                or state.get('session') != self._sessions.get(peer)):
            return False
        with self._lock:
            order = (state['revision'], peer)
            held = (self.state['revision'], self.state['driver']) if self.state else (0, '')
            if order <= held:
                return False
            self._revision = max(self._revision, state['revision'])
            self.state = {key: state[key] for key in ('driver', 'target', 'revision', 'session')}
            self.release()
            return True

    def hello(self, peer, session):
        if not isinstance(session, str) or len(session) != 32 or any(c not in '0123456789abcdef' for c in session):
            return False
        with self._lock:
            previous = self._sessions.get(peer)
            self._sessions[peer] = session
            if previous != session and self.state and self.state['driver'] == peer:
                self.state = None
                self.release()
        return True

    def route_keyboard(self, message):
        """None uses normal driver routing, False stays local, True consumes it."""
        if message.get('type') not in (protocol.MSG_KEYDOWN, protocol.MSG_KEYUP, protocol.MSG_TEXT):
            return None
        with self._lock:
            kind = message['type']
            data = dict(message.get('data', {}))
            key = data.get('key')
            held = self._held.get(key) if key else None
            if kind == protocol.MSG_KEYUP and held:
                self._held.pop(key, None)
                target, state = held
                self.send(target, {'shared_keyboard': dict(focus=state, message=message)})
                return True
            if held and held[1] != self.state:
                return True
            if self.state is None or self.state['driver'] == self.own:
                return None
            target = self.state['target']
            if target == self.own:
                return False
            state = dict(self.state)
            if not self.send(target, {'shared_keyboard': dict(focus=state, message=message)}):
                return False
            if kind == protocol.MSG_KEYDOWN:
                self._held[key] = (target, state)
            return True

    def read_keyboard(self, peer, payload, known):
        with self._lock:
            if (peer not in known or not self.state or self.state['target'] != self.own
                    or not isinstance(payload, dict) or payload.get('focus') != self.state):
                return None
            message = payload.get('message')
            if not isinstance(message, dict) or message.get('type') not in (protocol.MSG_KEYDOWN, protocol.MSG_KEYUP, protocol.MSG_TEXT):
                return None
            if not isinstance(message.get('data'), dict):
                return None
            read = protocol.read_input({**message, 'data': {**message['data'], 'seq': 1}})
            return read if read is not None and read.get('text', '') is not None else None

    def deliver_keyboard(self, peer, payload, known, inject):
        with self._lock:
            read = self.read_keyboard(peer, payload, known)
            if read is not None:
                inject(read)

    def shortcut(self, action):
        with self._lock:
            if self.state is None or self.state['driver'] == self.own:
                return False
            return self.send(self.state['driver'], {'shared_shortcut': dict(focus=dict(self.state), action=action)})

    @property
    def keyboard_away(self):
        with self._lock:
            return bool(self.state and self.state['driver'] != self.own and self.state['target'] != self.own)
