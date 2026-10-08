# ROM map

ROM: *Hamtaro: Ham-Ham Heartbreak* (USA), game code `AH3E`, maker `01`, version 0.
SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`, 8 MB (`0x08000000–0x087FFFFF`).
Developer: AlphaDream (same studio as *Mario & Luigi: Superstar Saga*).

| Start | End | Contents | Confidence |
|---|---|---|---|
| `0x08000000` | `0x080000BF` | cartridge header (entry branch, logo, title `HAMUTARO3`, code `AH3E`) | confirmed |
| `0x080000C0` | ? | startup code | likely |
| `0x08004548` | `0x08004817` | text updater, including gaps for internal literal pools | confirmed |
| `0x0804ffb6` | `0x0804ffb9` | unaligned pointer operand for Boss's clubhouse dialogue | confirmed |
| `0x084677f0` | `0x0846782f` | sixteen text-control handler pointers for `0xe0–0xef` | confirmed dispatch; individual meanings vary |
| `0x08467830` | `0x0846786f` | sixteen text-control handler pointers for `0xf0–0xff` | confirmed dispatch; individual meanings vary |
| `0x0846cc6b` | `0x0846ccc2` | Boss's response after Hamha in the provided clubhouse savestate | confirmed |
| `0x086CA1E0` | `0x086CA1EB` | save-type tag `SRAM_F_V103` (32 KB SRAM) | confirmed |
| ? | `0x086CC537` | last non-padding byte | confirmed |
| `0x086CC538` | `0x087FFFFF` | `0xFF` padding — **candidate free space** (~1.2 MB) for patches; confirm unreferenced before use | likely |

Most of the ROM remains unmapped. [dialogue.md](dialogue.md) also lists heuristic
text-region candidates; their bank boundaries are not established.
