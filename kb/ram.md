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

### Boss graphics shadows (observed clubhouse path)

| Address | Size | Name | Meaning | Confidence |
|---|---|---|---|---|
| `0x02007710` | `0x480` | `gBossDialoguePortraitTileShadow` | Decoded BG portrait; copied to `0x06003b80` | confirmed |
| `0x0201bbf0` | `0x20` | `gBossDialoguePortraitPaletteShadow` | Decoded BG palette; copied to bank 3 at `0x05000060` | confirmed |
| `0x0201d2b0` | `0x480` | `gRoomHeadTilesSlot2` | Separate room-head frame buffer; OBJ row copies begin `0x06010e20` | confirmed |

The dialogue face uses a BG tilemap; room heads use OAM. See
[portraits.md](portraits.md) and [the slot record](structs.md#roomheadslotrecord-stride-0x11c-likely-format).

### Event script variables

| Address | Type | Name | Meaning | Confidence |
|---|---|---|---|---|
| `0x02003990` | u8 array | `gEventByteVars` | Event byte variables, indexed by u16 (`0x02003990 + idx`) | confirmed |
| `0x020039cb` | u8 | `gBossHintCounter` | Byte var 0x003b: Boss repeat-greeting hint index 0–3 | confirmed |
| `0x020039f0` | u8 | `gEventScratchResult` | Byte var 0x0060: menu/page counts, Boss random hint, challenge results | confirmed mapped uses; scene meaning varies |
| `0x0201d0b0` | u16 array | `gEventWordVars` | Event word variables (`0x0201d0b0 + idx*2`); counters 9..11 tested | confirmed addressing |

Byte var 0x0060 is a scratch result reused by several routines; byte var 0x0012 is
set to 16 before Boss's lines. See [event_scripts.md](event_scripts.md).

### Gameplay counters and inventory — 2026-10-10/11

| Address | Type | Name | Meaning | Confidence |
|---|---|---|---|---|
| `0x0201d0c2` | u16 | `gSunflowerSeeds` | Word variable `0x0009`; status screen seed wallet | confirmed |
| `0x0201d0c4` | u16 | `gAcornCount` | Word variable `0x000a`; status screen acorns | confirmed |
| `0x0201d0c6` | u16 | `gRockCount` | Word variable `0x000b`; displayed rocks, distinct from actual records | confirmed display |
| `0x0201d0c8` | u16 | `gLoveMeterLevel` | Word variable `0x000c`; meter appearance and progression tier; normal 0..4 likely | confirmed appearance |
| `0x0201d0ca` | u16 | `gLoveMeterPoints` | Word variable `0x000d`; weighted fullness, normal cap 56 likely | confirmed fullness |
| `0x0201d0cc` | u16 | `gLovesRescued` | Word variable `0x000e`; Status Loves Rescued total | confirmed display |
| `0x0201d0bc` | u16 | `gCounterTransactionQuantity` | Word variable `0x0006`; shared requested/accepted gain or spend amount | likely |
| `0x0201d0be` | u16 | `gCounterAnimationTarget` | Word variable `0x0007`; shared counter animation target | likely |
| `0x0201bf90` | 64 records, stride 4 | `gRockRecords` | Rock type/state records; first u16 has type in bits 0..6 and occupancy/state in bits 7..11 | likely |
| `0x02003a06` | u8 | pending learned word | Byte variable `0x0076`; word ID or special learning request | likely |
| `0x02003b10` | u8 | inventory selection | Byte variable `0x0180`; selected menu position | likely |

From `inventory-screen.ss0`, separate pokes showed seeds 321, acorns 258,
and rocks 515, proving these are distinct totals wider than one byte.
Native width-2 reads occurred at instruction `0x08003a3c`, reported PC
`0x08003a40`, in `Event_CopyWordVarsFromMemory` (`0x080039e8`). Neighbouring
word variables 6, 7 and 8 did not change those totals or Loves Rescued.

A later discriminating poke changed word 0x000e from 0 to 7; reopening
Status showed Loves Rescued 7. The same width-2 memory-copy reader loaded
it from the first Status parameter command at `0x080d11a5`. Natural rescue
increment is statically traced to `0x08034554`; intended maximum remains unknown.

Separate level/points pokes of 0/28, 0/56 and 4/56 changed meter fullness and
appearance without changing rescue count. Reader traces reached meter natives
`0x08033e30`, `0x08033f94` and `0x0803426c`. Award native `0x08034490`
likely caps points at 56 and advances level at 14-point boundaries. Its
selector byte `0x02003a09`, phase byte `0x020039f1`, animation timer word
`0x0201d0f8` and displayed-counter copy `0x0201d0f4` are context-specific
scratch. See [love.md](love.md) for ROM sources and test limits.

The gain helpers limit seeds to 999 (`0x0804ae10`) and acorns to 50
(`0x0804b3c4` / `0x0804b3cc`). These caps remain **likely**, pending a
natural pickup/spending state. Rock helpers recount 64 record slots, so
poking the displayed rock total does not grant matching records. Seed and
acorn spending helpers accept zero when the requested quantity exceeds the
wallet. See [items_words.md](items_words.md) for writers and ROM tables.

On a disposable save copy, normal End Game -> Yep -> Continue preserved
seeds 123, acorns 234, rocks 345, learned count 11 and the Bestest learned bit.
Poked totals are not globally clamped on reload. Raw evidence stays in
`extracted/gameplay-ram-hunts/` and `extracted/gameplay/`.

Don't hard-code the `0x0202xxxx` addresses in mods — the array pointer may differ per
scene; go through `gEntityArray` / `gPlayerEntityIndex`. Copies of the position also exist
(`0x02022c6a`, `0x02023636`, `0x0202363e` tracked it during the search) — unexplained.

## IWRAM (0x03000000–0x03007FFF)

### Random number state and save bookkeeping — 2026-10-10

| Address | Type | Name | Meaning | Confidence |
|---|---|---|---|---|
| `0x03000000` | s32 | `gRngStateA` | First modular RNG component; normal modulus 30269 | confirmed |
| `0x03000004` | s32 | `gRngStateB` | Second modular RNG component; normal modulus 30307 | confirmed |
| `0x03000008` | s32 | `gRngStateC` | Third modular RNG component; normal modulus 30323 | confirmed |
| `0x03002158` | u8[5] | `gSaveBlockStatus` | Loaded copy per block: 0 invalid, 1 primary, 2 backup | confirmed primary/backup; invalid meaning likely |
| `0x03002be4` | u32 | `gSaveForceInitialize` | Nonzero selects destructive save initialization; not a normal save request | likely |
| `0x03005130` | Thumb pointer | `gSaveSramReadFunction` | Installed SRAM reader at `0x03001a98` | likely |
| `0x03005134` | Thumb pointer | `gSaveSramVerifyFunction` | Installed SRAM verifier at `0x030019f8` | likely |

The RNG update at `0x080003d8` is called once per main loop and once per
random-range request. The save packers cover selected regions, including
512 event bytes, 256 event words and 768 flag bits; these are saved extents,
not proven accessor guards. The three RNG words are outside those regions.
See [save.md](save.md) for SRAM addresses and exact packed offsets. The
selected counter/flag mappings, bank recovery and modular RNG updates were
tested in the emulator. The complete saved extents and boot seed behavior
remain static conclusions.

After removing probes, a positive RNG triple was poked and native state
writes were captured at `0x080003e8`, `0x080003f8`, `0x0800040a` (reported
PCs +4). Each matched `old * multiplier % modulus`. A subsequent all-zero
poke stayed zero after 30 idle frames. See [save.md](save.md) for arithmetic.

### Ham-Chat and item menu state

| Address / formula | Type | Name / meaning | Confidence |
|---|---|---|---|
| `0x030037c0` | u8[86] | `gHamChatLearnedOrder`; one-based word IDs in acquisition order | likely layout and persistence |
| `0x03003db0` | u8 | `gHamChatLearnedCount`; maintained dictionary/header total | confirmed display and persistence |
| `0x03002170 + ((wordId + 0x46) >> 3)` | packed bit | Learned flag for word IDs 1..86; mask `1 << ((wordId + 0x46) & 7)` | Bestest ID 0x44 confirmed; full formula likely |
| `0x0300218f`, mask 0x01 | packed bit | Flag 0x00f8; 0 Order Learned, 1 Alphabetical | confirmed menu action |
| `0x030038d0` | u8[48] | `gInventoryMenuSlotIds`; rebuilt item-ID list, 0xff empty | slot/rebuild confirmed; extent likely |
| `0x03002183`, mask 0x80 | packed bit | Flag 0x009f; Oilcan ownership (menu ID 1) | confirmed reopen and description |

Bestest's flag 0x008a is `0x03002181`, mask 0x04. Bit-only pokes revealed
and hid that word without changing 10/86; a count-only poke changed the
header to 11/86 without granting another word. Natural learning must maintain
flags, acquisition order and count together. The count reader is byte load
`0x080039c8`; selected-word flag reader is `0x08001462`, called from
`Ham_SelectLearnedWord` (`0x08033858`).

The item list is a display copy: slot-only Oilcan injection disappears on
reopen. Setting its ownership flag instead causes `Menu_BuildOwnedItemList`
(`0x08034c78`) to rebuild it. See [items_words.md](items_words.md) for the
item-to-flag ROM table, dictionary tables and native writers.

### Scene-specific challenge candidates (likely)

These event variables are reused by other scenes. Use them only in the named
challenge and trace its initializer/writer before a poke. No active challenge
state was available in this pass. [challenges.md](challenges.md) records the
source instructions, scores, prize gates and timing tables.

| Scene/value | RAM | Type | Writer / ROM rule | Confidence |
|---|---|---|---|---|
| Stickie elapsed ticks | `0x0201d270` (word 0x00e0) | u16 | Tick native `0x0801b7ac`; end above 3599; display `(3600-elapsed)/60` | likely |
| Stickie score | `0x0201d272` (word 0x00e1) | u16 | `0x0801c05c`; collections add 50/30/10 | likely |
| Stickie high score | `0x0201d134` (word 0x0042) | u16 | Update above prior record and 859; zero displayed as 860 | likely |
| Stickie difficulty / player step / paper multiplier | `0x02003b30` / `0x02003b33` / `0x02003b34` | u8 each | Phase 0..2; initial step 1, multiplier 2 | likely |
| Digdig dirt contents | `0x02003b36` | u8[9] | Board `0x0801c7e4`; four pairs plus special patch; removed 0xff | likely |
| Digdig attempts / matched pairs | `0x02003b3f` / `0x02003997` | u8 each | `0x0801ca90` / `0x0801c988`; fourth attempt, perfect 4 pairs | likely |
| Tic Tack-Q balls / line score | `0x02003b46` / `0x02003b52` | u8 each | Initial balls 4; line recount `0x0801e870` gives 0..8 | likely |
| Tic Tack-Q card marks / number labels | `0x03003560` / `0x03003af0` | u8[9] each | Setter `0x0801e810`; zero unmarked, nonzero participates in lines | likely |
| Tic Tack-Q actor timers | `0x02003b53` / `0x02003b54` / `0x02003b55` | u8 each | Random ranges [60,180) or [180,250), with actor/state gates | likely |
| Tic Tack-Q difficulty / cycle | `0x02003b45` / `0x02003b44` | u8 each | Difficulty 0..2 in inspected effects; ROM steps `0x084a6822` | likely |
| Stickie paper / spawner states | `0x03003d60` / `0x03003e20` | 10 / 3 records, stride 8 | Paper/spawner helpers; field meanings incomplete | likely |

### Text and dialogue

| Address | Type | Name | Meaning | Confidence |
|---|---|---|---|---|
| `0x030005f0` | TextState pointer | `gEventTextState` | Text state owned by the current dialogue event; zero after release | confirmed |
| `0x03000608` | TextState pointer | `gTextStateList` | Head of the generic text-state list; sentinel when empty | confirmed |
| `0x03000610` | TextState sentinel | `gTextStateSentinel` | List endpoint and empty-list head value | confirmed; size `0x34` likely |
| `0x03000646` | u8 | `gTextVariantSelect` | Substitution variant set by text prefixes `0xff`/`0x5e` | likely |
| `0x03000648` | text stream | `gTextGeneratedStream` | Generated by controls `0xf2`/`0xf3` (values) | confirmed |
| `0x03000658` | text stream | `gTextTransformedStream` | Transformed copy shown by controls `0xfa`–`0xfd` | confirmed |
| `0x03002b90` | text stream | `gTextInsertStreamE7` | Inserted by control `0xe7` | confirmed |
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
| `0x03002170` | bit array | `gEventFlags` | Gameplay flags, including learned words and ownership: byte `0x03002170 + (id>>3)`, bit `id&7` | confirmed addressing |
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

## Runtime-selected dialogue (likely; static coverage sweep)

Native `Event_NativeSelectTextSlots` at `0x0803b2d0` fills pointer registers
0 and 1 before the indirect show-text commands `0x080d9762` and `0x080d9772`.
The selected index is byte variable 0x0060 at `0x020039f0`. Source pointer
arrays are in RAM at `0x02001ab4` and `0x02001c6c`; their complete storage
bounds and initialization sources are not established. Slot 0 uses a direct
pointer for indexes below `0x1f`, otherwise a transformed stream in the
32-byte buffer at `0x03003ad0`. These are static findings, not live pokes.
See [text_coverage.md](text_coverage.md) for the exact native/script sources.
