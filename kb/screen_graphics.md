# Screen graphics export — 2026-10-11

Addresses apply to the verified USA AH3E ROM, SHA1
`2525cc23524068dfb3a2b4e0ce7b736f95023e82`.

## Reproduce the export

```powershell
$env:UV_CACHE_DIR = '.cache/uv'
uv run hamtools rom verify
# Capture the current emulator without pressing buttons:
uv run hamtools gfx screen --out extracted/gfx/screens/my-scene
# Or export a saved screen without starting the emulator:
uv run hamtools gfx screen --state states/gameplay-boss-random-ready.ss0 --out extracted/gfx/screens/boss-saved
```

The output directory must remain under `extracted/gfx/`. Omit `--out` for a
new timestamped directory. `--no-rom-scan` skips source hunting; `--force`
allows replacement of an existing export. The original ROM is verified again
before export. A saved state's ROM CRC is reported separately: a patched-ROM
state can hold different graphics even when exporting against the original.

Each export contains:

- `screen.png`, `reconstructed-screen.png`, `overview.png`, and `manifest.json`.
- `sprites/`: visible OAM pieces, indexed native PNGs, RGBA `-display.png`
  previews with horizontal/vertical flips, tile-aligned `-crop.png` previews,
  native `.4bpp`/`.8bpp` tile bytes, and per-piece address/geometry metadata.
- `room-heads/`: complete source frames for active slots whose RAM buffer,
  six row uploads and visible OAM consumer agree. These omit the transparent
  padding of the larger hardware sprite canvas.
- `backgrounds/`: enabled text BG maps, scrolled 240 x 160 viewports,
  tile atlases rendered with each referenced palette, native tiles and maps.
- `palettes/` and `palettes.png`: all sixteen BG and sixteen OBJ banks,
  BGR555 `.pal` files, PNG swatches, and colour/address JSON. Some loaded banks
  and offscreen map cells are unused by the visible viewport.
- `raw/`: frozen I/O, palette, OAM and VRAM; `capture.ss0` for a live export.
- `rom-sources.json` and `rom/`: every exact candidate from raw ROM or aligned
  BIOS LZ77 streams; retained streams and decompressed blocks stay local.

These are **export-only** screen assets. The existing portrait PNG importer
does not automatically turn arbitrary sprites or maps into mod recipes.
All PNGs, colours, savestates and binary streams stay gitignored.

## Verified clubhouse screen

The original ROM was launched with the human-selected Boss gameplay state,
then a fresh live state was captured at frame 100565. Its CRC32 `0xcd48b673`
matches the original ROM. The supplied older state has CRC32 `0x72370cf2`;
it was preserved. Local evidence is under
`extracted/gfx/screen-hunt/boss-gameplay/`.

The screen export has **25 visible OAM pieces, three complete 48 x 48 room
frames, two enabled text backgrounds, and 32 palette banks**. Combining
the decoded BG viewports and sprites by priority produces **0 differing
pixels out of 38,400** against the frozen emulator screenshot. Thus the
captured tile indices, palettes, positions, flips and layer ordering are
confirmed for this screen. This is a complete screen match, not an identity
guess based on a standalone tile atlas.

`DISPCNT = 0x1a00`: mode 0, 2D OBJ mapping, BG1/BG3/OBJ enabled. BG1 control
`0xdc06` selects 4bpp tiles at `0x06004000`, a 512 x 512 map at `0x0600e000`,
priority 2, scroll `(39,31)`. BG3 control `0x1700` selects tiles at
`0x06000000`, a 256 x 256 map at `0x0600b800`, priority 0. Its visible
viewport is transparent; dialogue tiles remain in offscreen map cells.

| Room frame | RAM buffer | First VRAM row | OBJ bank / OAM | Runtime evidence |
|---|---|---|---|---|
| Hamtaro, slot 0 | `0x02002590` | `0x06010c20` | 2 / 21 | player Entity 10 points to pose `0x08653494`; OAM at `(93,45)` |
| Boss, slot 2 | `0x0201d2b0` | `0x06010e20` | 4 / 22 | Entity 16 points to pose `0x086538d4`; OAM at `(93,21)` |
| Hamster in bed, slot 3 | `0x0201dab0` | `0x06010f20` | 5 / 20 | Entity 19 points to pose `0x08653af4`; OAM at `(37,101)` |

