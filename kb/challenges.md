# Movement actions and challenges

USA AH3E, verified original SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`.
Static analysis completed 2026-10-10/11. All challenge fields, thresholds and
special-action interpretations below are **likely** unless marked **guess**.
Ordinary movement has separate emulator confirmation in [ram.md](ram.md)
and the run-speed demo in [gameplay.md](gameplay.md).

The challenge names came from rooted dialogue/native text inventories.
Only the supplied rooms and menus were exercised. Active challenge states
are deferred by the human, so these are candidates for later pokes rather
than verified cheat codes.

## Ordinary walking and running

Hamtaro starts each ordinary input poll with zero X, height, and Y velocity.
The movement routine then chooses a complete velocity from a table. The player
update adds X/Y velocity to position and immediately clears it again. Holding B
selects the other table row immediately: this path has no accumulated acceleration
or run-up curve. Releasing directional input stops motion on the same poll.

The table at `0x08467af0` contains four walk directions, followed at `0x08467b10`
by four B-held run directions. Each entry is an `(X,Y)` pair of s32 16.16 values:
walk magnitude 1 pixel per poll; run magnitude 2. The direction priority is
Up, Down, Left, Right; only one direction is selected. These two row addresses
belong to one existing `kPlayerMoveVelocityTable`, not two independent tables.

| Value/address | Type | Meaning/default | ROM source | Cap/boundary | Confidence |
|---|---|---|---|---|---|
| `0x08467af0`, 0x20 bytes | 4 pairs of s32 16.16 | Ordinary walk velocity, magnitude 1 | Table pointer literal `0x080066c8`; load/call `0x080065d6`-`0x080065e4` | Four cardinal directions | likely; prior KB tested |
| `0x08467b10`, 0x20 bytes | 4 pairs of s32 16.16 | B-held run velocity, magnitude 2 | Same table, mode stride 0x20 | Two table modes; no walking acceleration cap | likely; prior KB tested |
| `0x030021d0` | u8 flags | Player-control gates; bit 1 suppresses B-run and alters B/menu handling; bit 3 suppresses A interaction; bit 2 selects one-poll reset path | Literals `0x08006360`, `0x0800658c`, `0x0800680c` | Bit field, not a speed | likely |
| `0x03000786` | u8 result/status | Movement mode initially 1, or 2 for B-held run; zero without D-pad; later overwritten with helper `0x08007348` result | `0x08006526`-`0x0800655c`; `0x080063ac`-`0x080063b0` | Do not treat as a persistent run flag | likely |
| `0x03000778` | s32 | Moving cadence-like value: 8 walking, 4 running, 0 idle | Literals `0x08006590`, `0x080065ac`; divide/store `0x08006596`-`0x0800659e` | Direct assignment, not a speed ramp; exact downstream purpose guess | likely values; guess purpose |
| `0x03000785` | u8 bit mask | Per-poll interaction request; A creates bit 0x08 | `0x080067d4`; pointer `0x08006808` | Cleared every poll; not a Ham-Chat word ID | likely |
| `0x03002c40` | u8 | Special/menu request subtype: B=1 when control bit 1 set; Select/L=2; Start/R=3 when permitted | `0x080067d4`; literals `0x0800683c`, `0x08006874`, `0x08006898` | Input selector 1-3; UI meaning needs runtime check | likely |
| `0x0200399c` (byte variable 0x000c) | u8 | Consecutive player polls without any held button; zero when any low-ten-bit button held | `0x08006404`-`0x08006450`, literal `0x0800643c` | Normal path reaches 0x80 then stops incrementing by signed-byte test | likely |
| `0x03001f98`, `0x03001f7c` | u8 each | Interaction/collision status bits and correction direction | Literals `0x080066f4`, `0x0800677c` | Collision can override requested velocity | likely |

`Player_HandleMovementInput` is `0x08006508`; its first velocity reset is the
call at `0x0800651e`. `Player_Update` is `0x0800631c`; position stores are
`0x080063c8` and `0x080063d0`, and X/Y velocity clears are `0x080063d2` and
`0x080063d4`. Obtain the current Entity through `*0x03002d88 +
u8[0x03002bfc] * 0x68`; never promote a scene-specific Entity address to a global.

Collision handling after the table load matters for mods. With status bit 2 set,
`0x08006716`/`0x08006738` can adjust the requested destination using an 8-pixel
grid mask. Under `(status & 0x0d) == 5`, `0x08006740`-`0x080067ae` overrides
one axis with magnitude 1. These are collision corrections, not evidence of
a dash, jump, or acceleration curve.

## Interaction and generic motion helpers

`0x08009754` reads the game's active-high RAM button masks: argument mode 0
means held, 1 new press, 2 press/repeat, 3 release. Thus ordinary running uses
**held B**, while `0x080067d4` reads **new presses** masked by 0x030f.
A request calls both map and nearby-actor interaction scans via `0x0800689c`.
The room script subsequently opens the Ham-Chat menu and dispatches the chosen
word. See `event_scripts.md` for that established separation.

| Address | Proposed/helper name | Behavior | Confidence |
|---|---|---|---|
| `0x080067d4` | `Player_PollInteractionButtons` | Clears request mask; translates permitted new presses to interaction/menu requests | likely |
| `0x0800689c` | `Player_ScanInteractionTargets` | Runs map scanner `0x0800761c` and actor scanner `0x08007e28` | likely |
| `0x0800af00` | `Entity_SetPosition` | Index plus three s32 values to Entity `+0x18/+0x1c/+0x20` | likely |
| `0x0800af1c` | existing `Entity_SetVelocity` | Index plus three values to `+0x24/+0x28/+0x2c` | likely static; prior KB tested |
| `0x0800af38` | `Entity_SetAcceleration` | Index plus three values to `+0x30/+0x34/+0x38` | likely |
| `0x0800b2f0` | existing `Entity_ApplyPhysics` | Position += velocity, then velocity += acceleration, for generic Entity processing | likely |

The generic physics function also integrates short fields `+0x3c/+0x3e/+0x40`
with `+0x44/+0x46/+0x48`. The first two are assigned 0x0200 when their signed
result exceeds 0x01ff (literal `0x0800b374`). This is not a movement-speed cap;
those fields' visual meaning remains unproven here.

A direct Thumb-BL scan in the low code region found calls to the acceleration
setter only at `0x08032430` and `0x08032494`, in `0x080323b0`. That routine
starts table-selected entities at Y=4, with Y velocity -0x8000 (-0.5 in 16.16;
literal `0x080324d0`) and Y acceleration 0x1000 (+0.0625, synthesized at
`0x08032428`-`0x08032430`). When Y exceeds 0x00047fff (literal `0x080324d8`),
it assigns Y=0x00048000 (4.5) and clears velocity/acceleration. The complete
`batch-080323b0.txt` export agrees with those ROM instructions. Its gameplay/UI ownership is unresolved.
This limited scan misses indirect calls and direct field writes. Do not rename
it as player jumping. In particular, generic three-axis physics proves neither
an ordinary jump command nor a dash action.

Established terminology is Ham-Chat, Scri-T/Scratch, Digdig, Tack-Q, Stickie,
Hula/Ham-Jam, and Rubrub. Reached challenge text associates word 0x03 with
Tack-Q, 0x04 with Digdig, and 0x0d with Stickie. The challenge callbacks below
are concrete action contexts; the broader Scratch/dance/polishing timing and
special-movement constants remain unmapped in this bounded investigation.

## Stickie Note: timer, score, and paper motion

Scene 3.4 root `0x08072340`; native reset `0x0801b560` is reached at
`0x08073065`. The displayed countdown is derived from an **upward elapsed
counter**, not a RAM counter that counts down. Code uses 60 ticks per display
second and a 3,600-tick duration. Real-time call frequency is untested.
The end-comparison literal `0x0801b83c` stores **3599 shifted left 16**
(`0x0e0f0000` as u32); elapsed is also shifted before comparison.
Its high u16 at `0x0801b83e` is 3599. Do not patch the full literal as plain 3599.

| Value/address | Type | Default/meaning | ROM source | Cap/threshold | Confidence |
|---|---|---|---|---|---|
| `0x0201d270` (word 0x00e0) | u16 | Elapsed ticks, reset to 0; incremented by timer native | Reset `0x0801b56e`; tick/store `0x0801b7b6`-`0x0801b7ba`; script resets `0x08072fb9` | End flag 0x00fd set when elapsed >3599; literal `0x0801b83c` | likely |
| Displayed time | derived integer | `(3600 - elapsed) / 60`; then minute/second digits | `0x0801c404`; duration synthesized at `0x0801c410`-`0x0801c412` | 60 seconds by code's 60-tick scale, not a measured wall-clock duration | likely |
| `0x0201d272` (word 0x00e1) | u16 | Score reset to 0; paper kinds 1/2/3 add 50/30/10 | Reset `0x0801b576`; additions `0x0801c1be`, `0x0801c1ec`, `0x0801c230` | Four digits rendered by `0x0801c46c`; no numeric clamp found in inspected additions | likely |
| `0x0201d134` (word 0x0042) | u16 | Stored high score; 860 displayed when stored value is zero | Record gate `0x0801b746`-`0x0801b768`; default `0x0801c4f8`-`0x0801c4fa` | Update only if score >stored record AND score >859; 859 literal `0x0801b790` | likely |
| Prize score boundaries | u16 script operands | Tiers at 400/600/800/1000/1200 | Branch commands `0x0807310e`, `0x08073104`, `0x080730fa`, `0x080730f0`, `0x080730e6` | Inclusive lower bounds; these differ from the record gate | likely |
| `0x02003b30` (byte 0x01a0) | u8 | Elapsed-time difficulty phase 0/1/2 | `0x0801b818`-`0x0801b872` | Phase 1 when elapsed >1800; phase 2 when >3000 | likely |
| `0x02003b33` (byte 0x01a3) | u8 | Stickie player's horizontal step, initialized 1 | `0x0801b59e`-`0x0801b5a0`; used `0x0801b454`-`0x0801b45e` and `0x0801b4aa`-`0x0801b4b4` | Position tests around X=40 and X=176; no speed cap checked | likely |
| `0x02003b34` (byte 0x01a4) | u8 | Paper velocity/acceleration multiplier, initialized 2 | `0x0801b5a8`-`0x0801b5aa`; paper setter `0x0801bb80` | No multiplier cap found | likely |
| Timer adjustment, paper kind 4 | signed constant applied to u16 | Subtract 600 elapsed ticks, equivalent to +10 displayed seconds on the nominal scale | `0x0801c278`-`0x0801c284`; literal `0x0801c358` | No underflow guard seen on this subtraction | likely arithmetic; human-visible behavior untested |

`0x0801b39c` handles Stickie movement/collection state. It reads the shared
selector `0x03001fac`, directly steps Entity 10's X using byte 0x01a3, and
triggers the collection animation through word-variable flags. This differs
from ordinary D-pad walk/run processing.

`0x0801bb80` chooses lateral/vertical velocities for paper entities 26 onward
and sets acceleration fields directly. Byte 0x01a4 multiplies those values;
for example lateral velocity is magnitude multiplier*0.5 or multiplier*1,
with opposing X acceleration magnitude multiplier*0x400 or multiplier*0x800.
These values govern drifting paper, not Hamtaro's walking acceleration.
Paper state records at `0x03003d60` have stride 8 and ten slots; spawner records
at `0x03003e20` have stride 8 and three slots. Native `0x0801b624` stops their
motion, `0x0801bdc4` updates spawners, and `0x0801c05c` handles collection.
The complete paper probabilities and collision reconstruction are outside scope.

## Digdig It: matching and attempt limits

Scene 3.5 root `0x080733f0`. This inspected challenge is a pair-matching game,
with no countdown timer identified. Do not equate its attempt counter with time.

| Value/address | Type | Default/meaning | ROM source | Cap/threshold | Confidence |
|---|---|---|---|---|---|
| `0x02003b35` (byte 0x01a5) | u8 bits | Completed-symbol mask; reset with board and ORed after a match | `0x0801c7e4`; `0x0801c9fe`-`0x0801ca06` | Low four bits used for ordinary symbols; bit 4 covers special symbol | likely |
| `0x02003b36`-`0x02003b3e` | u8[9] | Dirt-patch contents; four pairs of IDs 1-4 plus special 5 or 6 | `0x0801c7e4` RNG placement; sentinel tests `0x08073738` onwards | 9 patches; 0xff marks removed patches | likely |
| `0x02003b41`, `0x02003b42` (bytes 0x01b1/0x01b2) | u8 each | Player and partner patch selectors | Script sets `0x08073742` onwards; partner native `0x0801c8c4` | One-based IDs 1-9 | likely |
| `0x02003b3f` (byte 0x01af) | u8 | Attempts used, initialized 0, incremented once per attempt | Script `0x08073d58`; native `0x0801ca90` store `0x0801ca9c` | Completion selector becomes 1 when count >3; compare `0x0801caa2` | likely |
| `0x02003997` (byte 0x0007) | u8 | Successful pairs, initialized 0 and incremented on match | Script `0x08073d5c`; native `0x0801c988`, store `0x0801c9ba` | Perfect result checked at 4 by `0x08073f1a` and `0x08074416`; no independent saturation found | likely |
| `0x02003b74` (byte 0x01e4) | u8 | Symbol copied when wildcard 5 matches another symbol | `0x0801c9c0`-`0x0801c9c6` | Setup clears it; not a points total | likely |

`0x0801c988` reports match=1, mismatch=2 in shared byte variable 0x0060
(`0x020039f0`); equality or player symbol 5 counts as a match. `0x0801c9e4`
marks both chosen patches 0xff and reports completion when at least eight
patches have been removed. `0x0801c8c4` chooses an ordinary-symbol partner patch,
excluding the current/previous choices and the remembered wildcard symbol.
`0x0801cb14` chooses four distinct IDs in [1,8), so the highest generated ID is
7, not 8. `0x0801cb6c` maps those IDs through ROM table `0x084a680c` to reward
arguments; item identities belong to the item/word worker.

## Tic Tack-Q: balls, line score, and local timers

Scene 3.6 root `0x08074c20`. The reached text describes rolling a ball at numbered
balloons and completing rows/columns/diagonals. The code's timers below schedule
actors and display changes; they are not an established whole-game time limit.

| Value/address | Type | Default/meaning | ROM source | Cap/threshold | Confidence |
|---|---|---|---|---|---|
| `0x02003b46` (byte 0x01b6) | u8 | Balls remaining, initialized 4 | `0x0801d020`-`0x0801d022`; decrement `0x0801d668`-`0x0801d66a` | End flag 0x00fd set when zero after ball actor finishes, `0x0801d6ba`-`0x0801d6c6` | likely |
| `0x02003b52` (byte 0x01c2) | u8 | Completed-line score, initialized 0 and recomputed from card marks | Reset `0x0801d006`-`0x0801d00a`; updater `0x0801e870`, store `0x0801e932`; display `0x0801e628` | Structural range 0-8; script prizes at 1/3/5/6 and perfect=8, `0x08075804` through `0x080757dc` | likely |
| `0x03003560` | u8[9] | Card marks: zero is unmarked; ordinary hit stores number 1-9 | Clear `0x0801d072`-`0x0801d082`; setter `0x0801e810`, store `0x0801e828` | Any nonzero mark counts toward a line; number-to-cell lookup uses labels at `0x03003af0` | likely |
| `0x030035c0` | records, stride 8 | Balloon data; ordinary IDs and generated paired numbers | `0x0801cfe8`; pair helper `0x0801e498` | Initialization visits 16 slots; paired numbers are distinct 1-9 | likely |
| `0x02003b45` (byte 0x01b5) | u8 | Difficulty selector, initialized 1 | `0x0801d014`-`0x0801d018`; normal effect increments `0x0801df2c`-`0x0801df34`, decrements `0x0801dfba`-`0x0801dfc2` | Inspected effects keep it in 0-2; indexes speed/cycle/display tables | likely |
| `0x02003b44` (byte 0x01b4) | u8 | Cycle accumulator, initialized 0 | `0x0801d002`-`0x0801d004`; update `0x0801d590` | Adds ROM byte at `0x084a6822 + difficulty`; resets to 0 when post-add u8 >95 | likely |
| `0x02003b53` (byte 0x01c3) | u8 | Local actor countdown | Init `0x0801d1d8`-`0x0801d1e6`; decrement `0x0801d368`-`0x0801d36c` | RNG [60,180), only when relevant flag/state permits | likely |
| `0x02003b54` (byte 0x01c4) | u8 | Another local actor countdown | Init `0x0801d77a`-`0x0801d788`; decrement `0x0801d7c8`-`0x0801d7cc` | RNG [180,250); separate helper `0x0801d6e4` can load [60,180) | likely |
| `0x02003b55` (byte 0x01c5) | u8 | Third actor countdown | Earlier loader `0x0801d704`; actor spawn reload `0x0801d8b2`-`0x0801d8be`; decrement `0x0801d902`-`0x0801d906` | Spawn cycle RNG [180,250); helper also loads [60,180); decrements only in actor state 2 with flag 0x02a6 clear | likely |
| `0x02003b4a` / `0x02003b4b` (bytes 0x01ba/0x01bb) | u8 each | Display/sequence countdown and phase | Script init `0x080759d8`-`0x080759dc`; native `0x0801e524` | Countdown starts 2; phase wraps over 0-7; reload from `0x084a683a + difficulty*8 + phase` | likely |

The line updater `0x0801e870` starts its local total at zero, tests three
horizontal lines, three vertical lines, and both diagonals for all-nonzero marks,
and writes the total to byte 0x01c2 at `0x0801e932`. Thus 8 is a structural
maximum, not a saturation constant or a cumulative award. Balloon updater
`0x0801da4c` calls it at `0x0801dc7a` after a player-ball collision; the number
setter `0x0801e810` maps a one-based number to its shuffled card cell through
`0x0801e834`. Clearing a mark passes zero to the same setter.

The complete actor-C routine `0x0801d858` has states 0-3. State 0 spawns its
actors and overwrites its timer with RNG [180,250); state 1 waits for the entry
motion; state 2 decrements the timer only while flag 0x02a6 is clear; zero
triggers the next animation and state 3. This explains why the shorter [60,180)
loader alone did not describe the active actor cycle.

ROM table `0x084a681c` has three difficulty-indexed u16 values 128/192/256.
Setup `0x0801d194`-`0x0801d1a4` turns an entry into negative X velocity by
multiplying by 0x100: -0.5/-0.75/-1.0 in 16.16. Spawn helper `0x0801e134`
uses the same magnitudes with either sign according to the travel direction.
Cycle-step bytes at `0x084a6822` are 2/3/4 for difficulties 0/1/2. These
constants belong to balloons and their cycle, not ordinary player running.
No complete minigame reconstruction or active challenge test was attempted.

## Evidence and remaining checks

Independent ROM verification succeeded. Cached decompiles were checked against
literal values and contiguous Thumb disassembly produced from that same ROM.
Reached scene-script variable records supplied setup and prize-threshold sites;
text was used only to interpret context, never copied into this public document.
The RNG helper `0x08001508` is [low,high), consistent with Singer's save/RNG report.
Ghidra access was serialized. A batch rebuilt requested Thumb entry points temporarily and
exported complete functions. The normal Thumb return epilogues were checked
against disassembly where pseudocode reported an unrecovered indirect jump.
The score updater and mark helpers were checked in bounded contiguous ROM
listings. The project transaction was rolled back and the project closed.

Local evidence: `extracted/gameplay-actions/cache-literals.txt`,
`movement-actions-disasm.txt`, `entity-setters-disasm.txt`,
`input-query-disasm.txt`, `acceleration-callers-disasm.txt`,
`challenge-natives-disasm.txt`, `tic-score-disasm.txt`, `scene-values.txt`,
`batch-*.txt` (24 exports plus `batch-log.txt`), `tic-line-score-disasm.txt`,
and `tic-line-updater-disasm.txt`.
Cached evidence: Singer's `final-export-0800631c.txt`, `final-export-08006508.txt`,
`final-export-080067d4.txt`, `final-export-0800689c.txt`, `final-export-0800b2f0.txt`,
and `initial-0801*.txt`; main `extracted/gameplay/scenes.json` and
`extracted/text/dialogue.txt`. Everything derived remains under ignored paths.

Once the human supplies active challenge savestates, trace the native initializer
and timer/score writers before poking each candidate. Check Stickie countdown
start, end tick, point increments, record gate versus prize tiers, and the -600
tick adjustment near zero. Check Digdig one failed/successful pair and its fourth
attempt. Check Tic Tack-Q first ball, last ball, a single completed line, and a
perfect card. Preserve the analyst/parent's emulator ownership and active save.
Scratch, Hula/Ham-Jam, and Rubrub need their own active contexts before naming
specific physics fields or completion thresholds. The human has deferred these
contexts while menus/currency work continues.
