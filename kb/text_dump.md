# Text dump: `hamtools text`

How to get every script-referenced line of dialogue in readable form, and the tag
notation the dump uses. Tool added 2026-10-09 (Claude Opus 5.5). The output is extracted
game text: it goes to the gitignored `extracted/text/` and must **never** be committed.

```
uv run hamtools text dump              # writes rooted dialogue and supplemental inventories
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
- A runtime entry path into the 113 unreached show-text candidates. Their 101 streams
  (83 additional targets) are now in `unreferenced.txt` / `unreferenced.json`, with
  likely script structure and unproven reachability. See [text_coverage.md](text_coverage.md).
- Show-text commands `0x080d9762` and `0x080d9772` take their text from a pointer
  register (operand below 0x10). Native `0x0803b2d0` fills slots 0/1 from RAM pointer
  arrays and sometimes generated RAM text, so their current content is contextual.
  The switch at `0x080be96d` also has an entry below 0x10 (guess: an unused slot).
- RAM inserts (`e6`, `e7`, `f2`, `f3`, `f9`) and runtime transformations of table
  strings remain tags. The stored sources of the five variant table families are
  now exported in `variants.txt` / `variants.json`; see [text_tables.md](text_tables.md).
- Remaining native-rendered menus and embedded item/word records without established
  ROM sources and bounds. Four fixed native tables and seven literal sources are
  exported in `native.txt` / `native.json`; complete UI coverage is not claimed.

## Files

- `dialogue.txt`: one entry per stream, sorted by address. The header line is
  `@address  scene <scene.subscene list>  from <first command address> +N more`; the
  text follows and runs until a line ending with an end tag (`[end]`, `[null]`,
  `[end-nowait]`). `#` lines between entries are comments.
- `dialogue.json`: the same streams with every referencing command address.
- `inserts.txt`: the insert table, labelled with the tag index that selects each entry.
- `unreferenced.txt` / `unreferenced.json`: 101 unique source streams at 113 unreached
  text-shaped sites. JSON preserves every site, overlap with dialogue, and the
  `likely` / `unproven` distinction. These do not change `dialogue.json`'s references.
- `variants.txt` / `variants.json`: 556 distinct stored streams from five insertion
  families, including the empty stream. All 15 logical rows, 14 physical rows,
  651 logical entries, and 569 physical pointer slots are retained. Bounds and
  interpretation are likely; runtime transforms are not applied.
- `native.txt` / `native.json`: 448 distinct stored streams from four bounded native
  tables and seven fixed sources. JSON retains all 518 pointer slots (including
  73 nulls), and 10 literal references, separately from event-command operands.

`hamtools.text.parse_dump` reads `dialogue.txt` back. For every stream,
`encode(decoded text)` gives back the exact ROM bytes (tested on all 3,599 rooted
streams, all 101 candidate streams, all 556 variant streams, and all 448 native streams).
This is the basis for a future editing workflow.

The scene-pointer array has **11 slots**, ending at `0x08466970`, where descriptors
begin. Correcting the older 12-slot bound leaves the 148 unique roots unchanged.
The separate inventories are extraction outputs; Step 4 does not add editing or
reinsertion support for them.

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