All three are six tiles wide by six tiles high, `0x480` source bytes,
uploaded as six `0xc0`-byte rows with VRAM stride `0x400`. Their hardware
canvas is 64 x 64; the source frame is inset by one tile row and column.
The buffer/VRAM/frame relationships are **confirmed by the exact live
memory and rendered-screen comparisons**. Entity 13 is inactive: Bijou is
not visible in this capture. The sleeping character's personal name remains
unconfirmed; the export uses the slot number rather than a guessed identity.

## ROM source candidates

The following are **likely sources**, from exact decompression matches and
static script references. New loader executions were not probed. Boss's
frame already had independent runtime confirmation in [portraits.md](portraits.md).
Repeated matching palettes remain separate candidates in the local JSON.

| ROM source | Compressed / decoded bytes | Observed content |
|---|---|---|
| `0x0811d6ac` | `0x24` / `0x20` | Hamtaro OBJ bank 2; identical palette also occurs in two larger streams |
| `0x0811de38` | `0x157` / `0x480` | complete Hamtaro back-facing room frame in slot 0 |
| `0x0817bb88` | `0x26` / `0x20` | bed hamster palette; loaded OBJ banks 5 and 6 match |
| `0x0817bdf0` | `0x20b` / `0x480` | complete bed hamster room frame in slot 3 |
| `0x081b9f74` | `0x24` / `0x20` | Boss OBJ bank 4; existing likely palette source |
| `0x081b9f98` | `0x222` / `0x480` | Boss greeting room frame in slot 2; existing confirmed frame |
| `0x0824258c` | `0x27c8` / `0x4f00` | room background tiles; entire decoded block matches `0x06004000` |
| `0x08244d54` | `0x50b` / `0x1000` | scenery OBJ tiles at `0x06015000`; doors and furniture pieces |
| `0x08245260` | `0x70d` / `0xec0` | extra loaded OBJ tiles at `0x06012800`; individual roles incomplete |
| `0x08245970` | `0xc5` / `0xe0` | seven BG palette banks, 9..15 at `0x05000120` |
| `0x08245a38` | `0x43` / `0x40` | scenery OBJ palette banks 14/15 at `0x050003c0` |
| `0x08245a7c` | `0x3e7` / `0x800` | first 32 x 32 BG1 map block at `0x0600e000`; shadow `0x0200eb90` |
| `0x08245fa8` | `0x67` / `0x100` | additional BG1 map data at `0x0600f000`; shadow `0x02012b90` |

Faraday's static scene 1.1 walk found the corresponding setup loads at
`0x08050f84`, `0x08050f8e`, `0x08050f97`, `0x08050fbf` and `0x08050fe2`.
Palette source operands include `0x08051879` (BG bank pack), `0x08051882`
(Hamtaro), `0x0805189d` (bed hamster), and `0x080518c1` (scenery pack).
Static reachability corroborates the matches without proving that every
conditional load executed. The scan checks raw exact content and
four-byte-aligned type-0x10 headers with decoded lengths `0x20..0x18000`
divisible by 32. Other compression, unaligned headers, transformed data,
computed references and additional animation frames require further work.

## Decoder scope and validation

The frozen memory layout follows
[mGBA's version-11 state definition](https://github.com/mgba-emu/mgba/blob/master/include/mgba/internal/gba/serialize.h).
The PNG `gbAs` chunk is checksummed and its decompression is bounded.
Unknown versions, other game codes and invalid payloads are refused.
GBA OBJ addressing was checked against
[mGBA's OBJ renderer](https://github.com/mgba-emu/mgba/blob/master/src/gba/renderers/software-obj.c).

Source PNGs support ordinary 4bpp/8bpp tiles, both OBJ mapping modes,
hardware sprite dimensions, text BG screen blocks, flips, scroll wrapping
and transparent index zero. Affine OBJ pixels are exported in native
orientation; their transforms are not reconstructed. Display windows,
blending and mosaic are omitted from the composite; unsupported affine or
bitmap BGs retain raw VRAM and produce an explicit note. This scene's exact
comparison does not establish exact reconstruction for those other effects.

Synthetic tests cover state/checksum validation and bounded inflation,
OBJ strides/alignment/wrap, visibility and flips, BG screen-block layout and
scroll wrap, 8bpp tile layout, complete room-frame uploads, preservation of
ambiguous ROM matches, and refusal of unverified ROMs or external outputs.
All **444 tests passed**. The 28 delivered native sprite/frame PNGs encode
back to their tile files exactly, and all 129 PNG outputs passed integrity
checks. Local `verification.json` records the counts, SHA1 and screen match.
