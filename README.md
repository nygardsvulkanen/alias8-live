# Alias8 – Ableton Live script for the Livid Alias 8

**Work in progress.** Banks 1–3, the buttons, lights and encoder scrolling are written and tested against a simulated Live; encoder scrolling is confirmed on a real Alias 8. Zero configuration (works on a factory-reset Alias 8) is written and waiting for a hardware test. See `PLAN.md`.

A plug-and-play control surface script that turns a [Livid Alias 8](https://github.com/nygardsvulkanen/livid-editor) into a straightforward Ableton Live 12 mixer controller: track colours on the buttons, select, arm, mute, solo, volume, sends, pan and the selected track's rack macros. No editor setup needed, no naming rules for tracks or racks.

Ableton Live doesn't ship a script for the Alias 8, so this fills the gap. (Looking for the author's full setup with rack conventions and the big-text [Scribble Strip](https://github.com/nygardsvulkanen/scribble-strip) display? That's [alias8-scribble](https://github.com/nygardsvulkanen/alias8-scribble).)

## Planned layout

The buttons and faders do the same thing on every bank, so they stay in muscle memory. Only the knobs change.

| | Every bank |
|---|---|
| Top buttons | **Tap = select track** (track colour; the selected track blinks) · **hold = arm** (blinks red) |
| Bottom buttons | **Tap = mute** (dark when muted) · **hold = solo** (blue) |
| Faders | Track volume |
| Master fader | Master volume |

| | Bank 1 | Bank 2 | Bank 3 |
|---|---|---|---|
| Top knobs | Send A | Pan | Selected track's macros 1–8 |
| Bottom knobs | Send B | Send C | Selected track's macros 9–16 |

**Encoder:** turn it to change bank (the display shows the bank). Press it to switch to scroll mode: turning then moves Live's coloured box – which 8 tracks the Alias 8 controls – one track at a time. Press again to go back to changing banks. The box also follows when you select a track outside it in Live.

Track colours are rounded to the nearest of the Alias 8's seven colours (red, green, yellow, blue, pink, cyan, white). Bank 3 controls the macros of the selected track's first rack (an Instrument, Drum or Audio Effect Rack; a MIDI Effect Rack only if there is no other). Macros with nothing mapped to them are skipped. Macros use pickup: a macro only moves once the knob reaches its current value, so nothing jumps – the status bar says "turn to pick up" until then.

## Planned installation

1. Download the `Alias8` folder and copy it into `~/Music/Ableton/User Library/Remote Scripts/` (Windows: `Documents\Ableton\User Library\Remote Scripts\`).
2. Restart Live, open **Settings → Link, Tempo & MIDI**, and pick **Control Surface: Alias8**, **Input: Alias 8**, **Output: Alias 8**.

Works with the Alias 8's factory settings. When Live starts, the script asks the controller for two settings and changes them if needed: the colour map (so track colours come out right) and the encoder press (so it can switch to scroll mode). Nothing is saved in the controller, and the script puts the original values back when it stops, so the Alias 8 is left as it was.

## License

MIT – see `LICENSE`.
