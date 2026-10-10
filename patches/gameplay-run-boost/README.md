# Running speed demonstration

Hold B while walking to run at 3 pixels per frame instead of 2. Ordinary
walking remains 1 pixel per frame. This edits the running half of the
movement table at `0x08467af0`; no code hook or saved-data change is needed.

Build this demonstration by name so other enabled patches are excluded:

```powershell
$env:UV_CACHE_DIR = '.cache/uv'
$env:UV_NO_SYNC = '1'
uv run hamtools patch build gameplay-run-boost
```

The builder checks all four original signed 16.16 velocity values and writes
`build/hamtaro-mod.gba` plus `build/hamtaro-mod.bps`. Do not combine it with
`faster-walk`: both recipes edit the running entries.

Verified against the original ROM on 2026-10-11: walk remained 1 pixel/frame;
B-run measured 3 in all four directions, versus the original 2. Four controlled
collision endpoints matched the original. Cold boot, supplied Items/dictionary
screens, Boss interaction menu and 3,600 frames across the supplied room/menu
states showed no observed freeze or graphics corruption. Natural room transitions
and longer sessions remain human playtests.

This hunt's separate outputs are `build/gameplay-run-boost/hamtaro-mod.gba`
and `build/gameplay-run-boost/hamtaro-mod.bps`. Applying that BPS to the verified
original reproduced the built ROM exactly. The CLI command above writes the
default `build/` filenames; the recipe remains disabled for unnamed builds.

Playtest: apply the BPS to a copy of the verified USA ROM, or open the built
ROM with a test save copy. Load `walking.ss0`; walk without B, then run with B
Right/Left/Up/Down, release direction, and push against edges and the bed.
Repeat in `sunny_peaks.ss0`, change rooms naturally, open Items/dictionary and
return to walking. Report clipping, sticking, crashes or menu corruption.
See [gameplay.md](../../kb/gameplay.md) for the complete checklist and limitations.
