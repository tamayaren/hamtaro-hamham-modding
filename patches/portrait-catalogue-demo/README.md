# Hamtaro and Bijou dialogue portrait import demo

Disabled by default. The changed-only recipes were produced through the PNG
importer: Hamtaro has blue face colours and one changed pixel at image (8,8);
Bijou has green face colours. Original images, palettes and ROM allocations
are reconstructed locally and preserved. This tests tile and palette relocation
on the left and palette relocation on the right.

```powershell
$env:UV_CACHE_DIR = '.cache/uv'
$env:UV_NO_SYNC = '1'
uv run hamtools patch build portrait-catalogue-demo
```

Open `build/hamtaro-mod.gba` in mGBA, or apply `build/hamtaro-mod.bps` to your
own verified USA AH3E ROM with a BPS patcher. Build only this named mod to keep
the test independent of the local faster-walk edit. No ARM compiler is needed.

## Exact playtest checklist

1. Cold boot the built ROM; confirm the title animates normally.
2. Load `states/portrait-catalogue-companion-base.ss0` through mGBA's state-file
   dialog. The `.ss0` copy has identical contents to the bridge's original `.ss`
   file and is visible in the GUI's savestate filter. This is a separate
   Boss-front baseline with known flag 0x0010 temporarily set for the companion
   greeting; the original `dialogue-hunt-base.ss` was preserved.
3. Press A to open Ham-Chat, then A to choose Hamha. During the greeting,
   expect blue Hamtaro on the left and green Bijou on the right. Boss's following
   face and the room sprites should retain their original colours.
4. Advance every response page with A, close the conversation, and repeat it
   three times. Look for missing faces, wrong colours, garbled text or freezes.
5. Open and close the pause/dictionary menu. Walk away and return to Boss;
   repeat Hamha. Response pages, reopening Ham-Chat and the dictionary menu
   were smoke-checked; movement still needs your playtest.
6. Change rooms, talk to another speaker, return, and repeat the greeting.
   Room transitions and a longer play session still need your playtest.
7. Compare with the original ROM using the same companion baseline: the
   normal orange/white faces should return. Start a fresh conversation to load
   graphics from ROM; already-open savestates retain uploaded old graphics.

`states/portrait-catalogue-demo-visible.ss0` is the captured edited greeting.
Evidence under `extracted/gfx/catalogue/` includes exact original/edited
VRAM, palette and shadow comparisons. Neither those outputs nor savestates
belong in the public repository. The temporary progression flag is a test
condition; no story meaning or naturally reached later-game scene is claimed.

For a different portrait, export its name from `hamtools gfx list`, edit its
48 x 48 PNG locally, then import it with `--asset <name> --palette new`.
Check sharing metadata: edits to a shared tile or palette stream affect every
mapped consumer. See [the graphics guide](../../kb/graphics.md).
