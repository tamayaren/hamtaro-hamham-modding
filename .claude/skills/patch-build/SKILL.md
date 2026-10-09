---
name: patch-build
description: Write and build mods for Hamtaro — byte edits with original-byte checks, C/asm code compiled into ROM free space, Thumb BL hooks and pointer redirects — producing build/hamtaro-mod.gba and a shareable .bps patch. Use when changing game behavior, values, or code.
---

# Building mods

A mod is `patches/<mod-name>/mod.toml` plus optional sources. Full format: the docstring
at the top of `tools/hamtools/patch.py`.

```
uv run hamtools patch list                 # mods and whether enabled
uv run hamtools patch build                # all enabled mods
uv run hamtools patch build <mod> [...]    # only these
```

Outputs (gitignored): `build/hamtaro-mod.gba`, `build/hamtaro-mod.bps`, `build/obj/mod.map`.

## Choosing the technique

| Goal | Technique |
|---|---|
| Change a constant (speed, price, limit) used by code | `[[edit]]` the instruction's immediate (e.g. `movs r0, #2` → `#4`) or the data table entry |
| Change data (palette entry, stat table) | `[[edit]]` on the data |
| Replace dialogue with authored text | `[[text]]` with the original stream address, `expect_sha1`, and replacement `text` in tag notation; see `kb/text_dump.md#editing` |
| Add/replace logic | C function in `sources`, then `[[hook]]` a `bl` to call it, or `[[pointer]]` to swap a function pointer |

## Rules

- **Every edit/hook/pointer needs `expect`** — the original bytes at that address. Get them
  with `uv run hamtools rom peek <addr> --len N`. The build refuses to patch if they differ,
  which catches wrong addresses.
- Short `expect`/`hex` strings are fine in git; never paste larger ROM data into a mod.
- A `[[hook]]` overwrites 4 bytes with a Thumb `BL` — only place it on an existing 4-byte
  `bl` (or where you've worked out what the replaced instructions did and redo it in C).
- C runs as Thumb, compiled `-O2 -mlong-calls`. Calls into game code by name work for any
  function in `kb/symbols.csv` (declare it `extern`). Keep functions small; no libc.
  `patches/include/gba.h` has types, key bits and registers.
- Mod code is linked at `0x086D0000` (ROM free space); RAM for new variables isn't
  allocated yet — reuse a confirmed-unused RAM area recorded in `kb/ram.md`, or ask.
- Each mod folder gets a short `README.md`: what it does, how to test it.

## Dialogue text entries

`[[text]]` uses `expect_sha1` instead of original `expect` bytes: SHA1 of the
original stream including its end byte. Never include original dialogue in a
public mod. A replacement must encode to exactly one terminated stream.

Shorter/equal unshared streams are written in place. Longer streams and shared
tails move to free space after C code, and every walked direct `0x1a`/`0x1b`
operand at command + 2 is redirected (including unaligned pointers). All writes
use the same overlap check; explicit claims in free space are skipped. Text-only
mods need no compiler. Direct stream addresses come from `hamtools text dump`;
pointer-register commands and unknown/native-only text are unsupported. New
walker roots are picked up automatically, but unseen references remain a
coverage limitation and require scene verification.

`uv run hamtools text edits <edited-dump> --out patches/<mod>/mod.toml` exports
only changed whole streams and original hashes. Dumps stay in `extracted/`.
Use `--partial` only for intentional subsets; omitted entries stay unchanged.
Use `--force` only when replacing the whole existing output is intended.
Review exported text for copied ROM dialogue before committing it.

Width/page warnings use ROM glyph widths and the observed Boss defaults (168px,
three lines, spacing 1, font 0). Optional `width`, `lines`, `spacing`, `font`
fields adjust estimates only. Inserted text/icons and scene-dependent layout
still need playtesting. Preserve scene callbacks and ending/wait controls.
The disabled `boss-text-edit` example conflicts with `sunflower-dialogue` at
the Boss pointer, so build these examples individually.

## Then verify

Always follow with the `verify-mod` skill. A mod isn't done until it's been seen working in
the emulator.
