# Text dump: `hamtools text`

How to get every script-referenced line of dialogue in readable form, and the tag
notation the dump uses. Tool added 2026-10-09 (Claude Opus 5.5). The output is extracted
game text: it goes to the gitignored `extracted/text/` and must **never** be committed.

```
uv run hamtools text dump              # writes extracted/text/{dialogue.txt,dialogue.json,inserts.txt}
uv run hamtools text show 0x0846cc6b   # decode one stream at a ROM address
```

Both commands refuse a ROM whose SHA1 is not the expected USA dump.

## What it covers

`dump` runs the static walker (`hamtools.events.walk`) from all 148 scene entry scripts,
using the command lengths in [event_scripts.md](event_scripts.md) and the native-call
counts in [event_natives.csv](event_natives.csv). Every show-text command (0x1a/0x1b)
it reaches gives one stream: **3,599 streams**, the same set as the original walk.
It also decodes the **248 entries** of the insert table `0x084aa740`, used by `[word]`
(0xf0) and `[fa]` (0xfa). The table bound is the first word that is not a ROM pointer
(`0x084aab20`), so the count is **likely**. Scripts use index `ff` too; that is the
selected-index fallback described in [text_controls.md](text_controls.md), not an entry.

Not yet covered:
- About 113 show-text-shaped byte patterns outside the walk, and text reached only from
  native code or data tables (the coverage-sweep step).
- Show-text commands `0x080d9762` and `0x080d9772` take their text from a pointer
  register (operand below 0x10), so it is chosen at run time and is not in the dump.
  The switch at `0x080be96d` also has an entry below 0x10 (guess: an unused slot).
- The variant tables used by `f1`, `f6`–`fe` (`0x08465df8` etc.) and RAM inserts
  (`e6`, `e7`, `f2`, `f3`, `f9`) are shown as tags, not resolved.

## Files

- `dialogue.txt`: one entry per stream, sorted by address. The header line is
  `@address  scene <scene.subscene list>  from <first command address> +N more`; the
  text follows and runs until a line ending with an end tag (`[end]`, `[null]`,
  `[end-nowait]`). `#` lines between entries are comments.
- `dialogue.json`: the same streams with every referencing command address.
- `inserts.txt`: the insert table, labelled with the tag index that selects each entry.

`hamtools.text.parse_dump` reads `dialogue.txt` back. For every stream,
`encode(decoded text)` gives back the exact ROM bytes (tested on all 3,599 streams).
The editing workflow below uses this byte-exact codec.

## Notation

- Glyph bytes print as their characters ([glyphs.md](glyphs.md)). Byte 0xe2 (newline)
  is a real line break.
- Any byte without a character or tag prints as `{xx}`. No real stream needs this.
- Encoding also accepts `'`, `"` and `♥` for the game's `’`, `”` and `♡`.
- `[tag xx yy]`: control byte with its operand bytes in hex.

| Tag | Byte | Meaning (details in [text_controls.md](text_controls.md)) |
|---|---|---|
| `[end]` | e0 | wait for A, then end (or return from an insert) |
| `[null]` | 00 | end immediately (alias of e1) |
| `[end-nowait]` | e1 | end immediately |
| newline | e2 | next line |
| `[wait-line]` | e3 | wait for A, then next line |
| `[scroll]` | e4 | next line without waiting |
| `[wait]` | e5 | wait for A in place |
| `[insert-e6]` | e6 | insert RAM text `0x03001f60` (e.g. a name) |
| `[insert-e7]` | e7 | insert RAM text `0x03002b90` |
| `[normal]` `[blue]` `[red]` | e8 e9 ea | text colour |
| `[fast]` `[delay6]` `[delay2]` | eb ec ed | glyph delay 0 / 6 / 2 |
| `[page]` | ee | wait for A, then clear the page |
| `[wait-anim]` | ef | wait for an animation to finish |
| `[word i]` | f0 i | insert entry `i` of table `0x084aa740` |
| `[f1 i]` | f1 i | insert variant entry |
| `[value62 a b]` `[value77 a b]` | f2 / f3 a b | insert a formatted game value |
| `[callback n]` | f4 n | run scene callback `n` (portraits, sounds, …) |
| `[icon n]` | f5 n | inline icon entity |
| `[f6 i]` `[f7 i]` `[f8 i]` | f6–f8 i | insert variant entry |
| `[slot n]` | f9 n | insert pointer-register text |
| `[fa i]` | fa i | insert entry `i` of table `0x084aa740`, transformed |
| `[fb i]` … `[fe i]` | fb–fe i | insert transformed variant entry |
| `[v1]` `[v2]` | ff / 5e | select variant 1 / 2 for the next insert (no operand) |

The tag names are the tool's own; meanings marked likely in text_controls.md stay likely.

## Editing

