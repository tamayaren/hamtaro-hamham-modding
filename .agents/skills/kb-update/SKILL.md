---
name: kb-update
description: How to record reverse-engineering findings in the kb/ knowledge base — symbols.csv format, naming conventions, confidence levels, RAM/ROM maps, structs, and the findings log. Use whenever you learn an address, name a function, decode a format, or resolve or raise an open question.
---

# Updating the knowledge base

`kb/` is the project's memory. Every agent and every session starts from it, so record
findings as you go, in the same change that relies on them.

## Files

| File | Holds |
|---|---|
| `kb/symbols.csv` | every named address (functions, ROM data, RAM variables, I/O) — machine-readable, imported into Ghidra and the emulator |
| `kb/ram.md` | RAM map narrative: what lives where, grouped by system |
| `kb/rom_map.md` | ROM regions: code, data banks, graphics, text, free space |
| `kb/structs.md` | struct layouts (field offset, size, name, meaning) |
| `kb/findings.md` | dated log, newest first: what was learned, how, by which agent |
| `kb/questions.md` | open questions and hunches still to test |

## symbols.csv

Columns: `address,name,kind,size,mode,confidence,notes`

- `address`: full 32-bit hex, lowercase digits, `0x` prefix, **even** for Thumb functions.
- `kind`: `func` | `data` (ROM) | `ram` | `io`
- `size`: bytes in hex (`0x40`) or empty if unknown
- `mode`: `thumb` | `arm` for functions, empty otherwise
- `confidence`: `confirmed` | `likely` | `guess`
- `notes`: short, no commas (or quote the field)

Keep rows **sorted by address** (it reduces merge conflicts between parallel agents).
One name per address; rename by editing the row, and note the rename in `findings.md`.

## Naming

- Functions: `System_VerbNoun` in PascalCase, e.g. `Player_UpdateMovement`, `Text_DrawGlyph`.
  Unknown but noted: `sub_08012344`.
- RAM variables: `g` + PascalCase, e.g. `gPlayerX`, `gKeysHeld`. Struct instances get the
  struct name in `notes`.
- ROM data: `k` + PascalCase, e.g. `kHamtaroWalkPalette`, `kDialogPointerTable`.
- Systems (prefixes): `Main`, `Irq`, `Input`, `Gfx`, `Text`, `Map`, `Player`, `Npc`,
  `Event`, `Ham` (Ham-Chat words), `Save`, `Sound`, `Menu`, `Util`. Add new ones to this list.

## Confidence

- `confirmed` — tested in the emulator in a way that would have failed if wrong
  (e.g. poked the value and saw Hamtaro move; patched the function and saw the change).
- `likely` — strong static evidence (decompiled logic clearly matches) but not yet tested.
- `guess` — a hunch. Fine to record, never to build on silently.

## findings.md entry

```
## 2026-10-08 — Player X/Y position found (re-analyst)
- `gPlayerX` 0x0200xxxx (u16), `gPlayerY` 0x0200xxxx — confirmed by poking the value in mGBA.
- Method: RAM search while walking left/right.
- Next: find the movement function that writes it (`rom xrefs`).
```

## Never

- Paste ROM bytes beyond short signatures (≤ 16 bytes), extracted text, or graphics into `kb/`.
- Mark something `confirmed` that you didn't test.
