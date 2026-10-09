# Findings log

Newest first. See the `kb-update` skill for the entry format.

## 2026-10-09 — Complete text glyph table verified (Claude Opus 5.5)

- Ran a labelled probe of every byte `0x01`–`0xdf` in both font banks via the
  Boss/Hamha response pointer (`0x0804ffb6`); all pages displayed and closed.
- Full table with accents, symbols and blank slots in [glyphs.md](glyphs.md);
  `tools/hamtools/glyphs.py` drives the dialogue helper. Confidence: confirmed.
- Correction: `0xd0` is the apostrophe, `0xd1` is `…` (previously misrecorded).

## 2026-10-09 — Boss portraits located; readable dialogue C helper verified (GPT-6.1; Harvey re-engineer)

- Corrected the earlier `0xf4` portrait label: it consumes a scene callback ID.
  The live callback table is `0x03001fb0`; the `0x08` entry at `0x03001fd0`
  was read by `Scene_InvokeCallback` (`0x08001440`, exact load `0x0800144a`).
  That clubhouse callback sets Boss's idle animation `0x08687e17`.
- Boss portrait assets: idle `0x081bfc74` (compressed size `0x222`), alternate
  `0x081bfa60` (`0x213`), both LZ77-expanded size `0x480`. Geometry is likely
  48x48, while palette/layout/animated overlay details remain unmapped.
  Animation command `0xcb`, handler `0x0800d014`, reads the unaligned idle
  asset operand at `0x08687e18`. Both decompressed assets matched the live
  slot-2 buffer `0x0201d2b0` in their respective tests.
- The loader selects `(entityIndex - 10) / 3`, not a remainder. Boss was
  index 16 at entity `0x02022e8c`; the runtime selector was 2. Slot record
  `0x08469f14` contains the confirmed buffer pointer. Other slots and remaining
  record fields are static/likely. See [portraits.md](portraits.md).
- Added disabled `boss-portrait-demo`: a checked four-byte operand redirect
  uses the existing alternate face without importing graphics. The separate
  combined build changed 46 bytes and produced a 161-byte BPS. Fresh boot,
  alternate buffer/display, final wait/close, and repeat conversation passed.
  The initial fast test pressed A before typing finished; the corrected check
  waited for cursor `0x086d0028`, then observed empty root `0x03000610`.
- The response route is Clubhouse -> Boss -> Hamha -> show-text command
  `0x0804ffb4`, slot 0, pointer `0x0804ffb6`. Runtime operand reads identify
  `Event_ShowTextAndWait` (`0x080027a8`), exact read `0x08002876`, caller
  `Event_RunCommands` (`0x08000d74`). Broader branches/choices remain unmapped.
- Harvey implemented the authored-string encoder, generated C integration,
  shared `dialogue.h`, and meaningful parser/build tests in an isolated
  worktree. Integrated the helper and rewrote the sunflower C as a named,
  commented node with normal string literals. Unsupported glyphs fail with
  source positions; original C/raw initializers remain compatible.
- Probed digits `0x02–0x0b` and labelled punctuation `0xca–0xd9`, then expanded
  the helper with the confirmed common glyphs. Digits, commas, apostrophes,
  hyphen/underscore, parentheses, angle signs, slashes, curly double quotes,
  and `!?` now work in readable strings. ASCII double quote and unmapped
  glyphs remain errors; `0xd0` quote style is still unexposed.
  A readable C glyph probe displayed the new mappings, reached its end control,
  and closed normally; the probe sources/output remain local under `build/`.
- All 64 integrated tests passed with real ARM compilation and BPS checks.
  The readable helper produced the same `0x29`-byte stream, 44 changed bytes,
  and 135-byte BPS as the first mod. Fresh helper-built ROM boot, complete
  sentence, close, and repeat were verified. Restored the normal-portrait
  output after the optional demo and removed probes/released buttons.
- Updated README with project progress, addresses, editing/build guidance,
  verification scope, and remaining research. Canonical shared instructions
  distinguish ready text authoring from planned extraction/graphics tools;
  GPT/Claude commit attribution was added in the preceding dialogue commit.
- Evidence stays local in `extracted/dialogue-hunt-20261009/`, `states/`, and
  `screenshots/`. The original ROM SHA1 remains unchanged. Room transitions,
  animation reuse in other scenes, and longer gameplay still need playtesting.

## 2026-10-09 — Dialogue located and sunflower sentence mod verified (Codex; re-scout static scan)
- Verified the original ROM SHA1 before analysis. Used the human's
  `states/dialogue-state.ss0`, copied locally as `dialogue-hunt-base.ss`.
