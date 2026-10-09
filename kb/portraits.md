# Boss dialogue portrait and room head graphics

Addresses apply to the verified USA AH3E ROM, SHA1
`2525cc23524068dfb3a2b4e0ce7b736f95023e82`. All extracted graphics and
runtime evidence stay under `extracted/gfx/`.

## Correction to the earlier identification

`0x081bfc74` and `0x081bfa60` are Boss's **head in the room**, drawn with
OBJ sprites. Replaying their Entity animation changed the room head while
the face beside the dialogue stayed the same. The old `boss-portrait-demo`
therefore swaps a room-head frame. Its pointer and decompression tests remain
valid; the earlier identification as the dialogue face was too broad.
The affected symbols have been renamed to make this distinction explicit.

The actual dialogue face is a BG3 image at `0x080eb9bc`, with its own palette
at `0x080f437c`. `boss-recolor` changes this image's colours independently of
the room sprite.

## Dialogue-window portrait

| Address | Meaning | Confidence |
|---|---|---|
| `0x080eb9bc` | Boss dialogue tiles; LZ77, `0x33a` compressed / `0x480` decoded bytes | confirmed: live VRAM match |
| `0x080f437c` | Boss dialogue palette; LZ77, `0x26` compressed / `0x20` decoded bytes | confirmed: palette match and relocated palette test |
| `0x084b1dbb` | Event `0x06` loads left-slot palette | confirmed: operand reads |
| `0x084b1dbc` | Unaligned palette source operand | confirmed: read and checked repoint |
| `0x084b1dc4` | Event `0x06` loads left-slot tiles | confirmed: operand reads and upload |
| `0x084b1dc5` | Unaligned image source operand | confirmed: read and exact VRAM match |
| `0x084b1dce` / `0x084b1dcf` | Other-slot palette command / operand; destination `0x05000040` | likely: static decode; this slot was not displayed |
| `0x084b1dd7` / `0x084b1dd8` | Other-slot image command / operand; destination `0x06003700` | likely: static decode |
| `0x02007710` | Left portrait tile shadow, `0x480` bytes | confirmed: DMA source and raw match |
| `0x0201bbf0` | Left portrait palette shadow, `0x20` bytes | confirmed: DMA source and original/edited matches |
| `0x06003b80` | Live left-slot BG tiles | confirmed: watched DMA and exact match |
| `0x05000060` | Live BG palette bank 3, sixteen BGR555 colours | confirmed: palette match and visible recolour |

The image is **48 x 48, 4bpp**, comprising 36 row-major 8 x 8 tiles.
Each tile is 32 bytes; the low nibble is the left pixel of each pair.
Colours are sixteen little-endian BGR555 words. PNG export preserves indices
and duplicate colours, with index 0 transparent; the portrait also has opaque
white pixels. Format and geometry are **confirmed** by the exact VRAM match
and correctly displayed recolour.

BG3 uses character block 0 and screen block 23 (`0x0600b800`). In this window,
rows 21..26, columns 1..6 contain tiles `0x1dc..0x1ff`, palette bank 3, in
row-major order. The top-left tilemap entry is `0x0600bd42`; its tile is at
`0x06003b80`. The image appears at screen `(8, 104)` in this scene.
These tilemap contents and screen geometry are confirmed. The background is
scrolled with the window; reads of write-only scroll registers are not evidence
of scroll values. **The dialogue face uses a BG tilemap, not OAM.** Other
window positions and slots need their own scene checks.

## Decompressor and upload

`Event_CmdLoadLzGraphics` (`0x08001658`) handles event `0x06`: source and
destination pointers, read bytewise, nine bytes including the opcode.
It calls `Bios_LZ77UnCompWram` (`0x080e5614`), BIOS `swi 0x11`.
For a VRAM destination it decompresses at `destination + 0xfc003b90`, giving
`0x02007710` for Boss's `0x06003b80`. For a palette destination it uses
`destination + 0xfd01bb90`, giving `0x0201bbf0` for `0x05000060`.
With display enabled, `Gfx_QueueCopy` (`0x08009ac8`) queues the copy;
`Gfx_FlushCopyQueue` (`0x08009824`) uploads it via DMA3 at VBlank.

Source reads were reported at PCs `0x08001666`, `0x08001668`, `0x0800166e`,
`0x08001674`: exact Thumb instructions `0x08001662`, `0x08001664`,
`0x0800166a`, `0x08001670`. Uploads were reported at PC `0x0800992c`,
DMA setup instruction `0x08009928`. Tile-transfer registers showed source
`0x02007710`, destination `0x06003b80`, count `0x480` bytes; palette-transfer
registers showed source `0x0201bbf0`, destination `0x05000060`.
The Boss loader path and these uploads are **confirmed**. Forced-blank,
other destination, and event `0x07` branches remain static evidence only.

The complete image already contains eyes and mouth. During the tested greeting
and response it stayed equal to this full image: **no blink or mouth overlay
was observed for this dialogue portrait**. This does not exclude different
expressions elsewhere. The room head animates through separate complete frames.

## Room-head assets and Entity animation

