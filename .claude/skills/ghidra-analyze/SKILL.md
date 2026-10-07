---
name: ghidra-analyze
description: Static code analysis of the Hamtaro ROM with headless Ghidra — decompile functions to C, disassemble, list callers/callees, find references, create functions (ARM or Thumb), and sync kb/symbols.csv names into the Ghidra project. Use whenever you need to understand what code at an address does.
---

# Ghidra analysis

The project lives in `ghidra/projects/hamtaro.gpr` (gitignored, local). If it's missing:
`uv run hamtools ghidra init` (≈ several minutes; imports the ROM at 0x08000000 as
`ARM:LE:32:v4t`, adds the GBA memory map and I/O register labels, applies `kb/symbols.csv`,
runs auto-analysis).

Each command starts a JVM (~15 s). Batch your questions; don't call in a tight loop.

**Known issue:** auto-analysis on the raw ROM creates ~300k "functions" — most are graphics
and data misread as code. Real code decompiles fine; just don't trust `FUN_` entries far from
known code, and treat `ghidra stats` counts as meaningless for now. Confirm a function is real
via callers (`ghidra func`) or an emulator breakpoint before naming it.
If the Ghidra GUI has the project open, close it first (project lock).

## Commands

| Command | Use |
|---|---|
| `uv run hamtools ghidra decompile <addr\|name>` | C-like pseudocode of the function containing the address |
| `uv run hamtools ghidra disasm <addr> [--count 60]` | instruction listing |
| `uv run hamtools ghidra func <addr>` | size, signature, callers, callees |
| `uv run hamtools ghidra xrefs <addr>` | references Ghidra knows (calls, data reads/writes) |
| `uv run hamtools ghidra make-func <addr> --thumb [--name X]` | code Ghidra missed: disassemble + create function |
| `uv run hamtools ghidra sync` | push names from `kb/symbols.csv` into the project |
| `uv run hamtools ghidra stats` | function counts |
| `uv run hamtools ghidra analyze` | re-run auto-analysis after creating several functions by hand |

## Workflow: from a pc to an understood function

1. Got a pc from a watchpoint (`emu-probe`)? `ghidra func <pc>`. If "no function contains":
   find the start (look back for `push {…, lr}` in `ghidra disasm <pc - 0x40>`), then
   `ghidra make-func <start> --thumb`.
2. `ghidra decompile <start>`. Read it for: which RAM globals it touches (`DAT_02xxxxxx`),
   which functions it calls, constants (speeds, limits, counts).
3. Cross-check with `rom xrefs <global>` / `ghidra xrefs <global>` for other users.
4. Name what you're sure of in `kb/symbols.csv` (`kb-update` skill), then `ghidra sync`
   so later decompiles read better. Never edit names only inside Ghidra — they'd be lost
   on the next `init --force`.

## ARM vs Thumb gotchas

- Most game code is Thumb. Function pointers to Thumb code are odd (`0x08012345` → code
  at `0x08012344`). If decompiled output looks like garbage (`halt_baddata`, weird
  instructions), the mode is probably wrong: recreate with the other mode.
- Calls through `bx rN` / pointer tables often aren't followed by auto-analysis; create
  those targets by hand once you find them.
- `DAT_0400xxxx` accesses are hardware registers; the project labels common ones `REG_*`.

## Output hygiene

Decompiled C and listings are derived from the ROM: use them for understanding, record
*names, addresses and descriptions* in `kb/`, and keep any bulk dumps in `extracted/`.
