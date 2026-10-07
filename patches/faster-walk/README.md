# faster-walk

Hamtaro walks at **2 px/frame** (was 1) and runs (B held) at **3 px/frame** (was 2).

**How:** edits the non-zero component of each entry in `kPlayerMoveVelocityTable`
(`0x08467af0`, 2 speeds × 4 directions × (vx, vy), s32 16.16). No code changes.

**Verified (2026-10-08)**, clubhouse bedroom savestate, patched vs original ROM:

| | Original | Patched |
|---|---|---|
| Walk Up/Down/Left/Right | 1.00 px/frame | 2.00 px/frame |
| Run (B) Up/Down/Left | 2.00 px/frame | 3.00 px/frame |
| Stops at right wall / bed / top wall / bottom rail | x 224 / x 184 / y 32 / y 152 | identical |

**Playtest:** room exits/doors, talking to NPCs while moving, scenes with moving
platforms or cutscenes that walk Hamtaro automatically (they may use other tables).
