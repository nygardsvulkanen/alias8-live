# Alias8 - Ableton Live 12 control surface script for the Livid Alias 8.
#
# Buttons and faders do the same on every bank (so they stay in muscle memory); only the knobs change:
#   top buttons     tap = select the track, hold = arm
#   bottom buttons  tap = mute, hold = solo
#   faders          track volume; master fader = master volume
#   knobs           per bank, in the order of PAGE_ORDER in settings.py (default: sends, pan, macros):
#     "sends"       Send A (top row) / Send B (bottom row)      (SENDS_PAGE)
#     "pan"         pan / Send C                                (PAN_PAGE_SEND)
#     "macros"      macros 1-8 / 9-16 of the selected track's first rack, with pickup (MACRO_PICKUP)
# The 8 columns are the tracks in Live's coloured box (session highlight). Press the encoder (CC mode) and turn it
# to scroll the box; the box also follows a newly selected track outside it (BOX_FOLLOWS_SELECTION). The script
# reads the encoder's CC and type (absolute / relative) from the Alias 8 and never changes them.
#
# The Alias 8 sends each bank on its own MIDI channel (bank 1 = channel 1 ...). The script moves Live's
# mappings to the bank in use: it hears the Alias 8's bank message, and any control from another bank.

from __future__ import absolute_import, print_function, unicode_literals

import time

from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import MIDI_CC_TYPE, MIDI_NOTE_TYPE
from _Framework.SliderElement import SliderElement
from _Framework.ButtonElement import ButtonElement
from _Framework.SessionComponent import SessionComponent
from _Framework.MixerComponent import MixerComponent

from .colors import OFF, nearest_color, top_led, bottom_led
from .macros import first_rack, macro_param, Pickup
from . import controller
from . import pages, settings
from .settings import (DEBUG, SENDS_PAGE, PAN_PAGE_SEND, HOLD_SECONDS, MACRO_PICKUP, SELECTED_BLINKS, BOX_FOLLOWS_SELECTION, SCROLL_STEP, NUM_TRACKS,
                       KNOB_TOP_CC, KNOB_BOTTOM_CC, FADER_CC, MASTER_CC, BUTTON_TOP_NOTE,
                       BUTTON_BOTTOM_NOTE, ENCODER_CC)

BANK_SYSEX = (240, 0, 1, 97, 11, 113)          # the Alias 8 reports a bank change: + <bank> 247
SET_BANK_SYSEX = (240, 0, 1, 97, 11, 26)       # tell the Alias 8 which bank to show: + <bank> 247
BLINK_TICKS = 4                                # update_display runs about every 100 ms: blink at ~1.25 Hz
SETUP_TIMEOUT_TICKS = 15                       # ~1.5 s per try to answer a question about a setting
SETUP_TRIES = 3                                # then go on without it (factory values for the encoder)


def decode_relative(value):
    """Steps from one relative encoder message. Accepts both common formats: two's complement
    (1-15 forward, 113-127 back) and offset 64 (65-79 forward, 49-63 back). Anything else is ignored."""
    if 1 <= value <= 15:
        return value
    if 113 <= value <= 127:
        return value - 128
    if 49 <= value <= 79:
        return value - 64
    return 0


