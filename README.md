# Hamtaro: Ham-Ham Heartbreak — Modding

Reverse-engineering notes and modding tools for *Hamtaro: Ham-Ham Heartbreak* (GBA, USA),
built to be driven by coding agents (Claude Code and OpenAI Codex).

**No game data is included.** You need your own legally obtained dump of the USA ROM
(`AH3E`, SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`), placed at
`gba/Hamtaro - Ham-Ham Heartbreak (USA).gba` or pointed to by `$HAMTARO_ROM`.

## Quick start

```
uv sync
uv run hamtools rom verify
uv run hamtools rom info
```

## What's here

- `kb/` — what we know about the game: addresses, names, data formats
- `tools/hamtools/` — command-line tools for ROM analysis (and, later, patching)
- `AGENTS.md`, `.agents/skills/`, `agent-profile/` — the agent setup: instructions, skills,
  and a model-tier roster generated for both Claude Code and Codex

## Status

Phase 1 (tooling) done: emulator bridge + MCP server, headless Ghidra, mod build pipeline.
Next: first real mods (text, palettes, gameplay values).
