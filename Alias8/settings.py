# =====================================================================================================
#  Alias8 – SETTINGS
#
#  You don't have to change anything: the script works with the Alias 8's factory settings.
#  If you do change something, save the file and restart Live (or pick "None" and then "Alias8"
#  again under Settings > Link, Tempo & MIDI > Control Surface).
# =====================================================================================================

# How long a button press must be to count as a hold (seconds).
# Top buttons: tap = select the track, hold = arm it. Bottom buttons: tap = mute, hold = solo.
HOLD_SECONDS = 0.4

# Bank 1: which sends the two knob rows control (1 = Send A, 2 = Send B ...).
BANK1_SENDS = (1, 2)

# Bank 2: the top knobs are pan; the bottom knobs control this send (3 = Send C).
BANK2_SEND = 3

# Bank 3: the 16 knobs are the macros of the selected track's first rack. Pickup: a macro only moves once
# the knob reaches its current value, so nothing jumps (False = the macro jumps to the knob at once).
MACRO_PICKUP = True

# Live's coloured box (the 8 tracks the Alias 8 controls) moves along when you select a track outside it.
BOX_FOLLOWS_SELECTION = True

# Encoder in scroll mode (press it on the Alias 8): how many tracks one click moves the coloured box.
SCROLL_STEP = 1

# The selected track's button blinks (True) or just stays lit in its colour (False).
SELECTED_BLINKS = True


# -----------------------------------------------------------------------------------------------------
# Hardware – the Alias 8's factory layout. Only change these if you changed the controller in the
# Livid editor.
# -----------------------------------------------------------------------------------------------------
NUM_TRACKS = 8
BANK_CHANNELS = (0, 1, 2)        # bank 1, 2, 3 send on MIDI channel 1, 2, 3 (0-based here)
KNOB_TOP_CC = 1                  # top knob row: CC 1-8
KNOB_BOTTOM_CC = 9               # second knob row: CC 9-16
FADER_CC = 17                    # faders 1-8: CC 17-24
MASTER_CC = 25                   # master fader
BUTTON_TOP_NOTE = 0              # top buttons: notes 0-7
BUTTON_BOTTOM_NOTE = 8           # bottom buttons: notes 8-15
ENCODER_CC = 42                  # the encoder after a press (CC mode, relative); it sends on the active bank's channel
