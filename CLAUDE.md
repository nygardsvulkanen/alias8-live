# Alias8 – notes for Claude

Simple, shareable Ableton Live 12 control surface script for the Livid Alias 8 (script folder `Alias8`). Work in progress – see `PLAN.md` for the decided layout and phases.
Owner: Daniel (writes in Swedish; answer in Swedish, keep code/comments/docs in English).

## Related repos (next to this one in ~/Developer)
- `alias8-scribble` – Daniel's full personal script (folder `Alias8_Live`, symlinked into Live's Remote Scripts) + Scribble Strip protocol. Reuse ideas and small helpers from it by copying; never import from it, and never touch Daniel's `Alias8_Live` setup.
- `livid-editor` – the Livid editor; `app/js/wizard.js` has the exact sysex for controller setup.
- `scribble-strip` – not used by this script.

## Installed for Daniel
`~/Music/Ableton/User Library/Remote Scripts/Alias8` is a symlink to `Alias8/` in this repo (his earlier copy is on the Desktop as `Alias8-copy-backup-2026-11-24`). Edits here are live after reloading the script in Live (Control Surface None → Alias8, or restart Live).

## Working rules
- Keep it small and generic: no naming conventions, no personal settings, no UDP/viewer code.
- Buttons and faders must do the same on every bank (muscle memory); only knobs change.
- Never save anything to the controller ("save to device"); connect-time sysex is temporary.
- Every change: a line in `CHANGES.md`, commit.
- Testing: `python3 -m unittest discover tests` (fake Live / `_Framework` in `tests/mock_live.py`) until Daniel tests on hardware. Add a test for every behaviour.
- Layout: `Alias8/Alias8.py` (the script), `Alias8/colors.py` (pure colour logic), `Alias8/macros.py` (first rack, macros, pickup – pure), `Alias8/controller.py` (the temporary Alias 8 settings – pure), `Alias8/settings.py` (user settings + factory MIDI map).
