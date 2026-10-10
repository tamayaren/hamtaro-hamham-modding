# Structs

## SavedEventArrays (persistence extents, likely)

The paired save packers/unpackers describe how many bytes are saved, rather
than one contiguous C struct or proven accessor limits. [save.md](save.md)
has the individual block offsets and inverse mappings.

| RAM start | Saved extent | Representation | Confidence |
|---|---|---|---|
| `0x02003990` | `0x200` bytes | 512 u8 event variables | likely persistence; indexed addressing confirmed |
| `0x0201d0b0` | `0x200` bytes | 256 u16 event variables | likely persistence |
| `0x03002170` | `0x60` bytes | 768 packed flags | likely persistence; indexed addressing confirmed |

Sunflower seeds occupy word variable `0x0009`, byte offset `+0x12` from
`0x0201d0b0`. Their status-screen meaning is confirmed by a poke. A saved
array extent does not establish a seed cap or any menu's safe index range.

## SaveBlockHeader (size 0x08; gameplay blocks 1-3 confirmed)

Ordinary blocks in either SRAM bank use this header. Primary and backup
block bases come from ROM tables `0x084673e4` and `0x084673f8`; the backups
are `0x4000` bytes after the primaries. Block zero has special signature
handling and must not be interpreted as an ordinary gameplay block.

| Offset | Size | Name | Meaning | Confidence |
|---|---|---|---|---|
| `+0x00` | 4 | payloadLength | Number of bytes returned by the serializer | confirmed blocks 1-3 |
| `+0x04` | 1 | blockId | Selects packer/unpacker and reserved checksum span | confirmed blocks 1-3 |
| `+0x05` | 1 | subindex | Zero in tested gameplay blocks; record index for block 4 | confirmed zero; record meaning likely |
| `+0x06` | 2 | checksum | Folded complemented sum; valid stored span calculates to zero | confirmed blocks 1-3 |
| `+0x08` | variable | payload | Selected RAM regions packed in block-specific order | named fields confirmed; complete layout likely |

The checksum covers the reserved size, which can be larger than the bytes
actually written. A normal End Game save produced matching banks, valid
checksums and zero tails for blocks 1-3. Continue restored edited fields;
deliberate primary checksum corruption selected the backup bank. These
tests confirm ordinary gameplay headers, rather than block-4 records or
every abnormal recovery path. See [save.md](save.md) for exact evidence.

## RngState (three separate s32 words; positive transitions confirmed)

| Address | Field | Normal range | Update |
|---|---|---|---|
| `0x03000000` | A | 0..30268 | A * 171 modulo 30269 |
| `0x03000004` | B | 0..30306 | B * 172 modulo 30307 |
| `0x03000008` | C | 0..30322 | C * 176 modulo 30323 |

`Util_AdvanceRng` (`0x080003d8`) updates these words and returns a weighted
32-bit sum. Signed BIOS remainder is used; the ranges describe normal,
nonnegative input, not guards against invalid pokes. The identified save
packers do not include this state. See [save.md](save.md) for seeds, constants
and the range helper.

Native writes after a positive triple poke matched all three modular updates.
The all-zero state remained zero after 30 idle frames. Signed edge cases,
boot seeds and full draw arithmetic remain static conclusions.

## HamChatLearnedState (split RAM regions)

| Region | Representation | Meaning | Confidence |
|---|---|---|---|
| Flag IDs 0x0047..0x009c in `0x03002170` | 86 packed bits, endpoint bytes shared with other systems | One-based word ID +0x46 | Bestest bit confirmed; complete mapping likely |
| `0x030037c0`, 0x56 bytes | u8 IDs | Acquisition order, not alphabetical rank | likely; save mapping static |
| `0x03003db0` | u8 | Maintained learned count | confirmed poke and save/Continue |
| Flag 0x00f8, `0x0300218f` mask 0x01 | bit | Dictionary sort mode | confirmed real menu action |

The count and bits can disagree after pokes. The normal learning native
updates bit, order and count together, with a duplicate-word check; that
natural event remains untested. Preserve unrelated endpoint bits when
editing learned flags. Alphabetical rank bytes are a separate ROM table
at `0x084a77bc`. See [items_words.md](items_words.md).

## RescueAndMeterState (three separate event words)

| RAM | Event word | Representation / meaning | Confidence |
|---|---|---|---|
| `0x0201d0c8` | 0x000c | u16 maintained meter level; normal range 0..4 | appearance confirmed; normal progression likely |
| `0x0201d0ca` | 0x000d | u16 weighted meter points; normal cap 56 | fullness confirmed; natural cap likely |
| `0x0201d0cc` | 0x000e | u16 maintained rescue count | Status count confirmed; natural increment likely |

