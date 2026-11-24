# Alias8 – the Alias 8 settings the script needs (no Live imports here, so it can be tested on its own).
#
# When Live starts, the script asks the Alias 8 for these settings, remembers them, and sends its own if
# they differ. Nothing is saved in the controller ("save to device" is never sent); when the script stops,
# it sends the remembered values back, so the Alias 8 is left as it was.

HEADER = (240, 0, 1, 97, 11)     # Livid (manufacturer 97), Alias 8 (product 11)
REQUEST = 7                      # "request setting <cmd>"

COLOR_MAP = 34                   # which colour each velocity range shows
ENCODER_STYLE = 17               # bit 2 of the first byte: pressing the encoder toggles bank mode / CC mode

# Velocity ranges 0 / 1-3 / 4-7 / 8-15 / 16-31 / 32-63 / 64-126 / 127 -> off, red, green, yellow, blue,
# pink, cyan, white. (The factory map is 0 7 6 5 1 4 3 2: velocity 1 would show white.)
SCRIPT_COLOR_MAP = (0, 1, 2, 3, 4, 5, 6, 7)

SETTINGS = (COLOR_MAP, ENCODER_STYLE)


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
    """What the script wants for a setting, given what the controller has now."""
    if cmd == COLOR_MAP:
        return SCRIPT_COLOR_MAP
    if cmd == ENCODER_STYLE:
        current = tuple(current) or (0, 0)
        return (current[0] | 2,) + current[1:]
    return tuple(current)


# If the Alias 8 doesn't answer (it always should), assume the factory values.
FACTORY = {COLOR_MAP: (0, 7, 6, 5, 1, 4, 3, 2), ENCODER_STYLE: (0, 0)}
