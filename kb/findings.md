# Findings log

Newest first. See the `kb-update` skill for the entry format.

## 2026-10-08 — ROM baseline (Claude, setup)
- Verified dump SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`; header checksum valid; save type SRAM (32 KB),
  tag at `0x086CA1E0`.
- Data ends at `0x086CC537`; the rest of the 8 MB is `0xFF` padding — candidate free space.
