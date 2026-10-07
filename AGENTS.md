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
tools/hamtools/            Python CLI that all skills call (`uv run hamtools ...`)
tools/sync_agent_profile.py  regenerates .claude/skills, .claude/agents, .codex/agents
kb/                        knowledge base: symbols, RAM map, structs, ROM map, findings log
patches/                   mod sources (asm/C) — Phase 1+
mcp/mgba-bridge/           Windows-native emulator MCP server — Phase 1
ghidra/scripts/            headless Ghidra scripts — Phase 1
gba/  states/  build/  extracted/   local only, gitignored
```

## Tool status

| Tool | Status | Notes |
|---|---|---|
| `hamtools rom verify / info` | ready | checksum + header |
| mGBA emulator bridge (MCP) | planned (Phase 1) | persistent session, input, memory, savestates |
| Ghidra headless + scripts | planned (Phase 1) | needs Ghidra install |
| ARM toolchain / armips | planned (Phase 1) | for building patches |
| text / gfx tools | planned (Phase 2) | |

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
keep it sorted by address).

## Skills

| Skill | When |
|---|---|
| `gba-primer` | Any time you need GBA hardware facts: memory map, ARM/Thumb, BIOS calls, compression |
| `rom-recon` | Exploring the ROM statically: header, free space, pointer tables, compressed data |
| `kb-update` | Recording any finding — naming rules, file formats, confidence |

More skills land with their tools (emulator, Ghidra, text, graphics, patch build, verify).

## Commands

```
uv run hamtools rom verify           # check the ROM is the expected dump
uv run hamtools rom info             # header, save type, used/free space
uv run python tools/sync_agent_profile.py          # after editing skills or agents
uv run python tools/sync_agent_profile.py --check  # CI-style drift check
```

## Style

- Python 3.11, standard library first; add dependencies via `uv add`.
- Addresses always as full 32-bit hex: `0x08012345` (ROM), `0x02001234` (EWRAM),
  `0x03001234` (IWRAM). ROM file offset = address − `0x08000000`.
- Thumb function pointers have bit 0 set; record functions by their even address and note
  the mode.
