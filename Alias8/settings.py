# =====================================================================================================
#  Alias8 – SETTINGS
#
#  You don't have to change anything: the script works with the Alias 8's factory settings.
#  If you do change something, save the file and restart Live (or pick "None" and then "Alias8"
#  again under Settings > Link, Tempo & MIDI > Control Surface).
# =====================================================================================================

# -----------------------------------------------------------------------------------------------------
# PAGES – what the knobs do on each bank. Turn the encoder to change bank.
# The buttons and faders are the same on every bank; only the knobs change.
#
#   "sends"    top knobs = Send A, bottom knobs = Send B   (which sends: SENDS_PAGE below)
#   "pan"      top knobs = pan,    bottom knobs = Send C   (which send: PAN_PAGE_SEND below)
#   "macros"   the 16 knobs = macros 1-16 of the selected track's first rack
#
# Bank 1 is the first page in the list, bank 2 the second, and so on. Reorder them, leave one out, or use
# one twice – up to 15 banks. Examples:
#   PAGE_ORDER = ("sends", "pan", "macros")      add pan on bank 2
#   PAGE_ORDER = ("macros", "sends")             macros on bank 1
# -----------------------------------------------------------------------------------------------------
PAGE_ORDER = ("sends", "macros")

# "sends" page: which sends the two knob rows control (1 = Send A, 2 = Send B ...).
SENDS_PAGE = (1, 2)

# "pan" page: which send the bottom knobs control (3 = Send C).
PAN_PAGE_SEND = 3

# "macros" page: pickup – a macro only moves once the knob reaches its current value, so nothing jumps
# (False = the macro jumps to the knob at once).
MACRO_PICKUP = True


# -----------------------------------------------------------------------------------------------------
# OTHER SETTINGS
# -----------------------------------------------------------------------------------------------------

# How long a button press must be to count as a hold (seconds).
# Top buttons: tap = select the track, hold = arm it. Bottom buttons: tap = mute, hold = solo.
HOLD_SECONDS = 0.4

# Live's coloured box (the 8 tracks the Alias 8 controls) moves along when you select a track outside it.
BOX_FOLLOWS_SELECTION = True

# Encoder in scroll mode (press it on the Alias 8): how many tracks one click moves the coloured box.
SCROLL_STEP = 1

# The selected track's button blinks (True) or just stays lit in its colour (False).
SELECTED_BLINKS = True

# Troubleshooting: True = write what the script sees (encoder, settings from the Alias 8) to Live's Log.txt.
DEBUG = False


# -----------------------------------------------------------------------------------------------------
# Hardware – the Alias 8's factory layout. Only change these if you changed the controller in the
# Livid editor.
# -----------------------------------------------------------------------------------------------------
NUM_TRACKS = 8
# Bank N sends on MIDI channel N (the Alias 8's factory setting); the script follows PAGE_ORDER.
KNOB_TOP_CC = 1                  # top knob row: CC 1-8
KNOB_BOTTOM_CC = 9               # second knob row: CC 9-16
FADER_CC = 17                    # faders 1-8: CC 17-24
MASTER_CC = 25                   # master fader
BUTTON_TOP_NOTE = 0              # top buttons: notes 0-7
BUTTON_BOTTOM_NOTE = 8           # bottom buttons: notes 8-15
ENCODER_CC = 42                  # the encoder after a press (CC mode, relative); it sends on the active bank's channel