class Alias8(ControlSurface):

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._pages, problems = pages.page_order(settings.PAGE_ORDER)   # bank N (0-based) shows _pages[N]
        self._num_banks = len(self._pages)            # bank N sends on MIDI channel N
        self._bank = 0
        self._held = {}            # (row, column) -> [time pressed, hold action done]
        self._leds = {}            # (bank, row, column) -> last value sent
        self._tick = 0
        self._last_selected = None   # the selected track last time we looked (the box follows changes only)
        self._pickups = {}           # macro knob (row, column) -> (parameter, Pickup)
        self._awaiting = {}          # the Alias 8 setting we asked about -> ticks left to wait for its answer
        self._queue = []             # settings still to ask about, one at a time
        self._tries = {}             # setting -> how many times we asked
        self._saved = {}             # bank and the buttons' own LED colours from start-up -> put back on disconnect
        self._original = {}          # Alias 8 setting -> its value before we changed it (sent back on disconnect)
        self._enc_cc = ENCODER_CC    # the CC the encoder sends in CC mode (read from the Alias 8)
        self._enc_relative = False   # ... relative steps (True) or absolute 0-127 (False, factory)
        self._enc_last = None        # absolute mode: the last value, to see which way it turned
        self._ready = False          # no button lights until the colour map is sent (else wrong colours at start)
        with self.component_guard():
            self._create_controls()
            self._session = SessionComponent(NUM_TRACKS, 1)
            self._mixer = MixerComponent(NUM_TRACKS)
            self._session.set_mixer(self._mixer)
            self.set_highlighting_session_component(self._session)   # Live's coloured box
            self._assign_bank(0)
        self.schedule_message(2, self._start)
        if problems:
            self.show_message("Alias8: PAGE_ORDER in settings.py - left out %s (use sends, pan, macros; at most 15)"
                              % ", ".join(repr(p) for p in problems))
        else:
            self.show_message("Alias8 connected")

    def _start(self):
        # One question at a time: the Alias 8 is slow, and drops a question when more sysex follows at once.
        # Its bank and button colours first (before we light anything), then the colour map (then the lights).
        self._queue = list(controller.ASK)
        self._ask_next()

    # ------------------------------------------------------------------ controller setup (temporary)
    def _ask_next(self):
        if not self._queue:
            self._send_midi(SET_BANK_SYSEX + (0, 247))     # setup done: start on bank 1
            return
        cmd = self._queue[0]
        self._awaiting = {cmd: SETUP_TIMEOUT_TICKS}
        self._send_midi(controller.request(cmd))

    def _got_setting(self, cmd, current):
        """The Alias 8 told us one of its settings. The encoder's are only read; the colour map is
        replaced (temporarily) if it differs from the script's, and the original is kept for disconnect."""
        self._awaiting.pop(cmd, None)
        self._tries.pop(cmd, None)
        if self._queue and self._queue[0] == cmd:
            self._queue.pop(0)
        self._debug("Alias 8 setting %d = %s" % (cmd, tuple(current) if current is not None else "no answer"))
        if cmd == controller.ENCODER_MAP:
            self._set_encoder_cc(controller.encoder_cc(current or controller.FACTORY[cmd], ENCODER_CC))
        elif cmd == controller.ENCODER_TYPE:
            self._enc_relative = controller.encoder_relative(current or controller.FACTORY[cmd])
            self._enc_last = None
        elif cmd in controller.RESTORED:
            if current is not None:
                self._saved[cmd] = tuple(current)      # put back on disconnect
        elif cmd == controller.COLOR_MAP:
            if current is None or tuple(current) != tuple(controller.SCRIPT_COLOR_MAP):
                if current is not None:
                    self._original.setdefault(cmd, tuple(current))   # sent back on disconnect
                self._send_midi(controller.message(cmd, controller.SCRIPT_COLOR_MAP))
            self._ready = True                         # the colours are right now: light the buttons
            self._refresh_leds(force=True)
        self._ask_next()

    def _check_setup(self):
        for cmd in list(self._awaiting):
            self._awaiting[cmd] -= 1
            if self._awaiting[cmd] > 0:
                continue
            tries = self._tries.get(cmd, 1)
            if tries < controller.TRIES.get(cmd, SETUP_TRIES):                    # ask once more
                self._tries[cmd] = tries + 1
                self._awaiting[cmd] = SETUP_TIMEOUT_TICKS
                self._send_midi(controller.request(cmd))
            else:                                      # still no answer: go on without it
                self._got_setting(cmd, None)

    # ------------------------------------------------------------------ controls
    def _create_controls(self):
        self._knobs_top, self._knobs_bottom, self._faders, self._masters = [], [], [], []
        self._btn_top, self._btn_bottom = [], []
        for bank in range(self._num_banks):
            ch = bank
            self._knobs_top.append([SliderElement(MIDI_CC_TYPE, ch, KNOB_TOP_CC + i) for i in range(NUM_TRACKS)])
            self._knobs_bottom.append([SliderElement(MIDI_CC_TYPE, ch, KNOB_BOTTOM_CC + i) for i in range(NUM_TRACKS)])
            self._faders.append([SliderElement(MIDI_CC_TYPE, ch, FADER_CC + i) for i in range(NUM_TRACKS)])
            self._masters.append(SliderElement(MIDI_CC_TYPE, ch, MASTER_CC))
            self._btn_top.append([ButtonElement(True, MIDI_NOTE_TYPE, ch, BUTTON_TOP_NOTE + i) for i in range(NUM_TRACKS)])
            self._btn_bottom.append([ButtonElement(True, MIDI_NOTE_TYPE, ch, BUTTON_BOTTOM_NOTE + i) for i in range(NUM_TRACKS)])
            for i in range(NUM_TRACKS):
                self._knobs_top[bank][i].add_value_listener(self._make_knob_cb(bank, 0, i))
                self._knobs_bottom[bank][i].add_value_listener(self._make_knob_cb(bank, 1, i))
                self._faders[bank][i].add_value_listener(self._make_bank_cb(bank))
                self._btn_top[bank][i].add_value_listener(self._make_button_cb(bank, 0, i))
                self._btn_bottom[bank][i].add_value_listener(self._make_button_cb(bank, 1, i))
            self._masters[bank].add_value_listener(self._make_bank_cb(bank))
        self._build_encoders(ENCODER_CC)

    def _build_encoders(self, cc):
        """Listen for the encoder's CC mode on this CC. It sends on whatever bank is active, so on all 15 channels."""
        self._enc_cc = cc
        self._encoders = [SliderElement(MIDI_CC_TYPE, ch, cc) for ch in range(15)]
        for enc in self._encoders:
            enc.add_value_listener(self._make_encoder_cb(cc))

    def _set_encoder_cc(self, cc):
        if cc != self._enc_cc:
            with self.component_guard():
                self._build_encoders(cc)

    def _make_encoder_cb(self, cc):
        def cb(value):
            if cc == self._enc_cc:                     # (elements for an earlier CC stay quiet)
                self._on_encoder(value)
        return cb

    def _debug(self, text):
        if DEBUG:
            self.log_message("Alias8 debug: " + text)

    def _on_encoder(self, value):
        self._debug("encoder CC %d value %d (%s), box at track %d" % (
            self._enc_cc, value, "relative" if self._enc_relative else "absolute", self._session.track_offset() + 1))
        if self._enc_relative:
            steps = decode_relative(value)
        else:                                          # absolute: the direction it moved, one track per message
            last, self._enc_last = self._enc_last, value
            if last is None or value == last:
                return
            steps = 1 if value > last else -1
        if steps:
            self._scroll(steps * SCROLL_STEP)

    def _make_bank_cb(self, bank):
        def cb(value):
            # Live only sends the script values of controls it hasn't mapped: a control from another bank
            if bank != self._bank:
                self._set_bank(bank)
        return cb

    def _make_knob_cb(self, bank, row, i):
        def cb(value):
            if bank != self._bank:
                self._set_bank(bank)
            if self._pages[bank] == pages.MACROS:
                self._macro_knob(row * NUM_TRACKS + i + 1, value)
        return cb

    def _make_button_cb(self, bank, row, i):
        def cb(value):
            if bank != self._bank:
                self._set_bank(bank)
            if value:
                self._press(row, i)
            else:
                self._release(row, i)
        return cb

    # ------------------------------------------------------------------ banks
    def handle_sysex(self, midi_bytes):
        if tuple(midi_bytes[:6]) == BANK_SYSEX and len(midi_bytes) == 8:
            self._set_bank(midi_bytes[6])
            return
        if tuple(midi_bytes) == controller.ACK:
            return                                     # the Alias 8 confirming our colour map
        msg = controller.parse(midi_bytes)
        if msg is not None:
            if msg[0] in self._awaiting:               # the answer to our question at start-up
                self._got_setting(*msg)
            return                                     # other settings (e.g. the Livid editor reading them): ignore
        ControlSurface.handle_sysex(self, midi_bytes)

    def _set_bank(self, bank):
        if bank == self._bank:
            return
        self._bank = bank
        self._pickups.clear()                          # macro knobs pick up again on every visit
        with self.component_guard():
            self._assign_bank(bank)
        self._refresh_leds(force=True)
        if bank < self._num_banks:
            self.show_message("Alias8: bank %d - %s" % (bank + 1, pages.TITLES[self._pages[bank]]))
        else:
            self.show_message("Alias8: bank %d isn't used (banks 1-%d)" % (bank + 1, self._num_banks))

    def _assign_bank(self, bank):
        """Map the faders, master fader and knobs of this bank; the other banks' controls are released."""
        used = bank if bank < self._num_banks else None
        page = self._pages[used] if used is not None else None
        for i in range(NUM_TRACKS):
            strip = self._mixer.channel_strip(i)
            strip.set_volume_control(self._faders[used][i] if used is not None else None)
            sends, pan = None, None
            if page == pages.SENDS:
                sends = [None] * max(SENDS_PAGE)
                sends[SENDS_PAGE[0] - 1] = self._knobs_top[used][i]
                sends[SENDS_PAGE[1] - 1] = self._knobs_bottom[used][i]
            elif page == pages.PAN:
                sends = [None] * PAN_PAGE_SEND
                sends[PAN_PAGE_SEND - 1] = self._knobs_bottom[used][i]
                pan = self._knobs_top[used][i]
            strip.set_send_controls(tuple(sends) if sends else None)
            strip.set_pan_control(pan)
            # on a "macros" page the knobs stay unmapped: the script moves the macros itself (_macro_knob)
        self._mixer.master_strip().set_volume_control(self._masters[used] if used is not None else None)

    # ------------------------------------------------------------------ "macros" page
    def _macro_knob(self, n, value):
        """Knob for macro n (1-16) of the selected track's first rack."""
        try:
            track = self.song().view.selected_track
            rack = first_rack(track.devices)
        except Exception:
            return
        if rack is None:
            self.show_message("Alias8: %s has no rack" % track.name)
            return
        param = macro_param(rack, n)
        if param is None or not getattr(param, "is_enabled", True):
            return                                     # nothing mapped to it, or another macro controls it
        key = n
        entry = self._pickups.get(key)
        if entry is None or entry[0] != param:         # another track or rack: start over (== : Live hands out new wrappers)
            entry = (param, Pickup())
            self._pickups[key] = entry
        lo, hi = param.min, param.max
        if MACRO_PICKUP:
            new = entry[1].feed(param.value, lo, hi, value)
        else:
            new = lo + (hi - lo) * value / 127.0
        if new is None:
            self.show_message("Alias8: %s - %s %s (turn to pick up)" % (track.name, param.name, self._value_text(param)))
            return
        param.value = max(lo, min(hi, new))
        self.show_message("Alias8: %s - %s %s" % (track.name, param.name, self._value_text(param)))

    @staticmethod
    def _value_text(param):
        try:
            return param.str_for_value(param.value)
        except Exception:
            return str(int(round(param.value)))

    # ------------------------------------------------------------------ tracks
    def _track(self, i):
        """The track on column i (inside Live's coloured box), or None."""
        try:
            tracks = self.song().visible_tracks
            n = self._session.track_offset() + i
            return tracks[n] if n < len(tracks) else None
        except Exception:
            return None

    def _scroll(self, steps):
        """Move Live's coloured box by some tracks (stops at the first and last track)."""
        try:
            n = len(self.song().visible_tracks)
        except Exception:
            return
        old = self._session.track_offset()
        new = max(0, min(max(0, n - NUM_TRACKS), old + steps))
        if new != old:
            self._session.set_offsets(new, self._session.scene_offset())
            self.show_message("Alias8: tracks %d-%d" % (new + 1, min(n, new + NUM_TRACKS)))
            self._refresh_leds()

    def _follow_selection(self):
        """Move the coloured box so the selected track is inside it."""
        try:
            tracks = list(self.song().visible_tracks)
            sel = self.song().view.selected_track
            if sel == self._last_selected:             # == (not "is"): Live hands out a new wrapper on every read
                return                                 # only a new selection moves the box (scrolling stays put)
            self._last_selected = sel
            if sel not in tracks:
                return                                 # a return, the master, or a track in a folded group
            idx, off = tracks.index(sel), self._session.track_offset()
            if idx < off:
                off = idx
            elif idx >= off + NUM_TRACKS:
                off = idx - NUM_TRACKS + 1
            else:
                return
            self._session.set_offsets(off, self._session.scene_offset())
        except Exception:
            pass

    # ------------------------------------------------------------------ buttons
    def _press(self, row, i):
        self._held[(row, i)] = [time.time(), False]
        t = self._track(i)
        if t is not None and row == 0:
            self.song().view.selected_track = t        # select on press: feels immediate; a hold arms as well
        self._refresh_leds()

    def _release(self, row, i):
        held = self._held.pop((row, i), None)
        t = self._track(i)
        if held is None or held[1] or t is None:
            return                                     # the hold already did its job
        if row == 1:
            t.mute = not t.mute
            self.show_message("Alias8: %s %s" % (t.name, "muted" if t.mute else "unmuted"))
        self._refresh_leds()

    def _check_holds(self):
        now = time.time()
        for (row, i), held in list(self._held.items()):
            if held[1] or now - held[0] < HOLD_SECONDS:
                continue
            held[1] = True
            t = self._track(i)
            if t is None:
                continue
            if row == 0:
                if getattr(t, "can_be_armed", False):
                    t.arm = not t.arm
                    self.show_message("Alias8: %s %s" % (t.name, "armed" if t.arm else "disarmed"))
            else:
                t.solo = not t.solo
                self.show_message("Alias8: %s %s" % (t.name, "soloed" if t.solo else "unsoloed"))
            self._refresh_leds()

    # ------------------------------------------------------------------ lights
    def _refresh_leds(self, force=False):
        if not self._ready:
            return
        blink_on = (self._tick // BLINK_TICKS) % 2 == 0
        try:
            selected = self.song().view.selected_track
        except Exception:
            selected = None
        for i in range(NUM_TRACKS):
            t = self._track(i)
            color = muted = soloed = armed = None
            if t is not None:
                try:
                    color = nearest_color(t.color)
                    muted, soloed = bool(t.mute), bool(t.solo)
                    armed = bool(getattr(t, "can_be_armed", False) and t.arm)
                except Exception:
                    color = None
            top = top_led(color, t is not None and t == selected, armed, blink_on, SELECTED_BLINKS)
            bottom = bottom_led(color, muted, soloed)
            for bank in range(self._num_banks):              # every bank shows the same buttons
                self._led(bank, 0, i, top, force)
                self._led(bank, 1, i, bottom, force)

    def _led(self, bank, row, i, value, force):
        key = (bank, row, i)
        if not force and self._leds.get(key) == value:
            return
        self._leds[key] = value
        (self._btn_top if row == 0 else self._btn_bottom)[bank][i].send_value(value, True)

    def update_display(self):
        ControlSurface.update_display(self)
        self._tick += 1
        if self._awaiting:
            self._check_setup()
        self._check_holds()
        if BOX_FOLLOWS_SELECTION:
            self._follow_selection()
        self._refresh_leds()

    def disconnect(self):
        """Leave the Alias 8 as we found it: its buttons' own colours, its colour map and its bank.
        The colours go out as ordinary LED notes (sysex sent in a burst at shutdown gets lost), computed
        for the colour map that is active right now; the controller keeps them when the map changes back."""
        back = dict(self._original)
        back.update(self._saved)
        self._debug("disconnect: putting back %s" % (back or "nothing (unknown)"))
        active_map = controller.SCRIPT_COLOR_MAP if self._ready else self._original.get(
            controller.COLOR_MAP, controller.SCRIPT_COLOR_MAP)
        for bank in range(self._num_banks):
            colours = controller.bank_leds(self._saved, bank)
            for i in range(NUM_TRACKS):
                for row, buttons in ((0, self._btn_top), (1, self._btn_bottom)):
                    vel = OFF
                    if colours is not None:
                        vel = controller.velocity_for(colours[row * NUM_TRACKS + i], active_map)
                        if vel is None:
                            vel = OFF                  # that colour isn't in the map: dark
                    buttons[bank][i].send_value(vel, True)
        for cmd, data in self._original.items():       # the colour map
            self._send_midi(controller.message(cmd, data))
        saved_bank = self._saved.get(controller.CURRENT_BANK)
        if saved_bank and tuple(saved_bank)[:1] != (self._bank,):
            self._send_midi(controller.message(controller.CURRENT_BANK, saved_bank))   # back to its bank
        ControlSurface.disconnect(self)
