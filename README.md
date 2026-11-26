# Alias8 – Ableton Live script for the Livid Alias 8

A plug-and-play control surface script that turns a Livid Alias 8 into a straightforward Ableton Live 12 mixer controller. It puts track colours on the buttons and gives you select, arm, mute, solo, volume, sends and the selected track's rack macros (and pan, if you want it). No editor setup is needed, and there are no naming rules for tracks or racks.

Ableton Live doesn't ship a script for the Alias 8, so this fills the gap.

Also check out my [Livid editor](https://github.com/nygardsvulkanen/livid-editor).

Tested on macOS with Ableton Live 12.4 and an Alias 8 on factory settings.

## Installation

1. Download the latest `Alias8-v….zip` from [Releases](https://github.com/nygardsvulkanen/alias8-live/releases) and unzip it.
2. Copy the `Alias8` folder into your Remote Scripts folder:
   - macOS: `~/Music/Ableton/User Library/Remote Scripts/`
   - Windows: `Documents\Ableton\User Library\Remote Scripts\`
3. Restart Live.
4. Open **Settings → Link, Tempo & MIDI** and set **Control Surface** to **Alias8**, **Input** to **Alias 8** and **Output** to **Alias 8**.

## Layout

The buttons and faders do the same thing on every bank, so they stay in muscle memory. Only the knobs change.

| | Every bank |
|---|---|
| Top buttons | **Tap = select track** (track colour; the selected track blinks) · **hold = arm** (blinks red) |
| Bottom buttons | **Tap = mute** (dark when muted) · **hold = solo** (blue) |
| Faders | Track volume |
| Master fader | Master volume |

| | Bank 1 · `sends` | Bank 2 · `macros` |
|---|---|---|
| Top knobs | Send A | Selected track's macros 1–8 |
| Bottom knobs | Send B | Selected track's macros 9–16 |

A third page, `pan`, is available but off by default. On it the top knobs control pan and the bottom knobs Send C. A new Live set has only two return tracks, so Send C would do nothing there. To add the page, see Settings below.

**Encoder:**
- Turn it to change bank. The display shows the bank.
- Press it to switch the Alias 8 to CC mode. Turning it then moves Live's coloured box, which shows the 8 tracks the Alias 8 controls, one track at a time.
- Press it again to go back to changing banks.

The box also follows when you select a track outside it in Live.

The script follows your Alias 8's own encoder settings and never changes them. It reads which CC the encoder sends in CC mode, and whether that CC is absolute (the factory setting) or relative.

**Track colours** are rounded to the nearest of the Alias 8's seven colours: red, green, yellow, blue, pink, cyan and white.

**Macros:** the `macros` page controls the macros of the selected track's first rack. That can be an Instrument, Drum or Audio Effect Rack, and a MIDI Effect Rack only if the track has no other. Macros with nothing mapped to them are skipped.

Macros use pickup: a macro only moves once the knob reaches the macro's current value, so nothing jumps. Until then the status bar says "turn to pick up".

## Settings

Everything works without changes. To adjust something, edit `Alias8/settings.py` and restart Live, or switch Control Surface to None and back.

- `PAGE_ORDER` sets which page is on which bank. You can reorder the pages, leave one out or use one twice, up to 15 banks. For example, `PAGE_ORDER = ("sends", "pan", "macros")` adds the pan page on bank 2.
- `SENDS_PAGE` and `PAN_PAGE_SEND` set which sends the pages use.
- Other settings: the hold time, macro pickup, whether the box follows the selection, the scroll step and blinking.

## What it does to your Alias 8

When Live starts, the script reads a few of the controller's settings. The only one it changes is the colour map, so that track colours come out right.

Nothing is saved in the controller: the script never sends "save to device".

When the script stops (Live quits, or Control Surface is set to None), it puts back:
- the original colour map,
- the bank the Alias 8 was on,
- the buttons' own colours.

The controller then looks as it did before Live started. The encoder settings are left exactly as you set them.

## Known limitations

- **Absolute encoder:** with the factory encoder setting, scrolling stops when the encoder reaches the end of its 0–127 range. At the factory speed (8 per click) that is 16 clicks from end to end, so turn back a little if you need to go further. For endless scrolling, set the encoder's CC mode to *relative* in the Livid editor. A lower *Speed A* gives more clicks in absolute mode.
- **Live crashes:** if Live crashes instead of quitting, the controller keeps the script's colour map until you unplug it. It is never saved, so unplugging restores yours.
- **Windows:** not tested yet. It should work, because the script uses only Live's own Python API.

## License

MIT – see `LICENSE`.
