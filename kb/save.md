# Save data and RNG

Static investigation 2026-10-10; emulator confirmation 2026-10-11.
`confirmed` applies to gameplay blocks 1-3, selected persisted fields,
backup recovery and the observed RNG transitions. Opaque payload meanings,
boot seeds and unexercised paths remain **likely**, based on disassembly,
Ghidra and paired packing/unpacking routines. The existing `SRAM_F_V103`
identification was already documented;
it identifies the library/save medium, not the game's saved payload format.

ROM SHA1 independently checked with the main CLI and `uv run --no-sync`:
`2525cc23524068dfb3a2b4e0ce7b736f95023e82` (USA `AH3E`, 8 MiB).
Full derived output stays in local, ignored
`extracted/gameplay-save-rng/`. Temporary Ghidra function definitions used for export were rolled back. No
save helper is implemented; an offline writer needs further padding checks.

## What this means for modding

The game saves selected RAM regions, rather than its entire running state. The
save system has two redundant 16 KiB banks; these are backup copies, not evidence
of two selectable player files. Explicit script calls and some scene transitions can reach the gameplay
writer. End Game -> Yep was confirmed to save; automatic scene-transition
trigger conditions remain static conclusions.

The saved event arrays cover 512 byte variables, 256 word variables, and 96 bytes
of flags (768 bits). These are **persistence extents**, not validated input bounds
or confirmed gameplay caps. The RNG's three state words are outside every saved
region identified here. Idle frames advance the RNG, so waiting changes the next
random result even when no random event is requested.

## Save routines and entry points

All functions in this table are Thumb; record their even addresses.

| Address | Proposed name | Plain-language behavior | Confidence |
|---|---|---|---|
| `0x0800044c` | `Save_Checksum16` | Folded, complemented sum of little-endian u16 words; optional final byte; returns u16 | confirmed tested path |
| `0x08000744` | `Main_InitSaveAndTitle` | Clears/initializes game state, checks save signature, loads blocks 2 and 3, opens scene 0 | likely |
| `0x0800078c` | `Save_InitializeOrRepair` | Checks both bank signatures; repairs one bad signature or initializes save memory and records | likely |
| `0x08000ff4` | `Save_WriteBlock` | Packs selected block/subindex, fills header/checksum, writes primary and backup | likely |
| `0x0800108c` | `Save_WriteGameplayBlocks` | Writes blocks 1-3 in each bank; temporarily invalidates their headers before writing full data | confirmed tested path |
| `0x080011b4` | `Save_LoadBlock` | Checks primary checksum then backup; unpacks and records the successful copy | likely |
| `0x08001320` | `Save_LoadGameplayBank` | Checks blocks 1-3 as a bank; tries primary bank first, then backup bank | confirmed tested path |
| `0x08001dbc` | `Event_ChangeSubsceneAndMaybeSave` | Loads a subscene; calls gameplay writer when current scene is 1-9 and event flag 0x0001 is set | likely |
| `0x08003a5c` | `Event_CmdLoadSaveBlock` | Opcode 0x43; reads block operand; block 1 can restore scene/subscene | likely |
| `0x08003ae4` | `Event_CmdWriteSaveBlock` | Opcode 0x58; operands are block id and subindex; calls single-block writer | likely |
| `0x08003b08` | `Event_SaveGameplay` | Opcode 0x5f; normal End Game calls the gameplay writer | confirmed tested path |
| `0x08003b24` | `Event_LoadGameplay` | Opcode 0x60; Continue calls the bank loader and restores scene/subscene | confirmed tested path |
| `0x080e5644` | `Save_ReadSramBytes` | SRAM-library byte copy, installed as a RAM function at startup | likely |
| `0x080e5684` | `Save_WriteSramBytes` | Writes byte by byte; write instruction at `0x080e56a8` | likely |
| `0x080e56c4` | `Save_VerifySramBytes` | Compares source and SRAM bytes; zero means equal, otherwise mismatch address | likely |
| `0x080e5710` | `Save_InitSramLibrary` | Copies reader to `0x03001a98`, verifier to `0x030019f8`, and installs Thumb pointers | likely |
| `0x080e57ac` | `Save_WriteSramVerified` | Write and compare, at most three attempts; zero means success | confirmed tested path |

