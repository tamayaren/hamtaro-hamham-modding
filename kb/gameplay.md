# Gameplay values

USA AH3E; original ROM SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`.
Investigation 2026-10-10/11. `confirmed` means a discriminating emulator test;
`likely` means strong code/table evidence awaiting that test; `guess` is a
tentative interpretation. Confidence applies to the stated part of a row.

RAM is the game's working notebook: a poke changes this session. ROM is the
recipe: editing a table, script operand or instruction changes future updates.
A menu display copy can differ from owned items. A saved array's size is not
automatically a gameplay cap.

## Systems checked before hunting

The existing `hamtools text dump` and [text tables](text_tables.md) supplied
these names. Text stayed in `extracted/text/`; only descriptions are recorded here.

| Requested system | Evidence in this game | Investigation status |
|---|---|---|
| Walk/run | Two ordinary velocity modes; held B selects run | ROM rows and live rates confirmed |
| Dash / ordinary jump | No third mode in ordinary movement; dialogue words alone do not establish a mode | No separate dash/jump parameter found |
| Ham-Chat actions | Tack-Q, Digdig, Scri-T/Scratch, Stickie, Rubrub and dance-related actions | Dictionary mapped; action physics partly mapped through challenges |
| Learned words | Supplied dictionary shows 10/86 and two sorts | Bits, count and acquisition order are separate state |
| Items | Supplied Items screen; native descriptions and item-to-flag table | Ownership flags and rebuilt menu IDs mapped |
| Currency/collectibles | Sunflower seeds, acorns, rocks/gems, accessories | Three totals confirmed; gain caps/rock records static |
| Progression | Loves Rescued, separate meter points/level, packed flags and scene IDs | Count and meter display sources confirmed; natural awards/gates static |
| Chapter/day | No numeric chapter/day system established in text or inspected code | Room selectors are not named chapters/days |
| Challenges | Stickie Note, Digdig It, Tic Tack-Q reached scripts | Static candidates; active states deferred |
| Dance/polishing | Ham-Jam/Dance Hall, Rubrub and Accessory Room | Active parameters unresolved without those states |
| Timers/RNG | Script waits, challenge timers, Boss randomized hint | RNG state and Boss parameter demo confirmed |
| Save data | SRAM library and normal End Game/Continue | Gameplay blocks, selected persistence and backup recovery confirmed |

## Value overview

Use `E = *u32[0x03002d88] + u8[0x03002bfc] * 0x68` for the current
player Entity. Bedroom E=`0x02022c1c` is scene-specific. Signed 16.16 holds
whole pixels in its upper half: 0x00010000 is 1 pixel. Scene-specific event
variables can mean something else after changing rooms.

| Value | RAM address / formula | Type | ROM source, initializer or writer | Cap / rule | Confidence |
|---|---|---|---|---|---|
| Player X / Y | E+0x18 / E+0x20 | s32 16.16 | `Player_Update` `0x0800631c` | Collision bounds | confirmed |
| Walk velocity | E+0x24 / E+0x2c | s32 16.16 | Four pairs `0x08467af0`; first nonzero Y `0x08467af4` | Original 1 pixel/update | confirmed |
| B-run velocity | Same fields | s32 16.16 | Four pairs `0x08467b10`; pointer literal `0x080066c8` | Original 2; demo 3 pixels/update | confirmed |
| Ordinary acceleration ramp | No separate scalar | — | `0x08006508` assigns complete velocity; player clears it each update | Immediate selection in inspected path | likely code; fixed rates tested |
| Generic acceleration | Entity +0x30 / +0x34 / +0x38 | s32 16.16 | Setter `0x0800af38`, physics `0x0800b2f0` | No global speed cap established | likely |
| Player control / interaction | `0x030021d0` / `0x03000785` | u8 bits | `0x0800631c` / `0x080067d4` / `0x0800689c` | Gates B/A; A requests bit 0x08, not a word ID | likely |
| Cadence-like value | `0x03000778` | s32 | `0x08006508` | 8 walk / 4 run / 0 idle; precise purpose unknown | guess purpose |
| Dig/Scratch/jump/dance physics | Unmapped outside challenge contexts | — | Ham-Chat dispatch, animation and Entity helpers | No separate jump/dash constant established | unresolved |
| Learned word | `0x03002170+((wordId+0x46)>>3)`, mask `1<<((wordId+0x46)&7)` | bit | Reader `0x08033858`, learner `0x0803369c` | IDs 1..86; flags 0x0047..0x009c | Bestest ID 0x44 confirmed; full formula likely |
| Learned count | `0x03003db0` | u8 | Write `0x08033834`, read `0x080039c8` | Display /86; no inspected learner bounds guard | display/save confirmed; maintenance likely |
| Learned order / pending word | `0x030037c0` / `0x02003a06` | u8[86] / u8 | Append `0x0803382e`; starter request 0xff at `0x080db28f` | Ten starter IDs; high-bit requests have special handling | likely |
| Dictionary sort | `0x0300218f`, mask 0x01 | flag 0x00f8 | Script flag store `0x08003be8` | 0 Order Learned / 1 Alphabetical | confirmed |
| Word-name / companion tables | IDs select ROM slots | 87 pointers each | `0x084a7840` / `0x084a799c` | Slot 0 fallback; 86 words, IDs match insert IDs | likely complete tables |
| Alphabetical ranks | Derived from word ID | 86 ROM u8 | `0x084a77bc` | Distinct 0..93 with gaps; not alternate word IDs | likely |
| Item ownership | Flags at `0x03002170` | bit per ID | Table `0x084a7bd0`; rebuild `0x08034c78` | 48 IDs; 45 established description spans | Oilcan ID 1 / flag 0x009f confirmed; rest likely |
| Item menu slots / selection | `0x030038d0` / `0x02003b10` | u8[48] / u8 | Order `0x084a7ba0`; rebuild write `0x08034c88` | 0xff empty; temporary menu copy | slot/rebuild confirmed; extent/selection likely |
| Item descriptions / scroll | `0x02003b13` scroll | u8 | Offsets `0x084a7e4a`, pointers `0x084a7ea8`, limits `0x084a7e1c` | Per-item scrolling, not stack caps | likely; Oilcan description tested |
| Sunflower seeds | `0x0201d0c2`, word 9 | u16 | Gain `0x0804adc8`; u32 cap `0x0804ae10`; starter award `0x080daf48` | Gain cap 999; starter award 10 | RAM/save confirmed; cap/award likely |
| Acorns | `0x0201d0c4`, word 0x000a | u16 | Gain `0x0804b3b4`; 50 immediates `0x0804b3c4` / `0x0804b3cc` | Gain cap 50 | RAM/save confirmed; cap likely |
| Displayed rocks | `0x0201d0c6`, word 0x000b | u16 | Recount `0x0804aff0`; gain `0x0804af40` / `0x0804b1e8` | Recount 64 records, not this total alone | display/save confirmed; recount likely |
| Rock records / metadata | `0x0201bf90` | 64 records, stride 4 | Allocate `0x08009194`, count `0x08009210`; metadata `0x08465e48` | Nonzero 5-bit state occupied; 7-bit type, complete type span unknown | likely |
| Transaction / display target | `0x0201d0bc` / `0x0201d0be`, words 6/7 | u16 each | Resource add/spend/display natives | Gain uses remaining room; overlarge spend accepts zero | likely |
| Gems / accessories totals | No authoritative separate count found | — | Text, rock and ownership systems establish existence | Dedicated counts/caps unresolved | need polishing/shop context |
| Loves Rescued | `0x0201d0cc`, word 0x000e | u16 | Status command `0x080d11a5`; award increment `0x08034554` | Adds one per award; no count clamp established | display confirmed; natural increment likely |
| Love meter points | `0x0201d0ca`, word 0x000d | u16 | Weights `0x084a7b88`; 56 immediates `0x080344b0` / `0x080344b4`; write `0x08034738` | Normal cap 56; weights 2/3/4 | fullness confirmed; awards/cap likely |
| Love meter level | `0x0201d0c8`, word 0x000c | u16 | Write `0x0803474c`; threshold formula `0x0803473c`..`0x08034746` | Normal 0..4, boundaries 14/28/42/56 | appearance confirmed; natural boundaries likely |
| Rescue animation scratch | `0x02003a09` / `0x020039f1` / `0x0201d0f8` | u8 selector / u8 phase / u16 timer | `Event_UpdateRescueAward` `0x08034490` | Count increment at timer 48; timer unit untested | likely, context-specific |
| Gameplay flags | `0x03002170+(id>>3)`, bit `id&7` | 96 saved bytes | Read `0x08001458`, set `0x08001478`, opcodes 0x33/0x46 | 768 saved bits, not accessor validation | addressing/specific bits confirmed; extent likely |
| Scene / subscene | `0x03002c48` / `0x03001f58` | u8 each | Descriptor root `0x08466944`, loader `0x080009f8` | Room selectors; no named chapter/day counter found | scene 1.1 observed; full meaning likely |
| Boss hint counter | `0x020039cb`, byte 0x003b | u8 | `0x08050094`, per-hint stores | Steps 0..3, then random route | confirmed |
| Shared result / Boss random hint | `0x020039f0`, byte 0x0060 | u8 scratch | `0x0805009e`; bounds `0x080500a2` / `0x080500a4` | Original [0,3); demo [2,3); reused elsewhere | confirmed mapped route |
| Stickie elapsed / countdown | `0x0201d270`, word 0x00e0 | u16 upward ticks | `0x0801b7ac`; shifted threshold `0x0801b83c`; draw `0x0801c404` | End above 3599; display `(3600-elapsed)/60` | likely; real tick rate untested |
| Stickie score / record | `0x0201d272` / `0x0201d134` | u16 each | Score `0x0801c05c`; record gate `0x0801b746`, literal `0x0801b790` | Adds 50/30/10; record must beat prior and 859; zero shown 860 | likely |
| Stickie prizes / time bonus | Same score/elapsed | u16 operands / s32 delta | Commands `0x080730e6`..`0x0807310e`; -600 literal `0x0801c358` | Prize tiers 400/600/800/1000/1200; bonus has no inspected underflow guard | likely |
| Stickie motion/difficulty | `0x02003b30` / `0x02003b33` / `0x02003b34` | u8 each | Reset `0x0801b560`, paper motion `0x0801bb80` | Phase 0..2; initial player step 1, paper multiplier 2 | likely |
| Digdig board | `0x02003b36` | u8[9] | `0x0801c7e4`; partner `0x0801c8c4` | Four pairs plus special patch; removed 0xff | likely |
| Digdig attempts / pairs | `0x02003b3f` / `0x02003997` | u8 each | `0x0801ca90` / `0x0801c988` | Fourth attempt ends; perfect 4 pairs; no countdown found | likely |
| Tic Tack-Q balls | `0x02003b46` | u8 | Initial 4 `0x0801d020`, decrement `0x0801d668` | End at zero after actor finishes | likely |
| Tic Tack-Q lines / card | `0x02003b52` / `0x03003560` | u8 / u8[9] | Recount `0x0801e870`, setter `0x0801e810` | 0..8 from 3 rows, 3 columns, 2 diagonals; prizes 1/3/5/6/8 | likely |
| Tic Tack-Q difficulty/speed | `0x02003b45`; balloon Entity velocity | u8 / s32 16.16 | Speeds `0x084a681c`, steps `0x084a6822` | Difficulty 0..2; magnitudes 0.5/0.75/1 pixels/update | likely |
| Tic Tack-Q local timers | `0x02003b53` / `0x02003b54` / `0x02003b55` | u8 each | Actor natives `0x0801d26c` / `0x0801d724` / `0x0801d858` | [60,180) or [180,250), with actor/state gates | likely; not whole-game limit |
| Tic Tack-Q display timer/phase | `0x02003b4a` / `0x02003b4b` | u8 each | `0x0801e524`, durations `0x084a683a` | Phase 0..7; difficulty rows stride 8 | likely |
| Rubrub action tier | Love meter level above | u16 | Script `0x08055186` selects four actions `0x084b1a01` / `0x084b1a45` / `0x084b1a89` / `0x084b1acd` | Levels 0..1 / 2 / 3 / 4 | likely; polishing calculation untested |
| Ham-Jam scores / Rubrub completion | Unmapped gameplay fields | — | Reached dance/polishing scripts and natives | Need active dance/rock states before naming scores/timers | unresolved |
| Script wait | `0x0300001a` | u16 | `0x08001580`, inline opcode-0x02 u16 | 1..65535; zero underflow is static conclusion | likely |
| RNG A/B/C | `0x03000000` / `0x03000004` / `0x03000008` | s32 each | Update `0x080003d8`; multipliers `0x080003de` / `0x080003ee` / `0x080003fe`; moduli `0x0800042c` / `0x08000434` / `0x0800043c` | `old*171%30269`, `old*172%30307`, `old*176%30323`; all-zero absorbing | positive transitions/zero case confirmed |
| RNG boot/draw | Same state | u32 ROM literals | Seeds `0x08000388` / `0x08000390`; weights `0x08000440` / `0x08000444` / `0x08000448` | Seeds 15042/19955, C VCOUNT+1; helper [low,high) if high>low | full arithmetic likely; Boss range tested |
| Saved RAM | Selected regions, not contiguous | Packed copies | `0x08048f94` / `0x08049088` / `0x08049140` | 512 event bytes, 256 words, 768 flags plus other regions | selected fields confirmed; full map likely |
| SRAM banks / header | `0x0e000000` / `0x0e004000` | Two 16 KiB banks, 8-byte header | Tables `0x084673d0` / `0x084673e4` / `0x084673f8` | 32 KiB; blocks 1..3 tested, 0/4 special | gameplay layout confirmed; special blocks likely |
| Checksum / fallback | Header +0x06; `0x03002158` statuses | u16 / u8[5] | `0x0800044c`, save `0x0800108c`, load `0x08001320` | Folded complemented word sum; bad primary gameplay block selects backup bank | tested blocks/path confirmed |

Details: [RAM](ram.md), [structures](structs.md), [words/items/resources](items_words.md),
[movement/challenges](challenges.md), [love meter](love.md), [save/RNG](save.md), [event scripts](event_scripts.md).

## Progression gates

[gameplay_event_flags.csv](gameplay_event_flags.csv) maps 455 distinct reached-script
flag IDs to RAM bytes/masks and read/write sites; highest ID 0x02da. These are
static references, including words/items, not 455 named story milestones or
a complete native-access inventory.

Tested gates include 0x0010's alternate Boss greeting/companion portrait and
0x017d's first/subsequent greeting. Flag 0x007e is Rubrub learned (static word
identity); several earlier unnamed progression flags are also words. Sort
0x00f8 and Oilcan ownership 0x009f have confirmed menu effects. The
[event-script table](event_scripts.md#gameplay-flag-subsets-and-ram-addresses)
records RAM masks and remaining story uncertainties.

Script `0x08051baa` combines learned-word flags with meter-level gates 1..4;
Rubrub script `0x08055186` chooses four action tiers from the same level.
Their static connections are in [love.md](love.md). A chapter/day scalar
or intended maximum rescue count has not been established.

## Verified demonstrations

Both recipes are disabled by default and check original bytes. Build by name
to exclude the human's enabled faster-walk edits. Standalone outputs are in
`build/gameplay-run-boost/` and `build/gameplay-boss-hint/`, each containing
`hamtaro-mod.gba` / `hamtaro-mod.bps`. Applying either BPS to the verified
original reproduced its built ROM exactly.

| Demo | Original versus patched | Verification limit |
|---|---|---|
| [gameplay-run-boost](../patches/gameplay-run-boost/README.md) | Walk 1 stays 1; B-run 2 becomes 3 pixels/frame in all four directions | Four controlled collision endpoints match; other rooms/long sessions pending |
| [gameplay-boss-hint](../patches/gameplay-boss-hint/README.md) | Controlled random route: original result 0 -> first hint; patched result 2 -> third hint | Earlier hints/story gates not exhaustively tested |

Each cold-booted, exercised its target from original-ROM states and returned
to normal input. Each ran 900 frames in each of four supplied states (3,600
total): bedroom, Items, dictionary, Sunny Peaks. These were state loads, not
natural room-transition tests. Boss interaction/menu and hint close worked;
no freeze or garbled graphics was observed. See the
[verify-mod skill](../.agents/skills/verify-mod/SKILL.md). No all-words or
raised-cap demonstration is claimed verified.

## Exact human playtest checklist

Apply each BPS separately to a copy of the verified original with a BPS patcher,
or use its built ROM. Use a test save copy. Original states work because these
mods do not change RAM layout.

1. **Run boost:** load `walking.ss0`. Walk on open floor without B, then hold B.
   Run Right, Left, Up and Down, and release direction to stop. Speed should
   increase only with B. Push against room edges and the bed; check clipping
   or sticking. Repeat in `sunny_peaks.ss0`, make a natural room transition,
   open Items/dictionary, and return to walking. Do not combine with faster-walk:
   it edits the same running entries.
2. **Boss hint:** load local `gameplay-boss-random-ready.ss0`, a controlled copy
   of `dialogue-state.ss0`. A talks to Boss; A chooses Hamha; advance every page
   with A until control returns. Repeat three times: the random route should
   keep choosing the third hint. The same state on the original chooses the
   first hint. This lab state sets repeat gates/counter and zeros RNG; use an
   ordinary save afterward to check natural progression and earlier hints.
3. **Longer checks:** play each separately through several rooms and a
   save/Continue cycle on a test save. Report crashes, clipping, unexpected
   dialogue gates or menu corruption. Challenges and late story remain future
   coverage after their states exist.

## Deferred states and unresolved work

Available states were listed before use: `walking.ss0`, `sunny_peaks.ss0`,
`dialogue-state.ss0`, `inventory-screen.ss0`, `ham-chat-word-list.ss0`, plus older
local dialogue/portrait experiments. Raw evidence stays in `extracted/` and
the controlled Boss state in ignored `states/`.

The human said these will be prepared later; no blind navigation was attempted:

| Named state | What it resolves |
|---|---|
| `shop-before-purchase.ss0` | Natural spending, accepted quantities, seed/item limits |
| `collectible-before-pickup.ss0` | Natural gain/cap writers and rock records at boundaries |
| `stickie-note-running.ss0` | Timer rate/end tick, score/bonus/record versus prizes |
| `digdig-it-running.ss0` | Attempt/pair changes and fourth-attempt result |
| `tic-tack-q-running.ss0` | Balls, line recount, actor timers, perfect card |
| `rubrub-ready.ss0` | Rock state meanings, polishing and love-meter effect |
| `ham-jam-ready.ss0` | Dance timing, score and completion |
| `later-love-meter.ss0` | Natural love/rescue increments, fuller meter and story gates |

A natural word-learning or key-item acquisition state would also confirm those
writers. Without these contexts, likely caps/initializers and challenge addresses
remain documented candidates. No SRAM helper was added: special records and
abnormal save handling still need work before a general decoder/writer is justified.
