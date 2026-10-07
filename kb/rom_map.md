# ROM map

ROM: *Hamtaro: Ham-Ham Heartbreak* (USA), game code `AH3E`, maker `01`, version 0.
SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`, 8 MB (`0x08000000–0x087FFFFF`).
Developer: AlphaDream (same studio as *Mario & Luigi: Superstar Saga*).

| Start | End | Contents | Confidence |
|---|---|---|---|
| `0x08000000` | `0x080000BF` | cartridge header (entry branch, logo, title `HAMUTARO3`, code `AH3E`) | confirmed |
| `0x080000C0` | ? | startup code | likely |
| `0x086CA1E0` | `0x086CA1EB` | save-type tag `SRAM_F_V103` (32 KB SRAM) | confirmed |
| ? | `0x086CC537` | last non-padding byte | confirmed |
| `0x086CC538` | `0x087FFFFF` | `0xFF` padding — **candidate free space** (~1.2 MB) for patches; confirm unreferenced before use | likely |

Everything between the header and the end of used data is still unmapped.
