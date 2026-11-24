# Alias8 - Ableton Live 12 control surface script for the Livid Alias 8.
#
# Buttons and faders do the same on every bank (so they stay in muscle memory); only the knobs change:
#   top buttons     tap = select the track, hold = arm
#   bottom buttons  tap = mute, hold = solo
#   faders          track volume; master fader = master volume
#   bank 1 knobs    Send A (top row) / Send B (bottom row)      (BANK1_SENDS in settings.py)
#   bank 2, 3       not yet (phase 2: pan / Send C, the selected track's rack macros)
# The 8 columns are the tracks in Live's coloured box (session highlight); it follows the selected track
# (BOX_FOLLOWS_SELECTION) until the encoder can scroll it (phase 3).
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
from .settings import (HOLD_SECONDS, BANK1_SENDS, SELECTED_BLINKS, BOX_FOLLOWS_SELECTION, NUM_TRACKS, BANK_CHANNELS,
                       KNOB_TOP_CC, KNOB_BOTTOM_CC, FADER_CC, MASTER_CC, BUTTON_TOP_NOTE, BUTTON_BOTTOM_NOTE)

NUM_BANKS = len(BANK_CHANNELS)
BANK_SYSEX = (240, 0, 1, 97, 11, 113)          # the Alias 8 reports a bank change: + <bank> 247
SET_BANK_SYSEX = (240, 0, 1, 97, 11, 26)       # tell the Alias 8 which bank to show: + <bank> 247
BLINK_TICKS = 4                                # update_display runs about every 100 ms: blink at ~1.25 Hz


class Alias8(ControlSurface):

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._bank = 0
        self._held = {}            # (row, column) -> [time pressed, hold action done]
        self._leds = {}            # (bank, row, column) -> last value sent
        self._tick = 0
        with self.component_guard():
            self._create_controls()
            self._session = SessionComponent(NUM_TRACKS, 1)
            self._mixer = MixerComponent(NUM_TRACKS)
            self._session.set_mixer(self._mixer)
            self.set_highlighting_session_component(self._session)   # Live's coloured box
            self._assign_bank(0)
        self.schedule_message(2, self._start)
        self.show_message("Alias8 connected")

    def _start(self):
        self._send_midi(SET_BANK_SYSEX + (0, 247))     # start on bank 1
        self._refresh_leds(force=True)

    # ------------------------------------------------------------------ controls
    def _create_controls(self):
        self._knobs_top, self._knobs_bottom, self._faders, self._masters = [], [], [], []
        self._btn_top, self._btn_bottom = [], []
        for bank, ch in enumerate(BANK_CHANNELS):
            self._knobs_top.append([SliderElement(MIDI_CC_TYPE, ch, KNOB_TOP_CC + i) for i in range(NUM_TRACKS)])
            self._knobs_bottom.append([SliderElement(MIDI_CC_TYPE, ch, KNOB_BOTTOM_CC + i) for i in range(NUM_TRACKS)])
            self._faders.append([SliderElement(MIDI_CC_TYPE, ch, FADER_CC + i) for i in range(NUM_TRACKS)])
            self._masters.append(SliderElement(MIDI_CC_TYPE, ch, MASTER_CC))
            self._btn_top.append([ButtonElement(True, MIDI_NOTE_TYPE, ch, BUTTON_TOP_NOTE + i) for i in range(NUM_TRACKS)])
            self._btn_bottom.append([ButtonElement(True, MIDI_NOTE_TYPE, ch, BUTTON_BOTTOM_NOTE + i) for i in range(NUM_TRACKS)])
            for i in range(NUM_TRACKS):
                for el in (self._knobs_top[bank][i], self._knobs_bottom[bank][i], self._faders[bank][i]):
                    el.add_value_listener(self._make_bank_cb(bank))
                self._btn_top[bank][i].add_value_listener(self._make_button_cb(bank, 0, i))
                self._btn_bottom[bank][i].add_value_listener(self._make_button_cb(bank, 1, i))
            self._masters[bank].add_value_listener(self._make_bank_cb(bank))

    def _make_bank_cb(self, bank):
        def cb(value):
            # Live only sends the script values of controls it hasn't mapped: a control from another bank
            if bank != self._bank:
                self._set_bank(bank)
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
        ControlSurface.handle_sysex(self, midi_bytes)

    def _set_bank(self, bank):
        if bank == self._bank:
            return
        self._bank = bank
        with self.component_guard():
            self._assign_bank(bank)
        self._refresh_leds(force=True)
        if bank < NUM_BANKS:
            self.show_message("Alias8: bank %d" % (bank + 1))
        else:
            self.show_message("Alias8: bank %d isn't used (banks 1-%d)" % (bank + 1, NUM_BANKS))

    def _assign_bank(self, bank):
        """Map the faders, master fader and knobs of this bank; the other banks' controls are released."""
        used = bank if bank < NUM_BANKS else None
        for i in range(NUM_TRACKS):
            strip = self._mixer.channel_strip(i)
            strip.set_volume_control(self._faders[used][i] if used is not None else None)
            sends = [None] * max(BANK1_SENDS)
            if used == 0:
                sends[BANK1_SENDS[0] - 1] = self._knobs_top[0][i]
                sends[BANK1_SENDS[1] - 1] = self._knobs_bottom[0][i]
            strip.set_send_controls(tuple(sends) if used == 0 else None)
        self._mixer.master_strip().set_volume_control(self._masters[used] if used is not None else None)

    # ------------------------------------------------------------------ tracks
    def _track(self, i):
        """The track on column i (inside Live's coloured box), or None."""
        try:
            tracks = self.song().visible_tracks
            n = self._session.track_offset() + i
            return tracks[n] if n < len(tracks) else None
        except Exception:
            return None

    def _follow_selection(self):
        """Move the coloured box so the selected track is inside it."""
        try:
            tracks = list(self.song().visible_tracks)
            sel = self.song().view.selected_track
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
            for bank in range(NUM_BANKS):              # every bank shows the same buttons
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
        self._check_holds()
        if BOX_FOLLOWS_SELECTION:
            self._follow_selection()
        self._refresh_leds()

    def disconnect(self):
        for bank in range(NUM_BANKS):
            for i in range(NUM_TRACKS):
                self._btn_top[bank][i].send_value(OFF, True)
                self._btn_bottom[bank][i].send_value(OFF, True)
        ControlSurface.disconnect(self)