These are saved event words, not a percentage derived from rescue count.
Award native `0x08034490` adds one rescue and a selector-dependent weight,
then raises level at 14-point boundaries. Status reads them separately;
reopening did not reconcile deliberately inconsistent level/points pokes.
No rescue-count cap is established. See [love.md](love.md).

## InventoryMenuIds (48-byte display copy)

At `0x030038d0`, u8 item IDs, 0xff empty. The builder clears and rebuilds
the list using order table `0x084a7ba0` and item-to-flag table `0x084a7bd0`.
IDs 0..46 map to flags 0x009e..0x00cc; ID 47 maps to 0x009d (likely).
Oilcan ID 1 / flag 0x009f is confirmed by reopening after a flag-only poke.
48 slots describe a menu allocation, rather than a consumable stack cap.

## RockRecord (stride 0x04, likely)

Array `0x0201bf90`, 64 records. Saved in block 2 payload +0x05d8.

| Field | Representation | Interpretation | Confidence |
|---|---|---|---|
| First u16 bits 0..6 | 7-bit type ID | Indexes four-byte ROM metadata at `0x08465e48` | likely |
| First u16 bits 7..11 | 5-bit state | Zero means free; nonzero counted as occupied | likely |
| First u16 bits 12..15 | bits | Unclassified | unresolved |
| `+0x02` | two bytes | Unclassified remaining record data | unresolved |

The displayed rock count is separately stored at `0x0201d0c6`. Gain/recount
natives derive it from occupied records. A count-only poke does not grant
rocks. Polishing/gem meanings need the deferred Rubrub state; do not name
the five-bit field durability without that test.

## Challenge arrays (scene-specific, likely)

| Region | Extent | Representation / use |
|---|---|---|
| `0x02003b36` | 9 bytes | Digdig patch IDs: four pairs 1..4 plus special 5/6; removed 0xff |
| `0x03003560` | 9 bytes | Tic Tack-Q marks: zero unmarked, nonzero counts toward completed lines |
| `0x03003af0` | 9 bytes | Shuffled zero-based Tic Tack-Q number labels; helper receives one-based number |
| `0x030035c0` | 16 records, stride 8 | Tic Tack-Q balloon state; exact fields incomplete |
| `0x03003d60` | 10 records, stride 8 | Stickie paper state; exact fields incomplete |
| `0x03003e20` | 3 records, stride 8 | Stickie spawner state; exact fields incomplete |

These are allocations seen in initializers, not interchangeable global
inventories. Never apply one scene's interpretation after changing rooms.
See [challenges.md](challenges.md); runtime structure tests are pending.

## TextState (allocation size 0x34, likely)

Generic text object used by menus and dialogue. `Text_CreateState` at
`0x08004284` requests `0x34` bytes and appends the object to the list rooted at
`gTextStateList` (`0x03000608`). The sentinel is `0x03000610`.
The clubhouse dialogue instance was `0x0202447c`; that address is scene-specific.

| Offset | Size | Name | Meaning | Confidence |
|---|---|---|---|---|
| `+0x00` | 1 | status | Low seven bits select state; observed 3 processing, 4 glyph delay; 1 inactive in static code | likely |
| `+0x05` | 1 | glyphDelay | Delay copied to `+0x06` after a glyph unless status high bit bypasses it | likely |
| `+0x06` | 1 | delayRemaining | Countdown for glyph/scroll timing | likely |
| `+0x0b` | 1 | flags | Includes line redraw and alternate-font flags | likely |
| `+0x0c` | 4 | tileDestination | Destination used when copying rendered text tiles | likely |
| `+0x10` | 4 | cursor | Pointer to the next glyph/control, normally in ROM; can temporarily point to RAM | confirmed by redirect and traces |
| `+0x14` | 4 | returnCursor | Resume location saved during inserted text | confirmed by substitution/resume trace |
| `+0x18` | 4 | glyphBuffer | Buffer used by glyph renderer and copies | likely |
| `+0x1c` | 2 | pixelX | Horizontal glyph position in pixels | likely |
| `+0x1e` | 2 | lineIndex | Incremented by line advance, wrapped for buffer addressing | likely |
| `+0x28` | 4 | previousLinkSlot | Pointer to the list pointer that owns this object | likely |
| `+0x2c` | 4 | next | Next TextState, or sentinel | confirmed list insertion/removal; traversal static |
| `+0x30` | 4 | windowTemplate | Window template pointer; observed `0x08464e5c` in the Boss response | likely format; pointer read observed |

