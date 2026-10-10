# Dialogue portrait catalogue and room head graphics

Addresses apply to the verified USA AH3E ROM, SHA1
`2525cc23524068dfb3a2b4e0ce7b736f95023e82`. All extracted graphics and
runtime evidence stay under `extracted/gfx/`.

## Catalogue — 2026-10-10

`hamtools gfx list/export/import` now addresses **136 named loader definitions**
(**135 distinct tile/palette pairs**), covering the complete standard portrait
loader bank at `0x084b1c65` through `0x084b3095` exclusive. It contains 57
compressed tile images and 130 compressed palettes. Many named NPCs share one
image with different colours; a palette variant is a distinct catalogue entry.
Two monkey definitions are aliases of the same pair, not different expressions.
These counts and the full bank layout are **likely**, from static validation.

The address-only [portrait_catalogue.csv](portrait_catalogue.csv) is the tooling
registry. It records both defined slot routines, their individually reached
scene roots, the union of roots, nearby text addresses used for editorial labels,
and name confidence. No dialogue strings or image bytes are stored there.
Named speakers/roles are **guess** unless seen on screen; unidentified definitions
keep numeric names. A context may include another speaker, so an adjacent line
is evidence for a tentative label rather than proof of identity or expression.
Do not reinterpret a palette variant as a facial animation without a scene test.

The event walk still reaches 148 roots and 98,214 commands, with no problems or
unknown natives. All **2,711 reached event `0x06` occurrences** were decoded and
LZ77-validated. **336 loads** form **168 reached (tiles, palette, slot) sets**:
123 left and 45 right. Every portrait tile stream expands to `0x480` bytes and
every portrait palette to `0x20`. The other graphics loads have their own sizes;
five reuse a portrait palette destination but are not portrait load pairs.

Of 136 definitions, 130 are reached (85 only on the left, seven only on the
right, 38 on both). Six definitions are audited static partners/definitions,
with **no rooted runtime reachability claimed**: Snoozer, unidentified 033,
unidentified 044, unidentified 050, unidentified 070, and the monkey alias.
Every definition includes two explicit `0x06` commands and a `0x1f` return for
each slot; even unreached partners are repointed. This covers the standard bank
and every reached `0x06` portrait load, not hypothetical native-only or unseen
load paths outside that evidence.

`events.command_roots()` propagates all root labels through recorded flow edges.
This corrects the previous first-visitor-only provenance for shared routines.
Calls, branches, and context starts describe possible static use, including
continuations; they do not predict which flags select a particular path live.

### Operand format and caller path

Event `0x06` is **nine bytes**: opcode at +0, inline source `u32` at +1,
inline destination `u32` at +5, all little endian. These are **pointers, not
portrait IDs or table indices**, and they can be unaligned. The handler assembles
each pointer from four byte reads and takes the decoded byte count from the
LZ77 source header. It does not resolve event pointer-register indices here.

Ghidra decompilation of `0x08001658`, `Event_RunCommands` (`0x08000d74`),
and its caller `0x08000984` establishes the static dispatch path. Table slot
`0x0846744c` contains Thumb pointer `0x08001659`; the runner calls through
`bx r1` thunk `0x080e57f0`. Handler completion sets operand advance to eight
and opcode to zero; `0x08001530` fetches the next command. Static caller/table
interpretation remains likely; observed LR `0x08000d91` corroborates dispatch.
The bytewise format is confirmed by Boss and Bijou source-read probes.

### Slot geometry and live checks

| Slot | Tile source buffer | VRAM tiles | Palette buffer | BG palette | BG3 map in tested bottom window | Confidence |
|---|---|---|---|---|---|---|
| left | `0x02007710` | `0x06003b80` | `0x0201bbf0` | `0x05000060` (bank 3) | rows 21..26, columns 1..6, tiles `0x1dc..0x1ff` | confirmed: Boss and Hamtaro |
| right | `0x02007290` | `0x06003700` | `0x0201bbd0` | `0x05000040` (bank 2) | rows 21..26, columns 23..28, tiles `0x1b8..0x1db` | confirmed: Bijou |

The right top-left tilemap word is `0x0600bd6e`; both regions are row-major in
BG3 screen block 23 (`0x0600b800`). The observed faces start at screen x=8
and x=184. This geometry is scene-specific; other window positions need tests.

Hamtaro tiles `0x080e9e38` / palette `0x080f4224` exactly matched live left
VRAM and palette in the supplied Sunny Peaks state after Hamha. Bijou tiles
`0x080ea110` / palette `0x080f4244` exactly matched right VRAM, palette RAM,
and both shadow buffers. A restored Boss baseline with the **known progression
flag 0x0010 set temporarily** displayed the companion greeting. This was a
controlled test, not a claim that the original baseline naturally reaches it.
The original baseline was preserved; `states/portrait-catalogue-companion-base.ss`
is the separate reproducible probe baseline.

Read probes at Bijou source operands `0x084b1c9f` and `0x084b1ca8` captured
four one-byte reads each from reported PCs `0x08001666/68/6e/74` (instructions
`0x08001662/64/6a/70`). Right tile/palette writes at reported PC `0x0800992c`
(instruction `0x08009928`) recorded DMA source/destination/count triples:
`0x02007290` / `0x06003700` / `0x480`, and `0x0201bbd0` / `0x05000040` /
`0x20`. **Bijou's right loader and this upload path are confirmed.** Boss's
specific right loader `0x084b1dce` was not executed and remains likely.

