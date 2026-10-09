# Hamtaro: Ham-Ham Heartbreak — Modding & Reverse Engineering

Shared instructions for **every** coding agent in this repo (OpenAI Codex reads this file
directly; Claude Code reads it through `CLAUDE.md`). Keep it the single source of truth.

## Goal

Reverse-engineer *Hamtaro: Ham-Ham Heartbreak* (GBA, USA, `AH3E`) well enough to mod it:
text, graphics, gameplay values, and code. **Modding first**; a matching decompilation is a
possible later phase, not the current goal. The human owner is new to decompilation —
explain findings in plain language and keep them in the loop on anything they must do
(playing to a spot in the game, making savestates, playtesting).

## Hard rules

1. **This repo is public. Never commit copyrighted data.** No ROM, saves, savestates,
   screenshots of the game, extracted text dumps, graphics, or raw byte blobs from the ROM.
   Commit only: our tools, our docs/knowledge base (addresses, names, formats, *descriptions*),
   and patch *sources*. Short byte signatures (≤ 16 bytes) to identify code are fine.
   Anything extracted goes under `extracted/` (gitignored).
2. **Never modify the original ROM.** It lives at `gba/Hamtaro - Ham-Ham Heartbreak (USA).gba`
   (or `$HAMTARO_ROM`). All output goes to `build/`.
3. **Verify the ROM before trusting any address**: `uv run hamtools rom verify`.
   Expected SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`.
4. **Every confirmed finding goes into `kb/`** (see `kb-update` skill) in the same change that
   used it. Knowledge that lives only in a chat transcript is lost.
5. Mark confidence honestly: `confirmed` (tested in emulator), `likely` (strong static
   evidence), `guess`. Never promote a guess without testing it.

## Layout

```
AGENTS.md / CLAUDE.md      agent instructions (CLAUDE.md just imports this file)
.agents/skills/<name>/     shared skills (canonical; Codex reads here)
.claude/skills/            generated copy for Claude Code — do not edit, run the sync script
agent-profile/agents/      model-tier agent roster (canonical) → .claude/agents, .codex/agents
.mcp.json, .codex/config.toml  MCP server registration (Claude / Codex)
tools/hamtools/            Python package: CLI (`uv run hamtools ...`) + MCP server
  rom.py emu.py ghidra.py patch.py bps.py dialogue.py mcp_emu.py events.py text.py