The remaining fields are not mapped. `Text_SetString` (`0x08004258`) initializes
the cursor and status. `Text_Update` (`0x08004548`) reads glyph/control bytes and
advances the cursor. See [dialogue.md](dialogue.md) for controls and experiments.

## Entity (size 0x68)

Element of the array at `*gEntityArray` (`0x03002d88`). Positions are 3D (x, height, y),
all s32 16.16 fixed point. Updated by `Entity_ApplyPhysics` (`0x0800b2f0`) and, for the
player, `Player_Update` (`0x0800631c`).

| Offset | Size | Name | Meaning | Confidence |
|---|---|---|---|---|
| `+0x00` | 4 | spriteDescriptor | Pose selected by room-head command `0xcd`; observed `0x086538d4` for Boss | likely assignment; descriptor/OAM match confirmed |
| `+0x04` | 4 | animationScript | ROM animation script pointer; Boss replay selected a different room-head frame | confirmed |
| `+0x18` | 4 | x | X position | confirmed (poke moved Hamtaro) |
| `+0x1c` | 4 | z | height axis (between x and y; integrated like them) | likely |
| `+0x20` | 4 | y | Y position (screen down = +) | confirmed (poke moved Hamtaro, camera followed) |
| `+0x24` | 4 | vx | X velocity; added to x each update, then zeroed for the player | confirmed |
| `+0x28` | 4 | vz | height velocity | likely |
| `+0x2c` | 4 | vy | Y velocity | confirmed |
| `+0x30` / `+0x34` / `+0x38` | 4 each | ax / az / ay | acceleration added to velocity by `Entity_ApplyPhysics` | likely |
| `+0x3c` / `+0x3e` / `+0x40` | 2 each | ? | accumulate `+0x44` / `+0x46` / `+0x48`; first two clamp to 0x200 (scale?) | guess |
| `+0x4c` | 2 | animationOffset | Byte offset in the current script; reset for animation replay, advanced by command handlers | confirmed replay; static increments |
| `+0x63` | 1 | animationCounter? | Reset by the animation setter; exact counter purpose unmapped | likely |

Player velocity comes from `kPlayerMoveVelocityTable` (`0x08467af0`): 2 speed modes
(walk, run while B held) × 4 directions (Up, Down, Left, Right) × (vx, vy) s32 16.16.
Walk = 1 px/frame, run = 2 px/frame, measured against the frame counter. Only one direction
applies at a time (Up > Down > Left > Right priority), so there is no diagonal movement.

Ordinary input clears all three velocity fields before selecting a complete
table value, and `Player_Update` clears X/Y velocity after the position update.
This path does not build speed by accumulating acceleration. Generic entities
can use acceleration through `Entity_SetAcceleration` (`0x0800af38`) and
`Entity_ApplyPhysics`; that does not establish a separate player jump or dash.
See [challenges.md](challenges.md) for scene-specific motion candidates.

## RoomHeadSlotRecord (stride 0x11c, likely format)

Table base `0x08469cdc`; slot = `(Entity index - 10) / 3`. Boss index 16 uses
slot 2, record `0x08469f14`. This describes room OBJ heads, not BG dialogue faces.

| Offset | Size | Field | Meaning | Confidence |
|---|---|---|---|---|
| `+0x00` | 4 | tileBuffer | Decompression destination; slot 2 `0x0201d2b0` | confirmed buffer match |
| `+0x04` | 4 | vramDestination | OBJ row-upload base; slot 2 `0x06010e20` | confirmed VRAM rows |
| `+0x08` | pointer array, bounds unknown | poses | Command `0xcd` selects one by index; first slot-2 pointer `0x086538d4` | likely selection; descriptor/OAM match confirmed |
| `+0x118` | 1 | widthTiles | Number of 32-byte tiles per source row; observed 6 | likely semantics; 6-tile row match confirmed |
| `+0x119` | 1 | heightTiles | Number of rows; observed 6 | likely semantics; six uploaded rows confirmed |
| `+0x11a` | 2 | unknown | Remaining record bytes | unmapped |

Each row advances `widthTiles * 32` source bytes and `0x400` VRAM bytes.
The first pose is one 64 x 64, 4bpp OBJ, relative `(-12,-20)`, tile `0x50`,
palette bank 4. The head occupies an inset 6 x 6 tile area of this canvas.
Other pose entries and record count remain unmapped. See [portraits.md](portraits.md).