The disabled `portrait-catalogue-demo` was authored through PNG import. It
relocates Hamtaro tiles (one changed pixel) and palette (two colours) and Bijou
palette (two colours). Both displayed changes and all four live raw/shadow
comparisons per slot match the reconstructed recipe. Cold title boot and a
surrounding dialogue/menu smoke run were checked. No room transition or long
session is claimed. Local evidence is under `extracted/gfx/catalogue/`;
PNGs, raw comparisons, read/upload traces and Ghidra output are gitignored.

### Every definition

Both slots are defined for every row. `L`/`R` below are the actually reached
slot roots, not confirmation from the emulator. Compact scene roots use
`scene.{subscene,..}`; for example `2.{0..3,7}` means scene 2 subscenes
0, 1, 2, 3 and 7. Exact uncompressed root lists and context text **addresses**
are in the CSV. Tile/palette mapping and untested loader execution are likely;
the confidence column applies specifically to the editorial name.

| Name | Tiles | Palette | Left / right routine | Reached roots by slot | Name confidence |
|---|---|---|---|---|---|
| `hamtaro-portrait` | `0x080e9e38` | `0x080f4224` | `0x084b1c65` / `0x084b1c78` | L: 1.{1..6}; 2.{1..15,17..20,23..24}; 3.{1..12,14,16..18}; 4.{1..15}; 5.{1..7,9..21,23..34,37}; 6.{1..2,4..19}; 7.{1..3}; 9.{1..4}; 10.{10}<br>R: — | confirmed |
| `bijou-portrait` | `0x080ea110` | `0x080f4244` | `0x084b1c8b` / `0x084b1c9e` | L: 1.{1..2}; 2.{1..2,4..12,14,17,19,23}; 3.{2,7,11..12,15,17}; 4.{2,4..6,8..15}; 5.{3..7,9..21,23..24,27,30..31,33,37}; 6.{3,5,7,9,11..15,17..19}; 7.{1..3}; 9.{1..2,4}; 10.{12..13}<br>R: 1.{1..6}; 2.{1..15,17..20,23..24}; 3.{1..12,14,16..18}; 4.{1..15}; 5.{1..7,9..21,23..34,37}; 6.{1..2,4..19}; 7.{1..3}; 9.{1..4}; 10.{10} | confirmed |
| `oxnard-portrait` | `0x080ea3e0` | `0x080f4268` | `0x084b1cb1` / `0x084b1cc4` | L: 2.{2}; 10.{12}<br>R: — | guess |
| `maxwell-portrait` | `0x080ea6ec` | `0x080f428c` | `0x084b1cd7` / `0x084b1cea` | L: 6.{9,15}<br>R: 6.{13} | guess |
| `pashmina-portrait` | `0x080eaa68` | `0x080f42b4` | `0x084b1cfd` / `0x084b1d10` | L: 2.{6}<br>R: 2.{2}; 10.{12} | guess |
| `cappy-portrait` | `0x080ead9c` | `0x080f42dc` | `0x084b1d23` / `0x084b1d36` | L: 2.{5}; 6.{19}; 10.{12}<br>R: — | guess |
| `jingle-portrait` | `0x080eb068` | `0x080f4304` | `0x084b1d49` / `0x084b1d5c` | L: 6.{17,19}<br>R: — | guess |
| `panda-portrait` | `0x080eb388` | `0x080f432c` | `0x084b1d6f` / `0x084b1d82` | L: 2.{14}<br>R: — | guess |
| `dexter-portrait` | `0x080eb674` | `0x080f4354` | `0x084b1d95` / `0x084b1da8` | L: 5.{11,16,21}<br>R: 5.{11,16}; 10.{12} | guess |
| `boss-portrait` | `0x080eb9bc` | `0x080f437c` | `0x084b1dbb` / `0x084b1dce` | L: 1.{1}; 4.{14}; 10.{10,13}<br>R: — | confirmed |
| `howdy-portrait` | `0x080ebcf8` | `0x080f43a4` | `0x084b1de1` / `0x084b1df4` | L: 5.{11,14,16}; 10.{12}<br>R: — | guess |
| `sandy-portrait` | `0x080ebf98` | `0x080f43c8` | `0x084b1e07` / `0x084b1e1a` | L: 3.{10,12}<br>R: 3.{12}; 10.{12} | guess |
| `stan-portrait` | `0x080ec2bc` | `0x080f43f0` | `0x084b1e2d` / `0x084b1e40` | L: 3.{10,12}<br>R: 3.{12} | guess |
| `snoozer-portrait` | `0x080ec5c8` | `0x080f4418` | `0x084b1e53` / `0x084b1e66` | L: —<br>R: — | guess |
| `spat-portrait` | `0x080ec874` | `0x080f4440` | `0x084b1e79` / `0x084b1e8c` | L: 2.{2,4,14}; 3.{17}; 4.{1,5,12}; 5.{2,30}; 6.{9,14}; 7.{2..3}<br>R: — | guess |
| `harmony-portrait` | `0x080ecbc4` | `0x080f4468` | `0x084b1e9f` / `0x084b1eb2` | L: 7.{3}<br>R: — | guess |
| `elder-ham-portrait` | `0x080ecf10` | `0x080f4490` | `0x084b1ec5` / `0x084b1ed8` | L: 2.{4..5}<br>R: 2.{5}; 10.{12} | guess |
| `hot-spring-hamster-portrait` | `0x080ed1f4` | `0x080f44b4` | `0x084b1eeb` / `0x084b1efe` | L: 2.{4..5}<br>R: 2.{5} | guess |
| `barrette-portrait` | `0x080ed4e4` | `0x080f44dc` | `0x084b1f11` / `0x084b1f24` | L: 4.{9..10,12,14}; 10.{12}<br>R: 4.{12} | guess |
| `penelope-portrait` | `0x080ed840` | `0x080f4504` | `0x084b1f37` / `0x084b1f4a` | L: 4.{9,12}<br>R: 4.{9..10,12}; 10.{12} | guess |
| `unidentified-020-portrait` | `0x080edb10` | `0x080f4528` | `0x084b1f5d` / `0x084b1f70` | L: 3.{9,12}; 10.{12}<br>R: — | guess |
| `unidentified-021-portrait` | `0x080ede14` | `0x080f454c` | `0x084b1f83` / `0x084b1f96` | L: 1.{1}<br>R: — | guess |
| `broski-rival-portrait` | `0x080ee108` | `0x080f4574` | `0x084b1fa9` / `0x084b1fbc` | L: 1.{1,3}; 2.{11}; 4.{5}; 10.{12}<br>R: — | guess |
| `harmony-variant-portrait` | `0x080ee414` | `0x080f459c` | `0x084b1fcf` / `0x084b1fe2` | L: 1.{1..2}; 7.{3}; 10.{12..13}<br>R: 1.{1}; 4.{14} | guess |
| `sweethearts-portrait` | `0x080ee76c` | `0x080f45c4` | `0x084b1ff5` / `0x084b2008` | L: 1.{3}; 4.{5}<br>R: 1.{3}; 4.{5}; 10.{12} | guess |
| `broski-portrait` | `0x080eea80` | `0x080f45ec` | `0x084b201b` / `0x084b202e` | L: 4.{4}<br>R: — | guess |
| `business-hamster-portrait` | `0x080eed40` | `0x080f4610` | `0x084b2041` / `0x084b2054` | L: 1.{1}<br>R: — | guess |
| `reporter-portrait` | `0x080eefb4` | `0x080f4638` | `0x084b2067` / `0x084b207a` | L: 7.{3}<br>R: — | guess |
| `dark-hamster-portrait` | `0x080ef268` | `0x080f4660` | `0x084b208d` / `0x084b20a0` | L: 7.{2}<br>R: — | guess |
| `turn-taking-hamster-portrait` | `0x080ef53c` | `0x080f4684` | `0x084b20b3` / `0x084b20c6` | L: 2.{20}<br>R: 2.{20}; 10.{12} | guess |
| `rope-helper-portrait` | `0x080ef53c` | `0x080f46a4` | `0x084b20d9` / `0x084b20ec` | L: 2.{14,20}; 10.{12}<br>R: — | guess |
| `rough-hamster-portrait` | `0x080ef7cc` | `0x080f46c4` | `0x084b20ff` / `0x084b2112` | L: 5.{3,32}; 10.{12}<br>R: — | guess |
| `unidentified-032-portrait` | `0x080ef7cc` | `0x080f46e4` | `0x084b2125` / `0x084b2138` | L: 5.{2}<br>R: — | guess |
| `unidentified-033-portrait` | `0x080ef53c` | `0x080f470c` | `0x084b214b` / `0x084b215e` | L: —<br>R: — | guess |
| `embarrassed-hamster-portrait` | `0x080ef7cc` | `0x080f472c` | `0x084b2171` / `0x084b2184` | L: 3.{7..10,16}<br>R: 3.{7}; 10.{12} | guess |
| `unidentified-035-portrait` | `0x080ef7cc` | `0x080f4754` | `0x084b2197` / `0x084b21aa` | L: 2.{17}<br>R: — | guess |
| `laughing-hamster-portrait` | `0x080ef53c` | `0x080f4778` | `0x084b21bd` / `0x084b21d0` | L: 4.{1..2}; 5.{33}; 10.{12}<br>R: 4.{2} | guess |
| `shy-hamster-portrait` | `0x080ef7cc` | `0x080f4798` | `0x084b21e3` / `0x084b21f6` | L: 2.{11}<br>R: — | guess |
| `ham-o-matic-operator-portrait` | `0x080ef7cc` | `0x080f47c0` | `0x084b2209` / `0x084b221c` | L: 3.{2,17}<br>R: 10.{12} | guess |
| `control-room-operator-portrait` | `0x080ef7cc` | `0x080f47e8` | `0x084b222f` / `0x084b2242` | L: 3.{17}<br>R: — | guess |
| `unidentified-040-portrait` | `0x080ef7cc` | `0x080f4810` | `0x084b2255` / `0x084b2268` | L: 3.{4}<br>R: — | guess |
| `unidentified-041-portrait` | `0x080ef7cc` | `0x080f4838` | `0x084b227b` / `0x084b228e` | L: 3.{8}<br>R: — | guess |
| `unidentified-042-portrait` | `0x080ef7cc` | `0x080f4860` | `0x084b22a1` / `0x084b22b4` | L: 3.{11}<br>R: — | guess |
| `surprised-hamster-portrait` | `0x080ef7cc` | `0x080f4888` | `0x084b22c7` / `0x084b22da` | L: 3.{1}<br>R: — | guess |
| `unidentified-044-portrait` | `0x080ef7cc` | `0x080f48b0` | `0x084b22ed` / `0x084b2300` | L: —<br>R: — | guess |
| `researcher-portrait` | `0x080ef7cc` | `0x080f48d8` | `0x084b2313` / `0x084b2326` | L: 6.{6}; 7.{1}<br>R: 6.{6}; 10.{12} | guess |
| `wedding-hamster-portrait` | `0x080ef7cc` | `0x080f48fc` | `0x084b2339` / `0x084b234c` | L: 6.{4,9,12}; 10.{12}<br>R: 6.{12} | guess |
| `unidentified-047-portrait` | `0x080ef53c` | `0x080f4920` | `0x084b235f` / `0x084b2372` | L: 6.{8}<br>R: — | guess |
| `unidentified-048-portrait` | `0x080ef53c` | `0x080f4940` | `0x084b2385` / `0x084b2398` | L: 6.{9}<br>R: — | guess |
| `beach-tanner-portrait` | `0x080f095c` | `0x080f4960` | `0x084b23ab` / `0x084b23be` | L: 4.{6}<br>R: — | guess |
| `unidentified-050-portrait` | `0x080ef7cc` | `0x080f4988` | `0x084b23d1` / `0x084b23e4` | L: —<br>R: — | guess |
| `unidentified-051-portrait` | `0x080ef53c` | `0x080f49ac` | `0x084b23f7` / `0x084b240a` | L: 5.{17}<br>R: — | guess |
| `tower-painter-portrait` | `0x080ef7cc` | `0x080f49cc` | `0x084b241d` / `0x084b2430` | L: 7.{2}; 9.{4}; 10.{12}<br>R: — | guess |
| `accessory-clerk-portrait` | `0x080f0c2c` | `0x080f49f0` | `0x084b2443` / `0x084b2456` | L: 1.{6}; 9.{3}<br>R: — | guess |
| `game-explainer-portrait` | `0x080f0c2c` | `0x080f4a18` | `0x084b2469` / `0x084b247c` | L: 3.{4,6}<br>R: — | guess |
| `final-test-host-portrait` | `0x080f0c2c` | `0x080f4a40` | `0x084b248f` / `0x084b24a2` | L: 5.{30}<br>R: — | guess |
| `test-host-portrait` | `0x080f0c2c` | `0x080f4a68` | `0x084b24b5` / `0x084b24c8` | L: 5.{7}<br>R: — | guess |
| `coaster-clerk-portrait` | `0x080f0c2c` | `0x080f4a90` | `0x084b24db` / `0x084b24ee` | L: 3.{10}<br>R: — | guess |
| `tea-cups-clerk-portrait` | `0x080f0c2c` | `0x080f4ab8` | `0x084b2501` / `0x084b2514` | L: 3.{12}<br>R: — | guess |
| `ferris-wheel-clerk-portrait` | `0x080f0c2c` | `0x080f4ae0` | `0x084b2527` / `0x084b253a` | L: 3.{14}<br>R: — | guess |
| `ham-ranger-recruiter-portrait` | `0x080f0c2c` | `0x080f4b08` | `0x084b254d` / `0x084b2560` | L: 3.{11}<br>R: — | guess |
| `popcorn-vendor-portrait` | `0x080f0c2c` | `0x080f4b30` | `0x084b2573` / `0x084b2586` | L: 3.{7}<br>R: — | guess |
| `test-host-variant-portrait` | `0x080f0c2c` | `0x080f4b58` | `0x084b2599` / `0x084b25ac` | L: 5.{22}<br>R: — | guess |
| `unidentified-063-portrait` | `0x080f0c2c` | `0x080f4b80` | `0x084b25bf` / `0x084b25d2` | L: 1.{5}<br>R: — | guess |
| `handkerchief-hamster-portrait` | `0x080f0ef4` | `0x080f4ba8` | `0x084b25e5` / `0x084b25f8` | L: 2.{3}<br>R: — | guess |
| `soccer-hamster-portrait` | `0x080f0ef4` | `0x080f4bcc` | `0x084b260b` / `0x084b261e` | L: 4.{1}<br>R: 4.{1} | guess |
| `sweetheart-portrait` | `0x080f11a4` | `0x080f4bf0` | `0x084b2631` / `0x084b2644` | L: —<br>R: 4.{1}; 10.{12} | guess |
| `shouting-hamster-portrait` | `0x080f0ef4` | `0x080f4c10` | `0x084b2657` / `0x084b266a` | L: 5.{3,7}<br>R: 5.{32}; 10.{12} | guess |
| `unidentified-068-portrait` | `0x080f1428` | `0x080f4c34` | `0x084b267d` / `0x084b2690` | L: 5.{27}<br>R: — | guess |
| `restroom-date-portrait` | `0x080f0ef4` | `0x080f4c50` | `0x084b26a3` / `0x084b26b6` | L: 3.{14}<br>R: 3.{14..15}; 10.{12} | guess |
| `unidentified-070-portrait` | `0x080f0ef4` | `0x080f4c74` | `0x084b26c9` / `0x084b26dc` | L: —<br>R: — | guess |
| `bossy-hamster-portrait` | `0x080f0ef4` | `0x080f4c98` | `0x084b26ef` / `0x084b2702` | L: 3.{7}; 10.{12}<br>R: 3.{7} | guess |
| `unidentified-072-portrait` | `0x080f0ef4` | `0x080f4cbc` | `0x084b2715` / `0x084b2728` | L: 3.{1,12}<br>R: — | guess |
| `persistent-hamster-portrait` | `0x080f0ef4` | `0x080f4ce0` | `0x084b273b` / `0x084b274e` | L: 4.{7,15}<br>R: — | guess |
| `shop-clerk-portrait` | `0x080f0ef4` | `0x080f4d04` | `0x084b2761` / `0x084b2774` | L: 4.{11}<br>R: — | guess |
| `wife-portrait` | `0x080f0ef4` | `0x080f4d28` | `0x084b2787` / `0x084b279a` | L: 6.{2}<br>R: — | guess |
| `frightened-hamster-portrait` | `0x080f0ef4` | `0x080f4d4c` | `0x084b27ad` / `0x084b27c0` | L: 6.{4,9,12}<br>R: 6.{9}; 10.{12} | guess |
| `big-brother-portrait` | `0x080f16c0` | `0x080f4d6c` | `0x084b27d3` / `0x084b27e6` | L: 2.{7,10,18}<br>R: 2.{7,10}; 10.{12} | guess |
| `worried-parent-portrait` | `0x080f16c0` | `0x080f4d90` | `0x084b27f9` / `0x084b280c` | L: 3.{11}; 5.{23}; 10.{12}<br>R: 3.{11} | guess |
| `ham-red-mother-portrait` | `0x080f193c` | `0x080f4db0` | `0x084b281f` / `0x084b2832` | L: 3.{11}; 5.{23}<br>R: 3.{11} | guess |
| `work-supervisor-portrait` | `0x080f16c0` | `0x080f4dd8` | `0x084b2845` / `0x084b2858` | L: 4.{3}<br>R: — | guess |
| `drowning-hamster-portrait` | `0x080f16c0` | `0x080f4dfc` | `0x084b286b` / `0x084b287e` | L: —<br>R: 4.{3} | guess |
| `sad-wife-portrait` | `0x080f16c0` | `0x080f4e20` | `0x084b2891` / `0x084b28a4` | L: 4.{6}; 10.{12}<br>R: — | guess |
| `researchers-wife-portrait` | `0x080f16c0` | `0x080f4e44` | `0x084b28b7` / `0x084b28ca` | L: 6.{6}; 10.{12}<br>R: — | guess |
| `home-guard-portrait` | `0x080f16c0` | `0x080f4e64` | `0x084b28dd` / `0x084b28f0` | L: 6.{1}<br>R: — | guess |
| `georges-partner-portrait` | `0x080f16c0` | `0x080f4e84` | `0x084b2903` / `0x084b2916` | L: —<br>R: 9.{4}; 10.{12} | guess |
| `arnies-friend-portrait` | `0x080f1bec` | `0x080f4ea4` | `0x084b2929` / `0x084b293c` | L: 2.{7,9..10,12..13}; 9.{1}; 10.{12}<br>R: 2.{7,9} | guess |
| `ham-red-son-portrait` | `0x080f1e94` | `0x080f4ec4` | `0x084b294f` / `0x084b2962` | L: 3.{11}<br>R: 5.{23}; 10.{12} | guess |
| `piano-teacher-portrait` | `0x080f1bec` | `0x080f4ee0` | `0x084b2975` / `0x084b2988` | L: 5.{31}<br>R: — | guess |
| `gem-digger-portrait` | `0x080f1e94` | `0x080f4f00` | `0x084b299b` / `0x084b29ae` | L: 1.{4}<br>R: 1.{4} | guess |
| `gem-digger-variant-portrait` | `0x080f1e94` | `0x080f4f1c` | `0x084b29c1` / `0x084b29d4` | L: 1.{4}<br>R: — | guess |
| `unidentified-091-portrait` | `0x080f1bec` | `0x080f4f38` | `0x084b29e7` / `0x084b29fa` | L: 2.{23}<br>R: — | guess |
| `secret-room-hamster-portrait` | `0x080f1bec` | `0x080f4f58` | `0x084b2a0d` / `0x084b2a20` | L: 2.{23}<br>R: 2.{23} | guess |
| `daughter-portrait` | `0x080f1bec` | `0x080f4f78` | `0x084b2a33` / `0x084b2a46` | L: 3.{7}; 10.{12}<br>R: 3.{7} | guess |
| `nyuh-hamster-portrait` | `0x080f2118` | `0x080f4f98` | `0x084b2a59` / `0x084b2a6c` | L: 6.{10,13}<br>R: — | guess |
| `unidentified-095-portrait` | `0x080f1e94` | `0x080f4fb4` | `0x084b2a7f` / `0x084b2a92` | L: 6.{8}<br>R: — | guess |
| `letter-recipient-portrait` | `0x080f23d4` | `0x080f4fd0` | `0x084b2aa5` / `0x084b2ab8` | L: 4.{1..2}<br>R: — | guess |
| `heidis-admirer-portrait` | `0x080f23d4` | `0x080f4ff0` | `0x084b2acb` / `0x084b2ade` | L: 3.{14..15,18}; 10.{12}<br>R: — | guess |
| `bold-hamster-portrait` | `0x080f23d4` | `0x080f500c` | `0x084b2af1` / `0x084b2b04` | L: 5.{14,19}; 10.{12}<br>R: 5.{14} | guess |
| `dance-floor-hamster-portrait` | `0x080f23d4` | `0x080f502c` | `0x084b2b17` / `0x084b2b2a` | L: 4.{11,13}<br>R: — | guess |
| `unidentified-100-portrait` | `0x080f23d4` | `0x080f5048` | `0x084b2b3d` / `0x084b2b50` | L: 4.{13}<br>R: — | guess |
| `dance-greeter-portrait` | `0x080f23d4` | `0x080f5064` | `0x084b2b63` / `0x084b2b76` | L: 4.{11}<br>R: — | guess |
| `dance-host-portrait` | `0x080f23d4` | `0x080f5080` | `0x084b2b89` / `0x084b2b9c` | L: 4.{13}<br>R: — | guess |
| `hula-judge-portrait` | `0x080f23d4` | `0x080f509c` | `0x084b2baf` / `0x084b2bc2` | L: 4.{13}<br>R: — | guess |
| `originality-judge-portrait` | `0x080f23d4` | `0x080f50b8` | `0x084b2bd5` / `0x084b2be8` | L: 4.{13}<br>R: — | guess |
| `unidentified-105-portrait` | `0x080f23d4` | `0x080f50d4` | `0x084b2bfb` / `0x084b2c0e` | L: 4.{10}<br>R: — | guess |
| `timing-judge-portrait` | `0x080f23d4` | `0x080f50f0` | `0x084b2c21` / `0x084b2c34` | L: 4.{13}<br>R: — | guess |
| `performance-host-portrait` | `0x080f23d4` | `0x080f510c` | `0x084b2c47` / `0x084b2c5a` | L: 4.{14}<br>R: — | guess |
| `emotional-hamster-portrait` | `0x080f23d4` | `0x080f5128` | `0x084b2c6d` / `0x084b2c80` | L: 5.{14,19}<br>R: 5.{14,19}; 10.{12} | guess |
| `woods-native-portrait` | `0x080f23d4` | `0x080f5148` | `0x084b2c93` / `0x084b2ca6` | L: 6.{6..7,11..15,17..19}; 10.{12}<br>R: 6.{11..13,15..19} | guess |
| `mansion-guard-one-portrait` | `0x080f23d4` | `0x080f5164` | `0x084b2cb9` / `0x084b2ccc` | L: 6.{10}<br>R: — | guess |
| `mansion-guard-two-portrait` | `0x080f23d4` | `0x080f5180` | `0x084b2cdf` / `0x084b2cf2` | L: 6.{10}<br>R: 6.{10} | guess |
| `robot-portrait` | `0x080f267c` | `0x080f519c` | `0x084b2d05` / `0x084b2d18` | L: 3.{2,17}; 10.{12}<br>R: — | guess |
| `accessory-clerk-variant-portrait` | `0x080f2c14` | `0x080f51c4` | `0x084b2d2b` / `0x084b2d3e` | L: 1.{6}<br>R: — | guess |
| `shouting-elder-portrait` | `0x080f2c14` | `0x080f51e8` | `0x084b2d51` / `0x084b2d64` | L: 5.{4}<br>R: — | guess |
| `unidentified-115-portrait` | `0x080f2944` | `0x080f520c` | `0x084b2d77` / `0x084b2d8a` | L: 4.{13}<br>R: — | guess |
| `warm-hamster-portrait` | `0x080f2c14` | `0x080f5234` | `0x084b2d9d` / `0x084b2db0` | L: 5.{15}<br>R: — | guess |
| `ghost-portrait` | `0x080f2c14` | `0x080f5258` | `0x084b2dc3` / `0x084b2dd6` | L: 5.{15}<br>R: — | guess |
| `wedding-officiant-portrait` | `0x080f2c14` | `0x080f527c` | `0x084b2de9` / `0x084b2dfc` | L: 6.{9,13}<br>R: — | guess |
| `deal-vendor-portrait` | `0x080f2ea0` | `0x080f52a0` | `0x084b2e0f` / `0x084b2e22` | L: 2.{9,13}<br>R: — | guess |
| `ham-swap-clerk-portrait` | `0x080f2ea0` | `0x080f52c4` | `0x084b2e35` / `0x084b2e48` | L: 5.{1}<br>R: — | guess |
| `unidentified-121-portrait` | `0x080f2ea0` | `0x080f52e8` | `0x084b2e5b` / `0x084b2e6e` | L: 6.{2}<br>R: — | guess |
| `dig-game-host-portrait` | `0x080f319c` | `0x080f530c` | `0x084b2e81` / `0x084b2e94` | L: 3.{5}<br>R: — | guess |
| `husband-portrait` | `0x080f319c` | `0x080f532c` | `0x084b2ea7` / `0x084b2eba` | L: 4.{4,6,8,15}<br>R: 10.{12} | guess |
| `heyhoo-hamster-portrait` | `0x080f319c` | `0x080f534c` | `0x084b2ecd` / `0x084b2ee0` | L: 2.{2}<br>R: — | guess |
| `hungry-monkey-portrait` | `0x080f3430` | `0x080f536c` | `0x084b2ef3` / `0x084b2f06` | L: 2.{12}; 6.{18}<br>R: 6.{18}; 10.{12} | guess |
| `riddle-author-portrait` | `0x080f375c` | `0x080f5390` | `0x084b2f19` / `0x084b2f2c` | L: 6.{5}<br>R: — | guess |
| `village-elder-portrait` | `0x080f3a7c` | `0x080f53b4` | `0x084b2f3f` / `0x084b2f52` | L: 6.{9}<br>R: 6.{9} | guess |
| `ghost-variant-portrait` | `0x080f3db8` | `0x080f53dc` | `0x084b2f65` / `0x084b2f78` | L: 5.{17,30}<br>R: — | guess |
| `chick-portrait` | `0x080f4090` | `0x080f5400` | `0x084b2f8b` / `0x084b2f9e` | L: 6.{18}<br>R: — | guess |
| `monkey-variant-portrait` | `0x080f3430` | `0x080f536c` | `0x084b2fb1` / `0x084b2fc4` | L: —<br>R: — | guess |
| `ham-blue-portrait` | `0x080efa90` | `0x080f4810` | `0x084b2fd7` / `0x084b2fea` | L: —<br>R: 3.{4} | guess |
| `ham-green-portrait` | `0x080efda0` | `0x080f4838` | `0x084b2ffd` / `0x084b3010` | L: —<br>R: 3.{8} | guess |
| `ham-yellow-portrait` | `0x080f008c` | `0x080f4860` | `0x084b3023` / `0x084b3036` | L: —<br>R: 3.{11} | guess |
| `ham-pink-portrait` | `0x080f0388` | `0x080f4888` | `0x084b3049` / `0x084b305c` | L: —<br>R: 3.{1} | guess |
| `ham-red-portrait` | `0x080f0670` | `0x080f48b0` | `0x084b306f` / `0x084b3082` | L: 3.{3,18}<br>R: — | guess |

