# Structs

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