## GfxCopyQueueEntry (size 0x0c, likely)

The queue at `0x03000840` consists of three-word entries, indexed by a byte
cursor at `0x03002e24`. `Gfx_QueueTileRows` stores one entry per 4bpp row;
`Gfx_FlushCopyQueue` consumes entries and selects halfword/word DMA3 copies.

| Offset | Size | Field | Meaning | Confidence |
|---|---|---|---|---|
| `+0x00` | 4 | sourceOrFill | Source pointer, or flagged fill value | likely format; observed Boss DMA source confirmed |
| `+0x04` | 4 | destination | Graphics-memory destination | likely format; observed Boss destinations confirmed |
| `+0x08` | 4 | byteCount | Bytes to transfer; converted to DMA unit count | likely format; `0x480` tile transfer confirmed |

Fill encoding and queue limits were not independently tested.

## InputState (minimum covered size 0x14)

Base: `0x03000820`. Updated by `Input_Update` at `0x08009614` (Thumb).
The covered region ends at `+0x14`; the exact allocation size is unknown.
All identified fields use u16 storage. `+0x0a` is an unclassified two-byte gap.
`gKeysPrevious` is separate storage at `0x03000838`, accessed through its own pointer.

| Offset | Address | Size | Name | Meaning | Confidence |
|---|---|---|---|---|---|
| `+0x00` | `0x03000820` | 2 | `gKeysHeld` | Current active-high button mask, low 10 bits | confirmed |
| `+0x02` | `0x03000822` | 2 | `gKeysPressed` | `held & ~previous`; pure new presses, no repeat | confirmed |
| `+0x04` | `0x03000824` | 2 | `gKeysPressedRepeat` | Initially pure new presses; replaced by held mask when repeat countdown reaches zero | confirmed |
| `+0x06` | `0x03000826` | 2 | `gKeysReleased` | `previous & ~held`, one-poll release pulse | confirmed |
| `+0x08` | `0x03000828` | 2 | `gInputDpadPacked` | Packed high/low bytes from indexed D-pad tables | likely |
| `+0x0a` | `0x0300082a` | 2 unmapped bytes | unknown | No interpretation or type assigned | — |
| `+0x0c` | `0x0300082c` | 2 | `gInputRepeatInitialDelay` | Initial countdown; title value 90 | confirmed |
| `+0x0e` | `0x0300082e` | 2 | `gInputRepeatInterval` | Countdown reload at repeat; title value 4 | confirmed |
| `+0x10` | `0x03000830` | 2 | `gInputRepeatCountdown` | u16 countdown, initial load followed by same-poll decrement | confirmed |
| `+0x12` | `0x03000832` | 2 | `gInputUnchangedMaskFrames` | Static unchanged-held-mask counter; boundary behavior untested | likely |

Repeat timing was tested with L for 40 and 101 sampled held frames and R for 110.
With initial delay 90, first repeat occurred 89 frames after the first held poll.
Three L repeat hits spanned eight frames; six R repeat hits spanned twenty frames,
matching interval 4. Both the initial load and countdown/interval writer sites
were captured. Initial-delay restart occurs in the static code when
`pressed != 0 && pressed == held`; its behavior during partial-mask additions was
not separately timed. Countdown continues to decrement without held buttons.

For `+0x08`, the static code uses `index = (held & 0x00f0) >> 4` and, when index
is nonzero, stores `(table[0x08469cb4][index] << 8) | table[0x08469ca4][index]`.
The literal at `0x080096a4` points to the high-byte table `0x08469cb4`; the
literal at `0x080096a8` points to the low-byte table `0x08469ca4`. There is no
write on this path when no D-pad button is held, so static code suggests the last
value persists. Table purpose, individual byte meanings, and persistence were
not separately tested; confidence remains likely.

For `+0x12`, the static condition is `held == previous && count != 0xffff`:
increment if true, otherwise set zero. At `0xffff`, the branch at `0x08009666`
reaches `0x0800967c` (`mov r0,#0`), then stores at `0x0800967e`. This resets
rather than saturates. A 65,536-frame boundary experiment was not performed;
the counter semantics and boundary remain likely.

Confidence comes from empirical button/watchpoint transitions and timer timing,
corroborated by the parent's disassembly. The one script poke had no successful
post-write observation and provides no confirming evidence. See
[findings.md](findings.md) for the tests and tool limitations.
