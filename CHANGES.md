# Alias8 – changes

- 2026-11-24: Repo started: README with the planned layout, PLAN.md, CLAUDE.md, MIT license. No script yet.
- 2026-11-24: Phase 1: the `Alias8` script – Live's coloured box (follows the selected track), faders = volume, master fader, bank 1 knobs = Send A / B, top buttons tap = select / hold = arm, bottom buttons tap = mute / hold = solo, track colours on the buttons, bank switching. 18 tests against a fake Live (`tests/`). Not yet tried on hardware.
- 2026-11-24: The encoder scrolls Live's coloured box (press it on the Alias 8 for CC mode, then turn; CC 42 relative, `SCROLL_STEP`). The box now follows only a newly selected track, so scrolling isn't undone. 22 tests.
- 2026-11-24: Encoder scrolling confirmed on Daniel's Alias 8 in Live 12.4.
- 2026-11-24: Phase 2: bank 2 = pan / Send C (`BANK2_SEND`), bank 3 = macros 1-16 of the selected track's first rack with pickup (`MACRO_PICKUP`), unmapped and locked macros skipped, status bar shows the macro and its value. 30 tests. Not yet tried on hardware.
