# Knowledge base

What we know about the game. Start here before analyzing anything. The format rules are in
the `kb-update` skill (`.agents/skills/kb-update/SKILL.md`).

- [symbols.csv](symbols.csv) — every named address
- [rom_map.md](rom_map.md) — ROM layout
- [ram.md](ram.md) — RAM layout
- [structs.md](structs.md) — data structures
- [dialogue.md](dialogue.md) — dialogue locations, live text state, encoding, and a verified text mod
- [glyphs.md](glyphs.md) — full one-byte text glyph table with per-row confidence
- [text_controls.md](text_controls.md) — text control bytes `0xe0`–`0xff` and prefixes, verified byte lengths, colours
- [text_dump.md](text_dump.md) — `hamtools text dump`: extracting all script text, and the tag notation
- [event_scripts.md](event_scripts.md) — event-script interpreter, all 97 command lengths, and how NPC responses are selected
- [event_natives.csv](event_natives.csv) — operand counts for native functions called by event command 0x1c
- [findings.md](findings.md) — dated log of discoveries
- [questions.md](questions.md) — open questions

This KB holds addresses, names, and descriptions only — never game data itself.
