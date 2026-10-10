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
| `0x080e9e38` | `0x080f4223` | standard dialogue portrait image bank; 57 LZ77 sources, each `0x480` decoded bytes | likely bank/count; Hamtaro/Bijou/Boss live |
| `0x080eb9bc` | `0x080ebcf5` | Boss dialogue BG portrait; LZ77 expands to `0x480` bytes (48 x 48, 4bpp) | confirmed |
| `0x080f437c` | `0x080f43a1` | Boss dialogue palette; LZ77 expands to sixteen BGR555 colours | confirmed |
| `0x080f4224` | `0x080f5418` | dialogue portrait palettes; 130 LZ77 sources, each `0x20` decoded bytes; end is last stream byte | likely bank/count; Hamtaro/Bijou/Boss live |
| `0x081b9f74` | `0x081b9f97` | compressed Boss room-head palette; unique match to live OBJ bank 4 | likely source |
| `0x081bfa60` | `0x081bfc72` | alternate Boss room-head frame; LZ77 expands to `0x480` bytes | confirmed |
| `0x081bfc74` | `0x081bfe95` | Boss idle room-head frame; LZ77 expands to `0x480` bytes | confirmed |
| `0x08467434` | ? | event command handler pointer table; entry `0x1a` selects `0x080027a8` | confirmed observed handler; bounds unknown |
| `0x084677f0` | `0x0846782f` | sixteen text-control handler pointers for `0xe0–0xef` | confirmed dispatch; individual meanings vary |
| `0x08467830` | `0x0846786f` | sixteen text-control handler pointers for `0xf0–0xff` | confirmed dispatch; individual meanings vary |
| `0x08469cdc` | ? | room-head slot records, stride `0x11c`; buffers, OBJ destinations, pose pointers and dimensions | likely format; Boss slot 2 confirmed |
| `0x0846cc6b` | `0x0846ccc2` | Boss's response after Hamha in the provided clubhouse savestate | confirmed |
| `0x084b1dbb` | `0x084b1de0` | two palette/tile load pairs and returns; Boss dialogue portrait for two slots | left pair confirmed; other slot likely |
| `0x084b1c65` | `0x084b3094` | complete standard portrait loader bank; 136 definitions of two 19-byte slot routines | likely full bank; Hamtaro left/Bijou right/Boss left live |
| `0x086538d4` | `0x086538db` | first slot-2 room-head pose: one 4bpp 64 x 64 OBJ, tile `0x50`, palette 4 | confirmed descriptor/OAM match |
| `0x08687dde` | ? | alternate Boss room-head animation; `0xcb` operand at `0x08687ddf` | confirmed replay |
| `0x08687e17` | ? | Boss idle room-head animation; `0xcb` operand at `0x08687e18` | confirmed |
| `0x086CA1E0` | `0x086CA1EB` | save-type tag `SRAM_F_V103` (32 KB SRAM) | confirmed |
| ? | `0x086CC537` | last non-padding byte | confirmed |
| `0x086CC538` | `0x087FFFFF` | exact `0xFF` tail; start is an exclusive startup-copy bound, not a data dereference | likely static audit; see below |
| `0x086D0000` | `0x087FFFFF` | conservative patch pool; code/text/gfx share checked allocations | confirmed for tested allocations; arbitrary future accesses not ruled out |

Most of the ROM remains unmapped. [dialogue.md](dialogue.md) also lists heuristic
text-region candidates; their bank boundaries are not established.

## Dialogue portrait bank audit — 2026-10-10

See [portraits.md](portraits.md) and the address-only
[portrait_catalogue.csv](portrait_catalogue.csv). Each definition holds a left
and right routine: `0x06` palette source/destination, `0x06` tile source/destination,
then `0x1f` return. Operands are inline unaligned `u32` pointers. There are 135
distinct pairs: two monkey definitions alias the same tiles and palette. Shared
images are common (up to sixteen definitions per image); palettes are shared by
at most two definitions in this bank.

The rooted walk decodes every one of 2,711 `0x06` commands and validates its
LZ77 stream. All 336 reached portrait loads belong to the catalogue. Five other
loads reuse portrait palette destinations without being portrait pairs: at
`0x080a913e`, `0x080cfb60`, `0x080d959c`, `0x080df20d`, and `0x080df236`.
Larger palette uploads and the isolated 32-byte palette load are not labelled
as a portrait from destination alone. Static reachability remains likely.

All base/mirror source-pointer occurrences for changed catalogue streams are
mapped to the audited loader bank; the builder refuses unknown occurrences.
Repoint both defined slots even when a partner is outside reached roots.
Computed and unknown native-only consumers cannot be excluded by pointer scans.

The import demo allocates Hamtaro tiles at `0x086d0000` (729 bytes), Hamtaro
palette at `0x086d02dc` (32 bytes), and Bijou palette at `0x086d02fc` (35 bytes).
These conservative allocations are confirmed by title boot, visible original/
edited faces, exact VRAM/palette/shadow matches in both tested slots and a
surrounding dialogue smoke check. The original ROM SHA1 is unchanged.

## Free-space audit — 2026-10-10

"Truly unreferenced" is **not established**. Word `0x08000284` contains
`0x086cc538`. Startup Thumb instruction `0x080001e2` loads it and subtracts
`0x086ca218` (word `0x08000280`), then converts the `0x2320`-byte difference
to `0x8c8` DMA3 words. The copy goes to `0x02000000` and ends at `0x086cc537`.
The padding address is a **one-past-end bound**; this copy does not read it.
Disassembly corroborates the scout's finding (likely).

The tail is `0x133ac8` bytes of `0xff`. All 8,388,605 four-byte windows were
scanned, including unaligned operands and the `0x08`, `0x0a`, `0x0c` ROM
mirrors. There were 3,461 pointer-looking windows: 633 aligned, 2,828 unaligned;
1,566/933/962 by mirror, with 2,268 physical targets. These are candidates,
not 3,461 real references. The event walk decoded 98,214 commands from 148
roots without problems or unknown natives. Of 1,093 windows in those commands,
**none began at a mapped/likely pointer field**: 1,034 were shifted overlaps
and 59 were other command bytes; seven of the latter are in partly unmapped
opcodes. Heuristic LZ77 spans contained 1,289 candidates, with false parses
possible. Remaining unmapped code/data windows were not promoted to real
pointers or dismissed as certainly harmless.

No additional evidenced data reference into the tail was found. Computed
pointers, unmapped tables/opcodes, and later scenes cannot be excluded.
Keep `FREE_BASE = 0x086d0000`, leaving `0x3ac8` bytes after the startup bound.
Each allocation must be all `0xff` and disjoint from code, text and explicit
edits. The `boss-recolor` palette there booted and worked through repeated
conversations. This confirms that allocation in the tested scene; it does not
prove the entire padding range unused in every scene. Address-only audit
results and evidence are under `extracted/gfx/`.
