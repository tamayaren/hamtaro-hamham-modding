# Findings log

Newest first. See the `kb-update` skill for the entry format.

## 2026-10-08 — Input is polled in two places (Claude, tooling bring-up)
- Read-watchpoint on `REG_KEYINPUT` (0x04000130, 2 bytes) over 30 frames on the title screen:
  - pc `0x0800961c` — normal code (Thumb, system mode), once per frame; caller lr `0x08000231`.
  - pc `0x080004a8` — IRQ mode (Thumb), once per frame; lr `0x08000493` → part of the interrupt handler.
- Matches the static literal-pool hits from `hamtools rom xrefs 0x04000130`: `0x080004c4` and
  `0x0800966c` (each just after its reading function). Confidence: confirmed (both methods agree).
- Next: decompile the function around `0x0800961c` to find the RAM "keys held / keys pressed"
  variables — an easy first `ram.md` entry.

## 2026-10-08 — ROM baseline (Claude, setup)
- Verified dump SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`; header checksum valid; save type SRAM (32 KB),
  tag at `0x086CA1E0`.
- Data ends at `0x086CC537`; the rest of the 8 MB is `0xFF` padding — candidate free space.
