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
- `tools/hamtools/` — ROM analysis, emulator control, Ghidra analysis, and checked patch builds
- `patches/` — mod sources, including a readable dialogue C example and shared helpers
- `AGENTS.md`, `.agents/skills/`, `agent-profile/` — the agent setup: instructions, skills,
  and a model-tier roster generated for both Claude Code and Codex

## Progress so far — 2026-10-10

Phase 1 tooling is working, and the first gameplay and dialogue mods have been
tested in mGBA. Phase 2 now exports/imports Boss's dialogue portrait as PNG and
builds a verified blue-palette mod. Other graphics still need mapping.

| Area | Progress | Details |
|---|---|---|
| ROM baseline | Verified USA AH3E dump, header, save type, and candidate free space | [ROM map](kb/rom_map.md) |
| Tools | ROM searches, live emulator bridge/MCP, watchpoints, headless Ghidra, C/asm patch builds, BPS output | `uv run hamtools --help` |
| Movement | Entity positions and walk/run speed table located; faster-walk mod verified earlier | [RAM map](kb/ram.md), [faster-walk](patches/faster-walk/mod.toml) |
| Input | Held, pressed, released, repeat masks, and repeat timers mapped and tested | [InputState](kb/structs.md#inputstate-minimum-covered-size-0x14) |
| Dialogue | Boss's clubhouse Hamha response, unaligned script pointer, live cursor, text reader, and several controls located | [Dialogue findings](kb/dialogue.md) |
| Editable dialogue | Plain C string literals compile to the game's encoding; named nodes, newlines, input waits, end controls, and scene callbacks | [Editable example](patches/sunflower-dialogue/dialogue.c), [guide](patches/sunflower-dialogue/README.md) |
| Portraits | Actual Boss dialogue BG image, palette and upload mapped; PNG roundtrip and blue recolour verified; separate room-head OBJ assets identified | [Graphics guide](kb/graphics.md), [portrait findings](kb/portraits.md), [boss-recolor](patches/boss-recolor/README.md) |

The sunflower mod makes Boss say our authored sentence:

> There is a new sunflower by the water.

The sentence appears on two lines. It changes dialogue text; it does not add a
sunflower or alter a quest. The mapped dialogue route is
**Clubhouse -> Boss -> Hamha -> response**.

Useful addresses for this scene:

| Address | Meaning |
|---|---|
| `0x0804ffb6` | Unaligned event operand pointing to Boss's response |
| `0x0846cc6b` | Original encoded response stream |
| `0x03000608` | Generic text-state list head; follow each state's `+0x10` cursor |
| `0x080eb9bc` | Boss dialogue-window portrait, LZ77-compressed |
| `0x080f437c` | Its compressed sixteen-colour palette |
| `0x084b1dbc` | Checked left-slot palette operand |
| `0x081bfc74` | Separate Boss room-head frame; idle operand `0x08687e18` |

All addresses apply to the verified dump above. Scene-specific heap addresses,
callback IDs, and entity indices need confirmation in other scenes.

## Build and edit the dialogue example

Install the ARM `arm-none-eabi` toolchain for C/asm patches. Tools are detected
automatically; `ARM_TOOLCHAIN_BIN` can override its bin directory.

```powershell
$env:UV_CACHE_DIR = '.cache/uv'
uv run hamtools patch build sunflower-dialogue
```

This creates `build/hamtaro-mod.gba` and `build/hamtaro-mod.bps`. Builds verify
the source ROM hash, check original bytes at every edit, and validate the BPS
round-trip. The original ROM file is never edited. Apply the BPS to your own
verified ROM with a BPS patcher, or load the built ROM locally in mGBA.

Edit [dialogue.c](patches/sunflower-dialogue/dialogue.c), then rebuild:

```c
const u8 Mod_BossSunflowerDialogue[] = {
    DIALOGUE_CALL(Boss_IdleCallback),
    DIALOGUE_TEXT("There is a new sunflower\n"
                  "by the water."),
    DIALOGUE_END(),
};
```

[dialogue.h](patches/include/dialogue.h) supplies the controls. The builder
generates encoded C under `build/`; your source stays editable. Supported text
includes letters, 0-9, spaces/newlines, `.`, `!`, `?`, `-`, `_`, comma,
apostrophe, parentheses, angle signs, slashes, and curly quotes. The
[editing guide](patches/sunflower-dialogue/README.md) lists the supported forms.
Unmapped glyphs report the file, line, and column. Use `DIALOGUE_WAIT_LINE()`
between text calls for an input wait followed by line advance/scroll. Check
line lengths in the game.

Each named C array is a text node, and a checked TOML pointer binds it to a
located event operand. The complete tree's choices, conditions, and quest flags
are not yet decoded. Callback IDs are scene-specific: `0x08` sets Boss's idle
animation here, which also loads his room-head frame. The dialogue face has a
separate event graphics path.

To try the optional existing-face swap, build both mods explicitly:

```powershell
uv run hamtools patch build sunflower-dialogue boss-portrait-demo
```

The old portrait demo is disabled by default and affects that idle room-head
animation. Rebuild only `sunflower-dialogue` to restore it. For the actual
dialogue face, export/edit/import with `hamtools gfx`, or build the palette-only
example with `uv run hamtools patch build boss-recolor`.

## Verification and remaining work

Current automated suite: **350 tests passed**, including graphics roundtrips, literal encoding,
diagnostics, generated-source handling, real ARM compilation, checked edits,
linked text/control bytes, and BPS round-trips.

Emulator checks covered fresh title boot, the complete sunflower sentence,
normal/alternate portrait buffers, final input wait and close, repeated
conversation, local movement, and Ham-Chat. To reproduce the dialogue test,
make a savestate in front of Boss in the clubhouse, open Ham-Chat with A, and
choose Hamha with A. Wait for the greeting and response, then press A to close
and repeat. Room transitions and longer play sessions still need playtesting.

Next research: complete the glyph/control table; map more NPC entry operands
and event branches/choices; map other NPC graphics and later-scene expressions.
Boss's dialogue image, palette and tilemap are now editable. [Open questions](kb/questions.md)
and [the findings log](kb/findings.md) track confidence and evidence.

ROMs, saves, screenshots, graphics, and extracted text stay in gitignored local
directories. The public repository contains tools, knowledge, and patch sources.
Shared [agent instructions](AGENTS.md) also require commit credits for the
actual GPT/Claude models and contributing workers, including reasoning effort.
