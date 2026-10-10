# Ham-Chat, inventory, and resource counters

USA AH3E, verified original SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`.
Investigated 2026-10-10; emulator checks completed 2026-10-11.
`confirmed` describes the menu, poke, watchpoint or save test stated below.
Unexercised code paths, gain caps and the complete word/item mappings remain
`likely`. See [gameplay.md](gameplay.md) for the overview and pending states.
Derived text and listings stay under `extracted/gameplay-items-20261010/` and
`extracted/gameplay-ram-hunts/`; screenshots and follow-up traces are under
`extracted/gameplay/`.

## Learned words and matching IDs

The exact earlier decompile clue is retained: `0x08032e3c` checks learned flags
at **zero-based index + 0x47**, over **86 entries**, with dictionary mode
selected by **flag 0x00f8**. In the game's one-based word IDs this is
`flagId = wordId + 0x46`, for IDs `0x01..0x56`.

| Address | Type / extent | Meaning | Confidence |
|---|---|---|---|
| `0x03002170` | Packed flags | Learned bit: byte base + `(flagId >> 3)`, mask `1 << (flagId & 7)` | confirmed generic addressing; full learned subset likely |
| `0x03002178` bit 7 through `0x03002183` bit 4 | 86 bits | Flags `0x0047..0x009c`; endpoint bytes also contain other flags | likely |
| `0x030037c0` | u8[86], 0x56 bytes | One-based word IDs in acquisition order | likely; analyst's baseline matches ten starter IDs |
| `0x03003db0` | u8 | Maintained learned count; displayed separately from flags | confirmed display; natural maintenance likely |
| `0x02003a06` | u8, event byte var 0x0076 | Pending word to learn or special request | likely |
| `0x0300218f`, mask 0x01 | Flag 0x00f8 | 0 = Order Learned; 1 = Alphabetical | confirmed by analyst's real Sort action |
| `0x084a77bc` | 86 rank bytes, ending before `0x084a7812` | ID minus one selects alphabetical display rank; ranks are distinct 0..93 with gaps | likely |
| `0x084a7840` | 87 pointers, 0x15c bytes | Dictionary names: slot 0 fallback; slots 1..86 use word IDs | likely |
| `0x084a799c` | 87 pointers, 0x15c bytes | Companion text keyed by the same word ID and fallback | likely |
| `0x084aa740` | Existing insert pointer table | Text controls 0xf0 and 0xfa use its IDs | existing confirmed control; complete identity match likely |

All 86 non-fallback dictionary streams were checked against the verified ROM:
each is a terminated `0xfa` insertion of **its own one-based table index**.
Therefore native dictionary ID and insert-table ID match throughout 1..86.
Their stored string pointers differ because the dictionary stores wrappers.
The rank byte is a display position, not another word ID. Alphabetical mode
reserves 24 pages; Order Learned uses `ceil(count / 4)` at `0x080331fc`.

Rubrub is word `0x38`, giving flag `0x007e`, byte `0x0300217f`, mask `0x40`.
Its native wrapper is `0x0846c88a`; insert slot points to `0x0846a330`.
A previously unnamed gate testing flag 0x007e can be described as **Rubrub
learned (likely)**; its resulting branch behavior still needs a discriminating
runtime test. Other previously called progression flags are words too:

| Flag | One-based word ID | RAM byte | Mask |
|---|---|---|---|
| 0x007e | 0x38 | `0x0300217f` | 0x40 |
| 0x0091 | 0x4b | `0x03002182` | 0x02 |
| 0x0099 | 0x53 | `0x03002183` | 0x02 |
| 0x009a | 0x54 | `0x03002183` | 0x04 |
| 0x009b | 0x55 | `0x03002183` | 0x08 |

The analyst independently confirmed Bestest, decimal ID 68 (`0x44`), flag
0x008a at `0x03002181`, mask 0x04. A bit-only poke revealed that word while
count remained 10. A count-only poke to 11 made the header read 11/86.
These experiments establish why an all-words patch must update flags, order,
and count together. Full word/name lists remain in local text evidence.

## Readers, learning, and initialization

| Thumb function | Suggested name | Static behavior |
|---|---|---|
| `0x08001458` | Existing `Event_GetFlag` | Packed flag reader; actual load at `0x08001462` |
| `0x08001478` | Existing `Event_SetFlag` | Sets or clears one packed bit; write at `0x080014ae` |
| `0x08032e3c` | `Ham_RenderWordList` | Four name rows; flag index+0x47; ID+1 pointer slot or fallback |
| `0x08032f64` | `Ham_RenderWordCompanions` | Companion rows for the same selected word IDs |
| `0x080331fc` | `Ham_UpdateWordPageCount` | Writes page count to byte var 0x0060 (`0x020039f0`) |
| `0x0803344c` | `Ham_PositionPendingWordCursor` | Positions category/page/row from pending word and sort flag |
| `0x0803369c` | `Ham_ApplyPendingLearnedWord` | Ordinary learning, starter batch, and notification-only requests |
| `0x08033858` | `Ham_SelectLearnedWord` | Resolves current row and checks learned bit; writes ID to byte var 0x0022 (`0x020039b2`) |
| `0x08003978` | `Event_CopyByteVarsFromMemory` | Opcode 0x41 copies bytes from resolved source pointer into event byte variables |
| `0x080039e8` | `Event_CopyWordVarsFromMemory` | Opcode 0x42 copies u16s into event word variables |
| `0x0800060c` | `Main_ResetRuntimeState` | Clears acquisition list/count and other working arrays; calls flag/variable reset |

Ordinary learning in `0x0803369c` checks `wordId+0x46` at call
`0x08033808`. If already learned, it skips insertion and count increment.
A new word sets its learned flag at call `0x08033818`, sets notification flag
0x0107, appends its ID at write `0x0803382e`, increments count at
`0x08033834`, positions the menu cursor, and clears the pending byte.
A high-bit request other than 0xff instead positions the cursor and sets
notification flags without appending or incrementing. There is no visible
86-word bounds check in this native; invalid ordinary IDs can reach other flags.

Pending 0xff takes the starter branch: it adds IDs 1, 2, 3, 4, 7, 8, 9, 10,
13, 63, sets notification flags 0x0107/0x0108/0x0109, selects pending ID 1,
and calls the cursor helper at **`0x080337ea`**. These ten IDs match the
analyst's baseline. Scene 10.10 entry `0x080d97b0` calls shared initializer
`0x080db28b` at `0x080d97ef`. That initializer sets sorting flag 0x00f8,
writes pending 0xff at `0x080db28f`, and calls the learning script
`0x080d01c4` at `0x080db293`. That script reaches `0x080d073b` and invokes
the native at `0x080d0747`. This is a static starter/new-game route, not a
confirmed runtime breakpoint sequence.

`Main_ResetRuntimeState` zeroes the list by DMA and count at `0x0800063e`,
then calls `0x08000be0(0)` to clear flags and event variables. It is used by
boot and other reset paths, so it is unsuitable as an unconditional all-words
hook. The save worker maps list to block 1 payload +0x0338, count to +0x038f,
and learned flags to block 2's saved flag slice. Save reload copies all three;
it does not reconstruct count from learned bits. A standalone learned-bit
popcount routine was not found in the inspected readers.

The menu reads count using opcode 0x41 at `0x080d087a` / `0x080d0ab3`,
copying it to byte var 0x0060. Opcode 0x42 at `0x080d11b6` also copies one
u16 from the count address into word var 0x0022; its adjacent byte is included
in that read. The maintained field itself is u8, established by native writes
and the analyst's discriminating poke.

## Key-item ownership and descriptions

| Address | Type / extent | Meaning | Confidence |
|---|---|---|---|
| `0x030038d0` | u8[48], 0x30 bytes | Rebuilt menu item-ID list; 0xff is empty | confirmed slot 0/rebuild; total extent likely |
| `0x02003b10` | u8, byte var 0x0180 | Selected list position | likely |
| `0x02003b12` | u8, byte var 0x0182 | Page/scroll maximum derived from owned count | likely |
| `0x02003b13` | u8, byte var 0x0183 | Description scrolling offset | likely |
| `0x084a7ba0` | u8[48] | Menu order of item IDs; currently IDs 0..47 | likely |
| `0x084a7bd0` | u8[48] | Item ID to ownership flag ID | likely |
| `0x084a7e1c` | u8[45] | Description scrolling limits for IDs 0..44 | likely |
| `0x084a7e4a` | u16[46], 0x5c bytes | Start pointer indices for 45 descriptions plus terminal offset 211 at `0x084a7ea4` | likely |
| `0x084a7ea8` | 211 pointers, 0x34c bytes | Description-row strings; ends before `0x084a81f4` | likely |

`0x08034c78` fills 48 menu bytes with 0xff, tests each ordered item's mapped
flag via `Event_GetFlag` at `0x08034ca2`, and appends owned IDs. IDs 0..46
map to flags `0x009e..0x00cc`; ID 47 maps to flag `0x009d`. Thus Oilcan's
confirmed menu ID 1 maps statically to ownership flag `0x009f` at
`0x03002183`, mask 0x80. The flag's Oilcan ownership effect is **confirmed**: preserving other bits,
setting only 0x80 in `0x03002183`, and reopening the supplied empty inventory
rebuilt slot 0 as ID 1 and displayed Oilcan's icon and description. The next
slot remained 0xff. Writing the menu slot alone is temporary. Other item
flag mappings and natural acquisition writers remain **likely**.

This ownership range starts immediately after the learned-word flags.
All-words changes must preserve the upper bits of `0x03002183`.
The 48-entry menu allocation does not establish a consumable stack cap.
Only 45 item IDs have established description spans. IDs 45..47 need further
mapping before use. The scroll-limit bytes are not all simply offset differences
minus one: IDs 35/36 have additional stored rows despite limit 3.

`0x08034dac` renders four rows using
`descriptionPtrs[offsets[itemId] + row]`; it skips empty IDs.
`0x08034e94` renders scrolled rows 1..3, adding the scrolling offset.
`0x08034e50` wraps the offset to zero when offset+3 exceeds that item's limit.
A flag-2-gated input helper `0x080353d0` sets/clears groups of ownership flags
0x009e..0x00ca (45 IDs); it is an additional static cross-check, not a tested grant UI.

## Seeds, acorns, and rock records

The RAM analyst confirmed the three displayed u16 values, including values
above 255, and width-2 reads. The cap and transaction code below is **likely**;
menus accept poked values above these caps, so these are rules in named gain
helpers, not universal RAM validation.

| RAM address | Event word variable | Meaning / type | Static cap or role |
|---|---|---|---|
| `0x0201d0bc` | 0x0006 | u16 transaction quantity | Shared gain/spend scratch; not the seed total |
| `0x0201d0be` | 0x0007 | u16 display target | Shared counter-animation scratch; not the seed total |
| `0x0201d0c2` | 0x0009 | Seed total, u16 | Gain helper clamps to 999 |
| `0x0201d0c4` | 0x000a | Acorn total, u16 | Gain helper clamps to 50 |
| `0x0201d0c6` | 0x000b | Displayed rock total, u16 | Recomputed from occupied records in rock helpers; 64 record slots |
| `0x0201bf90` | Separate array | 64 rock records, stride 4, 0x100 bytes | First u16 low 7 bits = type ID; bits 7..11 = nonzero occupancy/state field |
| `0x08465e48` | ROM metadata | Four-byte records selected by rock type ID | Supplies category/name selector and initial 5-bit state; total entry count unresolved |

| Thumb function | Suggested name | Behavior / ROM cap site |
|---|---|---|
| `0x08009194` | `Menu_AllocateRockRecord` | First record with bits 7..11 zero; writes type/state; returns slot, or -1 after 64 slots |
| `0x08009210` | `Menu_CountOccupiedRockRecords` | Counts nonzero state fields across all 64 slots; returns u8 |
| `0x0800923c` | `Menu_GetRockRecordInfo` | Returns record's 5-bit state; optionally resolves text/metadata into output record |
| `0x0804ace4` | `Menu_ShowSeedCounter` | Seeds display setup; copies current total to animation scratch |
| `0x0804ad30` | `Menu_ShowRockCounter` | Rock counter display setup |
| `0x0804ad7c` | `Menu_ShowAcornCounter` | Acorn counter display setup |
| `0x0804adc8` | `Event_AddSeedsAnimated` | Reads quantity var 6, limits it to 999-current, writes total at `0x0804ae44`; 999 literal at `0x0804ae10` |
| `0x0804ae88` | `Event_RemoveSeedsAnimated` | If requested quantity exceeds total, accepts zero; writes subtraction at `0x0804aefe` |
| `0x0804af40` | `Event_AddRockAnimated` | Recounts records, allocates one type, sets success flag 0x0013, updates counter; no space means zero accepted |
| `0x0804aff0` | `Event_RefreshRockCounter` | Recounts occupied records into rock total and display target |
| `0x0804b1e8` | `Event_AddRocksAnimated` | Recounts records, caps quantity to 64-current, allocates types from event word array; 64 immediates at `0x0804b22c` / `0x0804b234` |
| `0x0804b2fc` | `Event_RemoveAcornsAnimated` | Overlarge request becomes zero; subtracts at `0x0804b372` |
| `0x0804b3b4` | `Event_AddAcornsAnimated` | Limits quantity to 50-current; 50 immediates at `0x0804b3c4` / `0x0804b3cc`; total write `0x0804b432` |

The allocation helper scans 64 slots, with checks at `0x080091ae` (63)
and `0x080091bc` (64). The counter scans all records, not just a packed
prefix. The metadata getter uses the low seven-bit type to select ROM records;
the physical ID width does not prove that all 128 types exist or are safe.
No meaning such as polish durability is assigned to the state field yet.
The save worker independently maps this 0x100-byte array to block 2 payload
+0x05d8. Displayed rock count and records must be tested together on acquisition.

A scene-10.10 child script sets transaction word var 6 to ten at
`0x080daf48` and calls the seed-add native at `0x080daf5d`. This explains a
starting seed award of ten after reset, statically; it does not make the
999 literal an initial balance. Acorns/rocks are zeroed by common reset;
no specific nonzero starter award for them was established here.
The add helpers assume ordinary in-range existing totals; deliberate pokes
above a cap are not evidence that the acquisition clamp is absent.

## Exact instruction checks against analyst traces

| Instruction address | Verified Thumb instruction | Interpretation |
|---|---|---|
| `0x08001462` | `ldrb r0, [r0]` | Flag byte read; LR 0x080338d7 normalizes to return 0x080338d6 after call at 0x080338d2 in `Ham_SelectLearnedWord` |
| `0x080039c8` | `ldrb r0, [r1]` | Count byte read by opcode 0x41 memory-copy handler |
| `0x08003a3c` | `ldrh r0, [r1]` | Seed/acorn/rock read by opcode 0x42 memory-copy handler |
| `0x08003be8` | `strb r0, [r2]` | Sort-bit write by existing `Event_CmdSetFlag` (0x08003b8c), opcode 0x46 |
| `0x08034c88` | `strb r1, [r0]` | Inventory-list rebuild writes 0xff before ownership tests |
| `0x08034dfc` | `ldrb r0, [r1]` | Selected item ID read by description renderer |

## Remaining confirmation

The supplied inventory and word-list states suffice to check menu counters,
sort behavior, Bestest's learned bit, and Oilcan ownership. They do not place
the player at a natural acquisition, purchase, or new-word event.

- Use the deferred pickup/shop states to test seeds 998 + 2 -> 999,
  acorns 49 + 2 -> 50, accepted spending, and rock record allocation at
  63/64 slots. These code caps remain likely.
- A future `word-before-learn.ss0` should confirm flag/order/count updates
  together, including duplicate learning. Do not derive count by popcount
  while ignoring the acquisition-order list.
- Fresh starter initialization needs its own named state before any
  all-words-on-new-game patch can be called verified. No such demo is
  delivered in this change.
- Only Oilcan's ownership bit was poked. IDs 45..47 and natural key-item
  writers still need mapping; 48 menu positions do not mean 48-item stacks.
- Rock state bits need a polishing/acquisition context before they can be
  named durability, polish progress, or gem state.

The verified exit-to-title/Continue test saved and restored resource totals,
the Bestest bit and count. See [save.md](save.md) for the exact SRAM fields.
Poked display totals above the gain caps survived reload; this demonstrates
that the gain helpers enforce caps, rather than a global RAM validator.

Ghidra's initial raw-ROM analysis split some functions and interpreted data
as code. Temporary Thumb reconstruction was rolled back after export.
Claimed instructions, literals and table bounds were checked against the
verified ROM and contiguous Thumb disassembly; unresolved epilogues were
not used as proof of behavior.