`0x08000984` checks event flag 0x0005 and can reinitialize RAM and call
`Save_InitializeOrRepair`; the separate force-initialize word `0x03002be4` can
force the destructive initialization branch. Do not equate that path with a
normal save, or invoke it as a helper.

`0x0801116c` and `0x080114d0` also use the checksum routine, but their inspected
logic concerns a transfer state machine, not a direct SRAM writer. Avoid naming
all checksum callers as save functions.

### ROM tables, SRAM banks, and header

| ROM address | Type/count | Proposed name | Meaning | Confidence |
|---|---|---|---|---|
| `0x084673d0` | 5 u32 | `kSaveChecksumSizes` | Allocation/checksum/read sizes, indexed by block id | likely |
| `0x084673e4` | 5 pointers | `kSavePrimaryBlockAddresses` | First bank destinations | likely |
| `0x084673f8` | 5 pointers | `kSaveBackupBlockAddresses` | Second bank destinations, each primary + 0x4000 | likely |
| `0x0846740c` | 5 Thumb pointers | `kSaveBlockPackers` | Block 0/1 share packer; then extended, auxiliary, record packers | likely |
| `0x08467420` | 5 Thumb pointers | `kSaveBlockUnpackers` | Corresponding inverse operations | likely |
| `0x086ca1e0` | library tag | existing `kSaveTypeTag` | SRAM library identification; existing KB entry | existing |

| Block | Primary start | Backup start | Reserved/read/checksum bytes | Serializer payload bytes | Actual write bytes | Interpretation |
|---|---|---|---|---|---|---|
| 0 | `0x0e000000` | `0x0e004000` | 0x00ee | shared with block 1 in function table | special initialization | Signature/header area; do not treat as a normal block |
| 1 | `0x0e0000ee` | `0x0e0040ee` | 0x05ca | 0x0395 | 0x039d | Core event state, scene ids, smaller variable/flag slices |
| 2 | `0x0e0006b8` | `0x0e0046b8` | 0x070a | 0x06ea | 0x06f2 | Extended event state, larger variable/flag slices, names |
| 3 | `0x0e000dc2` | `0x0e004dc2` | 0x066a | 0x00fb | 0x0103 | Auxiliary state regions and three bytes |
| 4 | `0x0e00142c` | `0x0e00542c` | 0x2bd4 overall | 0x0080 per record | 0x0088 per record | 51 records, stride 0x00dc; reader checks each 0x00dc record |

The bank boundary follows exactly from block 4: `0x142c + 0x2bd4 = 0x4000`.
Record indices are 0-50. The record formatter `0x08037614` and the record packer
point to staging buffer `0x03003cb0`; fuller human-facing record meaning remains
unresolved (do not call them player-save slots).

For ordinary blocks, the 8-byte header is:

| Offset | Type | Meaning | Confidence |
|---|---|---|---|
| +0x00 | u32 | Returned serializer payload length | confirmed blocks 1-3 |
| +0x04 | u8 | Block id | confirmed blocks 1-3 |
| +0x05 | u8 | Subindex; record index for block 4 | zero confirmed blocks 1-3; record meaning likely |
| +0x06 | u16 | Checksum | confirmed blocks 1-3 |
| +0x08 | bytes | Packed payload | likely |

The writer zeroes the checksum field, computes it over the ROM size-table span,
and inserts the result. The loader expects the same calculation over stored
bytes to return zero. Add each little-endian u16 to a 32-bit accumulator, add a
last odd byte if present, fold high 16 bits into low 16 bits twice, complement,
and keep 16 bits. This is not a CRC.

**Padding nuance:** allocation wrapper `0x0800aa20` requests a zero-filled buffer
through `0x0800aa2c`. Checksumming therefore includes zero padding beyond the
serializer's returned length, but the writer sends only payload length + 8.
The initialization path zeroes the SRAM working image. This strongly explains
why reserved sizes can exceed write lengths; verify actual SRAM padding and
checksum results before implementing an offline writer. Block 4's writer uses
the overall size-table value while the loader checks a single 0x00dc record;
zero tails make these sums equivalent in the inspected initialization model.