`hamtools patch build` accepts `[[text]]` entries in a mod's `mod.toml`.
Only the authored replacement and an original-stream hash belong in the public
mod source. Do not include the original dialogue, extracted dumps, or long byte
signatures. Example for the mapped Boss response (this short replacement fits):

```toml
name = "my-dialogue"
enabled = false

[[text]]
address = 0x0846cc6b
expect_sha1 = "ad6dd53ec50851ce5d7ce50592daa9853b4d146e"
text = "[callback 08]Our new line.[end]"
```

The hash covers `read_stream(original_rom, address).raw`, including the end byte.
The whole-ROM USA hash is checked first. `text.encode` and `validate_stream`
reject invalid glyphs/tags, incomplete controls, missing terminators, or bytes
after the first end. End-looking **operand** bytes remain valid. Preserve
scene-specific callbacks and waits when authoring; changing a callback changes
game behavior, not just wording.

Build with `uv run hamtools patch build my-dialogue`. A text-only mod needs no
ARM compiler. The original ROM stays read-only; `.gba` and `.bps` go to `build/`.
The disabled example `patches/boss-text-edit/` contains three fully authored
pages and deliberately exercises relocation. Build it separately from
`sunflower-dialogue`, which claims the same Boss operand.

### Placement and limits

- A replacement no longer than its original stream is written in place, with
  bytes after its new terminator left untouched, when no other known stream
  overlaps the original allocation.
- Longer or overlapping/shared-tail streams move to four-byte-aligned free
  space after compiled mod code, starting at `0x086d0000`. Every distinct direct
  `0x1a`/`0x1b` reference returned by `events.walk(original_rom)` is redirected
  at command + 2, including unaligned operands. The original shared text stays
  intact for other streams. Insert-table streams are also checked for overlaps.
- Code, manual edits, hooks, pointers, allocated text, and redirected operands
  share one conflict check. Allocation skips explicitly claimed free space.
  Duplicate replacements, source mismatches, out-of-ROM writes, exhausted or
  non-`0xff` free space, and overlapping writes fail before final outputs.
- Entry addresses must be direct text-stream addresses from the walker, not
  command addresses or arbitrary ROM strings. Pointer-register commands
  `0x080d9762` and `0x080d9772` cannot be repointed by this feature. Native-only,
  runtime-selected, and insert-table-only text needs separate analysis. An
  incomplete walk (problems or unknown native operands) blocks text builds.
- Coverage follows `events.walk()` automatically as its roots improve. The
  tool can redirect the references the walker knows; it does not prove the
  absence of undiscovered native/data references. Verify edited scenes in the
  emulator, especially while the coverage sweep is still in progress.

### Export only changed streams from an edited dump

Keep the dumped original and an edited copy in the gitignored `extracted/text/`.
Edit the text below an entry header, preserving its `@0x...` address and a
final `[end]`, `[null]`, or `[end-nowait]` tag. Then:

```
uv run hamtools text edits extracted/text/dialogue-edited.txt --out patches/my-dialogue/mod.toml
uv run hamtools patch build my-dialogue
```

The helper compares **encoded bytes** with the verified original, so aliases
that encode identically are not exported. Output is sorted `[[text]]` entries
containing only changed whole streams and their original SHA1 hashes. The
folder name becomes the mod name; exported mods are enabled unless you add
`enabled = false` before the first `[[text]]` entry. Review replacements before
committing: changing one phrase does not remove copied game dialogue elsewhere
in that stream. Commit only text you authored.

All dumped entries must be present by default. Use `--partial` for an
intentional subset; missing entries always mean **leave unchanged**, never
delete. Duplicates, unknown addresses, malformed tags, and missing/end-in-middle
controls are rejected. Existing output needs `--force` to replace it; doing
so replaces the whole file, including any other mod settings. The helper
refuses to overwrite the edited dump or source ROM, including file aliases.

### Layout warnings and playtesting

The builder reads glyph widths from the source ROM, without storing font data
in mod sources. Defaults estimate the observed Boss response: `width = 168`
pixels, `lines = 3`, `spacing = 1`, `font = 0`. Optional fields on `[[text]]`
adjust the estimate only; they do not resize the game's window. `font` may be
0 or 1. Long literal lines and excess unpaced newlines produce warnings, not
automatic wrapping or build errors. `[wait-line]`, `[scroll]`, and `[page]`
pace/reset the line estimate.

Inserted strings, names, values, icons, centering/fixed-width modes, and
scene callbacks can alter layout; inserted widths are excluded and flagged.
Other scenes can have different windows. The estimate cannot replace an
on-screen check. Load the patched ROM and `states/event-sel-boss-base.ss`,
open Boss's Hamha response, advance each page, close it, and check movement,
menus, and another conversation. Human playtesting should also cover room
changes, longer sessions, and scenes containing expanded inserts.
