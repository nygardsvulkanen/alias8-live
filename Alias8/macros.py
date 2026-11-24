# Alias8 – rack macros and pickup (no Live imports here, so it can be tested on its own).

MIDI_EFFECT = 4      # Live.Device.DeviceType.midi_effect


def first_rack(devices):
    """The first rack on a track (instrument, drum or audio effect rack); a MIDI Effect Rack only if
    there is no other. None if the track has no rack."""
    midi = None
    for d in devices:
        try:
            if not d.can_have_chains:
                continue
        except AttributeError:
            continue
        if getattr(d, "type", None) == MIDI_EFFECT:
            midi = midi or d
            continue
        return d
    return midi


def macro_param(rack, n):
    """Macro n (1-16) of a rack, or None if the rack has fewer macros or nothing is mapped to it.
    (A rack's parameters: [0] is its on/off switch, [1..16] the macros.)"""
    if rack is None:
        return None
    params = list(rack.parameters)
    if n >= len(params):
        return None
    mapped = getattr(rack, "macros_mapped", None)     # Live 11+: which macros have something mapped
    if mapped is not None and n - 1 < len(mapped) and not mapped[n - 1]:
        return None
    return params[n]


class Pickup(object):
    """Soft takeover: the knob only moves the parameter once it reaches (or passes) the parameter's
    value, then follows every movement. It lets go if the parameter is changed elsewhere (mouse,
    automation, another controller) and picks up again."""

    def __init__(self):
        self.last = None       # the knob's last position (0-127)
        self.caught = False
        self.sent = None       # the value we last gave the parameter

    def feed(self, current, pmin, pmax, value):
        """The new parameter value for knob position `value`, or None while waiting to catch it."""
        span = float(pmax - pmin) or 1.0
        pos = (current - pmin) / span * 127.0
        if self.caught and self.sent is not None and abs(current - self.sent) > span * 0.03:
            self.caught = False                        # changed elsewhere: pick up again
        if not self.caught:
            if abs(value - pos) <= 2 or (self.last is not None and (self.last - pos) * (value - pos) <= 0):
                self.caught = True
        self.last = value
        if self.caught:
            self.sent = pmin + span * value / 127.0
            return self.sent
        return None
