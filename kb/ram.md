# RAM map

Addresses refer to the verified USA AH3E ROM, SHA1
`2525cc23524068dfb3a2b4e0ce7b736f95023e82`. Confidence is recorded per variable.

## EWRAM (0x02000000–0x0203FFFF)

### Entities (characters)

Characters live in an array of 0x68-byte [Entity](structs.md#entity-size-0x68) structs.
The array is reached through the pointer `gEntityArray` (`0x03002d88`); Hamtaro's slot is
`gPlayerEntityIndex` (`0x03002bfc`). Entity address = `*gEntityArray + index * 0x68`.

Observed in the clubhouse bedroom (`states/walking.ss0`, local): array `0x0202280c`,
Hamtaro index 10 → entity `0x02022c1c`, so:

| Address (this scene) | Field | Meaning | Confidence |
|---|---|---|---|
| `0x02022c34` | Entity+0x18 | Hamtaro X, s32 16.16 fixed point (pixels in the high half) | confirmed |
| `0x02022c3c` | Entity+0x20 | Hamtaro Y, s32 16.16 | confirmed |
| `0x02022c40` | Entity+0x24 | X velocity, zeroed after each update | confirmed |
| `0x02022c48` | Entity+0x2c | Y velocity | confirmed |

### Event script variables

| Address | Type | Name | Meaning | Confidence |
|---|---|---|---|---|
| `0x02003990` | u8 array | `gEventByteVars` | Event byte variables, indexed by u16 (`0x02003990 + idx`) | confirmed |
| `0x020039cb` | u8 | `gBossHintCounter` | Byte var 0x003b: Boss repeat-greeting hint index 0–3 | confirmed |
| `0x0201d0b0` | u16 array | `gEventWordVars` | Event word variables (`0x0201d0b0 + idx*2`) | likely |

Byte var 0x0060 is a scratch result reused by several routines; byte var 0x0012 is
set to 16 before Boss's lines. See [event_scripts.md](event_scripts.md).

Don't hard-code the `0x0202xxxx` addresses in mods — the array pointer may differ per
scene; go through `gEntityArray` / `gPlayerEntityIndex`. Copies of the position also exist
(`0x02022c6a`, `0x02023636`, `0x0202363e` tracked it during the search) — unexplained.

## IWRAM (0x03000000–0x03007FFF)

### Text and dialogue

| Address | Type | Name | Meaning | Confidence |
|---|---|---|---|---|
| `0x030005f0` | TextState pointer | `gEventTextState` | Text state owned by the current dialogue event; zero after release | confirmed |
| `0x03000608` | TextState pointer | `gTextStateList` | Head of the generic text-state list; sentinel when empty | confirmed |
| `0x03000610` | TextState sentinel | `gTextStateSentinel` | List endpoint and empty-list head value | confirmed; size `0x34` likely |
| `0x03001fb0` | Thumb callback table | `gSceneCallbacks` | Scene-installed callbacks invoked by text control `0xf4`; number of entries unknown | confirmed callback `0x08` read; scope likely |

For the supplied clubhouse dialogue state, the active TextState is `0x0202447c`
in EWRAM and its stream cursor is `0x0202448c` (`+0x10`). Redirecting that cursor
changed the displayed passage. The root returned to the sentinel after the
patched dialogue closed. Follow the global list rather than hard-coding this
scene's heap addresses. See [dialogue.md](dialogue.md) and [TextState](structs.md#textstate-allocation-size-0x34-likely).

The Boss portrait is loaded into EWRAM `0x0201d2b0` in this scene. Both normal
and alternate `0x480`-byte tile blocks matched their independently decompressed
ROM assets. The loader chooses slot 2 for entity index 16; this is not a single
universal portrait buffer. See [portraits.md](portraits.md).

### Event interpreter and progression flags

| Address | Type | Name | Meaning | Confidence |
|---|---|---|---|---|
| `0x03000010` | u8 | `gEventOpcode` | Current event opcode; 0 = fetch next | confirmed |
| `0x03000014` | u32 | `gEventOperandAdvance` | Operand bytes to skip at next fetch | likely |
| `0x03000018` | u8 | `gEventPhase` | Phase of a multi-frame command | likely |
| `0x03001f58` | u8 | `gSubsceneId` | Current subscene | likely |
| `0x03001fac` | u16 | `gEventSelector` | Interaction/menu result consumed by dispatch commands | likely |
| `0x03002170` | bit array | `gEventFlags` | Progression flags: byte `0x03002170 + (id>>3)`, bit `id&7` | confirmed |
| `0x030021e0` | 32 pointers | `gInteractionRecords` | NPC/object interaction records for the room | likely |
| `0x03002ba0` | 16 u32 | `gEventPtrRegs` | Pointer registers for indirect pointer operands | likely |
| `0x03002be0` | u8 | `gEventCallDepth` | Event call-stack depth | likely |
| `0x03002c00` | 16 u32 | `gEventCallStack` | Saved call operand addresses | likely |
| `0x03002c48` | u8 | `gSceneId` | Current scene | likely |
| `0x03002c50` | u32 ptr | `gEventCursor` | Operand cursor; equals running opcode address + 1 | confirmed |

Poking a flag bit changes which event branch runs (flag 0x0010 = byte `0x03002172`
bit 0). Background contexts and the full field list are in
[event_scripts.md](event_scripts.md).

### Entity bookkeeping

| Address | Type | Name | Meaning | Confidence |
|---|---|---|---|---|
| `0x03002bfc` | u8 | `gPlayerEntityIndex` | Hamtaro's index in the entity array | confirmed |
| `0x03002bf4` | u8 | `gClubhouseBossEntityIndex` | Boss index used by this scene's callbacks; observed 16 | confirmed for clubhouse; reuse elsewhere unknown |
| `0x03002d88` | u32 ptr | `gEntityArray` | Pointer to the Entity array | confirmed |

### Input

`Input_Update` at `0x08009614` (Thumb) updates the input fields once per normal input
poll. Its caller function starts at `0x080001a4`; observed LR is `0x08000231`.
The input struct starts at `0x03000820`; see [InputState](structs.md#inputstate-minimum-covered-size-0x14).

| Address | Type | Name | Meaning | Confidence |
|---|---|---|---|---|
| `0x03000820` | u16 | `gKeysHeld` | Buttons currently held, active high | confirmed |
| `0x03000822` | u16 | `gKeysPressed` | Buttons newly pressed this poll; clears on the next held poll and does not repeat | confirmed |
| `0x03000824` | u16 | `gKeysPressedRepeat` | New presses, plus the whole held mask on auto-repeat pulses | confirmed |
| `0x03000826` | u16 | `gKeysReleased` | Buttons newly released this poll; clears on the next poll | confirmed |
| `0x03000828` | u16 | `gInputDpadPacked` | Packed bytes from D-pad lookup tables; purpose untested | likely |
| `0x0300082c` | u16 | `gInputRepeatInitialDelay` | Initial repeat delay; title value 90 produced the first repeat 89 frames after the initial press | confirmed |
| `0x0300082e` | u16 | `gInputRepeatInterval` | Repeat interval; title value 4 matched repeated pulses | confirmed |
| `0x03000830` | u16 | `gInputRepeatCountdown` | Loaded from initial delay, decremented in the same poll, then reloaded from interval at repeat | confirmed |
| `0x03000832` | u16 | `gInputUnchangedMaskFrames` | Static code increments while held mask is unchanged and count is below `0xffff`; otherwise resets to zero | likely |
| `0x03000838` | u16 | `gKeysPrevious` | Previous held mask when the updater begins; set to current held at its end | confirmed |

`0x0300082a` (`+0x0a`) is unmapped. The minimum covered struct region is `0x14`
bytes; its full allocation size is unknown. Previous-mask storage uses a separate
pointer at `0x03000838`.

All button masks use bits 0–9, with **1 meaning pressed/held**. The hardware
`REG_KEYINPUT` at `0x04000130` has the opposite polarity. The updater computes
`held = (~KEYINPUT) & 0x03ff`, `pressed = held & ~previous`, and
`released = previous & ~held`.

| Button | Mask | Button | Mask |
|---|---|---|---|
| A | `0x0001` | B | `0x0002` |
| Select | `0x0004` | Start | `0x0008` |
| Right | `0x0010` | Left | `0x0020` |
| Up | `0x0040` | Down | `0x0080` |
| R | `0x0100` | L | `0x0200` |

The hardware map follows `gba-primer`; L, R, and Right and their combinations were
tested dynamically. The fields are adjacent **u16** values, verified by width-2
watchpoint accesses and the parent's `strh` disassembly. A u32 read at
`0x03000820` combines held and newly pressed.

After a completed poll, `gKeysPrevious` equals `gKeysHeld`. Its previous-frame
meaning applies before the updater overwrites it. Stable reads alone cannot
distinguish these two fields.

Reproducible observed transitions (rows describe completed polls, using captured
changes and stable reads):

| Transition | Held | Pure pressed | Press/repeat | Released | Previous after update |
|---|---|---|---|---|---|
| Released baseline | `0x0000` | `0x0000` | `0x0000` | `0x0000` | `0x0000` |
| First L poll | `0x0200` | `0x0200` | `0x0200` | `0x0000` | `0x0200` |
| Next L poll | `0x0200` | `0x0000` | `0x0000` | `0x0000` | `0x0200` |
| L repeat poll | `0x0200` | `0x0000` | `0x0200` | `0x0000` | `0x0200` |
| First L release poll | `0x0000` | `0x0000` | `0x0000` | `0x0200` | `0x0000` |

Adding R to held L produced held `0x0300` and pure pressed `0x0100` for one poll.
Removing R left held L `0x0200`, no new press, and released `0x0100` for one poll.
Adding Right to L produced held `0x0210` and pure pressed `0x0010`; removing L
left held Right `0x0010`, no new press, and released `0x0200` for one poll.

On the title screen, a 40-frame L hold produced no repeat. Longer L/R tests with
delays 90/4 produced first repeats at press +89; pure pressed remained zero on
all repeat polls. The restored player-name screen had delay values 16/8, read
after testing; timing in that screen was not tested. Read the live configuration
when reproducing tests in another scene.

Full writer counts, frame stamps, timing limitations, and the unsuccessful poke
are documented in [the findings log](findings.md). Local raw evidence is in
`extracted/input-hunt-20261008/final-transitions.json` and the parent's
`extracted/input-ram-hunt/ghidra-input-*.txt`. No ROM bytes or raw dumps are tracked.
