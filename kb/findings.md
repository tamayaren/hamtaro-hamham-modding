# Findings log

Newest first. See the `kb-update` skill for the entry format.

## 2026-10-11 — Integrate completed branches into main (Codex)

- Fast-forwarded main to gameplay-values and merged text-edit-helper plus
  dialogue-portrait-catalogue. The helper implementation/tests were already
  present; its merge retains the newer dump description and records ancestry.
- Kept both research logs, the updated portrait questions, the gameplay flag
  meanings and main-loop observations. Reconciled symbols by address against
  their common base: 814 unique, sorted entries; no competing address meanings.
- Validation: all 431 tests passed; the agent profile check and staged diff
  check passed. The 455 flag mappings and both gameplay BPS round trips remain
  valid. No extracted game data was added. Original ROM/save hashes and the
  human's unstaged faster-walk source hash remained unchanged.

## 2026-10-11 — Gameplay values, save recovery and two verified demos (Codex; Heisenberg re-analyst; Singer, Wegener, Mencius re-engineer)

- Verified original AH3E SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`.
  `codex/gfx-portraits` was already included in main; work began on
  `codex/gameplay-values` from main. The human's uncommitted faster-walk
  recipe was preserved and excluded from the standalone demo builds.
- Heisenberg's supplied-menu hunts confirmed u16 seeds `0x0201d0c2`,
  acorns `0x0201d0c4`, displayed rocks `0x0201d0c6`, u8 learned count
  `0x03003db0`, Bestest learned flag 0x008a (`0x03002181`, mask 0x04),
  and sort flag 0x00f8. Distinct values above 255 verified the resource widths.
  The parent additionally poked `0x0201d0cc` to 7 and observed Loves Rescued 7.
  Word-counter reads are instruction `0x08003a3c`, reported PC +4.
- Wegener traced native word learning, the ten-word starter branch,
  acquisition order at `0x030037c0`, 86 dictionary IDs and their text/rank
  tables. Bit-only and count-only pokes can disagree, so an all-words change
  must maintain flags/order/count together. Complete mapping and natural
  learning remain likely. Several earlier unnamed story flags are words;
  0x007e is Rubrub ID 0x38 (likely). See [items_words.md](items_words.md).
- Slot-only Oilcan injection into `0x030038d0` disappears on reopen.
  A flag-only poke at `0x03002183`, mask 0x80 (flag 0x009f), instead caused
  `Menu_BuildOwnedItemList` `0x08034c78` to rebuild ID 1 and show its icon
  and description. This confirms ownership versus display-copy behavior.
  The full 48-entry ownership table and 45 description spans remain likely.
- Seed gain cap 999 (u32 literal `0x0804ae10`), acorn cap 50 (instruction
  immediates `0x0804b3c4` / `0x0804b3cc`), and 64 rock records at
  `0x0201bf90` are strong static findings. Spending rejects overlarge
  requests by accepting zero. Gain/spend caps and rock type/state meanings
  need the deferred acquisition/shop/polishing states; display pokes are
  not proof of real record grants.
- Singer mapped two 16 KiB SRAM banks, ordinary headers, selected RAM
  packers/unpackers and the folded complemented word-sum checksum. On a
  disposable original-ROM/save copy, End Game -> Yep saved edited resources,
  Bestest's bit and count; Continue restored them. Actual gameplay blocks
  1-3 in both banks matched predicted lengths/checksums and zero padding.
  Corrupting only primary block-1 checksum byte `0x0e0000f4` caused
  bank-wide backup recovery: statuses 1-3 at `0x03002158` became 2.
  Normal save/Continue called `0x0800108c` / `0x08001320` from handlers
  `0x08003b08` / `0x08003b24`. Special block-4 records remain untested.
  See [save.md](save.md); no general save helper was added.
- Confirmed RNG state words `0x03000000` / `0x03000004` / `0x03000008`:
  captured positive transitions matched multipliers 171/172/176 and moduli
  30269/30307/30323. After probe removal, an all-zero poke stayed zero for
  30 idle frames. Seed literals, signed edge cases and complete weighted
  draw arithmetic remain static. Idle updates and explicit requests share
  this generator; Boss's byte result is scratch reused by other systems.
- `gameplay-run-boost` changes four checked running components from 2 to
  3 pixels/frame. Live rates confirmed all directions; walking stayed 1.
  Four controlled collision endpoints matched the original. `gameplay-boss-hint`
  changes one checked range operand to [2,3): helper bounds 2/3 produced
  byte result 2 at `0x08003df4` and selected `0x08050104`; original zero RNG
  selected result 0's `0x080500c0`. Both conversations closed normally.
  Both mods cold-booted and ran 3,600 frames across four supplied states
  with no observed freeze or garbled graphics. Natural room transitions,
  other gates and longer sessions are explicit human playtests.
- Both standalone ROMs/BPS patches were built under `build/<demo>/`;
  BPS application to the original exactly reproduced each built ROM.
  Only disabled expect-checked sources/READMEs are tracked. A local controlled
  Boss state is `states/gameplay-boss-random-ready.ss0`; it sets repeat gates
  and zero RNG and should be used with a test save copy.
- Mencius mapped static Stickie elapsed/score/record, Digdig board/attempts,
  and Tic Tack-Q balls/line recount/actor timers. Tick rate, scores and
  completion behavior remain likely until active states exist. Ordinary
  movement assigns complete velocities, with no accumulated acceleration
  ramp in that path; generic acceleration does not establish a player jump.
  The Stickie end literal stores 3599 shifted left 16, matching the shifted
  timer comparison. See [challenges.md](challenges.md).
- Mencius separated rescue count word E from meter points D and level C,
  and traced award native `0x08034490`. Parent pokes of level/points 0/28,
  0/56 and 4/56 confirmed independent fullness/appearance while Loves Rescued
  stayed zero. Read watches reached meter frame/fill/sprite natives.
  Natural weights `0x084a7b88`, point cap 56 and 14-point level boundaries
  remain likely. Rubrub's four action tiers depend on level; its complete
  polishing calculation and intended rescue maximum remain open.
  `0x08051baa` is a word/level event script, not a Thumb function.
  See [love.md](love.md); static evidence is in `extracted/gameplay-love/`.
- Added [gameplay.md](gameplay.md), detailed menu/challenge/love/save documentation,
  and an address-only inventory of 455 reached-script flag IDs. Renamed
  `gRuntimeDialogueChoice` to `gEventScratchResult` at `0x020039f0`, because
  menu/page counts, random hints and challenge results reuse byte 0x0060.
  Corrected earlier flag-store instruction attribution: `0x08003be8` is the
  store; `0x08003bec` was the native watchpoint's pipelined PC.
- Evidence is local under `extracted/gameplay/`, `gameplay-ram-hunts/`,
  `gameplay-items-20261010/`, `gameplay-actions/`, and `gameplay-save-rng/`.
  Ghidra access and emulator ownership were serialized; temporary Ghidra
  reconstructions were rolled back after export. Shop/challenge/dance/polishing
  and later-meter states were deferred by the human; no blind navigation occurred.
- Validation: **350 tests passed**; `tools/sync_agent_profile.py --check`
  passed; 347 symbols are sorted with unique addresses and valid confidence/mode
  fields, and were synced into the local Ghidra project. Original ROM and human save SHA1s were unchanged; faster-walk source
  SHA256 remained `F867C26103077F0003036508867B09C96D4EF65E6220A05B70084F040045F443`.
  The emulator was restored to the baseline Status screen on the disposable
  original-ROM copy, with zero bridge-held keys and no probes. No game data is tracked.

## 2026-10-10 — C linking after portrait symbol catalogue growth (Codex)

- The full suite during the savestate filename fix exposed three C-link failures:
  Windows `CreateProcess` reported error 206 (filename/extension too long).
  Passing all 656 KB symbols as separate `--defsym` flags needed 33,004
  characters before other arguments, exceeding Windows' command-line limit
  after the portrait catalogue expanded `symbols.csv`.
- Moved the same absolute symbol assignments into the generated `mod.ld` file.
  This keeps the linker invocation short and preserves the existing Thumb
  function pointer adjustment. No game symbol addresses were changed.
- Added an ARM-toolchain test with 1,503 synthetic symbols and paths containing
  spaces. It checks the linked bytes retain the exact odd Thumb function pointer,
  ROM data pointer and RAM data pointer; no game data is involved.

## 2026-10-10 — Savestate filenames for mGBA's GUI (Codex)

- The human reported that mGBA's savestate file picker accepts `.ss0`, `.ss1`,
  etc., but hides our bridge-generated `.ss` files. The bridge uses
  `emu:saveStateFile` / `emu:loadStateFile`; our MCP filename helper supplied
  `.ss` and also incorrectly appended `.ss` to explicit native slot filenames.
- Created local `.ss0` copies of `portrait-catalogue-companion-base` and
  `portrait-catalogue-demo-visible`; SHA256 comparisons verified identical
  contents, preserving the original captures. Updated the playtest checklist.
  The GUI filter observation comes from the human; this change does not claim
  a new GUI-load or portrait confirmation.
- Bare MCP saves now use `.ss0`. Explicit legacy `.ss` and native `.ss0` through
  `.ss9` names are retained. Bare loads prefer `.ss0` and fall back to `.ss`;
  listings include full filenames rather than duplicate stems. Synthetic tests
  cover save/load/launch routing, legacy fallback and distinct explicit slots.
- Added the established `UV_NO_SYNC=1` workaround to the demo build instructions
  so uv does not try to replace the running Windows MCP executable.
- Validation after both tooling fixes: `uv run pytest -q` passed all 431 tests;
  `uv run python tools/sync_agent_profile.py --check` reported the profile in sync.

## 2026-10-10 — Complete standard dialogue portrait catalogue (Codex; Fermat re-scout; Socrates re-engineer)

- Verified USA ROM SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82` before
  address analysis. Fast-forwarded local `main` to the completed Boss graphics
  commit, then created `codex/dialogue-portrait-catalogue`. The human's
  `patches/faster-walk/mod.toml` edit remains untouched and uncommitted.
