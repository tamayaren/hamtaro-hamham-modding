# Open Questions & Roadmap (2026-10-09)

Summary of unanswered questions, active investigations, and how the human owner can assist ongoing reverse engineering for *Hamtaro: Ham-Ham Heartbreak*.

---

## 1. What Remains to Be Discovered

### 1.1 Story Meanings of Event Flags
We have verified that specific bits in the progression array (`gEventFlags` at `0x03002170`) change dialogue:
- **Flag 0x0010** (`0x03002172` bit 0): Swaps Boss's default dialogue route for the alternate route, and renders a companion portrait.
- **Flag 0x007e**: Gated in Boss's alternate route.
- **Flag 0x017d**: Set after Boss's first alternate line (`0x08050010`), gating subsequent conversations into the hint loop.
- **Flags 0x0190 & 0x0191**: Gate additional dialogue choices and one-off cutscenes (`0x08050135`).
- **Progression Function `0x08051baa`**: Computes scratch byte variable `0x0060` (values 0–4) from multiple quest flags.

*Question*: What in-game story milestones do these flags actually correspond to? (e.g., meeting Bijou, solving a couple's fight, learning a new word).

### 1.2 Other NPCs & Locations
- Boss's Clubhouse interaction route is mapped, but other NPCs (Bijou, Oxnard, Snoozer, Pashmina, Penelope, etc.) and outside locations (Acorn Heights, Sunflower Park, etc.) branch through room selector dispatch tables (e.g. `0x0804efbf`).
- Mapping these requires savestates in different rooms.

### 1.3 Complete Event Opcode Specification
- We have documented ~30 event opcodes (including branches, jumps, subroutines, menus, random picks, flag setters).
- A fully automated script disassembler/compiler requires knowing the exact operand byte counts for every event opcode in the table (`0x08467434`).

### 1.4 Portrait Graphics & Overlay Composition
- Compressed face tiles (48x48) are located, and BIOS decompression is understood.
- Still unmapped:
  - Where the tile palette is loaded.
  - How animated eye-blinking and mouth-moving overlays are layered onto the static face.
  - How the composite tiles are uploaded from WRAM buffer (`0x0201d2b0`) to VRAM.

### 1.5 Engine Core & Free Space
- Main loop callers (`swi 0x05` VBlankIntrWait).
- Verifying whether `0x086CC538` through `0x087FFFFF` is 100% unreferenced padding across all game states.
- Identifying the exact compiler toolchain used by AlphaDream (important for a future matching decompilation).

---

## 2. How the Human Owner Can Help

Because agents rely on emulator savestates to examine live game states, the human owner can dramatically accelerate reverse engineering:

1. **Provide Savestates Across the Game**:
   - Play to various story beats and save states in `states/` with descriptive names:
     - `states/bijou-park.ss0`
     - `states/oxnard-crying.ss0`
     - `states/spat-encounter.ss0`
     - `states/ham-chat-full-vocabulary.ss0`
   - Having states at different narrative stages makes it easy to compare flags and identify story flags.
2. **Playtest Built Mods**:
   - Boot `build/hamtaro-mod.gba` and check:
     - Does walking at higher speed cause clipping or collision bugs in narrow hallways?
     - Do room transitions or saving/reloading SRAM affect custom dialogue?
3. **Report Visual Bugs**:
   - When text or portraits are swapped, check if text boxes wrap cleanly or if screen transitions glitch.
