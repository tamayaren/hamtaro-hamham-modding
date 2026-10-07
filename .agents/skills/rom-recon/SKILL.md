---
name: rom-recon
description: Static exploration of the Hamtaro ROM without an emulator — verify the dump, read the header, hexdump an address, search for byte patterns or strings, find code/data that references an address (xrefs), and locate free space. Use before any ROM analysis or when looking for where a value, table, or string lives in the ROM.
---

# ROM recon

All commands run from the repo root. They read the ROM from `gba/` (or `$HAMTARO_ROM`)
and never modify it.

## 1. Always start by verifying

```
uv run hamtools rom verify
```

If the SHA1 doesn't match, stop — every address in `kb/` assumes this exact dump.

## 2. Commands

| Command | Does |
|---|---|
| `uv run hamtools rom info` | header fields, header checksum, save type, used size, free space |
| `uv run hamtools rom peek 0x08000000 [--len 64]` | hexdump at a ROM address (values below `0x02000000` are treated as file offsets) |
| `uv run hamtools rom find --hex "11 DF"` | every offset of a byte pattern (`??` wildcards allowed) |
| `uv run hamtools rom find --ascii "SRAM_"` | ASCII search |
| `uv run hamtools rom find --u32 0x02001234` | find a 32-bit little-endian value (literal pools, tables) |
| `uv run hamtools rom xrefs 0x0200xxxx` | same as `--u32`, also tries the Thumb (+1) form for ROM addresses; reports aligned hits only |

`find` also takes `--align 4` (word-aligned hits only). Add `--limit N` to cap results.
Output is addresses in `0x08xxxxxx` form.

## 3. Recipes

- **Who uses this RAM address?** `rom xrefs 0x0200ABCD` → each hit is a literal pool
  word; the function using it starts somewhere before the hit (scan back for a `push {…, lr}`
  prologue, or ask Ghidra once available).
- **Who calls this function?** `rom xrefs 0x08012344` (finds pointer tables and `ldr`+`bx`
  calls). Direct `bl` calls are PC-relative and won't show up — that needs Ghidra.
- **Find decompression calls:** `rom find --hex "11 DF"` (LZ77 → WRAM), `"12 DF"` (→ VRAM).
- **Find compressed blobs:** `rom find --hex "10 ?? ?? 00"` then sanity-check sizes; see the
  `gba-primer` skill for the header format.
- **Free space for patches:** `rom info` reports the trailing `0xFF` region. Before using any
  part of it, confirm nothing references it (`rom xrefs` on its start address).

## 4. Rules

- Output from these commands may include ROM bytes. Short signatures in `kb/` are fine;
  dumps go to `extracted/` (gitignored), never to tracked files.
- Record every confirmed location with the `kb-update` skill.