- Ghidra decompiled `0x08001658`, dispatcher `0x08000d74`, fetcher `0x08001530`,
  scene updater `0x08000984` and indirect `bx r1` thunk `0x080e57f0`.
  Event `0x06` takes inline little-endian source/destination u32s at +1/+5,
  assembled bytewise: **pointers, not table IDs**. Handler table slot
  `0x0846744c` holds Thumb pointer `0x08001659`; dispatch/frame interpretation
  is likely, with live LR `0x08000d91` corroboration. Bytewise operands are
  confirmed by Boss and Bijou source-read probes.
- Audited all **2,711 reached `0x06` commands** across 148 roots / 98,214
  commands, with no walker problems or unknown natives. **336 loads** form
  **168 distinct reached (tiles, palette, slot) sets**: 123 left and 45 right.
  Every portrait tile/palette source LZ77-decodes to `0x480` / `0x20` bytes.
  Five other graphics loads reuse portrait palette destinations and are
  explicitly excluded; every other graphics stream was decoded at its own size.
- Audited the whole standard loader bank `0x084b1c65`..`0x084b3095` exclusive:
  **136 definitions / 135 distinct pairs**, **57 tile images / 130 palettes**,
  two 19-byte slot routines each. 130 definitions are reached: 85 left-only,
  seven right-only, 38 both; six definitions and many opposite-slot partners
  are static-only. No invented roots or runtime claim for those definitions.
  Every rooted portrait load is covered. See [portraits.md](portraits.md).
