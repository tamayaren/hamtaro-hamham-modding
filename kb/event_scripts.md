# Event scripts and NPC response selection

USA AH3E, verified SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`.
This document describes formats and behavior, not extracted dialogue or script dumps.
Unless explicitly called confirmed, findings below are **likely**: static Ghidra
analysis cross-checked against ROM operands. The Boss Hamha selection chain, the
operand-cursor convention, flag storage, the flag 0x0010 and 0x017d branches, and
the byte-variable 0x003b hint counter were **confirmed** in the emulator
(see [Emulator verification](#emulator-verification)). Story meanings of numbered
flags are deliberately unnamed until separately tested.

## How a line is chosen

There are three different interpreters involved. The room's **event script** handles
interaction results, menus, flags, variables, calls, and branches. A show-text event
hands a pointer to the **glyph/control stream** reader. **Animation scripts** separately
control actors and portrait graphics. A byte such as `0x1a` means an event operation
only when the event interpreter reads it; it is not a universal dialogue control.

The concrete selection chain is:

1. A scene descriptor supplies an event entry point and a callback table.
2. The room script initializes player collision and NPC interaction records.
3. A nearby NPC's record supplies a numeric interaction selector, not a text pointer.
4. The room script dispatches that selector to an NPC-specific script route.
5. A menu returns another selector; that dispatch chooses the Ham-Chat action.
6. Progress flags and variables branch to a particular show-text command.
7. That command passes its unaligned pointer operand to the independent text reader.

Consequently an NPC can have many event routes and many text streams. Adjacent text
streams do not themselves describe a dialogue tree.

## Scene descriptors and interaction records

`0x080009f8` loads `(scene u8, subscene u8)`. It reads the scene-table pointer from
`0x08466944 + scene*4`, then a **0x10-byte descriptor** at `table + subscene*0x10`.
Descriptor `+0x00` is the event entry, `+0x04` points to a counted callback list
(first u32 count, then Thumb function pointers), and `+0x08` is the entity count.
The loader installs the event pointer at `0x03002c50`, resets opcode and argument
advance, allocates scene entities, and copies callbacks to `0x03001fb0`.
The scene and subscene globals are `0x03002c48` and `0x03001f58`.

For scene 1/subscene 1, descriptor `0x084669a0` points to event `0x0804ef60`
and callback list `0x08052820`. Scene 1's descriptor array starts at `0x08466990`;
subscene 0 instead enters `0x0804ee48`, which can select a subscene via event `0x0d`.
Confirmed: the supplied Boss savestate has scene 1 (`0x03002c48`), subscene 1
(`0x03001f58`), and idles with cursor `0x0804ef8f`, just after event 0x21 at `0x0804ef8e`.

Event `0x20` (`0x08002b30`) consumes 17 operand bytes and calls `0x0800618c` to
initialize player/map interaction. Relative to the opcode:

| Offset | Size | Meaning |
|---|---|---|
| +0x01 through +0x04 | four u8 | player/companion entity indices passed to initializer |
| +0x05 | u8 | initializer options; low five bits plus separate 0x40/0x80 handling |
| +0x06, +0x08 | two u16 | map/coordinate limits passed to initializer |
| +0x0a | u32 | map collision-data pointer (can use pointer-register indirection) |
| +0x0e | u32 | interaction-record pointer-list source |

The initializer copies 32 pointer slots to `0x030021e0`. The ROM list can contain
an early sentinel; do not treat all copied words as valid records. The interaction
scanners stop on a null pointer or an entity index beyond the scene's count.
Event `0x4d` (`0x08003cbc`) changes one pointer slot, with operands `u8 slot, u32 pointer`.

Clubhouse setup commands at `0x0805105a`, `0x08051074`, `0x0805108b`, and
`0x080510a5` install list `0x080e21a0` under different initialization conditions.
Slot 4 of that list (`0x080e21b0`) points to Boss's interaction record `0x080e2150`.
The record describes entity 16 and interaction selector **9**. Its geometry is a
circle with offsets `(16,16)` and radius 40. This is a trigger region, not the
portrait or dialogue-window geometry.

Interaction record layout (at least 0x10 bytes, likely):

| Offset | Type | Meaning |
|---|---|---|
| +0x00 | u16 | associated entity index |
| +0x02 | u16 | event selector returned on a hit |
| +0x04 | u16 | shape: zero circle; nonzero rectangle |
| +0x06 | u16 | behavior bits: bit 1 physical collision; bit 0 automatic trigger |
| +0x08, +0x0a | s16 | shape offsets relative to the entity |
| +0x0c | u16 | circle radius, or rectangle extent |
| +0x0e | s16 | additional rectangle extent; unused in circle test |

`Player_Update` (`0x0800631c`) calls input detection `0x080067d4`, which turns A
into action bit `0x08` in `0x03000785`, subject to player-control flags. Through
`0x0800689c`, the NPC scan at `0x08007e28` checks the record list, active entity
`+0x60`, shape, and action/automatic-trigger bit. Circle test `0x08007ed4` returns
record `+0x02` when squared distance is strictly less than radius squared;
rectangle test is `0x08007fa0`. The scan ignores physical-collision records.

`0x08007708` writes the selector to `0x03001fac`, sets interaction status bit 1
at `0x03001f98`, and clears `0x03000794`. The NPC scan also writes the hit entity
index to `0x03002164`. Map collision tiles can also produce selectors through
`0x0800761c`: low six bits and bits 6–9 of tile attributes select event numbers,
with additional automatic/action conditions. Thus the room dispatch includes
objects and exits as well as NPCs.

Event `0x21` (`0x08002c60`) runs player updates until status is `0x10` or its low
two bits equal 2. It then clears byte variable `0x0012` and completes, letting the
room script inspect the selector. Its first phase calls `0x080062d8`, which resets
the selector and interaction status.

## Interpreter state and instruction rules

`Event_RunCommands` at `0x08000d74` dispatches `handlers[currentOpcode]` through
`0x08467434`, passing the pointer at `0x03002c50` as the operand pointer. Handler
entries are Thumb pointers; event and text pointers are ordinary byte addresses.

| RAM address | Type | Meaning |
|---|---|---|
| `0x03000010` | u8 | current event opcode; zero means fetch/advance |
| `0x03000014` | u32 | operand bytes to skip on next fetch |
| `0x03000018` | u8 | phase of current multi-frame command |
| `0x0300001a` | u16 | command-local wait counter |
| `0x0300001c` | u8 | continue despite a yield request |
| `0x0300001d` | u8 | yield requested by handler |
| `0x03001fac` | u16 | shared selector/result register |
| `0x03002170` | packed bits | event/game flags: byte `id>>3`, bit `id&7` |
| `0x030021e0` | 32 pointers | current interaction record slots |
| `0x03002ba0` | 16 u32 | pointer registers used by many pointer operands |
| `0x03002be0` | u8 | event call-stack depth |
| `0x03002c00` | 16 u32 | event call-stack storage (copied as 0x40 bytes) |
| `0x03002c50` | pointer | current operand cursor; also temporarily a branch target |
| `0x02003990` | byte array | byte variables, addressed by u16 index |
| `0x0201d0b0` | u16 array | word variables, addressed by u16 index |
| `0x030005e8` | scratch | operand assembly buffer, not a persistent script cursor |

Opcode zero is handled by `0x08001530`: add the pending operand advance to the
cursor, read the next opcode, advance the cursor by one, and clear phase/advance.
Thus while `0x1a` runs at `0x0804ffb4`, the operand cursor is `0x0804ffb5`, not
`0x0804ffb4` and not the text pointer `0x0846cc6b`. Completed handlers usually set
opcode to zero and the consumed operand count; blocked handlers retain opcode,
set yield, and resume in a later frame. All integers in scripts are little endian
and can be unaligned.

Calls are unusual: event `0x1e` pushes the **address of its four-byte target
operand**, then redirects the cursor. Return `0x1f` restores that address with
pending advance 4, so the next fetch is the byte after the call operand. Do not
store an already-advanced return address with this convention.

Many pointer operands resolve values below 16 through `0x03002ba0[index]`.
This behavior is handler-specific: it is present for call, flag/variable branches,
text, and menu pointers, but the decoded absolute jump `0x0c` and selector table
`0x1d` use their stored targets directly. Do not apply indirection indiscriminately.

`0x08000dbc` schedules event contexts 1–16 in addition to the main context.
Context storage starts at `0x03000050`, stride `0x54`; slot zero temporarily saves
the main interpreter. Layout: cursor `+0x00`, 16 call pointers `+0x04`, pending
advance `+0x44`, wait counter `+0x48`, selector `+0x4a`, opcode `+0x4c`, stack depth
`+0x4d`, phase `+0x4e`, continue flag `+0x4f`, yield flag `+0x50`.
Event `0x26` (`0x08002fb4`) initializes a background slot with `u8 slot, u32 entry`.
Flags and variable arrays remain shared; the selector is saved per context.

## Complete command-length table

The handler table at `0x08467434` has **97 entries, 0x00–0x60**. The words after it
(`0x084675b8`) belong to a sound-function table used by command 0x0a, not to events.
Lengths include the opcode byte and come from the constant each handler stores to the
operand-advance variable `0x03000014` (decompiled for every handler, with Ghidra's mode
error at `0x080030b0` fixed). Confidence: **likely** overall, and backed by the whole-ROM
walk and live checks below. Commands not listed in the format table further down have
known lengths but unmapped meanings.

| Op | Handler | Len | Flow / meaning |
|---|---|---|---|
| 0x00 | `0x08001530` | 1 | no-op (fetch routine) |
| 0x01 | `0x08001568` | 1 | end: halts on this opcode |
| 0x02 | `0x08001580` | 3 | wait u16 frames |
| 0x03 | `0x080015d4` | 1 | — |
| 0x04 | `0x08001620` | 1 | — |
| 0x05 | `0x08001638` | 1 | yield |
| 0x06 | `0x08001658` | 9 | LZ77 data load |
| 0x07 | `0x0800177c` | 9 | LZ77 data load |
| 0x08 | `0x08001804` | 11 | — |
| 0x09 | `0x080018b8` | 11 | — |
| 0x0a | `0x08001944` | 4 | — |
| 0x0b | `0x08001a20` | 4 | — |
| 0x0c | `0x08001d78` | 5 | jump `ptr` |
| 0x0d | `0x08001dbc` | 2 | end: reload subscene |
| 0x0e | `0x08001df8` | 2 | end: load scene |
| 0x0f | `0x080021c0` | 14 | place entity (x,y,z) + animation |
| 0x10 | `0x08002284` | 6 | set entity animation |
| 0x11 | `0x080022f8` | 7 | set entity animation |
| 0x12 | `0x08001ebc` | 7 | — |
| 0x13 | `0x08001e2c` | 7 | — |
| 0x14 | `0x08001f54` | 9 | — |
| 0x15 | `0x080020a8` | 6 | — |
| 0x16 | `0x08002178` | 2 | — |
| 0x17 | `0x0800219c` | 2 | — |
| 0x18 | `0x08002530` | 10 | — |
| 0x19 | `0x080025f0` | 3 | open/close text window |
| 0x1a | `0x080027a8` | 6 | show text and wait |
| 0x1b | `0x080028e0` | 6 | show text |
| 0x1c | `0x080029bc` | 5+n | native call, see below |
| 0x1d | `0x080029fc` | 2+4N | switch `u8 N` + N `ptr` |
| 0x1e | `0x08002a70` | 5 | call `ptr` |
| 0x1f | `0x08002af8` | 1 | return |
| 0x20 | `0x08002b30` | 18 | init player/map interaction |
| 0x21 | `0x08002c60` | 1 | wait for interaction |
| 0x22 | `0x08002d40` | 9 | branch, target at +5 |
| 0x23 | `0x08002dbc` | 5 | — |
| 0x24 | `0x08002e10` | 10 | Ham-Chat menu |
| 0x25 | `0x08002f44` | 6 | — |
| 0x26 | `0x08002fb4` | 6 | start context, entry at +2 (`0xffffffff` = stop) |
| 0x27 | `0x08003078` | 1 | end: clear cursor |
| 0x28 | `0x080030a0` | 5 | selector = byte at `ptr` |
| 0x29 | `0x080030fc` | 3 | selector = byte var |
| 0x2a | `0x0800313c` | 3 | selector = word var |
| 0x2b | `0x0800317c` | 3 | selector = u16 |
| 0x2c | `0x08002104` | 11 | — |
| 0x2d | `0x080031ac` | 4 | byte var = u8 |
| 0x2e | `0x080031f4` | 5 | word var = u16 |
| 0x2f | `0x0800328c` | 8 | — |
| 0x30 | `0x0800330c` | 10 | branch, target at +6 |
| 0x31 | `0x080033a4` | 10 | branch, target at +6 |
| 0x32 | `0x0800343c` | 10 | branch, target at +6 |
| 0x33 | `0x080034d4` | 8 | branch, target at +4 |
| 0x34 | `0x08003578` | 15 | — |
| 0x35 | `0x08003690` | 15 | — |
| 0x36 | `0x08003760` | 4 | — |
| 0x37 | `0x080037ac` | 2 | — |
| 0x38 | `0x08002760` | 3 | — |
| 0x39 | `0x08002374` | 3 | — |
| 0x3a | `0x080023c0` | 8 | — |
| 0x3b | `0x08002418` | 3 | — |
| 0x3c | `0x080037d8` | 10 | branch, target at +6 |
| 0x3d | `0x08002cbc` | 1 | — |
| 0x3e | `0x08002460` | 5 | — |
| 0x3f | `0x0800386c` | 2 | — |
| 0x40 | `0x08003900` | 2 | — |
| 0x41 | `0x08003978` | 8 | — |
| 0x42 | `0x080039e8` | 8 | — |
| 0x43 | `0x08003a5c` | 2 | — |
| 0x44 | `0x080024b4` | 8 | — |
| 0x45 | `0x08002eb8` | 6 | — |
| 0x46 | `0x08003b8c` | 4 | set/clear flag |
| 0x47 | `0x08003bfc` | 3 | — |
| 0x48 | `0x08003c30` | 4 | — |
| 0x49 | `0x08003c6c` | 3 | — |
| 0x4a | `0x08002398` | 4 | — |
| 0x4b | `0x0800243c` | 3 | — |
| 0x4c | `0x08003c98` | 2 | — |
| 0x4d | `0x08003cbc` | 6 | set interaction record |
| 0x4e | `0x08003d50` | 5 | — |
| 0x4f | `0x08003d2c` | 3 | — |
| 0x50 | `0x08003db0` | 8 | var = random |
| 0x51 | `0x08003e14` | 5 | — |
| 0x52 | `0x08003e68` | 2 | — |
| 0x53 | `0x08003240` | 7 | pointer register = u32 |
| 0x54 | `0x08002994` | 3 | — |
| 0x55 | `0x08002cd8` | 2 | — |
| 0x56 | `0x08001aa4` | 5 | — |
| 0x57 | `0x08001b94` | 3 | — |
| 0x58 | `0x08003ae4` | 3 | — |
| 0x59 | `0x08002c1c` | 5 | — |
| 0x5a | `0x08003e94` | 1 | — |
| 0x5b | `0x08003eb8` | 3 | — |
| 0x5c | `0x08001c30` | 12 | — |
| 0x5d | `0x08002d04` | 3 | — |
| 0x5e | `0x08001ce8` | 4 | — |
| 0x5f | `0x08003b08` | 1 | — |
| 0x60 | `0x08003b24` | 1 | — |

Branch commands store advance zero when they jump and skip their operands otherwise.
Commands 0x43 and 0x60 can also load a scene; 0x0d/0x0e always do.

### Native calls (0x1c)

`1c ptr ...`: the handler calls the Thumb function `ptr` with a pointer to the bytes
after it. The function returns how many **extra** operand bytes it used (length = 5 + n).
A function can also jump: it writes `gEventCursor` and returns −4, cancelling the +4.
[event_natives.csv](event_natives.csv) lists every native reached by the walk:
602 functions, 593 with a fixed extra count (559 likely, 34 guesses), 2 conditional jumps
(`0x08020768`: jump unless variable == value; `0x08018858`: jump if entity animation
matches; both 9 extra bytes, target at extra +5), and 7 that load a scene and end the script.
Counts were read from each function's return instructions or its decompiled return
value, then checked: decoding after every call site must stay valid. All 602 pass.

### Script quirks a decoder must handle

- **0x00 is a one-byte no-op.** Its handler is the fetch routine, and the dispatcher keeps
  fetching until a handler yields. Scripts sometimes store a 4-byte operand where a native
  reads one byte (e.g. `0x0801165c`), and the leftover zero bytes run as no-ops.
- **Switch tables can be longer than N.** 0x1d does not bounds-check: selector *k* reads
  entry *k*, even past N, and selector 0 falls through after N entries. Two scripts
  (`0x080afbf7`, `0x080afc87`) have N=3 with a fourth valid target. Their fall-through would
  execute pointer bytes, so the selector there is never 0.
- **Pointer operands below 0x10** are pointer-register indexes in some handlers (call,
  branches, text). Only 3 such uses occur in reachable scripts.

### Whole-ROM walk (static validation)

A recursive-descent walk starting from all 148 scene/subscene entry scripts (scene table
`0x08466944`, 12 scenes) follows jumps, calls, branches, switch targets, background
contexts and native jumps. It decodes **98,214 commands with zero invalid opcodes** and
reaches **3,599 distinct show-text targets** (0x1a/0x1b). Byte patterns shaped like
show-text commands occur at 4,257 places in the ROM, and the walk covers 4,144 of them
(97%). The remainder may be false matches or scripts reached only from native code or
tables; that is the coverage-sweep step of text extraction.

**Live check:** in the emulator, breakpoint sampling of the fetch routine (`0x08001542`,
`r1` = opcode address) plus per-frame cursor polling over three savestates (clubhouse Boss
menu routes, Sunny Peaks, the bedroom) observed 28 distinct executing command addresses.
All 28 are addresses the static walk decoded. A wrong length would misalign later addresses,
so this is discriminating, but the sample is small: the table stays **likely**, not confirmed.

## Operand formats of mapped commands

Lengths include the one-byte opcode. `ptr` is an unaligned u32, `idx` a u16.
Operand meanings below are static conclusions for the commands mapped so far.

| Opcode | Handler | Length | Operands and behavior |
|---|---|---|---|
| 0x01 | `0x08001568` | 1 | stop at this opcode; yield and clear continue flag |
| 0x02 | `0x08001580` | 3 | u16 frame count; wait (zero underflows, not instant) |
| 0x04 | `0x08001620` | 1 | enable continue-through-yield, then fetch |
| 0x05 | `0x08001638` | 1 | clear continue, request yield, then fetch next time |
| 0x0c | `0x08001d78` | 5 | ptr absolute jump |
| 0x0d | `0x08001dbc` | 2 | u8 subscene; reload within current scene |
| 0x0e | `0x08001df8` | 2 | u8 scene; load subscene zero |
| 0x10 | `0x08002284` | 6 | u8 entity, ptr animation script (indirectable); set entity animation |
| 0x11 | `0x080022f8` | 7 | u8 entity, u8 extra (passed to `0x0800b018`), ptr animation; set animation |
| 0x19 | `0x080025f0` | 3 | u8 text slot, u8 open/close; zero closes |
| 0x1a | `0x080027a8` | 6 | u8 slot, ptr text; apply window template, show, wait |
| 0x1b | `0x080028e0` | 6 | u8 slot, ptr text; start/wait without initial template setup |
| 0x1c | `0x080029bc` | 5 + n | ptr native function; it receives the following operand pointer and returns n (see Native calls) |
| 0x1d | `0x080029fc` | 2 + 4*N | u8 N, N absolute targets; selector 1 chooses first; selector zero falls through |
| 0x1e | `0x08002a70` | 5 | ptr event subroutine; push operand address, redirect |
| 0x22 | `0x08002d40` | 9 | ptr item, ptr target; jump if menu-item predicate `0x0800810c` accepts item |
| 0x26 | `0x08002fb4` | 6 | u8 context slot, ptr entry; start background script (`0xffffffff` stops it) |
| 0x28 | `0x080030a0` | 5 | ptr; selector = byte at ptr (indirectable) |
| 0x1f | `0x08002af8` | 1 | return using stored operand address +4 |
| 0x21 | `0x08002c60` | 1 | player/interaction loop until a result |
| 0x24 | `0x08002e10` | 10 | u8 count, ptr menu item IDs, ptr item predicates; result to selector |
| 0x29 | `0x080030fc` | 3 | idx byte variable -> selector |
| 0x2a | `0x0800313c` | 3 | idx word variable -> selector |
| 0x2b | `0x0800317c` | 3 | u16 constant -> selector |
| 0x2d | `0x080031ac` | 4 | idx, u8 value -> byte variable |
| 0x2e | `0x080031f4` | 5 | idx, u16 value -> word variable |
| 0x30 | `0x0800330c` | 10 | u8 bank, idx, u16 value, ptr; branch on equality |
| 0x31 | `0x080033a4` | 10 | same; branch if variable >= value (unsigned) |
| 0x32 | `0x0800343c` | 10 | same; branch if variable < value (unsigned) |
| 0x33 | `0x080034d4` | 8 | u8 wanted, u16 flag, ptr; branch if flag equals wanted (zero vs nonzero) |
| 0x3c | `0x080037d8` | 10 | u8 entity, ptr animation, ptr target; branch if current animation pointer matches |
| 0x46 | `0x08003b8c` | 4 | u16 flag, u8 value; clear on zero, set otherwise |
| 0x4d | `0x08003cbc` | 6 | u8 interaction slot, ptr record |
| 0x50 | `0x08003db0` | 8 | u8 bank, idx, u16 low, u16 high; variable = random in [low, high) via `0x08001508` |
| 0x53 | `0x08003240` | 7 | idx pointer register, u32 value |

For 0x30–0x32, bank zero means byte variables (only low comparison byte matters);
nonzero means word variables. Successful branches set pending advance zero;
unsuccessful branches skip their operands. Selector dispatch does not visibly
bounds-check nonzero results against N: changing menu counts and target tables
requires care. Menu initialization at `0x08008544` retains original one-based
item positions when filtering items, rather than renumbering the surviving list.

Flag helpers `0x08001458` (read) and `0x08001478` (write) use the same packed
array as script commands 0x33/0x46. This provides native-code and script access
to the same progression state; a flag's story meaning requires finding its writers.

## Annotated Clubhouse -> Boss -> Hamha route

This expands the previously confirmed text endpoint into its predecessors. Rows marked
**(c)** were observed in the emulator; the others are static.

| Site | Selection step |
|---|---|
| `0x084669a0` | scene 1/subscene 1 descriptor selects `0x0804ef60` | **(c)**
| `0x0805105a` and setup variants above | install interaction list `0x080e21a0` |
| `0x080e2150` | Boss entity 16, interaction selector 9 |
| `0x0804ef8e` | event 0x21 waits for player interaction | **(c)**
| `0x0804efbf` | 15-way selector dispatch; ninth pointer at `0x0804efe1` selects `0x0804f464` |
| `0x0804f464` | load byte variable 0x0038 into selector |
| `0x0804f467` | selector 1/2 -> `0x0804f4f5`; 3/4 -> `0x0804f51c`; zero falls through to normal route |
| `0x0804f479` | call `0x08051baa`, deriving byte variable 0x0060 from progression |
| `0x0804f47e` | if byte variable 0x0060 >= 1, branch to additional gating at `0x0804f4af` |
| `0x0804f48e` | normal four-item menu, IDs at `0x084aab26`, predicates at `0x084aab54` **(c)** |
| `0x0804f498` | four-way menu dispatch; first pointer operand `0x0804f49a` selects Hamha route `0x0804ff99` |
| `0x0804ff99` | call shared greeting setup `0x084ad5f5` |
| `0x0804ff9e` | call shared action/animation setup `0x084ac58d` |
| `0x0804ffa3` | store 16 to byte variable 0x0012 (`0x020039a2`) |
| `0x0804ffa7` | flag 0x0010 set -> `0x0804ffe7`; clear -> fall through | **(c)**
| `0x0804ffaf` | call text-window setup `0x084b44d1` |
| `0x0804ffb4` | show-text slot 0; operand `0x0804ffb6` -> `0x0846cc6b` (previously confirmed) |
| `0x0804ffba` | close text slot 0; subsequent commands animate the actors |
| `0x0804ffe2` | jump to shared completion `0x0805032f` |
| `0x08050335` | jump back to interaction loop `0x0804ef8e` |

The normal first-menu route is gated before Hamha is reached. `0x08051baa` derives
byte variable 0x0060 using flags 0x009a/0x0099/0x0091/0x009b and word variable
0x000c. It can produce 0–4. At `0x0804f4af`, flag 0x02ad, byte variable 0x00d1,
and flag 0x00ca can keep the ordinary menu or select another Hamha entry
(`0x0805033a`, via the dispatch at `0x0804f4de`). This is a second reason the
same NPC and selected Ham-Chat word need not reach the same response.

There are also room-level gates before the 15-way interaction dispatch:
byte variable 0x0060 values 2, 3, 4, and 5 divert to other routes at
`0x0804ef97`, `0x0804efa1`, `0x0804efab`, and `0x0804efb5`.
This scratch variable is reused by several script routines; it is not one globally
stable quest ID. Do not assign it a single story label from one use.

## Concrete alternate Hamha branch

At `0x0804ffa7`, flag 0x0010 is byte `0x03002172`, mask `0x01`.
When clear the familiar response is selected; when set execution reaches:

| Site | Condition/action |
|---|---|
| `0x0804ffe7` | if flag 0x007e is clear, jump to `0x08050079` |
| `0x0804ffef` | if flag 0x017d is set, jump to `0x0805001e` |
| `0x0804fff7` | otherwise set flag 0x017d |
| `0x0804fffb` | if flag 0x0190 is clear, jump to `0x0805000b` |
| `0x08050003` | if flag 0x017e is clear, jump to `0x08050050` |
| `0x0805000b` | shared window setup |
| `0x08050010` | show-text pointer `0x08050012` -> `0x0846ccc3` |
| `0x0805001e` | if flag 0x0190 is clear -> `0x08050079` |
| `0x08050026` | if flag 0x017e is already set -> `0x08050079` |
| `0x0805002e` | otherwise set flag 0x017e |
| `0x08050037` | show-text pointer `0x08050039` -> `0x0846cd25` |
| `0x08050055` | show-text pointer `0x08050057` -> `0x0846cdd3` |

**Confirmed example:** with flag 0x0010=1, 0x007e=1, 0x017d=0, 0x0190=0, Boss's
reply runs at `0x08050010` and the event 0x46 handler (`0x08003b8c`, store at
`0x08003bec`) sets flag 0x017d (byte `0x0300219f` 0x00 -> 0x20). The next greeting
under the same conditions sees 0x017d=1 and diverts through `0x0805001e` to
`0x08050079`. This is a concrete **first-time versus subsequent-time gate**; what
story event flag 0x017d represents is still unknown. Setting flag 0x0010 also put a
second companion portrait into Hamtaro's greeting window, so 0x0010 drives more than
this branch and should not be given a story name from this test alone.

### Repeat route: hint counter and random choice

`0x08050079` is where both "flag 0x007e clear" and "already greeted" end up:

| Site | Condition/action |
|---|---|
| `0x08050079` | call `0x08050135` (may play a one-off scene; sets byte var 0x0060) |
| `0x0805007e` | if byte var 0x0060 >= 1, skip to completion `0x0805032f` |
| `0x0805008c` | if flag 0x0191 is set -> `0x0805011d` (separate line `0x08050122`) |
| `0x08050094` | if byte var 0x003b < 3 -> selector = var 0x003b (`0x080500ae`) |
| `0x0805009e` | otherwise byte var 0x0060 = random 0..2, selector = it (opcode 0x50) |
| `0x080500b1` | 2-target dispatch: 0 falls through, 1 -> `0x080500d9`, 2 -> `0x080500ff` |
| `0x080500c0` | hint line 1 (operand `0x080500c2`); if counter < 3 set it to 1 |
| `0x080500d9` | if flag 0x0190 set skip to hint 3; else hint line 2 at `0x080500e6`, counter = 2 |
| `0x080500ff` | hint line 3 at `0x08050104`, counter = 3 |
| `0x0805012d` | close window, jump to completion `0x0805032f` |

Byte variable 0x003b (EWRAM `0x020039cb`) is therefore a per-NPC **hint counter**:
consecutive greetings step through three lines, after which one of the three is
picked at random. This was confirmed live: from the base state (counter 0) the reply
was `0x080500c0`; the following greeting gave `0x080500e6`; presetting the counter to
2 gave `0x08050104` (see verification). `0x08050135` only plays its own scene when
flags 0x01d2 clear, 0x0190 set, and 0x007e set; otherwise it returns at `0x0805024b`.

## Modding points

- **Replace only the mapped response:** redirect the four-byte text operand at
  `0x0804ffb6`, with an original-byte check, to an authored stream. Other selection
  conditions and alternate show-text sites remain separate. Existing
  `patches/sunflower-dialogue/` demonstrates this confirmed binding.
- **Change an alternate response:** bind its own show-text operand, for example
  `0x08050012`, or the hint operands `0x080500c2`, `0x080500e8`, `0x08050106`;
  do not assume replacing the preceding stream affects it.
- **Change a repeat/hint cycle:** the counter thresholds are the u16 values in the
  0x31/0x32 commands (`0x08050094`, `0x080500c6`, ...) and the counter stores are the
  0x2d commands that follow each hint. The random range is the 0x50 command at
  `0x0805009e` (low/high at `0x080500a2`/`0x080500a4`).
- **Change when a response is chosen:** modify the appropriate event branch's
  condition or target. For `0x0804ffa7`, wanted bit is at `0x0804ffa8`, flag ID
  at `0x0804ffa9`, and target pointer at `0x0804ffab`. Patching this command is
  narrower than globally forcing flag 0x0010, which other systems also read.
- **Change which Ham-Chat choice reaches a route:** edit the corresponding menu
  target, such as `0x0804f49a`. Keep item predicates, original item indices, and
  the branch-table size consistent.
- **Change NPC interaction routing:** edit record `+0x02` or the room selector
  table. This affects which action menu/event runs, not just which sentence appears.

Preserve window open/close, animation waits, call-stack balance, and completion
jumps when replacing event sequences. A pointer-only authored-text mod is simpler
than rewriting the entire event route. No gameplay patch was built for this study.

## Emulator verification

All trials reload a local copy of `states/dialogue-state.ss0` (Hamtaro facing Boss),
poke the listed flag/variable bytes, press A (Boss menu) then A (Hamha), and record
the event cursor `0x03002c50` and opcode `0x03000010` every frame until the room
script returns to `0x0804ef8f`. Show-text sites are opcode addresses (cursor - 1).

| Trial | Pokes | Room-script show-text site(s) | State after |
|---|---|---|---|
| A baseline | none (flag 0x0010 clear) | `0x0804ffb4` (cursor observed `0x0804ffb5`) | unchanged |
| B, 1st greeting | flags 0x0010, 0x007e set | `0x08050010` | flag 0x017d set by pc `0x08003bec` |
| B, 2nd greeting | (continued) | `0x080500c0` | hint counter 1 |
| B, 3rd greeting (manual) | (continued) | `0x080500e6` | hint counter 2 |
| C | flag 0x0010 only | `0x080500c0` | — |
| D | flag 0x0010, byte var 0x003b = 2 | `0x08050104` | counter 3 |
| E | flag 0x0010 only | `0x080500c0` | counter 0 -> 1 |

Each run first shows Hamtaro's own greeting from the shared subroutine
(`0x084ad620`, called at `0x0804ff99`), then the menu at `0x0804f48e` is the
observed `0x24` command. These are discriminating tests: each poke changes which
show-text command runs, exactly as the decoded branches predict. Randomized
selection (counter >= 3) and the 0x007e-set/0x0190-set paths were not exercised.

Note for future tracing: sampling the cursor and opcode in two separate bridge
reads can pair a stale opcode with a new cursor (an apparent "text" at the yield
`0x084b80be` was this artifact). Read the opcode byte at cursor - 1 from ROM instead.

## Evidence and remaining work

Local evidence (gitignored): Codex's static decompiles and `disasm-checks.txt` in the
event-selection worktree's `extracted/event-selection/`; the tracers, script
decoder, and `trace.json` in the main checkout's `extracted/event-selection-claude/`.
Decompiled output and decoded scripts are not tracked. Ghidra misidentifies some
function boundaries; `0x08003db0` (opcode 0x50) had to be created as a Thumb function.

Command-length evidence (local, gitignored) is in the opcode-lengths worktree's
`extracted/opcode-lengths/`: per-handler decompiles, the walker, native tables, and
runtime-check results.

Still open: story meanings of flags 0x0010, 0x007e, 0x017d, 0x0190, 0x0191; meanings of
most commands in the length table; 34 guessed native counts (single call sites); the progression
routine `0x08051baa` and the `0x0804f4af` gate, which need later-game savestates;
and other NPCs' routes, which should follow the same pattern from the selector
dispatch at `0x0804efbf`.
