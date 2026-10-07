---
name: gba-primer
description: GBA hardware reference for reverse engineering — memory map, ARM vs Thumb code, BIOS SWI calls, compression headers, graphics/palette formats, input registers, pointer and literal-pool patterns. Use whenever you need a hardware fact while analyzing Hamtaro or explaining one to the human.
---

# GBA primer

Reference facts. When explaining to the human (who is new to this), translate into plain
language: "the game keeps Hamtaro's X position at address 0x0200xxxx in work RAM".

## Memory map

| Range | Name | Size | Notes |
|---|---|---|---|
| `0x00000000` | BIOS | 16 KB | SWI routines; not readable from game code after boot |
| `0x02000000` | EWRAM | 256 KB | big, slower work RAM — most game state lives here |
| `0x03000000` | IWRAM | 32 KB | fast RAM; hot ARM code is often copied here; stack near `0x03007F00`; IRQ handler pointer at `0x03007FFC` |
| `0x04000000` | I/O | 1 KB | hardware registers |
| `0x05000000` | Palette | 1 KB | BG palettes `+0x000`, sprite (OBJ) palettes `+0x200` |
| `0x06000000` | VRAM | 96 KB | tiles and tilemaps |
| `0x07000000` | OAM | 1 KB | 128 sprites × 8 bytes |
| `0x08000000` | ROM | up to 32 MB | this game: 8 MB, `0x08000000–0x087FFFFF`. File offset = addr − `0x08000000` |
| `0x0E000000` | SRAM | 32 KB here | save memory; 8-bit bus, accessed byte by byte |

## Useful I/O registers

- `0x04000000` DISPCNT (display mode, which BG layers are on)
- `0x04000008/A/C/E` BG0–3CNT, `0x04000010+` BG scroll offsets
- `0x040000B0–0x040000DF` DMA0–3 (games bulk-copy graphics with DMA)
- `0x04000130` KEYINPUT, **active low** (bit clear = pressed): A=0 B=1 Select=2 Start=3
  Right=4 Left=5 Up=6 Down=7 R=8 L=9. Games usually copy this into a RAM "held/pressed" pair
  each frame — finding that pair is an easy first RAM-hunt.

## ARM vs Thumb

- **Thumb**: 16-bit instructions, most game code. `bl` is a 32-bit pair. Common prologue
  `push {r4-r7, lr}` (`0xB5xx`), epilogue `pop {..., pc}` (`0xBDxx`) or `bx lr` (`0x4770`).
- **ARM**: 32-bit instructions, used for interrupt handlers and speed-critical code (often in
  IWRAM). Prologue `stmfd sp!, {..., lr}` (`0xE92D....`).
- A function pointer with **bit 0 set** points to Thumb code (`0x08001235` → Thumb function
  at `0x08001234`). Even pointers used with `bx` are ARM.
- Code loads 32-bit constants (addresses!) from **literal pools** right after the function:
  `ldr r0, [pc, #imm]`. So searching the ROM for the 4 little-endian bytes of an address
  finds the functions that use it → `hamtools rom xrefs <addr>`.

## BIOS calls (`swi N`)

| N | Routine | Why it matters |
|---|---|---|
| `0x05` | VBlankIntrWait | main loop sync — finds the game's frame loop |
| `0x06` | Div | division |
| `0x0B` / `0x0C` | CpuSet / CpuFastSet | memory copy/fill |
| `0x11` / `0x12` | LZ77UnCompWram / Vram | **decompressing graphics/data** |
| `0x13` | HuffUnComp | Huffman decompression |
| `0x14` / `0x15` | RLUnCompWram / Vram | run-length decompression |

In Thumb code a BIOS call is `swi N` = bytes `N 0xDF` (e.g. `11 DF` = LZ77 to WRAM).

## Compressed data headers

First byte = type, next 3 bytes = decompressed size (little endian):
`0x10` LZ77 · `0x24`/`0x28` Huffman (4/8-bit) · `0x30` run-length · `0x81`/`0x82` diff filter.
A plausible LZ77 block: `10 xx xx xx` with a size that is a multiple of 32 (tile data) and
reasonable (< 64 KB). Games may also use their own compression — verify by decompressing.

## Graphics

- Tile = 8×8 pixels. **4bpp**: 32 bytes/tile, 16-color palettes. **8bpp**: 64 bytes/tile, 256 colors.
- Color = 16-bit little-endian **BGR555**: `0bbbbbgggggrrrrr`. `0x7FFF` white, `0x001F` red.
- Tilemap entry (text BG): 16 bits = tile index (10) | hflip | vflip | palette (4).
- OAM entry: 3 × 16-bit attributes (+ 16-bit affine param slot). Y in attr0 low 8 bits,
  X in attr1 low 9 bits, tile index in attr2 low 10 bits.

## ROM pointers and data

- ROM pointers are little endian `xx xx xx 08` (this 8 MB ROM never needs `09`).
- Tables of pointers = runs of 4-byte values all in `0x08000000–0x087FFFFF`, 4-byte aligned.
- Text is usually *not* ASCII on GBA games — expect a custom character table. Find it by
  searching for a known on-screen phrase with relative-value search (letters keep their
  order and spacing, only the base value differs).