## Correction to the earlier identification

`0x081bfc74` and `0x081bfa60` are Boss's **head in the room**, drawn with
OBJ sprites. Replaying their Entity animation changed the room head while
the face beside the dialogue stayed the same. The old `boss-portrait-demo`
therefore swaps a room-head frame. Its pointer and decompression tests remain
valid; the earlier identification as the dialogue face was too broad.
The affected symbols have been renamed to make this distinction explicit.

The actual dialogue face is a BG3 image at `0x080eb9bc`, with its own palette
at `0x080f437c`. `boss-recolor` changes this image's colours independently of
the room sprite.

## Dialogue-window portrait

| Address | Meaning | Confidence |
|---|---|---|
| `0x080eb9bc` | Boss dialogue tiles; LZ77, `0x33a` compressed / `0x480` decoded bytes | confirmed: live VRAM match |
| `0x080f437c` | Boss dialogue palette; LZ77, `0x26` compressed / `0x20` decoded bytes | confirmed: palette match and relocated palette test |
| `0x084b1dbb` | Event `0x06` loads left-slot palette | confirmed: operand reads |
| `0x084b1dbc` | Unaligned palette source operand | confirmed: read and checked repoint |
| `0x084b1dc4` | Event `0x06` loads left-slot tiles | confirmed: operand reads and upload |
| `0x084b1dc5` | Unaligned image source operand | confirmed: read and exact VRAM match |
| `0x084b1dce` / `0x084b1dcf` | Other-slot palette command / operand; destination `0x05000040` | likely: static decode; this slot was not displayed |
| `0x084b1dd7` / `0x084b1dd8` | Other-slot image command / operand; destination `0x06003700` | likely: static decode |
| `0x02007710` | Left portrait tile shadow, `0x480` bytes | confirmed: DMA source and raw match |
| `0x0201bbf0` | Left portrait palette shadow, `0x20` bytes | confirmed: DMA source and original/edited matches |
| `0x06003b80` | Live left-slot BG tiles | confirmed: watched DMA and exact match |
| `0x05000060` | Live BG palette bank 3, sixteen BGR555 colours | confirmed: palette match and visible recolour |