| Address | Meaning | Confidence |
|---|---|---|
| `0x081b9f74` | Room-head palette; LZ77, `0x24` compressed / `0x20` decoded bytes | likely source: unique decoded match to live OBJ bank 4; load command not replayed |
| `0x081b9f98` | Greeting room-head frame; expands to `0x480` bytes | confirmed: live buffer and VRAM matches |
| `0x081bfa60` | Alternate room-head frame; `0x213` compressed / `0x480` decoded | confirmed by earlier replay |
| `0x081bfc74` | Idle room-head frame; `0x222` compressed / `0x480` decoded | confirmed by replay and pointer demo |
| `0x08687e17` / `0x08687e18` | Idle Entity animation / unaligned frame operand | confirmed |
| `0x08687dde` / `0x08687ddf` | Alternate Entity animation / operand | confirmed by replay |
| `0x0201d2b0` | Slot 2 room-head tile buffer | confirmed |
| `0x06010e20` | Slot 2 OBJ row-upload base | confirmed: frame tiles match row-strided VRAM |

`Anim_CtrlLoadRoomHeadTiles` (`0x0800d014`) reads `0xcb` plus its four-byte
source and calls the same BIOS wrapper. It selects `(Entity_GetIndex() - 10) / 3`
and reads the first word of `0x08469cdc + slot * 0x11c`; Boss index 16 selects 2.
Slot 0 uses `0x02002590`; slot 1 uses `0x0201fcd0` (both likely static pointers).

`0xcc`, `Anim_CtrlUploadRoomHeadTiles` (`0x0800d074`), reads destination
`+0x04` and tile width/height `+0x118/+0x119` from that record. Boss has
`0x06010e20`, 6, 6. `Gfx_QueueTileRows` (`0x08009b80`) queues six `0xc0`-byte
rows, source stride `0xc0`, destination stride `0x400`: the **2D OBJ grid's
32-tile row stride**. This explains why a contiguous VRAM search missed it.
The matched layout is confirmed; helper/command interpretation remains likely.

`0xcd` at `0x0800d0c8` takes a delay and pose index and assigns the descriptor
at record `+0x08 + pose * 4` to Entity `+0x00` (likely). The first slot-2
descriptor is `0x086538d4`: one 4bpp 64 x 64 OBJ, relative `(-12, -20)`,
starting tile `0x50`, palette bank 4. Its matching live OAM entry was at
`(93, 21)`. The uploaded 48 x 48 head sits one tile row/column inside this
64 x 64 canvas. Descriptor geometry and matching OAM are confirmed; the full
pose table remains unmapped. Scripts load full head frames with changing
mouth/eyes; no separate overlay was identified in this path.

Text `0xf4` invokes a **scene callback**, not a universal portrait ID.
`Scene_InvokeCallback` (`0x08001440`) indexes `0x03001fb0`. Here `0x08`
calls `Boss_CallbackIdleAnimation` (`0x0804193c`) and sets the room-head
animation to `0x08687e17`. Its table read was reported at PC `0x0800144e`,
instruction `0x0800144a`, LR `0x08005569`. Callbacks `0x09` (`0x080418b8`)
and `0x16` (`0x080418dc`) select `0x08679610` and `0x08687dde` (likely).
Boss was Entity 16 at `0x02022e8c`, array base `0x0202280c`, stride `0x68`;
script pointer `0x02022e90`, offset `0x02022ed8`. These are scene observations.

Room-head palette source references include event operands at `0x08051894`
(destination `0x05000280`) and `0x08687cd2` / `0x08687cde`. General room-head
editing and the remaining pose/animation commands are outside the gfx registry.

## Editing and verification

See [the graphics guide](graphics.md). The supported asset is `boss-portrait`.
An unchanged PNG preserves both original compressed streams exactly.
Imports produce source recipes containing only changed pixels/colours and
original-stream SHA1s. The builder reconstructs and recompresses locally,
allocates alongside code/text in checked padding starting at `0x086d0000`,
and checks both unaligned pointer operands. Gfx-only mods need no ARM compiler.
See [the free-space audit](rom_map.md#free-space-audit-2026-10-10).

`patches/boss-recolor` changes palette entries 4 and 5. The 38-byte replacement
at `0x086d0000` serves both palette operands; the original allocations remain
untouched. The left portrait is visibly blue, with unchanged tile data and
exact expected palette data in RAM and graphics memory. Cold boot, greeting,
response pages, conversation close/repeat, and surrounding animation were
checked. The other portrait slot, room changes, and longer play remain human
checks.

An already-open original savestate contains the old palette in RAM. Start a
fresh conversation after loading it, or use `states/dialogue-hunt-base.ss`,
press A, then A to choose Hamha. `states/boss-recolor-visible.ss` was captured
on the patched ROM. The human's `boss-portrait.ss0` was copied to
`boss-portrait.ss` for the bridge's naming convention; its original was retained.

Evidence: `extracted/gfx/` contains PNGs, original/recoloured upload traces,
raw comparisons, and verification JSON. Earlier room-head traces remain at
`extracted/dialogue-hunt-20261009/`.
