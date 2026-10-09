# Project Progress Overview (2026-10-09)

*Hamtaro: Ham-Ham Heartbreak* (GBA, USA, `AH3E`) reverse engineering and modding project.

This digest provides a concise, high-level summary of everything discovered, confirmed, and built as of October 9, 2026.

---

## 1. Executive Summary

In just two days of collaborative reverse engineering, the project has transitioned from a fresh ROM verification to full decompilation analysis, live emulator tracing, and working gameplay and dialogue mods:

- **Verified Baseline**: Clean USA ROM identified (SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`), built on AlphaDream's engine with ~1.2 MB of clean candidate free space at the end of the cartridge (`0x086CC538`–`0x087FFFFF`).
- **Complete Tooling Suite (`hamtools`)**: Custom CLI and MCP integration supporting ROM hashing, memory searches, live mGBA automation, watchpoints, headless Ghidra decompilation, and automated ARM C patch compilation with BPS generation.
- **Player Movement & Physics**: Located Hamtaro's live position in memory, mapped the entity array structure, and confirmed the velocity table driving movement.
- **Input Subsystem**: Fully mapped active-high button masks (held, newly pressed, released, and repeat pulses) and auto-repeat timing registers.
- **Dialogue & Text Engine**: Located Boss's clubhouse Hamha conversation, mapped the custom one-byte character set (100% verified across both font banks), decoded control codes, and mapped the live text heap list.
- **Event Script Interpreter**: Reverse-engineered the room event interpreter, showing how scene descriptors, NPC interaction records, Ham-Chat menus, progression flags, hint counters, and random selections choose NPC dialogue lines.
- **Portraits & Animations**: Located compressed LZ77 portrait graphics for Boss (normal and alternate), identified the slot-indexing math, and verified asset swapping.
- **Authored C Mods**: Built and verified real mods producing clean BPS patches without modifying original ROM bytes.

---

## 2. Status of Active Mods

| Mod | Type | Status | What it does |
|---|---|---|---|
| `faster-walk` | Byte edit | Verified in mGBA | Doubles Hamtaro's walking speed (1 &rarr; 2 px/frame) and running speed (2 &rarr; 3 px/frame) by editing `kPlayerMoveVelocityTable`. Wall collisions remain accurate. |
| `sunflower-dialogue` | C code + Pointer redirect | Verified in mGBA | Replaces Boss's clubhouse Hamha response with a custom two-line authored sentence using readable C string literals compiled into free space. |
| `boss-portrait-demo` | Pointer redirect | Verified in mGBA | Redirects Boss's idle animation asset operand to load his alternate face graphic from ROM using native LZ77 decompression. |

All mods build through `uv run hamtools patch build`, perform strict SHA1 and original-byte checks, and generate shareable `.bps` patches.

---

## 3. High-Level System Architecture

The game's runtime architecture is driven by three cooperating interpreters:

```
+-------------------------------------------------------------+
|                     1. Event Interpreter                    |
|  - Room event scripts (scene entry, entity placement)       |
|  - Proximity trigger circles & interaction records          |
|  - Ham-Chat 4-word menu dispatch                            |
|  - Story flags & hint counters (decides WHICH line to play) |
+-------------------------------------------------------------+
                               |
                               | Show-Text Command (0x1a)
                               v
+-------------------------------------------------------------+
|                 2. Dialogue & Glyph Engine                  |
|  - Reads custom 1-byte encoded text streams from ROM        |
|  - Formats text into TextState windows & handles scrolling  |
|  - Dispatches controls (line break, wait for A, callbacks)  |
+-------------------------------------------------------------+
                               |
                               | Scene Callback (0xf4)
                               v
+-------------------------------------------------------------+
|                 3. Animation & Portrait Engine              |
|  - Controls character animation scripts                     |
|  - Opcode 0xcb triggers BIOS LZ77 portrait decompression    |
|  - Loads 48x48 character face into RAM portrait buffer      |
+-------------------------------------------------------------+
```

---

## 4. Confidence Levels at a Glance

In accordance with our strict verification rules, all claims are tagged with their evidence level:

- **Confirmed (Tested in mGBA)**:
  - Movement velocity table (`0x08467af0`) and entity position coordinates.
  - Controller input masks (`0x03000820`–`0x03000838`) and repeat counters.
  - Boss Hamha response pointer (`0x0804ffb6`) and text stream (`0x0846cc6b`).
  - Native glyph set from `0x01` through `0xdf` (all letters, accents, numbers, punctuation, and symbols).
  - Boss portrait compressed assets (`0x081bfc74`, `0x081bfa60`) and destination buffer (`0x0201d2b0`).
  - Flag 0x0010, flag 0x017d (first-time flag), and byte var 0x003b (repeat hint counter).
- **Likely (Strong static Ghidra / disassembly evidence)**:
  - Broader event script opcode catalog (~30 opcodes identified).
  - General interaction record layouts and collision tile attribute parsing.
  - Portrait slot calculation formula `(entityIndex - 10) / 3`.
  - ROM text bank candidate regions (`0x0846a160`–`0x084a60cf`).
- **Open Questions / Needs Player Assistance**:
  - Narrative meanings of numbered progression flags (requires later-game savestates).
  - Portrait palette indexing and dynamic mouth/eye overlay blinking.
  - Interaction script routes for other Ham-Hams across different areas.

---

## 5. Navigation & Further Reading

For detailed deep-dives, see the companion digest documents in this directory:

- [Dialogue & Event System](dialogue-system-2026-10-09.md) &mdash; Detailed breakdown of dialogue text, font encoding, script branching, and portraits.
- [Gameplay & RAM Internals](gameplay-internals-2026-10-09.md) &mdash; Memory maps, entity structs, player physics, and controller input handling.
- [Modding & Authoring Guide](modding-guide-2026-10-09.md) &mdash; Step-by-step instructions on writing dialogue, modifying speeds, and building patches.
- [Open Questions & Roadmap](open-questions-2026-10-09.md) &mdash; What remains to be decoded and how human playtesting can unlock the next milestones.
