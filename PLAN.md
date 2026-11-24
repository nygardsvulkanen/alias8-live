# Plan – Alias8 (simple, shareable Alias 8 script)

Decided with Daniel on 2026-11-24.

## Goal
Plug in an Alias 8, pick "Alias8" in Live, done. A generic mixer controller anyone can use: no editor setup, no track/rack naming rules, no Scribble Strip. The full personal setup lives on in `alias8-scribble` (script folder `Alias8_Live`); both can be installed side by side.

## Decisions
- **Name in Live / folder:** `Alias8`.
- **Buttons and faders never change with the bank** (muscle memory):
  - top buttons: tap = select track (track colour, the selected track blinks), hold = arm (alternates with red)
  - bottom buttons: tap = mute (dark when muted), hold = solo (blue)
  - faders = track volume, master fader = master volume
- **Knobs per bank:** bank 1 sends A/B · bank 2 pan / send C · bank 3 selected track's rack macros 1–8 / 9–16 (pickup).
- **Encoder:** bank mode by default (turn = bank, factory behaviour, display shows the bank). Pressing the encoder toggles the Alias 8 into CC mode: turn = scroll Live's session box (8 tracks) one track at a time. Press again = back to bank mode.
- **Zero configuration:** works on factory settings. On connect the script sends temporary sysex (not saved): local LED control off for buttons, "any channel" off, the colour map, and the encoder's CC-mode slot (CC 42, relative). Same commands the Livid editor's wizard sends; never "save to device".

## Phases
1. ✅ (2026-11-24, mock-tested) **Skeleton + bank 1:** `_Framework` ControlSurface with SessionComponent (red box, 8 tracks), MixerComponent (volume, sends, master), track colours → nearest Alias colour, select / mute with tap.
2. ✅ (2026-11-24, confirmed on hardware) **Banks 2–3:** pan / send C, rack macros 1–16 with pickup (DeviceComponent or the first rack's macros).
3. ✅ (2026-11-24, confirmed on a factory-reset Alias 8) **Zero config + lights:** connect-time sysex, bank detection (Alias bank sysex / MIDI channel), encoder press → scroll mode, LED polish (blink, dim).
4. **Docs + release:** README with a labelled picture of the Alias 8, short `settings.py` (~10 options), MIT, CHANGES, a zip on GitHub Releases.
5. **Hardware test with Daniel → v1.0.** Until then only tested with a mock Live.

## Reuse from alias8-scribble (copy, don't import)
- `nearest_led_color` (logic.py) and the velocity → colour map (1 red, 4 green, 8 yellow, 16 blue, 32 pink, 64 cyan, 127 white).
- Bank sysex: the Alias 8 sends `F0 00 01 61 0B 71 <bank> F7` on a bank change; set bank with `F0 00 01 61 0B 1A <bank> F7`.
- Pickup logic for macros.
- The connect-time sysex: see the Livid editor's `app/js/wizard.js` ("ableton" template) for exact commands.

## Notes from phase 1
- Buttons are handled by the script (tap/hold), not by MixerComponent: select acts on press (a hold then also arms), mute acts on release (a hold solos instead).
- Faders/knobs use Live's own mapping (MixerComponent); the script moves the mappings to the active bank (bank sysex, or any control arriving on another bank's channel).
- The selected track blinks (the Alias 8 has no brightness levels); armed alternates with red.
- The coloured box follows the selected track (BOX_FOLLOWS_SELECTION) – needed until the encoder can scroll it.
- Encoder scrolling (CC 42 relative, any channel) was moved up from phase 3 on 2026-11-24, when Daniel tried it on hardware. Daniel's Alias 8 (set up with the editor wizard) reports encoder slots (126 bank, 42, 43, 44) all relative. The factory CC-mode number is still unknown: zero config (phase 3) must set it.
- The box follows only a *new* selection, so scrolling away from the selected track isn't undone.
- Phase 2: bank 2 = pan (top) / `BANK2_SEND` (bottom) via MixerComponent. Bank 3 knobs stay unmapped; the script sets the macros itself with pickup (`macros.py`), the selected track's first non-MIDI rack, skipping unmapped (`macros_mapped`) and locked (`is_enabled` False) macros. Pickup restarts when the bank, track or rack changes.
- Zero config, found by diffing the Alias 8's settings dumps in Live's log (wizard setup vs after "defaults (reset)"): only two settings matter. Cmd 34 colour map – factory `0 7 6 5 1 4 3 2`, script needs `0 1 2 3 4 5 6 7`. Cmd 17 – factory `0 0`. **Correction (2026-11-24):** it is the encoder *type* per slot (bit n = slot n relative, else absolute), not the press toggle; the press toggles CC mode on a factory Alias 8 too. Setting the bit made the display show `01` instead of `CC`, so the script no longer touches it (Daniel: follow the user's own Alias 8 configuration). Encoder map (cmd 16: 126 bank, 42/43/44 relative) and local control (cmd 8 = 0) are the same as the factory's. `controller.py` asks for cmds 34, 16 and 17 at start-up. Only the colour map is changed (and sent back on disconnect); the encoder's CC (cmd 16, slot 1) and type (cmd 17) are only read, and the script understands both absolute and relative. Nothing is saved. No answer within ~2 s = assume factory.
- Banks 4–15: nothing is mapped and the status bar says so. Phase 3: maybe send the controller back to bank 3.
- Hold actions were done in phase 1 already (they belong with the buttons).

## Open questions (find out during phase 1–3)
- Factory MIDI map of the Alias 8 (knobs CC 1–16, faders 17–24, master 25, buttons notes 0–15 – confirm with the editor's "Sequential" template).
- Does the encoder press itself send anything the script can see, or only switch mode in the controller?
- Factory colour map: replace it on connect, or map to it?