`Save_InitializeOrRepair` compares the first 16 bank bytes with the ROM header
region at `0x080000a0`, using the installed byte verifier. It repairs one failed
signature from the ROM header bytes. During full initialization it uses a
three-byte clear marker at SRAM offsets +0x0009 and +0x4009, then removes it.
It also stages header-adjacent names from the pointers at `0x02002318` and
`0x0200231c`. Dynamic tests should distinguish missing signatures, checksum
failure, and a normal gameplay save.

### Exact packed RAM coverage

Payload offsets below start **after** the 8-byte save header. Copy lengths were
checked against BIOS wrappers `0x080e55fc` (CpuFastSet) and `0x080e5600` (CpuSet):
the control/count argument is not a byte length, and Ghidra's `PTR_REG_*` names
on these constants are misleading. The matching unpackers use the same regions.
Complete mapping extents remain **likely**. The seed/acorn/rock fields,
Bestest learned bit and learned count below were confirmed by normal save
and Continue; other rows retain static confidence.

Block 1 packer `0x08048f94`, unpacker `0x080491d0`:

| Payload offset | RAM start | Bytes/type | Description |
|---|---|---|---|
| +0x0000 | `0x03002c00` | 0x40 / 16 u32 | Event call stack |
| +0x0040 | `0x02002320` | 0x270 / opaque | Core state block; internal fields not mapped here |
| +0x02b0 | `0x0201d0b0` | 0x40 / 32 u16 | First 32 event word variables |
| +0x02f0 | `0x03002170` | 0x08 / flags | First 64 flag bits; packer forces bit 3 of first byte in the saved copy |
| +0x02f8 | `0x02003990` | 0x20 / 32 u8 | First 32 event byte variables |
| +0x0318 | `0x0201c090` | 0x20 / opaque | Additional state region |
| +0x0338 | `0x030037c0` | 0x56 / u8 IDs | Ham-Chat acquisition order; complete layout likely |
| +0x038e | `0x03002be0` | u8 | Event call depth |
| +0x038f | `0x03003db0` | u8 | Ham-Chat learned count; persistence confirmed |
| +0x0390 | `0x03002c48` | u8 | Scene id |
| +0x0391 | `0x03001f58` | u8 | Subscene id |
| +0x0392 | `0x030021d0` | u8 | Player control gates; bit meanings likely |
| +0x0393 | `0x03001f50` | u8 | Meaning unresolved |
| +0x0394 | `0x03001f80` | u8 | Meaning unresolved |

Block 2 packer `0x08049088`, unpacker `0x080492b4`:

| Payload offset | RAM start | Bytes/type | Description |
|---|---|---|---|
| +0x0000 | `0x03002ba0` | 0x40 / 16 u32 | Event pointer registers |
| +0x0040 | `0x03001fb0` | 0x1a0 / opaque | Region beginning with scene callbacks; not all bytes proven to be callbacks |
| +0x01e0 | `0x0201d0f0` | 0x1c0 / 224 u16 | Remaining saved event word variables |
| +0x03a0 | `0x03002178` | 0x58 / flags | Remaining saved 704 flag bits |
| +0x03f8 | `0x020039b0` | 0x1e0 / 480 u8 | Remaining saved event byte variables |
| +0x05d8 | `0x0201bf90` | 0x100 / 64 records | Rock records, stride 4; static format |
| +0x06d8 | `0x03002b90` | 9 u8 | Name/text bytes; semantic ownership not established here |
| +0x06e1 | `0x03001f60` | 9 u8 | Name/text bytes; semantic ownership not established here |

Examples useful to other workers: Boss hint counter `0x020039cb` maps to block 2
payload +0x0413 (primary SRAM `0x0e000ad3`); runtime choice `0x020039f0` maps to
payload +0x0438 (primary SRAM `0x0e000af8`). Flag 0x017d uses RAM `0x0300219f`,
bit 5, block 2 payload +0x03c7 (primary SRAM `0x0e000a87`). These are proposed
persistence probes, not newly confirmed meanings.

Block 3 packer `0x08049140`, unpacker `0x08049360`:

| Payload offset | RAM start | Bytes/type | Description |
|---|---|---|---|
| +0x0000 | `0x0201e2b0` | 0x20 / opaque | Auxiliary state |
| +0x0020 | `0x03003700` | 0x60 / opaque | Auxiliary state |
| +0x0080 | `0x03003c00` | 0x78 / opaque | Auxiliary state |
| +0x00f8 | `0x030035bc` | u8 | Meaning unresolved |
| +0x00f9 | `0x0300376c` | u8 | Meaning unresolved |
| +0x00fa | `0x03003c84` | u8 | Meaning unresolved |

Block 4 packer `0x080491ac` copies 0x80 bytes from `0x03003cb0`.
Unpacker `0x080493cc` copies each record's 0xd4-byte area after its 8-byte header
to the array pointed to by `0x03002ba0`, 51 times with stride 0xdc. This includes
padding beyond the packer's 0x80 meaningful bytes. Do not reduce that destination
array to the 16 pointer-register words used elsewhere; its ownership is reused.

## RNG state, transition, and seed

| Address | Proposed name | Type/range | Description | Confidence |
|---|---|---|---|---|
| `0x03000000` | `gRngStateA` | s32; normal 0-30268 | First modular state; normal boot seed 15042 | confirmed transitions; seed likely |
| `0x03000004` | `gRngStateB` | s32; normal 0-30306 | Second modular state; normal boot seed 19955 | confirmed transitions; seed likely |
| `0x03000008` | `gRngStateC` | s32; normal 0-30322 | Third state; boot seed is VCOUNT low byte + 1 | confirmed transitions; seed likely |
| `0x08000298` | `Main_InitHardwareAndRng` | Thumb function | Hardware setup plus the three seed stores | likely |
| `0x080003d8` | `Util_AdvanceRng` | Thumb function | Observed modular state writes; weighted return arithmetic static | confirmed transitions |
| `0x08001508` | existing `Util_RandomRange` | u16 input/output | Requests a draw; Boss [0,3) / [2,3) route test; general arithmetic static | confirmed mapped route |
| `0x08003db0` | existing `Event_CmdRandomVar` | Thumb function | Opcode 0x50; Boss result 2 written at instruction 0x08003df4 | confirmed byte route; word route likely |
| `0x080e5608` | `Util_BiosSignedRemainder` | Thumb function | BIOS Div wrapper returning remainder r1 as r0 | likely |

One step applies multiplier/modulus pairs (171, 30269), (172, 30307), and
(176, 30323) to A, B, C respectively. Then it sums new A * 70946,
new B * 70857, and new C * 70820, with the ordinary 32-bit wrapping arithmetic.
The BIOS wrapper uses signed division. The listed ranges describe normal
nonnegative state; corrupted or deliberately negative inputs are not guarded.
A zero component remains zero and the all-zero state stays all zero.

The range helper derives a 16-bit draw from bits 15-30 of that wrapped sum.
After truncating both bounds to u16, if high > low it returns
`low + floor(draw16 * (high - low) / 65536)`, in [low, high). If high <= low it
returns the raw draw16 instead. Thus equal bounds do **not** mean a fixed result.
Opcode 0x50 stores into u8 or u16; the u8 case additionally truncates the result.

| ROM constant site | Value / interpretation | Confidence |
|---|---|---|
| `0x08000388` | A boot seed 0x3ac2 = 15042 | likely |
| `0x08000390` | B boot seed 0x4df3 = 19955 | likely |
| `0x08000398` | Pointer to VCOUNT `0x04000006`; C = (u16 register & 0xff) + 1 | likely |
| `0x0800042c` | Modulus A 30269 | confirmed positive-state transition |
| `0x08000434` | Modulus B 30307 | confirmed positive-state transition |
| `0x0800043c` | Modulus C 30323 | confirmed positive-state transition |
| `0x08000440` | Weight A 70946 | likely |
| `0x08000444` | Weight B 70857 | likely |
| `0x08000448` | Weight C 70820 | likely |

Multipliers are instruction immediates at `0x080003de`, `0x080003ee`, and
`0x080003fe`, not a data table. State stores are `0x080003e8`, `0x080003f8`, and
`0x0800040a`. Seed stores are `0x080002d6`, `0x080002dc`, and `0x080002ea`.
Main-loop call site `0x08000250` advances RNG once per loop/frame, after normal
updates. The separate range-helper call site `0x08001512` adds an advance for
each request. Several other gameplay systems call the same range helper.