The image is **48 x 48, 4bpp**, comprising 36 row-major 8 x 8 tiles.
Each tile is 32 bytes; the low nibble is the left pixel of each pair.
Colours are sixteen little-endian BGR555 words. PNG export preserves indices
and duplicate colours, with index 0 transparent; the portrait also has opaque
white pixels. Format and geometry are **confirmed** by the exact VRAM match
and correctly displayed recolour.

BG3 uses character block 0 and screen block 23 (`0x0600b800`). In this window,
rows 21..26, columns 1..6 contain tiles `0x1dc..0x1ff`, palette bank 3, in
row-major order. The top-left tilemap entry is `0x0600bd42`; its tile is at
`0x06003b80`. The image appears at screen `(8, 104)` in this scene.
These tilemap contents and screen geometry are confirmed. The background is
scrolled with the window; reads of write-only scroll registers are not evidence
of scroll values. **The dialogue face uses a BG tilemap, not OAM.** Other
window positions and slots need their own scene checks.

## Decompressor and upload

`Event_CmdLoadLzGraphics` (`0x08001658`) handles event `0x06`: source and
destination pointers, read bytewise, nine bytes including the opcode.
It calls `Bios_LZ77UnCompWram` (`0x080e5614`), BIOS `swi 0x11`.
For a VRAM destination it decompresses at `destination + 0xfc003b90`, giving
`0x02007710` for Boss's `0x06003b80`. For a palette destination it uses
`destination + 0xfd01bb90`, giving `0x0201bbf0` for `0x05000060`.
With display enabled, `Gfx_QueueCopy` (`0x08009ac8`) queues the copy;
`Gfx_FlushCopyQueue` (`0x08009824`) uploads it via DMA3 at VBlank.

