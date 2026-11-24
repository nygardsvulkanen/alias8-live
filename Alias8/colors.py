# Alias8 – button colours (no Live code here, so it can be tested on its own).
#
# The Alias 8 picks a button's colour from the velocity Live sends it (with the colour map the script
# sets up): 1 red, 4 green, 8 yellow, 16 blue, 32 pink, 64 cyan, 127 white, 0 off.

OFF, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = 0, 1, 4, 8, 16, 32, 64, 127

_HUES = ((0.0, RED), (60.0, YELLOW), (120.0, GREEN), (180.0, CYAN), (240.0, BLUE), (300.0, MAGENTA), (360.0, RED))


def nearest_color(rgb):
    """The closest of the Alias 8's 7 colours to a Live track colour (0xRRGGBB)."""
    r = ((rgb >> 16) & 255) / 255.0
    g = ((rgb >> 8) & 255) / 255.0
    b = (rgb & 255) / 255.0
    mx, mn = max(r, g, b), min(r, g, b)
    if mx < 0.08:
        return OFF
    if (mx - mn) / mx < 0.25:
        return WHITE                     # greys and near-whites
    d = mx - mn
    if mx == r:
        hue = 60.0 * (((g - b) / d) % 6)
    elif mx == g:
        hue = 60.0 * ((b - r) / d + 2)
    else:
        hue = 60.0 * ((r - g) / d + 4)
    if 20.0 <= hue < 40.0:               # oranges lean to yellow only when they're really yellowish
        return RED if hue < 33.0 else YELLOW
    return min(_HUES, key=lambda h: abs(h[0] - hue))[1]


def top_led(color, selected, armed, blink_on, selected_blinks=True):
    """Top button (select / arm): the track colour; the selected track blinks; armed alternates with red."""
    if color is None:
        return OFF                       # no track on this column
    if armed:
        if selected:
            return RED if blink_on else OFF
        return RED if blink_on else color
    if selected and selected_blinks:
        return color if blink_on else OFF
    return color


def bottom_led(color, muted, soloed):
    """Bottom button (mute / solo): the track colour, dark when muted, blue when soloed."""
    if color is None:
        return OFF
    if soloed:
        return BLUE
    if muted:
        return OFF
    return color
