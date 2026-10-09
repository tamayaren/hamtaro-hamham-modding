# Text control bytes

Static mapping by Codex (2026-10-09), then emulator-verified by Claude the same day,
for the USA AH3E ROM with SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`.
**Byte lengths of every control used in game text are confirmed**; see
[Verification](#verification). Behaviour descriptions in the tables below remain
**likely** unless the verification section says otherwise.

Sources: the existing local exports
`extracted/glyph-hunt-20261009/decompile-controls.txt`, `font-reader.txt`, and
`reader-tables.json`; read-only ROM literal-pool resolution; existing
[dialogue.md](dialogue.md) and [structs.md](structs.md). The already-exported
`extracted/dialogue-hunt-20261009/reader-disasm.txt` and
`reader-decompile.txt` clarify the line helpers' cursor advances;
`text-portrait-controls.txt` supplies existing wait-indicator/scroll evidence.
No extracted dialogue, graphics, byte dumps, or decompiled code are reproduced here.

## Priority: controls for all-glyph pages

- **Delay zero:** `0xeb`, handler `0x08005268`, one byte. Sets TextState
  `+0x05 = 0` for subsequent glyphs.
- **Nonwaiting line advance/scroll:** `0xe4`, handler `0x0800516c`, one byte.
  It still yields the reader for this update.
- **Wait then clear page:** `0xee`, handler `0x080052c0`, one byte.
  `0xed` is instead the two-tick glyph-delay setter at `0x0800529c`.
- **Bank selection:** no safe stream-only selector is established by these
  exports. The direct renderer selects bank zero with TextState `+0x0b`
  bit `0x08` clear, and bank one with that bit set. None of the 32 handlers
  directly toggles it. Parent-owned state setup can select the bank while
  preserving other flag bits; `0x5e` and `0xff` choose substitution variants,
  not a proven persistent font bank.

The parent independently decoded 512 glyphs in two 256-slot banks, each glyph
16 by 16 pixels in 64 bytes of packed 2bpp data, with private bank atlases under
`extracted/glyph-hunt-20261009/`. This document records dispatch reachability;
the parent owns the character assignments and narrow/normal atlas labels.

## Reading the notation

`OP b` means a control followed by one unsigned byte. Counts include the opcode.
`C` is TextState's stream cursor (`+0x10`); `R` is its single saved return cursor
(`+0x14`). `next` means the first byte after this control's complete encoding.
`continue` means the reader can process another byte in the same update; `yield`
means it stops processing this state for that update. A yield is not necessarily
an input wait.

`M` is the global substitution-variant byte at `0x03000646`. A table operand
written `i` means `b`, except that `b = 0xff` is replaced by the byte at
`0x02003999` for the handlers explicitly marked `i`. This is a selected-index
fallback, not a terminator or extra opcode inside the operand. Its game meaning
and valid bounds are unknown. `slot` in `0xf9` instead means `b & 0x0f`, with
no such fallback.

Names in the handler column are proposed descriptive names unless already
present in the knowledge base. Addresses are exact **even Thumb addresses**;
dispatch-table function pointers have bit zero set.

## Byte classification and cursor ownership

| Byte at the reader cursor | Classification | Cursor passed to handler |
|---|---|---|
| `0x00` | Alias for `0xe1`, end or return; no glyph | Still points to `0x00` |
| `0x01`–`0x5d`, `0x5f`–`0xdf` | Direct glyph; font slot is byte minus one, plus `0x100` for alternate font | Glyph path consumes one byte |
| `0x5e` | Special substitution prefix | Reader consumes prefix; handler sees following byte |
| `0xe0`–`0xef` | Sixteen controls via table `0x084677f0` | Still points to opcode; handler or line helper must advance it |
| `0xf0`–`0xff` | Sixteen controls via table `0x08467830` | Reader already consumed opcode; handler sees first operand or next control |

This distinction matters particularly for `0xff`: it has **no consumed
operand**, even though its handler reads the next byte. That byte is lookahead
and is dispatched normally afterward. The same is true of `0x5e`.

## State and global fields used below

These are local descriptive field names, with likely confidence. Offsets are
relative to the TextState object, not fixed RAM addresses. The writes column
lists direct writes and identified line/flush helper effects; unexported callees
can have additional effects.

| Offset | Size | Description |
|---|---|---|
| `+0x00` | u8 | Status: `1` inactive, `2` scrolling, `3` reading, `4` glyph delay; high bit bypasses glyph delay |
| `+0x01`, `+0x02` | u8 each | Text width and height in tiles; visible line count is height divided by two |
| `+0x03` | u8 | Starting horizontal position; `0xff` requests centering through helper `0x08005fa4` |
| `+0x04` | u8 | Glyph spacing; low seven bits are spacing/cell width, high bit selects fixed-width centered cells |
| `+0x05`, `+0x06` | u8 each | Configured glyph delay and remaining delay |
| `+0x07` | u8 | Glyph palette quartet / background fill group; renderer uses its low two bits |
| `+0x08` | u8 | Remaining automatic line advances before a bottom-of-window wait |
| `+0x09` | u8 | Line limit compared against `+0x1e` |
| `+0x0a` | u8 | Allocation mask for inline entities |
| `+0x0b` | u8 | Flags: `0x04` requests clearing the working glyph buffer on next update; `0x08` selects alternate font |
| `+0x0c` | pointer | Rendered tile destination |
| `+0x10`, `+0x14` | pointer each | `C`, current stream, and `R`, inserted-stream return location |
| `+0x18` | pointer | Working glyph buffer |
| `+0x1c`, `+0x1e` | u16 each | Horizontal pixel position and logical line index |
| `+0x20` | u16 | First logical line of the currently displayed window, used by page clear |
| `+0x30` | pointer | Window template; inline entities use its signed coordinates at `+0x20`, `+0x22` |

Useful global addresses resolved from literal pools:

| Address | Interpretation |
|---|---|
| `0x03000645` | Pending glyph-buffer flush flag; drawing sets it, helper `0x080049f0` clears it |
| `0x03000646` | `M`, substitution-variant selector; not TextState's font bit |
| `0x03000648` | Generated insertion stream used by `0xf2` and `0xf3` |
| `0x03001fa0` | u16 accepted-input latch written at start of `Text_Update` by helper `0x08009754(3, 1)`; waits test nonzero |
| `0x03002d88` | Pointer to the entity array; entity stride is `0x68` |
| `0x03001f9c` | Entity index consulted by `0xef` |
| `0x03001f6c` | Animation pointer compared by `0xef`; zero disables that wait |

Input-wait controls use entity zero's `+0x60` as the wait-indicator active flag;
they initialize the indicator through `0x08004ecc` when needed and clear its
flag on accepted input. They also call `0x080e4188` with `0x00000145` on acceptance;
the supplied exports do not establish that helper's complete effect.

## Controls `0xe0`–`0xef`

Every entry occupies **one byte** and has no inline operands. Several hold the
cursor on that byte until a condition is met. `Flush` means helper
`0x080049f0`: when delay is zero or bypassed, it copies the current working
glyph line into the destination and clears the pending-flush flag. It does not
clear the page.

| Opcode / layout | Handler, even Thumb address | Effect and cursor behavior | State fields / other writes | Confidence |
|---|---|---|---|---|
| `0xe0` (1 byte) | `Text_CtrlEndWait`, `0x08004f34` | Wait for input. With `R = 0`, flush pending work and set status inactive on acceptance; `C` stays on the end byte and yields. With `R != 0`, acceptance restores `C = R`, clears `R`, and continues. | `+0x00` or `+0x10`, `+0x14`; flush and wait-indicator globals | likely |
| `0xe1` (1 byte; also `0x00`) | `Text_CtrlEndOrReturn`, `0x08004fb8` | With `R = 0`, flush, set status inactive, and yield without advancing `C`. Otherwise flush if pending, restore `C = R`, clear `R`, and continue immediately. | `+0x00` or `+0x10`, `+0x14`; flush flag | likely |
| `0xe2` (1 byte) | `Text_CtrlNewline`, `0x08005050` | Advance one line when below the limit. At the limit, scroll automatically while `+0x08` is nonzero; otherwise await input. A successful line/scroll helper consumes the opcode. Always yields, including a normal newline. | `+0x00`, `+0x08`, `+0x0b`, `+0x10`, `+0x1c`, `+0x1e`; scrolling helpers/buffers, flush and indicator | likely |
| `0xe3` (1 byte) | `Text_CtrlWaitNextLine`, `0x080050f0` | Always wait for input, then advance or scroll according to the line limit. Reset `+0x08` to visible lines minus one. Helper consumes opcode on acceptance; always yields. | `+0x00`, `+0x08`, `+0x0b`, `+0x10`, `+0x1c`, `+0x1e`; scrolling helpers/buffers, flush and indicator | likely |
| `0xe4` (1 byte) | `Text_CtrlAdvanceLineForced`, `0x0800516c` | Flush, then advance/scroll without testing input. Decrement `+0x08` if nonzero; request working-buffer clear. Helper consumes opcode; yields. | `+0x00`, `+0x08`, `+0x0b`, `+0x10`, `+0x1c`, `+0x1e`; scrolling helpers/buffers, flush | likely |
| `0xe5` (1 byte) | `Text_CtrlWaitInPlace`, `0x080051a4` | Flush if pending, wait for input, then reset `+0x08` to visible lines minus one, advance `C` by one, and continue. Does not itself advance the line or clear the page. | `+0x08`, `+0x10`; flush and indicator | likely |
| `0xe6` (1 byte) | `Text_CtrlInsertTextE6`, `0x08005210` | Save `R = next`; replace `C` with the RAM stream at `0x03001f60`; continue. Exact inserted content depends on game state. | `+0x10`, `+0x14` | likely |
| `0xe7` (1 byte) | `Text_CtrlInsertTextE7`, `0x08005224` | Save `R = next`; replace `C` with the RAM stream at `0x03002b90`; continue. Content/ownership not established. | `+0x10`, `+0x14` | likely |
| `0xe8` (1 byte) | `Text_CtrlSetFillGroup3`, `0x08005238` | Set glyph/fill group to `3`; advance `C` by one; continue. No named color established. | `+0x07`, `+0x10` | likely |
| `0xe9` (1 byte) | `Text_CtrlSetFillGroup2`, `0x08005248` | Set glyph/fill group to `2`; advance `C` by one; continue. | `+0x07`, `+0x10` | likely |
| `0xea` (1 byte) | `Text_CtrlSetFillGroup1`, `0x08005258` | Set glyph/fill group to `1`; advance `C` by one; continue. | `+0x07`, `+0x10` | likely |
| `0xeb` (1 byte) | `Text_CtrlSetDelayZero`, `0x08005268` | Set configured glyph delay to `0`; advance `C` by one; continue. Remaining delay is not explicitly reset. | `+0x05`, `+0x10` | likely |
| `0xec` (1 byte) | `Text_CtrlSetDelay6`, `0x08005278` | If previous delay is zero, flush before setting configured delay to `6`. Advance `C` by one; continue. | `+0x05`, `+0x10`; conditional flush | likely |
| `0xed` (1 byte) | `Text_CtrlSetDelay2`, `0x0800529c` | If previous delay is zero, flush before setting configured delay to `2`. Advance `C` by one; continue. | `+0x05`, `+0x10`; conditional flush | likely |
| `0xee` (1 byte) | `Text_CtrlWaitClearPage`, `0x080052c0` | Wait for input, then consume opcode, reset line to `+0x20` and X through `0x08005fa4`, fill the entire tile destination with current background group, request working-buffer clear, remove delay-bypass bit, reset line budget/limit, and call `0x080059e0`. Always yields. | `+0x00`, `+0x08`, `+0x09`, `+0x0b`, `+0x10`, `+0x1c`, `+0x1e`; tile destination, flush and indicator; further `0x080059e0` effects unknown | likely |
| `0xef` (1 byte) | `Text_CtrlWaitAnimation`, `0x08005384` | Hold while the selected entity is active and its nonnull animation pointer matches the nonzero pointer at `0x03001f6c`. Otherwise consume opcode and continue. This polls completion; it is not a conditional branch to another text address. | `+0x10` on completion; conditional flush | likely |

The newline helpers are `Text_AdvanceLine` at `0x08004ff4` and the scroll-start
helper at `0x08005018`. Both advance `C` by **one**, increment the logical line,
set flag `0x04`, and recalculate X from `+0x03`; they choose reading status `3`
and scrolling status `2`, respectively. The latter additionally calls
`0x08004c98` and `0x08005928`. Their full effects are outside the supplied
exports. The zero-argument call to the flush helper in the decompiled `0xe4`
handler is a recovered-signature defect; it should not be interpreted as a
distinct no-state flush API.

On accepted `0xee`, the fill length is width × height × `0x20` bytes at
`+0x0c`. `+0x09` becomes the low byte of the reset logical line minus one plus
visible lines, and `+0x08` becomes visible lines minus one. This is page clear
plus input wait, rather than a clear-only control.

## Controls `0xf0`–`0xff`

The reader's opcode advance is already included in each count. All handlers in
this group continue after their action. For every insertion below, `R = next`
and `C` becomes the selected/generated stream. There is no inserted-stream
length operand; its end/return byte controls completion.

`A(i)` means the pointer entry at `0x084aa740 + 4*i`. `V(T, M, i)` means first
select a pointer-table row via `T + 4*M`, then its entry `i`. `S(M, i)` means
`V(0x08465df8, M, i)` for `i < 4`, otherwise
`V(0x08465e04, M, i - 3)`. The second index is **i minus three**, not i minus
four. These formulas describe address selection, not validated index bounds.

Two different string helpers are used: `H = 0x08006074` and `J = 0x08005ffc`.
Their bodies are absent from these exports, so the distinction is preserved
instead of assigning unproven linguistic, font, or trimming semantics.

| Opcode / layout | Handler, even Thumb address | Effect / operand meaning | State fields / other writes | Confidence |
|---|---|---|---|---|
| `0xf0 i` (2 bytes) | `Text_CtrlInsertTableF0`, `0x0800546c` | Insert the result of `H(A(i))`. | `+0x10`, `+0x14`; helper effects unknown | likely |
| `0xf1 i` (2 bytes) | `Text_CtrlInsertVariantF1`, `0x080054a0` | Insert `H(V(0x08465e28, M, i))`; reset `M = 0` after selection. | `+0x10`, `+0x14`, `M`; helper effects unknown | likely |
| `0xf2 a b` (3 bytes) | `Text_CtrlInsertValue62`, `0x080054e8` | Query helper `0x08000d34` with family `0x62` and index `b`; pass returned u16 and format byte `a` to `0x08004820`; insert generated stream at `0x03000648`. Exact format meaning unknown. | `+0x10`, `+0x14`, generated stream; query/formatter effects unknown | likely |
| `0xf3 a b` (3 bytes) | `Text_CtrlInsertValue77`, `0x08005520` | Same construction as `0xf2`, but query family is `0x77`. Neither argument is an inline pointer. | `+0x10`, `+0x14`, generated stream; query/formatter effects unknown | likely |
| `0xf4 b` (2 bytes) | `Text_CtrlInvokeCallback`, `0x08005558` | Consume one callback ID, then invoke `Scene_InvokeCallback` at `0x08001440`. Meaning is installed by the current scene; not a universal portrait ID. | `+0x10`; callback effects depend on scene | likely |
| `0xf5 b` (2 bytes) | `Text_CtrlInsertInlineEntity`, `0x08005570` | With a window template, allocate an entity normally from slots `3`–`7`, position at text X/current visible line, and set animation from `0x084675e8`, indexed by `5*b + allocationIndex`. In all cases advance text X by 16 pixels. | `+0x10`, `+0x1c`, conditionally `+0x0a`; entity state via several helpers | likely |
| `0xf6 i` (2 bytes) | `Text_CtrlInsertSplitF6`, `0x08005684` | Insert `H(S(M, i))`; reset `M = 0`. | `+0x10`, `+0x14`, `M`; helper effects unknown | likely |
| `0xf7 i` (2 bytes) | `Text_CtrlInsertVariantF7`, `0x080056ec` | Insert `H(V(0x08465e10, M, i))`; reset `M = 0`. | `+0x10`, `+0x14`, `M`; helper effects unknown | likely |
| `0xf8 i` (2 bytes) | `Text_CtrlInsertVariantF8`, `0x08005734` | Insert `H(V(0x08465e1c, M, i))`; reset `M = 0`. | `+0x10`, `+0x14`, `M`; helper effects unknown | likely |
| `0xf9 b` (2 bytes) | `Text_CtrlInsertSlotF9`, `0x0800577c` | Select pointer slot `0x03002ba0 + 4*(b & 0x0f)`, pass its address to helper `0x08006078`, then insert the pointer read from that slot. Reset `M = 0`. No `0xff` fallback. | `+0x10`, `+0x14`, `M`; slot/helper effects unknown | likely |
| `0xfa i` (2 bytes) | `Text_CtrlInsertTableFA`, `0x080057b4` | Insert `J(A(i))`; counterpart of `0xf0` using the other helper. | `+0x10`, `+0x14`; helper effects unknown | likely |
| `0xfb i` (2 bytes) | `Text_CtrlInsertVariantFB`, `0x080057e8` | Insert `J(V(0x08465e28, M, i))`; reset `M = 0`. | `+0x10`, `+0x14`, `M`; helper effects unknown | likely |
| `0xfc i` (2 bytes) | `Text_CtrlInsertSplitFC`, `0x08005830` | Insert `J(S(M, i))`; reset `M = 0`. | `+0x10`, `+0x14`, `M`; helper effects unknown | likely |
| `0xfd i` (2 bytes) | `Text_CtrlInsertVariantFD`, `0x08005898` | Insert `J(V(0x08465e10, M, i))`; reset `M = 0`. | `+0x10`, `+0x14`, `M`; helper effects unknown | likely |
| `0xfe i` (2 bytes) | `Text_CtrlInsertVariantFE`, `0x080058e0` | Insert `J(V(0x08465e1c, M, i))`; reset `M = 0`. | `+0x10`, `+0x14`, `M`; helper effects unknown | likely |
| `0xff` (1 byte; lookahead only) | `Text_CtrlSelectVariant1`, `0x080053e4` | Inspect next byte: set `M = 1` if it is in the prefix whitelist below, otherwise `M = 0`. Leave `C` at that byte so the reader dispatches it normally. | `+0x10` from reader's advance only; `M` | likely |

`0xf5`'s allocation search has no separate failure path in the export: if all
five intended entities are active, the counter reaches five and subsequent
operations target entity eight. Operand bounds and this exhaustion case need
testing before treating it as a general icon insertion API.

## Prefix `0x5e` and modifier behavior

| Encoding | Handler, even Thumb address | Byte count / effect | Writes | Confidence |
|---|---|---|---|---|
| `0x5e` | `Text_CtrlSelectVariant2`, `0x08005428` | One prefix byte, zero consumed operands. Inspect next byte; set `M = 2` for whitelist members, otherwise `M = 0`; continue with `C` still pointing at the inspected byte. | `+0x10` from reader's advance only; `M` | likely |

The shared whitelist is `0xf1`, `0xf6`, `0xf7`, `0xf8`, `0xf9`, `0xfb`,
`0xfc`, `0xfd`, `0xfe`. Therefore a prefix plus one of these controls and its
one-byte operand occupies **three bytes**. The prefix chooses a variant row;
the substitution consumes its own operand and resets `M` afterward. For
`0xf9`, the export shows the prefix being accepted and `M` being reset but does
not expose how helper `0x08006078` uses `M`.

Neither prefix quotes a literal glyph byte. A prefix followed by `0x5e` or a
control still goes through the ordinary classification on the next iteration.
Both are global selectors, so their lifetime and interference across multiple
TextStates deserve testing. Do not use them as persistent font-mode switches.

## Inserted-stream returns and branch limits

`0xe6`, `0xe7`, `0xf0`–`0xf3`, and `0xf6`–`0xfe` each overwrite the same
single `R` field. They do not push a return-address stack. Nesting substitutions
can overwrite the outer return location. `0xe1`/`0x00` returns immediately;
`0xe0` returns after accepted input if `R` is nonzero. At top level these end
the message instead of resuming the byte after the terminator.

No handler in this map consumes an arbitrary ROM pointer or inline branch
target. Table substitutions, callback execution, and `0xef`'s polling condition
do not establish general branching or choice support. Named authored text
arrays still require an event-script binding to be reachable.

## Practical choices for authored text and glyph probes

- **Page clearing:** `0xee` is the identified wait-and-clear-page control. It
  resumes the following stream on a later update after accepted input. `0xe4`
  forces line advance/scroll and is not a whole-page clear. No clear-only
  opcode was found in this set.
- **Speed zero:** `0xeb` sets delay to zero for subsequent glyphs. `0xec` and
  `0xed` restore explicit delays of six and two. A later newline or terminator
  flushes the batched working line. Reaching `0xeb` does not explicitly cancel
  a delay countdown that was already underway.
- **Normal/alternate font:** the direct reader uses normal font when
  TextState `+0x0b & 0x08` is zero and alternate font when it is set. None of
  these exported control handlers directly toggles that bit. For a parent-owned
  state setup or memory probe, preserve all other bits while clearing/setting
  `0x08`. A stream-only font-switch recipe is not established here; substitution
  helper internals remain unknown.
- **Glyph escapes:** no literal-glyph escape is established. Direct glyph
  bytes are only `0x01`–`0x5d` and `0x5f`–`0xdf`. `0x00`, `0x5e`, and
  `0xe0`–`0xff` do not render their nominal glyph slots through this reader.
  Consequently normal slots `0x005d` and `0x00df`–`0x00ff`, and alternate
  slots `0x015d` and `0x01df`–`0x01ff`, cannot be reached as direct glyphs.
  This is a dispatch restriction, not evidence that those stored glyphs are blank.
- **Built-in substitutions:** `0xe6` and `0xe7` consume no operands but require
  their RAM streams to be valid in the current scene. Table insertions consume
  the operands shown above and require valid indexes. Use a known existing
  context/index rather than arbitrary values while the table bounds and helper
  transformations are unknown. Do not nest them as if they were function calls.
- **Callbacks:** use `0xf4` only with a callback known for the current scene.
  Existing clubhouse evidence for callback `0x08` is in
  [portraits.md](portraits.md#how-dialogue-reaches-the-portrait).

For both font modes, normal glyph index is byte minus one. The alternate path
adds `0x100`. The resolved glyph base is `0x0864b040` and the width-table base is
`0x08653040`; alternate glyphs consequently start at `0x0864f040`, and alternate
widths at `0x08653140`. Each stored glyph consumes `0x40` bytes. The parent owns
which images/characters those slots represent. Other bytes on the direct glyph
path may render blank or unusual images; that requires the separate font map.

## Remaining questions and validation

Static checks: all 32 opcode-to-handler mappings agree with `reader-tables.json`;
cursor/operand reasoning was checked against the reader and individual exports;
literal addresses were resolved only after the ROM hash matched. Runtime length tests are recorded in [Verification](#verification); handler names
are now in `symbols.csv`.

Next investigations, owned by the parent rather than performed here:

- Understand helpers `0x08006074`, `0x08005ffc`, `0x08006078`, and `0x08004820`:
  their transformations, possible indirect font effects, termination, and buffer
  bounds are not in these exports. The generated-value family names and format
  byte `a` remain unknown; numeric formatting is only a hypothesis.
- Identify `0xe7`'s RAM stream owner, each substitution table's content category
  and valid index bounds, and the selected-index byte at `0x02003999`.
- Test `0xee` clearing/reset behavior, `0xeb` batching/flush behavior, modifier
  row selection and lifetime, `0xf5` allocation/bounds, and nested substitutions.
- Resolve additional page-clear cleanup through `0x080059e0` and scroll helper
  effects; verify exact accepted buttons and the effect of `0x080e4188`.

## Verification

### Lengths: whole-ROM static check

All 3,599 text streams reached by the event-script walk (see
[event_scripts.md](event_scripts.md#whole-rom-walk-static-validation)) were decoded with
the lengths above. Every stream terminates (3,132 on `0xe0`, 467 on `0x00`). In 3,397
cases the terminator is immediately followed by another referenced stream, and **no
stream overruns the start of the next**. Changing any one length shows which controls
this check pins down. A ±1 change to `e2`, `e3`, `e4`, `e8`, `ee`, `ef`, `f2`, `f3`,
`f4` or `f5` creates overruns or lost alignments. The rarer controls are not
distinguished by this check, so they were tested live.

### Lengths: emulator read-watch test

Method: from the Boss savestate, start the Hamha conversation, point the live TextState
cursor (`+0x10`) at a real occurrence of the control in a game stream, and put read
watchpoints on the next four ROM bytes. The reader's byte fetch is reported at pc
`0x08004630`. Operand bytes are instead read by the control's own handler, and the next
fetched byte marks the end of the control. For insertions, the saved return cursor
(`+0x14`) independently gives the same end. Calibrated on `e2` (length 1).

| Control | Length | Evidence (handler pc reading operands; return cursor) | Result |
|---|---|---|---|
| `e4` `e5` `e8` `e9` `ea` `eb` `ec` `ed` `ee` | 1 | next byte fetched by reader; `e5`/`ee` held until A | confirmed |
| `e6` | 1 | returns to +1; inserted RAM stream `0x03001f60` | confirmed |
| `e7` | 1 | returns to +1; inserted RAM stream `0x03002b90` | confirmed |
| `f0` | 2 | operand read at `0x08005476`; return +2; inserted ROM string | confirmed |
| `f1` | 2 | `0x080054aa`; return +2 | confirmed |
| `f2` | 3 | `0x080054f2`, `0x080054f8`; return +3; generated stream `0x03000648` | confirmed |
| `f3` | 3 | `0x0800552a`, `0x08005530`; return +3; generated stream `0x03000648` | confirmed |
| `f6` | 2 | `0x0800568e`; return +2 | confirmed |
| `f8` | 2 | `0x0800573e`; return +2 | confirmed |
| `f9` | 2 | `0x08005786`; return +2. The slot held junk in this scene, so its content needs the script to set the slot first | confirmed length |
| `fa` `fb` `fc` `fd` | 2 | `0x080057be`, `0x080057f2`, `0x0800583a`, `0x080058a2`; return +2; output copied to RAM at `0x03000658` | confirmed |
| `ff`, `5e` | 1 | lookahead read of the next byte at `0x080053ec` / `0x08005430`; next control then dispatched normally | confirmed |
| `e0` `e1` `e2` `e3` `f4` | 1 / 2 | earlier dialogue work plus the static check | confirmed |
| `ef` `f5` | 1 / 2 | static check only (both context-dependent) | likely |
| `f7` `fe` | 2 | never used in script-referenced text | likely |

### Behaviour seen on screen

- `ea` = **red**, `e9` = **blue**, `e8` = back to **normal** text colour (fill groups 1, 2, 3).
  Example pattern: `ea`, `f0 nn`, `e8` shows a Ham-Chat word in red.
- `f0` / `fa` insert ROM strings (Ham-Chat words, names). The `f0` table entries are
  ROM strings displayed directly; `fa`–`fd` copy their result to RAM `0x03000658`
  before display, so helper `J` transforms the text.
- `e5` and `ee` wait for A; `eb` makes the following text appear instantly.
- One referenced stream is a developer font test, showing digits and letters under a
  `FONTO` caption. Leftover debug text exists in the ROM.

Local evidence (gitignored): `extracted/text-controls/` in the text-controls-verify
worktree (static check, sensitivity runs, read-watch results, screenshots).