- Added address-only `kb/portrait_catalogue.csv`, with names, both slot loaders,
  per-slot/all scene roots, context text addresses and name confidence. Names
  are **guess** except live Hamtaro, Bijou and Boss. Most later NPCs reuse
  images with different palettes; two monkey definitions alias one pair.
  Palette variants are not asserted to be facial expressions. The event walker
  now records flow edges and propagates all possible roots through shared
  routines, instead of recording only the first visitor.
- **Confirmed non-Boss left face:** Hamtaro `0x080e9e38` / `0x080f4224`
  matched complete live VRAM/palette bytes in the supplied Sunny Peaks scene.
  **Confirmed right face:** Bijou `0x080ea110` / `0x080f4244` matched complete
  tiles/palette and shadows at `0x02007290` / `0x0201bbd0`, uploaded to
  `0x06003700` / `0x05000040`. Tested from a separate restored Boss baseline
  with the already-mapped companion flag 0x0010 temporarily set; this is a
  controlled test, not a naturally reached story-state claim.
- Bijou right operands `0x084b1c9f` / `0x084b1ca8` recorded four byte reads
  each at reported PCs `0x08001666/68/6e/74`, instructions `0x08001662/64/6a/70`.
  DMA3 at instruction `0x08009928` (reported `0x0800992c`) recorded source/
  destination/count: `0x02007290` / `0x06003700` / `0x480`, and `0x0201bbd0` /
  `0x05000040` / `0x20`. BG3 screen-block-23 rows 21..26, columns 23..28 select
  right tiles `0x1b8..0x1db`, bank 2; first word `0x0600bd6e`.
  Boss's specific right loader `0x084b1dce` remains **likely**, not promoted.
