# Dialogue and text

Addresses refer to the verified USA AH3E ROM, SHA1
`2525cc23524068dfb3a2b4e0ce7b736f95023e82`.
No original dialogue text or extracted byte streams are stored here.

## Confirmed NPC entry

The human's `states/dialogue-state.ss0` places Hamtaro in front of Boss in the
clubhouse. Press A to open Ham-Chat, then A to choose Hamha; allow the greeting
animation to finish before inspecting Boss's response.

| Address | Meaning | Confidence |
|---|---|---|
| `0x0804ffb6` | Unaligned four-byte event-script operand pointing to Boss's response | confirmed |
| `0x0804ffb4` | Show-text event command `0x1a`, followed by slot `0x00` and the pointer operand | confirmed response path; broader event semantics incomplete |
| `0x0846cc6b` | Start of that response's encoded text/control stream | confirmed |
| `0x0846ccc2` | Final `0xe0` of that response; next stream starts at `0x0846ccc3` | confirmed |

The response occupies `0x58` bytes, including controls. It is read directly from
ROM, without decompression on the observed path. The pointer operand is two bytes
past a four-byte boundary. Aligned-only pointer searches miss it; use an
unaligned search for `0x0846cc6b`. It is a data pointer, so preserve its actual
address rather than applying the Thumb-function bit convention.

Changing the live cursor from `0x0846cc7a` to another existing wait control at
`0x0846cccb`, then pressing A, produced a different passage. Restoring the
savestate undid the experiment. The sunflower mod subsequently redirected the
event operand to our own ROM text and displayed it correctly.

## Finding the live stream in RAM

`gTextStateList` at `0x03000608` is the head pointer for a list of TextState
objects. The list ends at the sentinel `0x03000610`; this is also the head when
there are no allocated text states. Menus use this system too, so a nonempty
list alone does not identify NPC dialogue. Follow each state's `+0x2c` next
pointer and inspect its `+0x10` stream cursor.

In this scene the active dialogue TextState is `0x0202447c`, so its cursor field
is `0x0202448c`. These are scene observations, not addresses to hard-code in mods.
The cursor reached `0x0846cc7a` at the first response wait and `0x0846ccc2` at
the final wait. With the sunflower mod it reached `0x086d0028`, the new stream's
final control. Pressing A there closed the dialogue and returned the head to
`0x03000610`.

`gEventTextState` at `0x030005f0` also points to the dialogue state while this
event owns it; writer `0x0800264c`, clear at `0x08002734`. The ROM-looking word
occasionally found at `0x030005e8` is not the text cursor: runtime writes show
that region being reused for byte-sized event operands.