- Boss's response stream starts at `0x0846cc6b`, ends with a wait control at
  `0x0846ccc2`, and is reached by the unaligned pointer operand `0x0804ffb6`.
  A RAM cursor redirect displayed a different passage; no original ROM file edits.
- Text list root `0x03000608`; sentinel `0x03000610`; event-owned state pointer
  `0x030005f0`. In this scene, TextState `0x0202447c`, cursor `0x0202448c`.
  Watchpoint PC `0x08004630` identifies the stream read at `0x0800462c` in
  `Text_Update` (`0x08004548`); glyph cursor store at `0x08004772`.
- Mapped two control dispatch tables and the main cursor/list fields. Lowercase
  uses ASCII values; spaces/capitals/punctuation and controls are custom.
  Full mappings and static candidate-bank limits remain incomplete.
- `patches/sunflower-dialogue` supplies the human's authored sentence in a new
  `0x29`-byte stream at `0x086d0000` and redirects only the four-byte operand.
  Build changed 44 bytes, produced a 135-byte BPS, and verified its round-trip.
  Six pytest tests passed with the installed ARM toolchain.
- Patched title boot, full two-line sentence, normal portrait, final wait/close,
  repeat conversation, local movement, and Ham-Chat menu were tested. The final
  wait reads `0x086d0028`; after A the list root returned to `0x03000610`.
  Room transitions and longer sessions remain for the human.
- Details and confidence limits: [dialogue.md](dialogue.md). Bulk static output,
  runtime traces, screenshots, and savestates stay in gitignored local paths.

## 2026-10-08 — First mod: faster-walk (Claude)
- `patches/faster-walk`: walk 1→2, run 2→3 px/frame via 8 edits to `kPlayerMoveVelocityTable`.
- Verified on the patched ROM against the frame counter in all directions (open floor), and
  collision stops (right wall x 224, bed x 184, top wall y 32, bottom rail y 152) match the
  original ROM exactly; screenshots identical apart from speed. This also confirms the
  table drives player movement (`kPlayerMoveVelocityTable` → confirmed by modification).

## 2026-10-08 — Hamtaro's position, movement code, and walk/run speed table (Claude)
- RAM search (u16 and u32, walk right/down/left/up + idle filters) from savestate
  `walking.ss0` (clubhouse bedroom) → X `0x02022c34`, Y `0x02022c3c`, s32 16.16.
  **Confirmed** by poking: X+40 moved Hamtaro 40 px right; Y+30 moved him down and the
  camera followed. Values persist (not overwritten from a copy).
- Change-watchpoints: position written in `Player_Update` (`0x0800631c`; stores at
  `0x080063c8`/`0x080063d0`) as `pos += vel; vel = 0`. Velocity written by
  `Entity_SetVelocity` (`0x0800af1c`), called from `Player_HandleMovementInput` (`0x08006508`).
- Entities: 0x68-byte array via `gEntityArray` (`0x03002d88`), player slot
  `gPlayerEntityIndex` (`0x03002bfc`) = 10 here; 10 × 0x68 + `0x0202280c` = `0x02022c1c` ✓.
- Speed: `Player_HandleMovementInput` picks `kPlayerMoveVelocityTable[run][dir]`
  (`0x08467af0`): walk 1.0, run (B held) 2.0 px/frame. Measured over 26–28 frames:
  +26 px walking, +52 px running. (A first measurement of "3 px/frame" was an artifact —
  each Python round trip spans ~3 frames; measure against `frame`, not per request.)
- Next: a "faster walking" mod is now an edit of 8 table entries; scaling the walk entries
  needs no code. Check collisions still behave at higher speeds.

## 2026-10-08 — Input RAM masks and repeat layout verified (re-analyst)

- Independently verified USA AH3E ROM with `uv run hamtools rom verify`; SHA1
  `2525cc23524068dfb3a2b4e0ce7b736f95023e82`. The default uv cache was denied by
  the sandbox; setting `UV_CACHE_DIR` to the repo's ignored `.cache/uv` succeeded.
- Confirmed u16 active-high fields: held `0x03000820`, pure newly pressed
  `0x03000822`, press/auto-repeat `0x03000824`, released `0x03000826`, previous
  held `0x03000838`. Timer fields `0x0300082c`, `0x0300082e`, `0x03000830`
  are confirmed from read values, captured timer writes, and observed repeat
  timing. `Input_Update` is at `0x08009614` (Thumb); caller function
  `0x080001a4`, observed LR `0x08000231`. Ghidra reports 128 code bytes excluding
  an internal 16-byte literal pool, so CSV function size is left blank.