- Generalized `gfx list/export/import` to every catalogue name while retaining
  Boss compatibility, changed-only pixel/colour recipes and original compressed
  hashes. Sharing metadata shows affected definitions. Changed sources repoint
  every mapped use across entries/both slots; unknown unaligned base/mirror
  pointer occurrences and competing replacements are refused clearly. Per-speaker
  splitting and computed/native-only consumers remain outside this evidence.
- Added disabled `portrait-catalogue-demo`, authored through PNG import: one
  Hamtaro pixel and two colours, two Bijou colours. Relocated tiles at
  `0x086d0000`, palettes at `0x086d02dc` / `0x086d02fc`; six operands checked.
  **Confirmed** title boot, visible blue left Hamtaro / green right Bijou,
  complete expected raw tiles/palettes and both shadows per slot. Response pages,
  reopened Ham-Chat and dictionary open/close worked; more than 3,600 frames
  (one minute) elapsed across the two smoke observations. Room changes and long
  sessions are explicit human checklist items. Original ROM remains unchanged.
- Generalized Boss-specific left RAM/graphics symbols to shared slot names;
  added right-slot symbols, all source streams and slot definitions. All rows
  are sorted by address. Untested formats/definitions remain **likely** and
  editorial names remain **guess** as appropriate.
- Validation: **401 tests passed**, including synthetic inline/truncated operands,
  shared/cyclic root flow, static partners, cross-asset tile/palette sharing,
  hashes, stale/omitted/mirror pointers, conflicts and original-ROM protection.
  ROM-gated tests audit every load/definition, export/import all 136 entries
  unchanged in both palette modes, and check changed-reference completeness for
  all 187 unique source streams. `tools/sync_agent_profile.py --check` passed.
  Default sandbox temp permissions caused fixture setup errors; rerunning with
  normal Windows temp/compiler access passed. No extracted data is committed.
- Evidence: `extracted/gfx/catalogue/` holds catalogue audit, context inspection,
  contact sheet, original/edited PNGs, full Ghidra outputs, source/upload traces,
  byte comparison and smoke JSON. Separate local states include
  `portrait-catalogue-companion-base.ss`, `portrait-catalogue-two-slot-visible.ss`
  and `portrait-catalogue-demo-visible.ss`. These are all gitignored.

## 2026-10-10 — Boss dialogue graphics tooling and blue portrait (Codex; Popper re-scout; Mill re-engineer)

- Corrected the earlier visual identification: `0x081bfc74` / `0x081bfa60`
  are room-head OBJ frames, not the dialogue BG face. Renamed the affected
  RAM/ROM/function symbols; earlier decompression and pointer-swap evidence
  remains valid. See [portraits.md](portraits.md).
