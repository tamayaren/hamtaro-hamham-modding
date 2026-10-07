---
name: ram-hunt
description: Find where the game stores a value in RAM (position, money, item counts, flags, timers) with cheat-search style snapshots and filters, then confirm it by poking and find the code that writes it. Use when the goal is "find the address of X" for anything that changes on screen.
---

# RAM hunt

Like a cheat-search: snapshot all RAM, change something in the game, keep only the
addresses that changed the same way, repeat until a handful remain.

## Procedure

1. **Get to a stable spot.** Load or ask for a savestate. Save your own: `emu_save_state("hunt-base")`.
2. **Pick width.** Positions/counters are usually `u16` (`width=2`); flags/small counts `u8`;
   sub-pixel positions or money can be `u32`. Unsure → start with 2.
3. **Snapshot:** `ram_search_start(width=2)` (~150k candidates).
4. **Change the thing, then filter:**
   - walk right → `ram_search_filter("increased")`; walk left → `"decreased"`
   - do nothing for a while → `"unchanged"` (removes timers/animation noise — do this often)
   - known exact value (e.g. 3 seeds on screen) → `ram_search_filter("eq", 3)`
5. **Repeat** 4 until < ~20 candidates. Alternate opposite changes (right/left, gain/spend)
   so coincidences drop out.
6. **Confirm by poking:** `emu_write(address, value, width)` then `emu_screenshot`. If the
   thing on screen changes (or snaps back immediately — then it is a copy; look for the
   master value), you've found it. Restore with `emu_load_state("hunt-base")`.
7. **Find the writer:** `emu_watch(address, length=width, kind="write")`, do the action,
   `emu_hits()`. That pc is the code that updates it → hand to `ghidra-analyze`.
8. **Record** with `kb-update`: `kb/ram.md` + `kb/symbols.csv` (kind `ram`), confidence
   `confirmed` only after step 6 worked.

## Pitfalls

- Many games keep a value in several places (logic copy, render copy, OAM). The one that
  matters is the one whose write changes the game; others get overwritten each frame.
- Positions are often fixed-point (`x << 8` or `<< 4`): moving 1 pixel changes the value by
  256 or 16. Use `increased`/`decreased`, not exact values.
- Values in a struct: once one field is found, `emu_read` the surrounding 0x40 bytes —
  neighbours are often related (x, y, direction, animation frame).
- Movement input is read every frame; filter on what *changes on screen*, not key state.
