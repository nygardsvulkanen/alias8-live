# Alias8 – Ableton Live script for the Livid Alias 8

**Work in progress – not usable yet.**

A plug-and-play control surface script that turns a [Livid Alias 8](https://github.com/nygardsvulkanen/livid-editor) into a straightforward Ableton Live 12 mixer controller: track colours on the buttons, select, arm, mute, solo, volume, sends, pan and the selected track's rack macros. No editor setup needed, no naming rules for tracks or racks.

Ableton Live doesn't ship a script for the Alias 8, so this fills the gap. (Looking for the author's full setup with rack conventions and the big-text [Scribble Strip](https://github.com/nygardsvulkanen/scribble-strip) display? That's [alias8-scribble](https://github.com/nygardsvulkanen/alias8-scribble).)

## Planned layout

The buttons and faders do the same thing on every bank, so they stay in muscle memory. Only the knobs change.

| | Every bank |
|---|---|
| Top buttons | **Tap = select track** (track colour, brighter when selected) · **hold = arm** (blinks red) |
| Bottom buttons | **Tap = mute** (dark when muted) · **hold = solo** (blue) |
| Faders | Track volume |
| Master fader | Master volume |

| | Bank 1 | Bank 2 | Bank 3 |
|---|---|---|---|
| Top knobs | Send A | Pan | Selected track's macros 1–8 |
| Bottom knobs | Send B | Send C | Selected track's macros 9–16 |

**Encoder:** turn it to change bank (the display shows the bank). Press it to switch to scroll mode: turning then moves Live's coloured box – which 8 tracks the Alias 8 controls – one track at a time. Press again to go back to changing banks.

Track colours are rounded to the nearest of the Alias 8's seven colours (red, green, yellow, blue, pink, cyan, white). Macros use pickup: a macro only moves once the knob reaches its current value, so nothing jumps.

## Planned installation

1. Download the `Alias8` folder and copy it into `~/Music/Ableton/User Library/Remote Scripts/` (Windows: `Documents\Ableton\User Library\Remote Scripts\`).
2. Restart Live, open **Settings → Link, Tempo & MIDI**, and pick **Control Surface: Alias8**, **Input: Alias 8**, **Output: Alias 8**.

Works with the Alias 8's factory settings. When Live starts, the script sends the controller the few settings it needs (Live controls the button lights; the colour map) – temporarily, nothing is saved, so the Alias 8 is back to normal when you unplug it.

## License

MIT – see `LICENSE`.