- Confirmed the actual face at `0x080eb9bc` (`0x33a` LZ77 bytes -> `0x480`
  bytes, 48 x 48, row-major 4bpp) and palette at `0x080f437c` (`0x26` LZ77
  bytes -> sixteen BGR555 colours). Decoded data exactly matched live tiles
  and palette; a relocated edited palette visibly changed the face.
- Watched bytewise source operands at `0x084b1dbc` / `0x084b1dc5` in event
  `0x06`, `0x08001658`. BIOS `swi 0x11` decodes to shadows `0x0201bbf0`
  and `0x02007710`; DMA3 uploads to `0x05000060` / `0x06003b80`, reported
  PC `0x0800992c`, instruction `0x08009928`. BG3 map rows 21..26 and
  columns 1..6 select tiles `0x1dc..0x1ff`, palette 3. Other-slot source
  operands `0x084b1dcf` / `0x084b1dd8` remain likely; that slot was not shown.
- Room-head rows upload at `0x06010e20` with source stride `0xc0` and OBJ
  VRAM stride `0x400`. Slot record `+0x04/+0x118/+0x119` supplies destination,
  width and height. The first pose `0x086538d4` matches a 64 x 64 4bpp OBJ
  using palette 4; its full pose table remains unmapped. A unique decoded
  room-head palette at `0x081b9f74` matches live bank 4 (likely source).
