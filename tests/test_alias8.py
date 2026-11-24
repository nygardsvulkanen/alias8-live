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
        self.assertIs(song.view.selected_track, tracks[2])
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
        self.assertIsNone(strip.sends)                           # bank 2 knobs: not yet
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
        self.assertIs(song.view.selected_track, tracks[6])

    def test_unused_bank(self):
        s, song, tracks, mod = make()
        s.handle_sysex((240, 0, 1, 97, 11, 113, 5, 247))
        self.assertIsNone(s._mixer.channel_strip(0).volume)
        self.assertIn("isn't used", s.messages[-1])

    def test_follows_the_coloured_box(self):
        s, song, tracks, mod = make()
        s._session.set_offsets(2, 0)
        s._btn_top[0][0].receive(127)
        self.assertIs(song.view.selected_track, tracks[2])

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
