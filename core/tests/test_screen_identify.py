import unittest
from core import screen_identify


class IdentifyTests(unittest.TestCase):
    def test_identify_only_includes_connected_arrangeable_machines(self):
        layout = dict.fromkeys(['own', 'live', 'offline', 'left-out', 'not-in-use'])
        eligible = screen_identify.eligible_machines(layout, 'own', ['live', 'left-out', 'not-in-use'],
                                                     ['left-out', 'not-in-use'])
        self.assertEqual(eligible, ['own', 'live'])
        self.assertEqual(screen_identify.request(eligible)['identify_labels'], {'own': 'A', 'live': 'B'})

    def test_request_crosses_a_chain_and_cycles_are_deduplicated(self):
        trackers = [screen_identify.Requests() for _ in range(3)]
        message = screen_identify.request(['A', 'B', 'C'])
        for tracker in trackers:
            self.assertTrue(tracker.accept(message))
            self.assertFalse(tracker.accept(message))
            message = screen_identify.relay(message)
        self.assertFalse(trackers[0].accept(message))
        self.assertEqual(message['identify_labels'], {'A': 'A', 'B': 'B', 'C': 'C'})

    def test_invalid_requests_and_exhausted_hops_cannot_relay(self):
        tracker = screen_identify.Requests()
        message = screen_identify.request(['own'])
        self.assertFalse(tracker.accept({**message, 'identify_hops': True}))
        self.assertFalse(tracker.accept({**message, 'identify_labels': {'own': '<script>'}}))
        self.assertIsNone(screen_identify.relay({**message, 'identify_hops': 0}))
