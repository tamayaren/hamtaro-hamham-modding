---
name: verify-mod
description: Verify a built Hamtaro mod in the emulator — boot the patched ROM, reproduce the scenario from a savestate, compare against the original game, check for crashes, and hand the human a playtest checklist. Use after every patch build and before calling a mod done.
---

# Verifying a mod

1. **Build + tests:** `uv run hamtools patch build <mod>` and `uv run pytest -q`.
2. **Boot the patched ROM:** close any running mGBA, then
   `emu_launch(rom="build/hamtaro-mod.gba")`. Screenshot the title screen — a white/black
   screen or freeze at boot means a broken hook or code placement.
3. **Reproduce the scenario:** load the relevant savestate (`emu_load_state`). Note:
   savestates hold RAM, not ROM, so a state made on the original game works on the patched
   one *if* the patch doesn't change RAM layout.
4. **Show the change:** take screenshots / RAM reads that prove the new behavior, and the
   same steps on the original ROM (`emu_launch()` after closing) for comparison.
5. **Smoke test around it:** a minute of the surrounding gameplay — open the menu, talk to
   someone, change rooms. Watch for freezes and garbled graphics.
6. **Hand off:** tell the human, in plain words:
   - what changed and where to see it,
   - which savestate to load,
   - what to try that you couldn't (long play sessions, specific scenes),
   - how to apply the `.bps` to their own ROM (any BPS patcher, e.g. Floating IPS / Rom Patcher JS).
7. **Record:** `kb/findings.md` entry; mark related symbols `confirmed` if this test proved them.

If anything failed, say so plainly with the evidence (screenshot path, error, what you tried).
