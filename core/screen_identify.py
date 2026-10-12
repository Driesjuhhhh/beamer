"""Bounded identification broadcasts across a connected desktop mesh."""
import secrets
import time


def machine_tags(machines):
    result = {}
    for index, machine in enumerate(dict.fromkeys(machines)):
        number, tag = index+1, ''
        while number:
            number, digit = divmod(number-1, 26)
            tag = chr(65+digit)+tag
        result[machine] = tag
    return result


def eligible_machines(layout, own, connected, excluded=()):
    connected, excluded = set(connected), set(excluded)
    return [machine for machine in layout if machine not in excluded and
            (machine == own or machine in connected)]


def request(machines=()):
    return {"identify_screens": True, "identify_id": secrets.token_hex(16), "identify_hops": 8,
            "identify_labels": machine_tags(machines)}


class Requests:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.seen = {}

    def accept(self, data):
        if not isinstance(data, dict) or data.get("identify_screens") is not True:
            return False
        labels = data.get("identify_labels", {})
        if (not isinstance(labels, dict) or len(labels) > 64 or
                any(not isinstance(key, str) or len(key) > 64 or not isinstance(tag, str) or
                    not 1 <= len(tag) <= 3 or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for c in tag)
                    for key, tag in labels.items())):
            return False
        ident = data.get("identify_id")
        if ident is None:
            return True
        hops = data.get("identify_hops")
        if (not isinstance(ident, str) or len(ident) != 32 or any(c not in '0123456789abcdef' for c in ident)
                or type(hops) is not int or not 0 <= hops <= 8):
            return False
        now = self.clock()
        self.seen = {key: stamp for key, stamp in self.seen.items() if now-stamp < 60}
        if ident in self.seen:
            return False
        if len(self.seen) >= 128:
            self.seen.pop(next(iter(self.seen)))
        self.seen[ident] = now
        return True


def relay(data):
    if data.get("identify_id") and data.get("identify_hops", 0) > 0:
        return {**data, "identify_hops": data["identify_hops"]-1}
    return None