Source reads were reported at PCs `0x08001666`, `0x08001668`, `0x0800166e`,
`0x08001674`: exact Thumb instructions `0x08001662`, `0x08001664`,
`0x0800166a`, `0x08001670`. Uploads were reported at PC `0x0800992c`,
DMA setup instruction `0x08009928`. Tile-transfer registers showed source
`0x02007710`, destination `0x06003b80`, count `0x480` bytes; palette-transfer
registers showed source `0x0201bbf0`, destination `0x05000060`.
The Boss loader path and these uploads are **confirmed**. Forced-blank,
other destination, and event `0x07` branches remain static evidence only.

The complete image already contains eyes and mouth. During the tested greeting
and response it stayed equal to this full image: **no blink or mouth overlay
was observed for this dialogue portrait**. This does not exclude different
expressions elsewhere. The room head animates through separate complete frames.

## Room-head assets and Entity animation

| Address | Meaning | Confidence |
|---|---|---|
| `0x081b9f74` | Room-head palette; LZ77, `0x24` compressed / `0x20` decoded bytes | likely source: unique decoded match to live OBJ bank 4; load command not replayed |
| `0x081b9f98` | Greeting room-head frame; expands to `0x480` bytes | confirmed: live buffer and VRAM matches |
| `0x081bfa60` | Alternate room-head frame; `0x213` compressed / `0x480` decoded | confirmed by earlier replay |
| `0x081bfc74` | Idle room-head frame; `0x222` compressed / `0x480` decoded | confirmed by replay and pointer demo |
| `0x08687e17` / `0x08687e18` | Idle Entity animation / unaligned frame operand | confirmed |
| `0x08687dde` / `0x08687ddf` | Alternate Entity animation / operand | confirmed by replay |
| `0x0201d2b0` | Slot 2 room-head tile buffer | confirmed |
| `0x06010e20` | Slot 2 OBJ row-upload base | confirmed: frame tiles match row-strided VRAM |

