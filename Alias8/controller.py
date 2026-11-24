# Alias8 – talking to the Alias 8 about its settings (no Live imports here, so it can be tested on its own).
#
# When Live starts, the script asks the Alias 8 for a few settings.
#   - The colour map is the only one it changes, so track colours come out right. Nothing is saved in the
#     controller ("save to device" is never sent), and the original map is sent back when the script stops.
#   - The encoder settings are only read: the script follows whatever the user set up in the Livid editor
#     (which CC the encoder sends in CC mode, and whether that is absolute or relative).

HEADER = (240, 0, 1, 97, 11)     # Livid (manufacturer 97), Alias 8 (product 11)
REQUEST = 7                      # "request setting <cmd>"

ENCODER_MAP = 16                 # per encoder slot: CC number, mode. Slot 0 = bank mode (CC 126), slot 1 = CC mode
ENCODER_TYPE = 17                # bit n of byte 0: encoder slot n is relative (1) or absolute (0)
COLOR_MAP = 34                   # which colour each velocity range shows

# Velocity ranges 0 / 1-3 / 4-7 / 8-15 / 16-31 / 32-63 / 64-126 / 127 -> off, red, green, yellow, blue,
# pink, cyan, white. (The factory map is 0 7 6 5 1 4 3 2: velocity 1 would show white.)
SCRIPT_COLOR_MAP = (0, 1, 2, 3, 4, 5, 6, 7)

ASK = (COLOR_MAP, ENCODER_MAP, ENCODER_TYPE)     # what the script asks for at start-up
CHANGED = (COLOR_MAP,)                          # what it may change (temporarily)

# If the Alias 8 doesn't answer (it always should), assume the factory values.
FACTORY = {
    COLOR_MAP: (0, 7, 6, 5, 1, 4, 3, 2),
    ENCODER_MAP: (126, 1, 42, 1, 43, 1, 44, 1),
    ENCODER_TYPE: (0, 0),
}


def request(cmd):
    return HEADER + (REQUEST, cmd, 247)


def message(cmd, data):
    return HEADER + (cmd,) + tuple(data) + (247,)


def parse(midi_bytes):
    """(cmd, data) of an Alias 8 settings message, or None."""
    m = tuple(midi_bytes)
    if len(m) < 8 or m[:5] != HEADER or m[-1] != 247:
        return None
    return m[5], m[6:-1]


def wanted(cmd, current):
    """What the script wants for a setting it changes, given what the controller has now."""
    if cmd == COLOR_MAP:
        return SCRIPT_COLOR_MAP
    return tuple(current)


def encoder_cc(encoder_map, default):
    """The CC the encoder sends in CC mode (slot 1 of the encoder map)."""
    try:
        cc = int(encoder_map[2])
    except (IndexError, TypeError, ValueError):
        return default
    return cc if 0 <= cc < 120 else default


def encoder_relative(encoder_type):
    """True if the encoder's CC mode (slot 1) is relative, False if absolute."""
    try:
        return bool(int(encoder_type[0]) & 2)
    except (IndexError, TypeError, ValueError):
        return False