- Method: reused the one live emulator, saved its player-name session, reset to
  the title, saved a released baseline, and searched both RAM regions as u16.
  Search: 147456 candidates -> 123889 released zeros -> 2 held-L candidates
  (`0x03000820`, `0x03000838`); both also followed released zero and held R.
  Individual write-watchpoints and change-watchpoints then located and separated
  the transient fields. All reported accesses were width 2, Thumb, normal code.

Representative **write-watchpoint** evidence (each window includes time between
tool requests; counts are captured writes, including writes of unchanged values):

| Variable | Reported PC | Actual Thumb store | LR | Write count | Frame window |
|---|---|---|---|---|---|
| Held `0x03000820` | `0x0800963c` | `0x08009638` | `0x08000231` | 468 | 4675–5142 |
| Pure pressed `0x03000822` | `0x08009634` | `0x08009630` | `0x08000231` | 1905 | 12155–14062 |
| Previous `0x03000838` | `0x08009684` | `0x08009680` | `0x08000231` | 240 | 4903–5142 |
| Press/repeat `0x03000824`, normal assignment | `0x08009636` | `0x08009632` | `0x08000231` | 728 | 26848–27575 |
| Press/repeat `0x03000824`, repeat assignment | `0x08009656` | `0x08009652` | `0x08000231` | 160 | 26851–27573 |
| Released `0x03000826` | `0x0800963a` | `0x08009636` | `0x08000231` | 728 | 26848–27575 |

The parent's decompile/disassembly validates the actual stores: the reported
Thumb PC is four bytes beyond the accessing instruction for these sites.
The KEYINPUT read is `0x08009618`, reported as `0x0800961c`; function entry is
`0x08009614`. Literal references: `0x0800966c` -> KEYINPUT `0x04000130`,
`0x08009670` -> mask `0x03ff`, `0x08009674` -> input base `0x03000820`,
`0x08009678` -> previous storage `0x03000838`.

Observed **change-watchpoint** transitions, independently captured from writes:

- One short L pulse: held/pure pressed `0 -> 0x0200` at 9746, both cleared at
  9747; released `0 -> 0x0200` at 9747, cleared 9748. A separate sustained L
  test pulsed pure pressed at 16674, cleared 16675, then recorded 1133 further
  pure-press writes with zero changes and a stable zero first value. Held and
  previous remained `0x0200`.
- Add R while L stays held: held `0x0200 -> 0x0300` at 21404; pure pressed
  `0 -> 0x0100 -> 0` at 21404/21405, change count 2. Remove R: held back to
  `0x0200` at 22397; zero pure-press changes; released `0 -> 0x0100 -> 0`
  at 22397/22398, change count 2.
- Add Right while L stays held: held `0x0200 -> 0x0210` at 24566; pure pressed
  `0 -> 0x0010 -> 0` at 24566/24567. Remove L: held `0x0010` at 25329;
  zero pure-press changes; released `0 -> 0x0200 -> 0` at 25329/25330.
  Release Right: held zero at 26171; released `0 -> 0x0010 -> 0` at
  26171/26172, with zero pure-press changes.
- Long L: held from 17993 until release at 18094, measured span 101 frames.
  Pure pressed pulsed only at 17993/17994 (change count 2). Press/repeat
  had **3 nonzero repeat change hits** at reported PC `0x08009656`, first
  18082, last 18090, value `0x0200`. This is not the total repeat-site write
  count: its write probe recorded **59 writes** through 18316, including zero
  assignments after release. Release pulsed `0x0200` at 18094/18095 (count 2).
- Short L: 40 sampled held frames, 23187–23226; only the initial +4 pulse at
  23187/23188 (count 2), zero nonzero changes at the repeat assignment.
  Released pulsed `0x0200` at 23227/23228.
- Long R: 110 sampled held frames, 27192–27301. Pure pressed pulsed `0x0100`
  at 27192/27193 (count 2), and never repeated. Press/repeat had **6 nonzero
  repeat change hits**, first 27281, last 27301, value `0x0100`, while the
  write probe recorded 160 total repeat-site writes in its longer window.
  Released pulsed `0x0100` at 27302/27303 (count 2).

Repeat/countdown evidence with title configuration initial=90 and interval=4:

| Countdown event at `0x03000830` | Reported PC | Actual store | Captured evidence |
|---|---|---|---|
| Load initial delay | `0x08009648` | `0x08009644` | One load to 90 at first L frame 17993; another at first R frame 27192 |
| Decrement | `0x0800964e` | `0x0800964a` | 561 change hits in the long-L capture; 728 in long-R; an observed `4 -> 3` decrement in R window |
| Reload interval | `0x0800965a` | `0x08009656` | First L reload `0 -> 4` at 18082, coinciding with first repeat; continued reloads also happen while released |

First repeats were at initial press +89 in both longer tests. L's three
nonzero repeats spanned eight frames and R's six spanned twenty frames, agreeing
with interval 4 and the static same-poll initial decrement. The restored
player-name screen later read initial/interval 16/8; that screen's timing was
not tested. Delays vary with game state.

Confidence limits and tool timing:

- Bridge runs continuously. It groups hits by PC, retaining only the first
  registers/extra and aggregate count/first/last frame until cleared. Intermediate
  repeat timestamps are not individually preserved; the ranges/counts and static
  interval agree. Native watchpoint `newValue` may be signed even for width 2;
  interpret displayed mask/timer values as `value & 0xffff`.
- `emu_press` releases before returning. A one-frame request produced no sampled
  edge, while a two-frame request produced one. Later 40/101/110-frame tests had
  measured spans of 40/101/110; requested duration alone is not a guarantee of
  edge sampling. Ordinary post-press reads do not establish first-frame values.
- A script poke wrote `0x0100` to held RAM while native probes were active.
  Subsequent read/screenshot/hits timed out, so it has no confirming observation.
  The parent identified possible reentrant probe register reads as a tooling
  cause; it is not proof that the variable was wrong. No further pokes were made.
  Recovery checked the exact original-ROM/bridge command line before stopping
  only unresponsive mGBA PID 40536, then used `emu_launch` with the title baseline.
  Confirmed confidence rests on button transitions that distinguish the fields,
  per-candidate writer probes, and validated disassembly, not this poke.
- D-pad packed field `+0x08` and unchanged-mask counter `+0x12` remain likely.
  `+0x0a` is unmapped; allocation size beyond the covered `0x14` bytes is unknown.
  Static `+0x12` resets at `0xffff` via `0x08009666 -> 0x0800967c`, rather than
  saturating; the boundary was not tested. D-pad packing and byte/table meanings
  remain open for future work; table pointers/order are recorded in structs.md.

Local evidence (all gitignored):

- Complete chronological tool results: `extracted/input-hunt-20261008/final-transitions.json`.
  Earlier checkpoints: `discovery.json`, `watchpoints-through-sustained-L.json`,
  `transitions-before-poke-stall.json`, `emulator-transitions.json`,
  `expanded-repeat-traces.json` in the same directory; `progress.md` is the final handoff.
- Parent static corroboration: `extracted/input-ram-hunt/ghidra-input-decompile.txt`,
  `ghidra-input-disasm.txt`, `ghidra-input-function.txt`. This analyst made no Ghidra calls.
- Saved states: `states/input-hunt-title-base.ss` and `states/input-hunt-original-session.ss`.
  Screen captures are under `screenshots/`.
- Final cleanup: all seven probes removed, buttons released, original player-name
  session reloaded and visually checked; status keys all/bridge both zero,
  `emu_hits` empty, held/pressed/repeat/released/previous read zero. No commits,
  ROM edits, or tracked tooling changes by this task.

## 2026-10-08 — Input is polled in two places (Claude, tooling bring-up)
- Read-watchpoint on `REG_KEYINPUT` (0x04000130, 2 bytes) over 30 frames on the title screen:
  - reported pc `0x0800961c` — normal code (Thumb, system mode), once per frame; lr `0x08000231`.
    Later disassembly identified the actual read at `0x08009618`, in `Input_Update`
    starting at `0x08009614`; caller function starts at `0x080001a4`.
  - reported pc `0x080004a8` — IRQ mode (Thumb), once per frame; lr `0x08000493` → part of the interrupt handler.
- Matches the static literal-pool hits from `hamtools rom xrefs 0x04000130`: `0x080004c4` and
  `0x0800966c` (each just after its reading function). Confidence: confirmed (both methods agree).
- Held/pressed RAM mapping was completed in the newer entry above.

## 2026-10-08 — ROM baseline (Claude, setup)
- Verified dump SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`; header checksum valid; save type SRAM (32 KB),
  tag at `0x086CA1E0`.
- Data ends at `0x086CC537`; the rest of the 8 MB is `0xFF` padding — candidate free space.