`Anim_CtrlLoadRoomHeadTiles` (`0x0800d014`) reads `0xcb` plus its four-byte
source and calls the same BIOS wrapper. It selects `(Entity_GetIndex() - 10) / 3`
and reads the first word of `0x08469cdc + slot * 0x11c`; Boss index 16 selects 2.
Slot 0 uses `0x02002590`; slot 1 uses `0x0201fcd0` (both likely static pointers).

`0xcc`, `Anim_CtrlUploadRoomHeadTiles` (`0x0800d074`), reads destination
`+0x04` and tile width/height `+0x118/+0x119` from that record. Boss has
`0x06010e20`, 6, 6. `Gfx_QueueTileRows` (`0x08009b80`) queues six `0xc0`-byte
rows, source stride `0xc0`, destination stride `0x400`: the **2D OBJ grid's
32-tile row stride**. This explains why a contiguous VRAM search missed it.
The matched layout is confirmed; helper/command interpretation remains likely.

`0xcd` at `0x0800d0c8` takes a delay and pose index and assigns the descriptor
at record `+0x08 + pose * 4` to Entity `+0x00` (likely). The first slot-2
descriptor is `0x086538d4`: one 4bpp 64 x 64 OBJ, relative `(-12, -20)`,
starting tile `0x50`, palette bank 4. Its matching live OAM entry was at
`(93, 21)`. The uploaded 48 x 48 head sits one tile row/column inside this
64 x 64 canvas. Descriptor geometry and matching OAM are confirmed; the full
pose table remains unmapped. Scripts load full head frames with changing
mouth/eyes; no separate overlay was identified in this path.

