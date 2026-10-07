# Findings log

Newest first. See the `kb-update` skill for the entry format.

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
