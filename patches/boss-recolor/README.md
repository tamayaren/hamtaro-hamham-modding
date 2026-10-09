# Blue Boss dialogue portrait

Changes Boss's dialogue portrait fur and shadow colours to blue. Two authored
palette words are reconstructed against the original palette hash, compressed
into free space, and referenced by checked pointer edits. No game graphics or
original bytes are included in this folder. The mod is disabled by default.

```powershell
$env:UV_CACHE_DIR = '.cache/uv'
uv run hamtools patch build boss-recolor
```

Load `build/hamtaro-mod.gba` in mGBA, or apply `build/hamtaro-mod.bps` to your
own verified USA AH3E ROM with a BPS patcher. This example needs no ARM compiler.
The output filenames are reused by other builds: build this mod again to restore it.

## Playtest

1. Load `states/dialogue-hunt-base.ss`. Press A, then A to choose Hamha.
   The face beside Boss's dialogue should have blue fur. His room sprite
   should retain its normal colours.
2. Read and advance the response, close it, and talk to Boss again. The blue
   portrait should persist without garbled tiles or palette flashes.
3. Open/close menus, leave and re-enter the clubhouse, then talk again. Check
   other characters' portraits and play longer to look for unrelated changes.
4. If a later scene puts Boss's portrait in the other dialogue slot, check it
   there too; that slot's pointer is patched but was not exercised here.

`states/boss-recolor-visible.ss` is a local on-screen state made on this build.
An original `states/boss-portrait.ss` already holds the old palette in RAM;
close the conversation and start another to make the patch load. The original
human state `boss-portrait.ss0` is also retained.

Verified: cold boot, correct live palette and unchanged image bytes, fresh
greeting/response, page advance, closing/repeating dialogue, and continued
room animation for more than a minute. All tests and the agent-profile drift
check pass. Room changes, the other slot and longer sessions remain human checks.

See [the graphics guide](../../kb/graphics.md) and
[the portrait findings](../../kb/portraits.md) for export/import and scope.