See [TextState](structs.md#textstate-allocation-size-0x34-likely) for the fields.

## Encoding and controls

This is a custom one-byte glyph/control encoding. Lowercase resembles ASCII,
but complete sentences cannot be treated as ordinary ASCII strings.

| Byte or range | Meaning | Confidence |
|---|---|---|
| `0x01` | Space | confirmed by the sunflower sentence |
| `0x02` through `0x0b` | Digits 0 through 9 | confirmed by labelled local glyph probe |
| `0x0c` through `0x25` | Expected A through Z: ASCII uppercase minus `0x35` | likely for the full range |
| `0x1f` | Capital T | confirmed by the mod |
| `0x61` through `0x7a` | ASCII lowercase glyph values | confirmed for letters displayed in the mod; full range likely |
| `0xca` | Period | confirmed by the mod |
| `0xcb`, `0xcc` | Hyphen, underscore | confirmed by labelled glyph probe |
| `0xcd`, `0xce` | Opening/closing double quote glyphs; helper uses curly double quotes | confirmed by labelled glyph probe |
| `0xcf` | Comma | confirmed by labelled glyph probe |
| `0xd0` | Apostrophe/closing single quote; helper accepts ASCII `'` or `’` | confirmed by full glyph-table probe |
| `0xd1` | Ellipsis `…` (earlier entry called this the apostrophe; corrected) | confirmed by full glyph-table probe |
| `0xd2`, `0xd3` | Opening/closing parentheses | confirmed by labelled glyph probe |
| `0xd4`, `0xd5` | Less-than/greater-than signs | confirmed by labelled glyph probe |
| `0xd6`, `0xd7` | Forward slash/backslash | confirmed by labelled glyph probe |
| `0xd8`, `0xd9` | Exclamation mark, question mark | confirmed by labelled glyph probe |
| `0xe0` | Finish message, wait for input, then close | confirmed by original and patched final waits |
| `0xe1`, also `0x00` | Finish/return from an inserted stream; resume `+0x14` if present | confirmed cursor restoration; static zero-to-e1 dispatch |
| `0xe2` | New line; at the bottom it can wait/scroll | confirmed new line; bottom behavior from static code |
| `0xe3` | Wait for input, then advance/scroll to the next line | confirmed by the original conversation |
| `0xe6` | Insert a dynamic stream from `0x03001f60`, saving the return cursor | confirmed by cursor write/resume trace |
| `0xf4` plus one argument | Invoke a scene callback; `0x08` sets Boss's idle animation in this scene | confirmed callback table read and resulting animation/portrait |

The reader handles `0x5e` separately. Do not assume it is an ordinary printable
ASCII caret. The full glyph table is in [glyphs.md](glyphs.md). Font modes and control
operands are still incompletely mapped.

The earlier portrait-selection label for `0xf4` was too narrow. Callback IDs
depend on the current scene, and the portrait loads through an animation
command. See [portraits.md](portraits.md) for the verified asset pointers and
the optional portrait swap.

## Editable C nodes and dialogue tree

The mapped route is **Clubhouse -> Boss -> Hamha -> response**. Its show-text
command is `0x0804ffb4`, slot `0x00`, with the unaligned text pointer at
`0x0804ffb6`. This identifies one response node; the complete event tree,
conditional routes, choices, and quest-flag behavior are not yet decoded.

`patches/sunflower-dialogue/dialogue.c` names that node and records its binding
in comments. `patches/include/dialogue.h` provides literal text, input waits,
end controls, and scene callback helpers. `tools/hamtools/dialogue.py` expands
authored strings before the patch compiler runs, writing generated source only
under `build/`. It does not extract game dialogue.

The helper accepts the full native alphabet in [glyphs.md](glyphs.md):
letters with accents, digits, punctuation and symbols, plus newline. Characters
outside the font are errors with source positions; raw initializers remain
compatible. Rows there carry their own confidence; every printable row was displayed
by the full-range probe in both font banks.

Each `const u8` array names a stream. Its TOML pointer binding determines which
located event operand reaches it; adjacent arrays do not imply branching.
See [the editable example](../patches/sunflower-dialogue/README.md) for the
syntax, additional wait/scroll lines, and build commands.

## Reader and dispatch

All listed functions are Thumb; their recorded addresses are even.

| Address | Name | Evidence |
|---|---|---|
| `0x080027a8` | `Event_ShowTextAndWait` | Copies the five argument bytes, applies the slot's text-window template, starts text, and waits; observed operand read at `0x08002876` |
| `0x08004258` | `Text_SetString` | Cursor store at `0x0800425c`; observed write PC `0x08004260` |
| `0x08004284` | `Text_CreateState` | Static allocation of `0x34` bytes; observed list insertion at `0x080042b6` |
| `0x08004500` | `Text_DestroyState` | Unlinks/frees a state; observed head update at `0x0800451c` |
| `0x08004548` | `Text_Update` | Reads stream byte at `0x0800462c`, advances glyph cursor at `0x08004772` |
| `0x08004ff4` | `Text_AdvanceLine` | Observed cursor store at `0x0800500c`; increments line position |

The event handler first configures the text state from its window template,
then reads the unaligned pointer byte by byte. The observed operand read
reported PC `0x0800287a`, exact `ldrb` at `0x08002876`, with LR `0x08000d91`
inside `Event_RunCommands` (`0x08000d74`). After TextState status becomes 1,
the handler reports five consumed argument bytes to the event engine.
The neighboring `0x080028e0` handler has a similar text-start/wait path but
does not perform that initial template configuration; it is not the handler
observed reading this response operand.

The event command table starts at `0x08467434` (literal at `0x08000dac`).
Its entry `0x1a`, at `0x0846749c`, is the Thumb pointer `0x080027a9`, matching
the observed handler. The table's total entry count remains unmapped.

Read-watchpoints on the original response and patched final control both report
PC `0x08004630`, corresponding to the Thumb `ldrb` at `0x0800462c`. Cursor
writes after glyphs report `0x08004776`, corresponding to `0x08004772`.
Watchpoint PCs are four bytes ahead of these accessing instructions.

The two dispatch tables contain sixteen Thumb pointers each:

- `0x084677f0`: controls `0xe0` through `0xef`.
- `0x08467830`: controls `0xf0` through `0xff`.

The first group passes the cursor while it still points at the opcode. For the
second group, `Text_Update` advances past the opcode before calling its handler.
Inserting an extra increment would skip the argument.

Ghidra initially split the reader at a false function entry `0x08004590`.
The actual prologue is `0x08004548`, with code continuing through `0x08004817`
around literal pools. The false inner function was removed and the real body
recreated locally. The reader's known caller starts at `0x08000984`.

## Further static candidates

A read-only scout found high densities of the same encoded glyph/control values
in `0x0846a160–0x0846c68f`, `0x0846c9b0–0x0847a96f`,
`0x0847a990–0x0847b50f`, and `0x0847b570–0x084a60cf`.
These boundaries are **guess** level heuristic regions, not proven text-bank
limits or message counts. Only the Boss response above was dynamically located.
Pointer-table candidates at `0x08465514` and `0x084aa740` remain unconfirmed.

## Verified mod and local evidence

`patches/sunflower-dialogue/` contains only our authored sentence and a four-byte
original-pointer check. The build places the new `0x29`-byte stream at
`0x086d0000` and redirects `0x0804ffb6`. The original stream is preserved in
the built image. The stream includes a line break and final wait control.

Initial validation: six pytest tests passed; BPS round-trip checked by the builder;
patched title booted; the complete sentence and normal portrait were visually
checked; final wait/close and another conversation were tested. Local movement
and the Ham-Chat menu were also exercised. Room changes and longer gameplay
remain for human playtesting.

The readable C helper subsequently reproduced the same `0x29`-byte stream and
44 changed bytes. All 64 integrated tests passed, including real ARM builds,
generated-source/include handling, invalid input diagnostics, raw initializer
compatibility, linked control bytes, and BPS round-trips. The fresh helper-built
ROM booted, displayed the full sentence, closed on A, and repeated successfully.

Local-only evidence: `extracted/dialogue-hunt-20261009/`,
`states/dialogue-hunt-*.ss`, `states/sunflower-dialogue-visible.ss`, and
`screenshots/sunflower-dialogue.png`. These paths are gitignored.

Glyph evidence also stays local: `screenshots/dialogue-glyph-probe.png`,
`screenshots/dialogue-punctuation-probe.png`, `screenshots/dialogue-authored-glyphs.png`,
and `extracted/dialogue-hunt-20261009/authored-glyph-test.json`.