Low-address static state xrefs identify initialization and updates; apparent
RNG xrefs in graphics/script data are false-code artifacts. No additional reseed
writer was identified, and none of the save packers covers these three words.
This does not prove arbitrary indirect writes cannot exist. Test cold boot,
Continue, scene changes, and save/reload to establish actual reseed behavior.

## Emulator confirmation — 2026-10-11

The original ROM was copied to `build/gameplay-original/` with a disposable
save. Tests used that filename, preserving the human's original ROM/save.
Every poke was preceded by probe removal. Local evidence is in
`extracted/gameplay/`, including `save-write-trace.json`, `save-checksums.json`,
`save-reload.json`, `save-backup-reload.json`, and RNG/Boss reports.

From `inventory-screen.ss0`, poked seeds/acorns/rocks to 123/234/345,
set Bestest's flag 0x008a, and changed learned count to 11. Back to Status,
Right twice to End Game, A, Left to Yep, A returned to the title.
The default answer was Nope; menu transitions needed time to settle.
The writer `0x0800108c` ran once (reported breakpoint PC `0x0800108e`,
LR `0x08003b0f`), from opcode 0x5f's handler `0x08003b08`.
The verified SRAM writer ran twelve times: temporary header invalidations
and final writes for three blocks in both banks. Its first captured call
had source `0x03007e20`, destination `0x0e0000ee`, length 4.
The separate single-block writer was not reached by this action.

Actual blocks 1/2/3 contained payload lengths 0x0395/0x06ea/0x00fb,
matching block IDs, zero subindices, zero tails to their reserved extents,
and checksums which made the predicted calculation return zero in both
banks. Both entire 16 KiB banks matched in this test. Odd-byte checksum
handling, block 0 and block 4 were not dynamically exercised.

| Tested value | Primary SRAM address | Observed saved/reloaded value |
|---|---|---|
| Seeds / acorns / displayed rocks | `0x0e0003b8` / `0x0e0003ba` / `0x0e0003bc` | 123 / 234 / 345 |
| Bestest learned bit | `0x0e000a69`, mask 0x04 | Set |
| Learned count | `0x0e000485` | 11 |

Continue called bank loader `0x08001320` (reported breakpoint PC
`0x08001322`, LR `0x08003b2d`) from opcode 0x60's handler `0x08003b24`.
RAM and the Status screen retained these edits; block statuses 1-3 were 1.
The displayed rock total survived without creating matching rock records.
This test confirms persistence, not acquisition caps or record semantics.

For recovery, only the disposable primary block-1 checksum byte at
`0x0e0000f4` was XORed with 1. After reset and Continue, all three gameplay
statuses became 2 and the same values returned. This confirms bank-wide
backup fallback when one primary gameplay block fails. Both copies invalid,
signature repair, forced initialization and save interruption remain untested.

For RNG, poked a positive triple, captured native writes at instructions
`0x080003e8` / `0x080003f8` / `0x0800040a`, and checked each captured old
state against its multiplier/modulus formula. All three matched. After
removing probes, all three words were poked to zero; they stayed zero after
30 idle frames. These tests confirm the modular state and absorbing zero
case, rather than boot seed or every possible signed input.

The Boss demo leaves global RNG code unchanged and edits the inline range
to [2,3). From a controlled repeat-route copy of the supplied Boss state,
the helper `0x08001508` received r0=2, r1=3; instruction `0x08003df4`
wrote byte result 2 and selected show-text command `0x08050104`. The original
with the same zero RNG selected result 0's command `0x080500c0`.
Do not use [2,2): the helper's static high<=low path returns a raw draw.

## Remaining uncertainty

The complete payload maps are static; only the named fields above passed a
discriminating persistence test. Block-4 record meaning/padding, abnormal
save recovery and exact autosave timing need separate states/tests before
an offline save writer is justified. No save decoder/writer helper is
implemented by this change.

No reseed beyond boot was found in inspected code. Boot hardware timing,
Continue/scene reseeding and arbitrary indirect writes are not exhaustively
tested. Boot seed literals and weighted draw arithmetic remain likely even
though the modular transitions and Boss parameter patch were demonstrated.