- Popper audited every four-byte ROM window and mirrors. `0x086cc538` is
  referenced as the exclusive startup-copy bound, so the whole tail cannot
  be called literally unreferenced. No additional evidenced data reference
  was established. The documented audit retains unresolved raw/computed
  cases; conservative allocations continue at `0x086d0000`. See
  [rom_map.md](rom_map.md#free-space-audit-2026-10-10).
- Added `hamtools gfx list/export/import`, Pillow PNG support, BIOS LZ77
  compression, and 4bpp layout conversion. Imports store changed-only authored
  pixel/colour recipes plus original hashes. Derived streams stay under
  `extracted/gfx/`. Graphics share the builder's code/text collision map;
  hash, original-pointer, free-space and original-ROM protections are checked.
  Both original/new palette modes preserve an unchanged Boss export byte-for-byte.
- `boss-recolor` changes palette entries 4 and 5 only. Its 38-byte palette at
  `0x086d0000` is reached through two checked repoints. Verified cold boot,
  blue left portrait, exact edited palette and unchanged tiles in RAM/VRAM,
  greeting, response pages, close/repeat, and continued surrounding animation
  for more than a minute. Original ROM SHA1 remained unchanged. Other slot,
  room changes and longer sessions remain human playtests.
- Validation: **350 tests passed**, including 137 synthetic codec cases and
  ROM-gated PNG roundtrip; `tools/sync_agent_profile.py --check` passed.
  A Windows sandbox temp failure was resolved by running tests with the normal
  temp/tool paths. The running MCP executable prevented project reinstall;
  Pillow was installed separately after `uv add pillow`, then `UV_NO_SYNC=1`
  was used for this session. No game data is committed. The human's faster-walk
  edit was left untouched.
- Local evidence: `extracted/gfx/`, including the address-only free-space
  audit, PNGs, upload traces and verification JSON; patched state
  `states/boss-recolor-visible.ss`. The supplied `boss-portrait.ss0` was
  retained and copied to `.ss` for MCP naming.

## 2026-10-09 — Dialogue coverage and variant inventories (Codex; Ohm re-analyst; Claude research)

- Corrected the scene-pointer array to 11 slots at `0x08466944` through
  `0x08466970` exclusive. The twelfth word was a descriptor entry. The reached
  walk remains 148 unique roots, 98,214 commands, 4,144 direct text sites, and
  3,599 streams. See [text_coverage.md](text_coverage.md).
- Audited the 113 missed text candidates using command boundaries, unaligned
  pointer searches, and native cursor/callback paths. Their 101 streams (83 new
  targets) are likely script fragments; no additional runtime-reached root is
  claimed. Exported separately as `unreferenced.txt` / `unreferenced.json`.
- `events.walk` supports explicit/additional source-labelled roots for future
  evidenced entries and records command sizes. Truncated variable headers report
  problems rather than raising indexing errors.
- Ohm mapped five variant families: 15 logical rows, 14 physical rows, 651
  logical entries, 569 physical slots, 556 distinct stored streams. Fixed bounds,
  final empty slots, and shared rows are retained in `variants.txt` / `variants.json`.
  All new table interpretation remains likely. See [text_tables.md](text_tables.md).
- Added `native.txt` / `native.json`: four evidenced native tables preserve 518
  slots (73 nulls) and 441 unique streams; seven fixed sources/10 literal references
  bring the inventory to 448. Bounds and source relationships remain likely;
  runtime-generated text and unmapped UI tables are explicitly excluded.
- Traced indirect show sites `0x080d9762` / `0x080d9772` to native
  `0x0803b2d0`: pointer slots 0/1 select RAM arrays at `0x02001ab4` and
  `0x02001c6c`, with generated text at `0x03003ad0`. Contextual content is not
  misrepresented as static ROM dialogue.
- Validation: **101 tests passed**, agent profile in sync, symbol rows sorted,
  and original ROM SHA1 unchanged. Exact re-encoding of rooted, candidate,
  variant, and native streams;
  synthetic operand-coincidence, explicit-root, truncation, table-boundary, and
  shared-row checks. No emulator state or original ROM was changed. Earlier
  unfinished Claude coverage research was read and preserved in its own worktree.

## 2026-10-09 — Dialogue editing and ROM re-insertion (Codex; Herschel, re-engineer)

- `[[text]]` entries now build authored tag notation with an original-stream SHA1,
  safe in-place placement, or free-space relocation with all walked direct
  `0x1a`/`0x1b` references redirected. Shared tails, duplicate targets, overlapping
  writes, incomplete walks, invalid streams, and exhausted/nonpadding space are
  rejected or safely relocated. Synthetic tests cover these cases; no original
  dialogue or extracted data is stored in patch sources.
- **Confirmed in mGBA:** from `states/event-sel-boss-base.ss`, the Boss/Hamha
  stream at `0x0846cc6b` (88 bytes) was replaced by 137 authored bytes at
  `0x086d0000`; operand `0x0804ffb6` followed the new address. All three pages,
  red/normal colour tags, portrait, page clearing, and final close worked.
  Title boot, dictionary, movement, and repeat interaction also worked.
- **Confirmed in mGBA:** a separate 19-byte replacement stayed at `0x0846cc6b`;
  its operand remained unchanged and the cursor reached `0x0846cc7d`. Both
  variants closed to TextState-list sentinel `0x03000610`; relocated text also
  cleared event text pointer `0x030005f0` to zero. The original ROM hash is intact.
- `kTextGlyphWidths` `0x08653040`: normal-bank advance plus spacing **confirmed**
  by a predicted/measured 147-pixel cursor. The Boss window measured 168px and
  three lines. Alternate-bank indexing remains **likely** from the existing
  reader export. Advisory layout checks read widths from the ROM; inserts and
  other scene settings still need playtesting. See [glyphs.md](glyphs.md).
- `hamtools text edits` exports only changed whole streams and original hashes;
  partial dumps require `--partial`, existing output requires `--force`. See
  [text_dump.md](text_dump.md#editing). The disabled `boss-text-edit` example
  must be built separately from `sunflower-dialogue` (same pointer claim).
- Local evidence: `screenshots/text-edit-{relocated,inplace}-*.png` in the
  `text-edit` worktree; original comparison under the main repo's screenshots.
  Native-only/runtime text and unseen references remain coverage limits. Human
  playtesting still needs room changes, longer sessions, and other window layouts.

## 2026-10-09 — `hamtools text dump`: readable extraction of all script text (Claude Opus 5.5)

- New modules `tools/hamtools/events.py` (static script walker, command lengths, natives
  from [event_natives.csv](event_natives.csv)) and `tools/hamtools/text.py` (lossless
  codec with tags, dump/parse). See [text_dump.md](text_dump.md).
- The walker reproduces the prototype exactly: 148 entries, 98,214 commands, 3,599 text
  streams, 0 problems. Every stream decodes and re-encodes to its exact bytes; no stream
  needs a raw `{xx}` byte.
- Insert table `0x084aa740` has 248 entries (likely; bounded by the first non-pointer).
- Run-time text: show-text at `0x080d9762`/`0x080d9772` uses a pointer register; switch
  `0x080be96d` has an entry below 0x10.
- Next: coverage sweep for text outside the walk; then an edit/re-insert workflow.

## 2026-10-09 — Text control lengths verified (Codex glyph-controls analyst; Claude Opus 5.5)

- Codex statically mapped all 32 text controls plus prefixes `0x5e`/`0xff`
  ([text_controls.md](text_controls.md)); imported from its uncommitted worktree.
- Static check: all 3,599 script-referenced streams decode and terminate with those
  lengths, with no overruns; length sensitivity pins down the common controls.
- Emulator: redirected the live dialogue cursor onto real occurrences of each rarer
  control with read watchpoints on the following bytes. Lengths of every control used
  in script text are confirmed (only unused `f7`/`fe` and context-bound `ef`/`f5`
  remain likely). `ea` red, `e9` blue, `e8` normal colour seen on screen.
- Found a developer font-test stream among script-referenced text.
- Next: build the text decoder and the event walker as `hamtools` commands.

## 2026-10-09 — All event command lengths; whole-ROM script walk (Claude Opus 5.5)

- Handler table `0x08467434` has 97 entries (0x00–0x60); `0x084675b8` onward is a
  separate sound-function table used by command 0x0a.
- Read every handler's operand-advance constant from Ghidra decompiles. Ghidra had
  decoded part of handler 0x28 (`0x080030b0`–`0x080030e7`) as ARM, which gave garbage;
  re-disassembled as Thumb, 0x28 is 5 bytes.
- 0x1c native calls return their extra operand count (or −4 after jumping). Resolved
  602 native functions; recorded in [event_natives.csv](event_natives.csv).
- 0x00 is a one-byte no-op; switch 0x1d is unbounded (two scripts have hidden fourth
  targets).
- Validation: a recursive walk from 148 scene entry scripts decodes 98,214 commands
  with zero invalid opcodes and reaches 3,599 show-text targets (97% of show-text-shaped
  byte patterns). In mGBA, 28 sampled executing command addresses all matched the walk.
  Confidence likely (small live sample).
- Next: build the event decoder/walker plus the text decoder as `hamtools` commands.

## 2026-10-09 — Event scripts: how Boss's Hamha response is chosen (GPT-6-astra re-lead; Claude Opus 5.5)

- Codex (re-lead) mapped statically the scene descriptor -> room event -> interaction
  record -> selector dispatch -> Ham-Chat menu -> flag branches -> show-text chain,
  interpreter state, call/return convention, and ~30 opcode formats.
  See [event_scripts.md](event_scripts.md).
- Claude confirmed it in mGBA from `states/dialogue-state.ss0`: scene 1/subscene 1,
  idle cursor `0x0804ef8f`; the reply cursor is opcode address + 1 (`0x0804ffb5`).
  Flag 0x0010 (byte `0x03002172` bit 0) clear -> `0x0804ffb4`; set with 0x007e ->
  first-time line `0x08050010`, which sets flag 0x017d (store `0x08003bec`).
- Found the repeat route `0x08050079`: byte var 0x003b (`0x020039cb`) is a hint
  counter stepping lines `0x080500c0` -> `0x080500e6` -> `0x08050104`, then opcode
  0x50 (`0x08003db0`, random in range) picks one. Preset counter 2 -> third hint,
  confirmed. Added opcodes 0x10, 0x11, 0x50.
- Method: per-frame cursor/opcode tracing over flag/variable pokes, plus static decode.
- Next: flag story meanings and other NPCs need later-game savestates.

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