Text `0xf4` invokes a **scene callback**, not a universal portrait ID.
`Scene_InvokeCallback` (`0x08001440`) indexes `0x03001fb0`. Here `0x08`
calls `Boss_CallbackIdleAnimation` (`0x0804193c`) and sets the room-head
animation to `0x08687e17`. Its table read was reported at PC `0x0800144e`,
instruction `0x0800144a`, LR `0x08005569`. Callbacks `0x09` (`0x080418b8`)
and `0x16` (`0x080418dc`) select `0x08679610` and `0x08687dde` (likely).
Boss was Entity 16 at `0x02022e8c`, array base `0x0202280c`, stride `0x68`;
script pointer `0x02022e90`, offset `0x02022ed8`. These are scene observations.

Room-head palette source references include event operands at `0x08051894`
(destination `0x05000280`) and `0x08687cd2` / `0x08687cde`. General room-head
editing and the remaining pose/animation commands are outside the gfx registry.

## Editing and verification

See [the graphics guide](graphics.md). `boss-portrait` remains supported alongside
the complete catalogue above.
An unchanged PNG preserves both original compressed streams exactly.
Imports produce source recipes containing only changed pixels/colours and
original-stream SHA1s. The builder reconstructs and recompresses locally,
allocates alongside code/text in checked padding starting at `0x086d0000`,
and checks both unaligned pointer operands. Gfx-only mods need no ARM compiler.
See [the free-space audit](rom_map.md#free-space-audit-2026-10-10).

`patches/boss-recolor` changes palette entries 4 and 5. The 38-byte replacement
at `0x086d0000` serves both palette operands; the original allocations remain
untouched. The left portrait is visibly blue, with unchanged tile data and
exact expected palette data in RAM and graphics memory. Cold boot, greeting,
response pages, conversation close/repeat, and surrounding animation were
checked. Bijou now verifies the right slot generally; this Boss-specific right loader,
room changes, and longer play remain human checks.

An already-open original savestate contains the old palette in RAM. Start a
fresh conversation after loading it, or use `states/dialogue-hunt-base.ss`,
press A, then A to choose Hamha. `states/boss-recolor-visible.ss` was captured
on the patched ROM. The human's `boss-portrait.ss0` was copied to
`boss-portrait.ss` for the bridge's naming convention; its original was retained.

Evidence: `extracted/gfx/` contains PNGs, original/recoloured upload traces,
raw comparisons, and verification JSON. Earlier room-head traces remain at
`extracted/dialogue-hunt-20261009/`.
