# Graphics editing: Boss dialogue portrait

The first Phase 2 asset is `boss-portrait`, the face beside Boss's dialogue.
See [portraits.md](portraits.md) for the verified addresses and the distinction
between this BG image and the separate room-head OBJ animation.

## Export and import

```powershell
$env:UV_CACHE_DIR = '.cache/uv'
uv run hamtools rom verify
uv run hamtools gfx list
uv run hamtools gfx export boss-portrait
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
without its sidecar requires `--asset boss-portrait`.

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
are preserved, and both known unaligned operands are repointed with original-byte
checks. Code, graphics, text and manual edits share the collision map; duplicate
replacements, overwritten source/references, non-padding targets and exhaustion
fail. Gfx-only recipes need no ARM compiler.

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

Only this asset is in the registry. Other NPCs, other expressions, arbitrary
tilemaps, 8bpp, custom compression and room-head editing need mapping before
support is added. The two known dialogue slots are repointed; only the left
slot was exercised. The padding audit supports conservative tested allocations,
not a claim that every possible game path ignores the whole tail.

Tests use synthetic graphics; the real-ROM roundtrip skips when the dump is
missing or mismatched and keeps its temporary artifacts under `extracted/gfx/`.
When a running Windows MCP executable prevents uv from reinstalling this project,
sync added dependencies separately and set `UV_NO_SYNC=1` for the active session.
