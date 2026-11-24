"""Tests for the Alias8 script against a fake Live (tests/mock_live.py).

Run from the repo root:  python3 -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import mock_live  # noqa: E402

RED_TRACK, GREEN_TRACK, GREY_TRACK = 0xE0201B, 0x3DC300, 0x888888


def make(n_tracks=10):
    tracks = [mock_live.Track("T%d" % (i + 1), (RED_TRACK, GREEN_TRACK, GREY_TRACK)[i % 3]) for i in range(n_tracks)]
    song = mock_live.Song(tracks)
    mock_live.install(song)
    for m in [m for m in sys.modules if m.startswith("Alias8")]:
        del sys.modules[m]
    from Alias8 import create_instance
    from Alias8 import Alias8 as mod
    s = create_instance(None)
    s.run_scheduled()
    return s, song, tracks, sys.modules["Alias8.Alias8"]


RELATIVE = (240, 0, 1, 97, 11, 17, 2, 0, 247)       # the Alias 8 answers: encoder CC mode is relative
ABSOLUTE = (240, 0, 1, 97, 11, 17, 0, 0, 247)       # ... absolute (factory)


class Clock(object):
    def __init__(self, mod):
        self.now = 1000.0
        import types
        mod.time = types.SimpleNamespace(time=lambda: self.now)   # only the script's clock


class TestAlias8(unittest.TestCase):

    def test_bank1_mapping(self):
        s, song, tracks, mod = make()
        for i in range(8):
            strip = s._mixer.channel_strip(i)
            self.assertIs(strip.volume, s._faders[0][i])
            self.assertEqual(strip.sends, (s._knobs_top[0][i], s._knobs_bottom[0][i]))
        self.assertIs(s._mixer.master_strip().volume, s._masters[0])
        self.assertIs(s.highlight, s._session)
        self.assertIn((240, 0, 1, 97, 11, 26, 0, 247), s.midi_out)     # starts the controller on bank 1

    def test_track_colours_on_buttons(self):
        s, song, tracks, mod = make()
        from Alias8.colors import RED, GREEN, WHITE
        self.assertEqual([s._btn_bottom[0][i].sent[-1] for i in range(3)], [RED, GREEN, WHITE])
        self.assertEqual([s._btn_top[1][i].sent[-1] for i in range(3)], [RED, GREEN, WHITE])   # every bank

    def test_fewer_tracks_than_columns(self):
        s, song, tracks, mod = make(n_tracks=5)
        self.assertEqual([s._btn_top[0][i].sent[-1] for i in range(5, 8)], [0, 0, 0])
        s._btn_bottom[0][6].receive(127)
        s._btn_bottom[0][6].receive(0)          # nothing there: no error

    def test_tap_top_selects(self):
        s, song, tracks, mod = make()
        Clock(mod)
        s._btn_top[0][2].receive(127)
        self.assertEqual(song.view.selected_track, tracks[2])
        s._btn_top[0][2].receive(0)
        self.assertFalse(tracks[2].arm)

    def test_hold_top_arms(self):
        s, song, tracks, mod = make()
        clock = Clock(mod)
        s._btn_top[0][1].receive(127)
        clock.now += 0.5
        s.update_display()
        self.assertTrue(tracks[1].arm)
        s._btn_top[0][1].receive(0)
        self.assertTrue(tracks[1].arm)          # release after a hold changes nothing

    def test_hold_top_skips_tracks_that_cant_be_armed(self):
        s, song, tracks, mod = make()
        tracks[0].can_be_armed = False
        clock = Clock(mod)
        s._btn_top[0][0].receive(127)
        clock.now += 0.5
        s.update_display()
        self.assertFalse(tracks[0].arm)

    def test_tap_bottom_mutes_on_release(self):
        s, song, tracks, mod = make()
        clock = Clock(mod)
        s._btn_bottom[0][3].receive(127)
        self.assertFalse(tracks[3].mute)        # not on press: it might become a hold
        clock.now += 0.1
        s._btn_bottom[0][3].receive(0)
        self.assertTrue(tracks[3].mute)
        self.assertEqual(s._btn_bottom[0][3].sent[-1], 0)      # dark when muted

    def test_hold_bottom_solos_without_muting(self):
        s, song, tracks, mod = make()
        clock = Clock(mod)
        s._btn_bottom[0][4].receive(127)
        clock.now += 0.5
        s.update_display()
        s._btn_bottom[0][4].receive(0)
        self.assertTrue(tracks[4].solo)
        self.assertFalse(tracks[4].mute)
        from Alias8.colors import BLUE
        self.assertEqual(s._btn_bottom[0][4].sent[-1], BLUE)

    def test_selected_track_blinks(self):
        s, song, tracks, mod = make()
        song.view.selected_track = tracks[0]
        seen = set()
        for _ in range(12):
            s.update_display()
            seen.add(s._btn_top[0][0].sent[-1])
        from Alias8.colors import RED
        self.assertEqual(seen, {RED, 0})

    def test_bank_change_from_sysex(self):
        s, song, tracks, mod = make()
        s.handle_sysex((240, 0, 1, 97, 11, 113, 1, 247))
        self.assertEqual(s._bank, 1)
        strip = s._mixer.channel_strip(0)
        self.assertIs(strip.volume, s._faders[1][0])            # faders keep doing volume
        self.assertEqual(strip.sends, (None, None, s._knobs_bottom[1][0]))   # bank 2: Send C
        self.assertIs(s._mixer.master_strip().volume, s._masters[1])

    def test_bank_change_from_a_control_on_another_channel(self):
        s, song, tracks, mod = make()
        s._faders[2][5].receive(64)
        self.assertEqual(s._bank, 2)
        self.assertIs(s._mixer.channel_strip(5).volume, s._faders[2][5])

    def test_buttons_work_on_every_bank(self):
        s, song, tracks, mod = make()
        s._btn_top[2][6].receive(127)
        self.assertEqual(s._bank, 2)
        self.assertEqual(song.view.selected_track, tracks[6])

    def test_unused_bank(self):
        s, song, tracks, mod = make()
        s.handle_sysex((240, 0, 1, 97, 11, 113, 5, 247))
        self.assertIsNone(s._mixer.channel_strip(0).volume)
        self.assertIn("isn't used", s.messages[-1])

    def test_follows_the_coloured_box(self):
        s, song, tracks, mod = make()
        s._session.set_offsets(2, 0)
        s._btn_top[0][0].receive(127)
        self.assertEqual(song.view.selected_track, tracks[2])

    def test_box_follows_selected_track(self):
        s, song, tracks, mod = make(n_tracks=20)
        song.view.selected_track = tracks[12]
        s.update_display()
        self.assertEqual(s._session.track_offset(), 5)      # track 13 is now the last column
        song.view.selected_track = tracks[1]
        s.update_display()
        self.assertEqual(s._session.track_offset(), 1)
        song.view.selected_track = tracks[4]
        s.update_display()
        self.assertEqual(s._session.track_offset(), 1)      # already inside: the box stays

    def test_encoder_scrolls_the_box(self):
        s, song, tracks, mod = make(n_tracks=20)
        s.handle_sysex(RELATIVE)
        s._encoders[0].receive(1)                 # one click forward (two's complement)
        self.assertEqual(s._session.track_offset(), 1)
        s._encoders[4].receive(65)                # offset-64 format, on bank 5's channel
        self.assertEqual(s._session.track_offset(), 2)
        s._encoders[0].receive(127)               # one click back
        self.assertEqual(s._session.track_offset(), 1)
        self.assertIn("tracks 2-9", s.messages[-1])
        s._btn_top[0][0].receive(127)
        self.assertEqual(song.view.selected_track, tracks[1])   # the columns follow the box

    def test_encoder_stops_at_the_ends(self):
        s, song, tracks, mod = make(n_tracks=10)
        s.handle_sysex(RELATIVE)
        s._encoders[0].receive(127)
        self.assertEqual(s._session.track_offset(), 0)
        for _ in range(5):
            s._encoders[0].receive(1)
        self.assertEqual(s._session.track_offset(), 2)        # 10 tracks: the last box is tracks 3-10

    def test_scrolling_isnt_undone_by_the_selection(self):
        s, song, tracks, mod = make(n_tracks=20)
        s.handle_sysex(RELATIVE)
        song.view.selected_track = tracks[0]
        s.update_display()
        for _ in range(9):
            s._encoders[0].receive(1)
        s.update_display()
        self.assertEqual(s._session.track_offset(), 9)        # the selected track 1 is outside, the box stays

    def test_scrolling_past_the_selected_track_with_live_wrappers(self):
        # Live returns a new object for selected_track on every read: the box must not snap back to it
        s, song, tracks, mod = make(n_tracks=20)
        s.handle_sysex(RELATIVE)
        song.view.wrap = True
        song.view.selected_track = tracks[0]
        s.update_display()
        offsets = []
        for _ in range(9):
            s._encoders[0].receive(1)
            s.update_display()
            s.update_display()
            offsets.append(s._session.track_offset())
        self.assertEqual(offsets, list(range(1, 10)))           # moved every click, never pulled back

    def test_decode_relative(self):
        from Alias8.Alias8 import decode_relative
        self.assertEqual([decode_relative(v) for v in (0, 1, 3, 127, 125, 64, 65, 63, 30)], [0, 1, 3, -1, -3, 0, 1, -1, 0])

    # ---------------------------------------------------------------- bank 2
    def test_bank2_pan_and_send_c(self):
        s, song, tracks, mod = make()
        s.handle_sysex((240, 0, 1, 97, 11, 113, 1, 247))
        strip = s._mixer.channel_strip(3)
        self.assertIs(strip.pan, s._knobs_top[1][3])
        self.assertEqual(strip.sends, (None, None, s._knobs_bottom[1][3]))
        self.assertIs(strip.volume, s._faders[1][3])
        s.handle_sysex((240, 0, 1, 97, 11, 113, 0, 247))     # back to bank 1: pan released
        self.assertIsNone(strip.pan)

    # ---------------------------------------------------------------- bank 3
    def _bank3(self, devices, mapped=None):
        s, song, tracks, mod = make()
        tracks[0].devices = devices
        song.view.selected_track = tracks[0]
        s.handle_sysex((240, 0, 1, 97, 11, 113, 2, 247))
        strip = s._mixer.channel_strip(0)
        self.assertIsNone(strip.sends)                       # knobs aren't mapped by Live on bank 3
        self.assertIsNone(strip.pan)
        return s, song, tracks

    def test_bank3_macro_with_pickup(self):
        rack = mock_live.Device("Rack", rack=True, values=[64.0] * 16)
        s, song, tracks = self._bank3([mock_live.Device("EQ"), rack])
        knob = s._knobs_top[2][0]                            # macro 1
        knob.receive(10)
        self.assertEqual(rack.parameters[1].value, 64.0)     # far from 64: not picked up yet
        self.assertIn("turn to pick up", s.messages[-1])
        knob.receive(50)
        knob.receive(70)                                     # passed 64: caught
        self.assertAlmostEqual(rack.parameters[1].value, 70.0)
        knob.receive(90)
        self.assertAlmostEqual(rack.parameters[1].value, 90.0)
        self.assertIn("T1 - Macro 1 90", s.messages[-1])

    def test_bank3_bottom_row_is_macros_9_to_16(self):
        rack = mock_live.Device("Rack", rack=True)
        s, song, tracks = self._bank3([rack])
        s._knobs_bottom[2][7].receive(0)                     # macro 16 is at 0: caught at once
        s._knobs_bottom[2][7].receive(5)
        self.assertAlmostEqual(rack.parameters[16].value, 5.0)

    def test_bank3_follows_the_selected_track(self):
        r1 = mock_live.Device("R1", rack=True)
        r2 = mock_live.Device("R2", rack=True, values=[100.0] * 16)
        s, song, tracks = self._bank3([r1])
        tracks[1].devices = [r2]
        s._knobs_top[2][1].receive(0)
        s._knobs_top[2][1].receive(3)
        self.assertAlmostEqual(r1.parameters[2].value, 3.0)
        song.view.selected_track = tracks[1]
        s._knobs_top[2][1].receive(4)
        self.assertEqual(r2.parameters[2].value, 100.0)      # new track: picks up again
        self.assertEqual(r1.parameters[2].value, 3.0)

    def test_bank3_skips_unmapped_and_locked_macros(self):
        rack = mock_live.Device("Rack", rack=True, macros_mapped=[False] + [True] * 15)
        rack.parameters[2].is_enabled = False
        s, song, tracks = self._bank3([rack])
        s._knobs_top[2][0].receive(0); s._knobs_top[2][0].receive(9)
        s._knobs_top[2][1].receive(0); s._knobs_top[2][1].receive(9)
        self.assertEqual(rack.parameters[1].value, 0.0)
        self.assertEqual(rack.parameters[2].value, 0.0)

    def test_bank3_prefers_a_rack_over_a_midi_rack(self):
        midi = mock_live.Device("Arp Rack", rack=True, type=4)
        inst = mock_live.Device("Synth Rack", rack=True)
        s, song, tracks = self._bank3([midi, inst])
        s._knobs_top[2][0].receive(0); s._knobs_top[2][0].receive(8)
        self.assertAlmostEqual(inst.parameters[1].value, 8.0)
        self.assertEqual(midi.parameters[1].value, 0.0)

    def test_bank3_track_without_rack(self):
        s, song, tracks = self._bank3([mock_live.Device("EQ")])
        s._knobs_top[2][0].receive(20)
        self.assertIn("has no rack", s.messages[-1])

    def test_pickup_lets_go_when_changed_elsewhere(self):
        from Alias8.macros import Pickup
        p = Pickup()
        self.assertEqual(p.feed(0.0, 0, 127, 0), 0.0)
        self.assertEqual(p.feed(0.0, 0, 127, 10), 10.0)
        self.assertIsNone(p.feed(100.0, 0, 127, 11))       # someone moved it to 100: wait for the knob

    # ---------------------------------------------------------------- controller setup
    def test_asks_for_the_settings_it_needs(self):
        s, song, tracks, mod = make()
        self.assertIn((240, 0, 1, 97, 11, 7, 34, 247), s.midi_out)
        self.assertIn((240, 0, 1, 97, 11, 7, 17, 247), s.midi_out)
        self.assertIn((240, 0, 1, 97, 11, 7, 16, 247), s.midi_out)

    def test_factory_controller_gets_the_colour_map_only(self):
        s, song, tracks, mod = make()
        self.assertIn((240, 0, 1, 97, 11, 34, 0, 1, 2, 3, 4, 5, 6, 7, 247), s.midi_out)   # sent at start
        s.midi_out = []
        s.handle_sysex((240, 0, 1, 97, 11, 34, 0, 7, 6, 5, 1, 4, 3, 2, 247))   # factory answers
        s.handle_sysex(ABSOLUTE)
        s.handle_sysex((240, 0, 1, 97, 11, 16, 126, 1, 42, 1, 43, 1, 44, 1, 247))
        self.assertEqual(s.midi_out, [])                                       # encoder untouched
        s.disconnect()                                                         # put the colours back
        self.assertEqual([m for m in s.midi_out if m[:5] == (240, 0, 1, 97, 11)],
                         [(240, 0, 1, 97, 11, 34, 0, 7, 6, 5, 1, 4, 3, 2, 247)])

    def test_colour_map_is_sent_before_any_light(self):
        s, song, tracks, mod = make()
        for _ in range(3):
            s.update_display()
        kinds = [e[0] for e in mock_live.LOG]
        first_led = kinds.index("led")
        sent_map = mock_live.LOG.index(("midi", (240, 0, 1, 97, 11, 34, 0, 1, 2, 3, 4, 5, 6, 7, 247)))
        asked = mock_live.LOG.index(("midi", (240, 0, 1, 97, 11, 7, 34, 247)))
        self.assertLess(asked, sent_map)          # ask first, so the answer is still the controller's own map
        self.assertLess(sent_map, first_led)

    def test_no_lights_before_start(self):
        tracks = [mock_live.Track("T1")]
        mock_live.install(mock_live.Song(tracks))
        for m in [m for m in sys.modules if m.startswith("Alias8")]:
            del sys.modules[m]
        from Alias8 import create_instance
        s = create_instance(None)
        s.update_display()                        # Live may refresh before the scheduled start
        self.assertFalse([e for e in mock_live.LOG if e[0] == "led"])

    def test_already_set_up_controller_is_left_alone(self):
        s, song, tracks, mod = make()
        s.midi_out = []
        s.handle_sysex((240, 0, 1, 97, 11, 34, 0, 1, 2, 3, 4, 5, 6, 7, 247))   # set up by the editor wizard
        s.handle_sysex(RELATIVE)
        self.assertEqual(s.midi_out, [])
        s.disconnect()
        self.assertFalse([m for m in s.midi_out if m[:5] == (240, 0, 1, 97, 11)])

    def test_never_changes_the_encoder(self):
        s, song, tracks, mod = make()
        for msg in (ABSOLUTE, RELATIVE, (240, 0, 1, 97, 11, 16, 126, 1, 50, 1, 43, 1, 44, 1, 247)):
            s.handle_sysex(msg)
        for _ in range(25):
            s.update_display()
        s.disconnect()
        self.assertFalse([m for m in s.midi_out if m[:6] in ((240, 0, 1, 97, 11, 16), (240, 0, 1, 97, 11, 17))])

    def test_absolute_encoder_scrolls_by_direction(self):
        s, song, tracks, mod = make(n_tracks=20)
        s.handle_sysex(ABSOLUTE)
        for v in (64, 72, 80, 88):          # turning forward, 8 per click (factory speed)
            s._encoders[0].receive(v)
        self.assertEqual(s._session.track_offset(), 3)       # the first value only sets the start
        s._encoders[0].receive(80)
        self.assertEqual(s._session.track_offset(), 2)
        s._encoders[0].receive(80)                            # no change: nothing
        self.assertEqual(s._session.track_offset(), 2)

    def test_encoder_cc_comes_from_the_controller(self):
        s, song, tracks, mod = make(n_tracks=20)
        s.handle_sysex(RELATIVE)
        s.handle_sysex((240, 0, 1, 97, 11, 16, 126, 1, 50, 1, 43, 1, 44, 1, 247))   # CC mode on CC 50
        self.assertEqual(s._encoders[0].args[2], 50)
        s._encoders[3].receive(1)
        self.assertEqual(s._session.track_offset(), 1)

    def test_no_answer_assumes_factory(self):
        s, song, tracks, mod = make(n_tracks=20)
        self.assertIn((240, 0, 1, 97, 11, 34, 0, 1, 2, 3, 4, 5, 6, 7, 247), s.midi_out)
        for _ in range(25):
            s.update_display()
        self.assertFalse(s._enc_relative)                     # factory: absolute, CC 42
        self.assertEqual(s._enc_cc, 42)
        s.midi_out = []
        s.disconnect()                                        # their map is unknown: nothing to put back
        self.assertFalse([m for m in s.midi_out if m[:6] == (240, 0, 1, 97, 11, 34)])

    def test_later_settings_messages_are_ignored(self):
        s, song, tracks, mod = make()
        s.handle_sysex((240, 0, 1, 97, 11, 34, 0, 1, 2, 3, 4, 5, 6, 7, 247))
        s.handle_sysex(RELATIVE)
        s.handle_sysex((240, 0, 1, 97, 11, 16, 126, 1, 42, 1, 43, 1, 44, 1, 247))
        s.midi_out = []
        s.handle_sysex((240, 0, 1, 97, 11, 34, 0, 7, 6, 5, 1, 4, 3, 2, 247))   # e.g. the editor reading it later
        s.handle_sysex(ABSOLUTE)
        self.assertEqual(s.midi_out, [])
        self.assertTrue(s._enc_relative)

    def test_ack_is_quiet(self):
        s, song, tracks, mod = make()
        s.midi_out = []
        s.handle_sysex((240, 0, 1, 97, 11, 127, 247))
        self.assertEqual(s.midi_out, [])

    def test_debug_is_off_by_default(self):
        from Alias8 import settings
        self.assertFalse(settings.DEBUG)

    def test_disconnect_turns_lights_off(self):
        s, song, tracks, mod = make()
        s.disconnect()
        self.assertEqual(s._btn_top[0][0].sent[-1], 0)
        self.assertEqual(s._btn_bottom[2][7].sent[-1], 0)


class TestColours(unittest.TestCase):

    def test_nearest(self):
        from Alias8.colors import nearest_color, RED, GREEN, BLUE, WHITE, OFF, YELLOW
        self.assertEqual(nearest_color(0xFF0000), RED)
        self.assertEqual(nearest_color(0x00FF00), GREEN)
        self.assertEqual(nearest_color(0x1060FF), BLUE)
        self.assertEqual(nearest_color(0x999999), WHITE)
        self.assertEqual(nearest_color(0x000000), OFF)
        self.assertEqual(nearest_color(0xFFD000), YELLOW)

    def test_top_led_arm_and_select(self):
        from Alias8.colors import top_led, RED, GREEN
        self.assertEqual(top_led(GREEN, False, True, True), RED)
        self.assertEqual(top_led(GREEN, False, True, False), GREEN)
        self.assertEqual(top_led(GREEN, True, True, False), 0)
        self.assertEqual(top_led(GREEN, True, False, True, selected_blinks=False), GREEN)
        self.assertEqual(top_led(None, True, True, True), 0)


if __name__ == "__main__":
    unittest.main()