tools/mgba/bridge.lua      Lua script loaded into mGBA; serves the emulator on 127.0.0.1:61337
tools/sync_agent_profile.py  regenerates .claude/skills, .claude/agents, .codex/agents
kb/                        knowledge base: symbols, RAM map, structs, ROM map, findings log
patches/<mod>/mod.toml     mod sources; patches/include/gba.h and dialogue.h shared headers
tests/                     pytest (`uv run pytest -q`)
gba/ states/ build/ extracted/ screenshots/ ghidra/projects/ .cache/   local only, gitignored
```

## Tool status

| Tool | Status | Notes |
|---|---|---|
| `hamtools rom ...` | ready | verify, info, peek, find, xrefs |
| emulator: `hamtaro-emu` MCP + `hamtools emu ...` | ready | mGBA 0.11 dev build + `tools/mgba/bridge.lua`; input, screenshots, memory, savestates, watchpoints, RAM search |
| `hamtools ghidra ...` | ready | PyGhidra + Ghidra 12.1.4; decompile, disasm, func, xrefs, make-func, sync |
| `hamtools patch ...` | ready | edits/hooks/pointers/text + C in free space → `build/*.gba` + `.bps` |
| authored dialogue C helper | ready | `patches/include/dialogue.h`; literal `DIALOGUE_TEXT(...)` encoding during `hamtools patch build`; see `patches/sunflower-dialogue/` |
| `hamtools text ...` | ready | dump, show, edits: rooted dialogue + separate candidate/variant/native inventories; lossless tags and changed-only mod export; dumps → `extracted/text/` (never commit); see `kb/text_dump.md` |
| text re-insertion | ready | `[[text]]` replacements checked by original-stream SHA1; safe in-place edits or automatic free-space relocation and direct-reference repointing |
| graphics editing tools | planned (Phase 2) | Known portrait pointers can be redirected with checked byte edits; general graphics editing is not implemented |

In the Codex sandbox the default uv cache may be denied; set `UV_CACHE_DIR=.cache/uv`
(gitignored) before `uv run`.

External tools are found automatically; override with `HAMTARO_MGBA` (mGBA.exe 0.11+),
`GHIDRA_INSTALL_DIR`, `ARM_TOOLCHAIN_BIN`, `HAMTARO_ROM`.

If a skill refers to a tool marked *planned*, stop and say so — don't improvise a substitute
that writes into the repo.

## The core loop

1. **Goal** in plain words ("make Hamtaro walk faster").
2. **Locate** — find the RAM value (emulator search) or ROM data/code (static analysis).
3. **Understand** — find the code that reads/writes it; decompile; name things.
4. **Record** — `kb/` entries with confidence.
5. **Change** — patch source under `patches/`, built into `build/`.
6. **Verify** — boot the patched ROM, compare against the original, check nothing else broke.
7. **Hand off** — tell the human exactly what to playtest.

If you need the game in a specific state (a menu, a scene, a character on screen), ask the
human for a savestate in `states/` with a descriptive name rather than trying to play there.

## Agent roster (model tiers)

Defined once in `agent-profile/agents/` (those files are authoritative for model and effort;
keep this table in sync), generated for both harnesses. Delegate down the
tiers: use the cheapest tier that can do the job reliably, escalate on failure.

| Tier | Agent | Codex model (effort) | Claude model (effort) | Use for |
|---|---|---|---|---|
| 1 | `re-lead` | gpt-6-astra (xhigh) | Opus 5.5 (xhigh) | planning, hard RE puzzles, reviewing findings before they're `confirmed`, architecture |
| 2 | `re-engineer` | gpt-6.1-sol (xhigh) | Opus 5.5 (high) | decompiling/understanding functions, writing patches and tooling |
| 3 | `re-analyst` | gpt-6.1-sol (max) | Sonnet 5.5 (high) | routine mapping: RAM hunts, data extraction, KB updates, mod verification |
| 4 | `re-scout` | gpt-6-luna (max) | Haiku 5.5 (high) | read-only lookups: search code/KB, scan ROM, describe screenshots |

Parallel work: give each agent a disjoint area (e.g. text vs graphics) and its own git
worktree; merge KB changes carefully (`kb/symbols.csv` is the usual conflict point —
keep it sorted by address). Shared resources: there is **one emulator** (one bridge port
per mGBA instance) and the Ghidra project is **locked by one process at a time** — point
worktrees at the main project with `HAMTARO_GHIDRA_PROJECT=<main repo>/ghidra/projects`
and expect to take turns, or let one agent own the emulator and others do static work.

## Skills

| Skill | When |
|---|---|
| `gba-primer` | Any time you need GBA hardware facts: memory map, ARM/Thumb, BIOS calls, compression |
| `rom-recon` | Exploring the ROM statically: header, free space, byte/pointer searches |
| `emu-probe` | Seeing/driving the live game; "what code touches this address?" |
| `ram-hunt` | Finding where a value lives in RAM |
| `ghidra-analyze` | Understanding code: decompile, callers/callees, naming |
| `patch-build` | Writing and building a mod |
| `verify-mod` | Testing a built mod before calling it done |
| `kb-update` | Recording any finding — naming rules, file formats, confidence |

## Commands

```
uv run hamtools rom verify                         # check the ROM is the expected dump
uv run hamtools ghidra init                        # one-time: build the Ghidra project (minutes)
uv run hamtools ghidra decompile 0x0800961c        # understand a function
uv run hamtools emu launch                         # start mGBA with the bridge
uv run hamtools text dump                          # readable dialogue → extracted/text/
uv run hamtools patch build                        # build enabled mods
uv run pytest -q                                   # tests
uv run python tools/sync_agent_profile.py          # after editing skills or agents
uv run python tools/sync_agent_profile.py --check  # drift check
```

## Style

- Python 3.11, standard library first; add dependencies via `uv add`.
- Addresses always as full 32-bit hex: `0x08012345` (ROM), `0x02001234` (EWRAM),
  `0x03001234` (IWRAM). ROM file offset = address − `0x08000000`.
- Thumb function pointers have bit 0 set; record functions by their even address and note
  the mode.

## Commit attribution (all agents, including Claude)

Every commit prepared by an AI agent must credit the main agent and every subagent whose
work contributed to that commit, using standard `Co-authored-by: Name <email>` trailers.
Preserve the human's configured Git author/committer identity; do not change Git identity
settings to impersonate the agent.

- Main-agent credit: include the provider/model's readable name, exact model identifier,
  and reasoning effort when the runtime reports it. Use the actual running model, not a
  guessed default. For example, a GPT-6.1 Codex run can identify `gpt-6.1-sol` and `max`.
- Subagent credit: include its worker nickname, role, actual model, and reasoning effort
  (for example, `Erdos (re-scout; gpt-6-luna; max)`). Credit only agents that contributed.
- Apply the same rule to Claude Code and Claude workers: identify the actual Claude model
  and effort when available. If a detail is unavailable, say `unknown` rather than invent it.
- Use a supplied attribution email when available. Otherwise use stable attribution labels
  `codex@users.noreply.github.com`, `claude@users.noreply.github.com`, or
  `<worker-role>@users.noreply.github.com`; these are labels, not claims of verified accounts.
- Put each credit on its own trailer line after a blank line at the end of the commit
  message. Check the completed message before committing. Preserve these trailers when
  amending, cherry-picking, or preparing a squash message, and when pushing those commits.

`AGENTS.md` is the canonical shared instruction file. `CLAUDE.md` imports it; the singular
`AGENT.md` is only a pointer to this file so the instructions stay in one place.
