# Graphics editing: dialogue portrait catalogue

All 136 definitions in the standard dialogue portrait bank are named assets.
See [portraits.md](portraits.md) for the catalogue, exact script roots, honest
name confidence, and the distinction between BG faces and room-head OBJ animation.
Hamtaro, Bijou and Boss are identified live; other speaker/role names are guesses.
Unidentified entries keep numeric names. Six definitions have no reached root.

## Export and import

```powershell
$env:UV_CACHE_DIR = '.cache/uv'
uv run hamtools rom verify
uv run hamtools gfx list
uv run hamtools gfx export boss-portrait
uv run hamtools gfx export bijou-portrait
```

This writes `extracted/gfx/boss-portrait.png` and an asset/hash `.json` sidecar.
Edit the PNG locally. Keep it 48 x 48 pixels, with alpha either 0 or 255.
An indexed editor can recolour palette entries without changing pixel indices.
If saving truecolour, preserve transparency. Outputs always stay under
`extracted/gfx/`; existing exports need `--force` to replace them.

```powershell
uv run hamtools gfx import extracted/gfx/boss-portrait.png --out patches/my-boss/mod.toml
# To change colours or generate a new palette:
uv run hamtools gfx import extracted/gfx/edited-boss.png --asset boss-portrait --palette new --out patches/my-boss/mod.toml --force
uv run hamtools patch build my-boss
```

The default `--palette original` maps edited pixels to the nearest existing
opaque colour, without dithering. `--palette new` preserves a compatible
indexed PNG's indices and edited palette. Other PNGs are quantized deterministically
in BGR555 space to at most fifteen opaque colours plus index 0 transparency.
Partial alpha, wrong dimensions, animation, damaged PNGs and 16-bit channels
are rejected. Duplicate colours do not lose their original indices on an
unchanged export/import; both compressed streams are reused exactly.

Asset inference uses the sidecar, or the exported filename. A renamed PNG
without its sidecar requires `--asset <name>` from `hamtools gfx list`.
The list reports source addresses, slots, name confidence, possible scene roots,
and every affected asset sharing either stream. Export/import JSON sidecars also
record that sharing; keep them beside the local images.

## Public source format and build placement

Import writes a disabled-by-default `[[gfx]]` mod recipe under `patches/`.
It stores original compressed-stream SHA1s and **only changed pixels/colours**.
It never stores an original palette, image, compressed bytes, or a dependency
on a local PNG. Review that differences are your authored edits before committing.
The complete re-encoded streams are local inspection outputs under
`extracted/gfx/imports/<mod>/`, not patch inputs.

The builder reads your verified original ROM, validates hashes and original
four-byte operands, reconstructs the image/palette, and compresses changed data
using BIOS-compatible LZ77. Changed streams are allocated on four-byte boundaries
inside the checked padding pool starting at `0x086d0000`. Original allocations
are preserved, and **every mapped reference to each changed source** is repointed
with original-byte checks, across entries and both defined slots. Code, graphics,
text and manual edits share the collision map; duplicate
replacements, overwritten source/references, non-padding targets and exhaustion
fail. Gfx-only recipes need no ARM compiler.

Shared changes are global: editing an image shared by sixteen NPC definitions
changes that image for all sixteen, while their distinct palettes remain intact.
Editing a shared palette changes every consumer of that palette. Two recipes
competing to replace one shared source are refused, even if their names differ.
The error names the source and affected entries; combine the authored changes
into one recipe for that source. Per-speaker splitting is not implemented.

Before relocating, import/build searches every unaligned four-byte window for
the source pointer and its two cartridge mirrors. An occurrence outside the
mapped reference union is refused with its address; it is not silently ignored
or automatically treated as an event operand. All catalogue streams pass this
check against the verified original dump. Computed or native-only references
outside static evidence remain a coverage limitation requiring scene playtests.

Build explicitly by mod name. `build/hamtaro-mod.gba` and
`build/hamtaro-mod.bps` are local outputs, and the BPS is self-checked by applying
it back to the original ROM. Neither should be committed.

## First example and limits

```powershell
uv run hamtools patch build boss-recolor
```

This changes only Boss's dialogue fur/shadow palette entries 4 and 5 to blue.
The image, text, room sprite and original ROM remain unchanged. See
[the example's playtest steps](../patches/boss-recolor/README.md).

Savestates hold already-uploaded graphics and palette RAM. An original state
with the face on screen will initially retain old colours: close it and talk
again to reload the palette from the patched ROM. The supplied
`states/dialogue-hunt-base.ss` can start a fresh conversation with A, then A
to select Hamha. `states/boss-recolor-visible.ss` shows the verified result.

Every standard-bank image/palette definition and both slot loaders are in the
registry. Many definitions are colour variants rather than different expressions;
the monkey variant is an alias. Hamtaro's left and Bijou's right slots are verified
with exact graphics/shadow matches and imported edits. Other scenes and named
expressions still need identity checks. Arbitrary tilemaps, 8bpp, custom compression
and room-head editing remain outside this catalogue. The padding audit supports
the tested allocations; it does not establish that every game path ignores the tail.

## Two-speaker import demo and exact playtest

```powershell
uv run hamtools patch build portrait-catalogue-demo
```

This disabled example uses only authored differences: blue Hamtaro (two palette
colours and one pixel) and green Bijou (two palette colours). It relocates three
streams and checks six operands. Build it explicitly, so it runs without the
human's unrelated faster-walk edit. See [the demo checklist](../patches/portrait-catalogue-demo/README.md).

Load `states/portrait-catalogue-companion-base.ss` in the built ROM. Press A to
open Ham-Chat, then A to select Hamha. During the greeting Hamtaro appears on the
left and Bijou on the right; the window then hands over to Boss. The separate
`states/portrait-catalogue-demo-visible.ss` captures the imported colours.
The companion baseline has the known flag 0x0010 temporarily set for the test;
it is separate from the preserved original Boss baseline. Do not use a state
whose graphics were already uploaded to judge whether a new import loaded.

Tests cover inline operands, shared root provenance, unvisited partners, reference
unions, competing edits and unknown pointers using synthetic data. ROM-gated
checks audit all 2,711 reached graphics loads, all definitions, unchanged PNG
roundtrips in both palette modes for every entry, and authored edits to all 187
distinct source streams. They skip if the dump is missing or mismatched and keep
temporary extracted artifacts under `extracted/gfx/`.
When a running Windows MCP executable prevents uv from reinstalling this project,
sync added dependencies separately and set `UV_NO_SYNC=1` for the active session.
