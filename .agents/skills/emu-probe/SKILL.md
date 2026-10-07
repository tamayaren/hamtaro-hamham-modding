---
name: emu-probe
description: Drive the live mGBA emulator running Hamtaro — launch, screenshots, button presses, savestates, reading/writing memory, and watchpoints/breakpoints that record which code touches an address. Use whenever you need to see or test the running game, or to answer "what code reads/writes this address?".
---

# Emulator probing

The emulator is a normal mGBA window (0.11 dev build) with `tools/mgba/bridge.lua` loaded.
The game runs in real time and the human can see it. Two ways in:

- **MCP tools** (`hamtaro-emu` server): `emu_*` and `ram_search_*` — preferred.
- **CLI** (same bridge): `uv run hamtools emu launch|status|shot|press|wait|read|regs|watch`.

## Starting

`emu_launch` (reuses a running emulator). For a patched ROM: `emu_launch(rom="build/hamtaro-mod.gba")`.
To start at a known spot: `emu_launch(savestate="<name>")` or `emu_load_state("<name>")`.
`emu_list_states` shows what the human has saved in `states/`.

**Don't play blind to reach a scene.** Navigating menus with `emu_press` is fine; anything
longer, ask the human for a savestate with a descriptive name (e.g. `clubhouse-first-visit`).
Save your own states with `emu_save_state` before experiments so you can rewind.

## Seeing

- `emu_screenshot` → image (240×160). `emu_press(..., screenshot=True)` returns one after the press.
- 60 frames = 1 second. Menus often need `wait_after` ≥ 20 frames to settle.

## Memory

- `emu_read(address, length, fmt)` — any bus address. `fmt` u8/u16/u32/s8/s16/s32/hex.
- `emu_write(address, value, width)` — test a theory: poke a value, screenshot, see if the
  game reacts as predicted. That is how a finding becomes `confirmed`.
- `REG_KEYINPUT` (0x04000130) is synthesized by the bridge from the current key state
  (reading it directly from a script hangs mGBA).

## Who touches this address? (watchpoints / breakpoints)

```
emu_watch(address="0x0200xxxx", length=2, kind="write")   # write | read | rw | change
emu_hits(run_frames=60)                                    # distinct pc sites + counts + regs
emu_unwatch()
```

- `pc` is the instruction mGBA reports; `cpsr` bit 5 (`0x20`) set = Thumb. Mode bits
  `0x12` = IRQ handler, `0x1f` = normal code.
- `lr` is the caller's return address (Thumb → odd) — a quick way to find the caller.
- `extra` has the access details (`address`, `width`, `oldValue`, `accessType`).
- Confirm the exact instruction in Ghidra (`ghidra-analyze` skill) before naming things.
- `emu_break(address)` records executions of one instruction (with registers) without pausing.

Probes cost speed; remove them when done (`emu_unwatch()`).

## Known reference points

- Input is polled from `0x0800961c` (main code, Thumb) and `0x080004a8` (IRQ handler).
  Useful to sanity-check that watchpoints work.

## Troubleshooting

- "emulator not running": `emu_launch`.
- Timeouts: the game may be paused in the mGBA window (Emulation menu), or a menu is open.
- Bridge log: `.cache/mgba-bridge.log`. Editing `bridge.lua` requires relaunching mGBA.
