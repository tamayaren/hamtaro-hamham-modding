# Boss text editing example

This disabled-by-default mod replaces the Clubhouse -> Boss -> Hamha response
with three original pages in tag notation. Its 137-byte stream is longer than
the original 88-byte allocation, so the builder places it in free space and
repoints every direct script reference. No compiler is needed for `[[text]]`.

```
uv run hamtools patch build boss-text-edit
```

Build it alone: `sunflower-dialogue` redirects the same pointer and a combined
build correctly rejects the conflict. Outputs are `build/hamtaro-mod.gba` and
`build/hamtaro-mod.bps`; the original ROM is never written.

Load `states/event-sel-boss-base.ss`, press A, then A to choose Hamha. The first
page says **I can read our new text!**, with **new** in red. Advance twice to
see the other pages, then close the dialogue. Check the normal Boss portrait,
line breaks, colour reset, movement, menus, and another conversation. Longer
play sessions and dialogue in other scenes still need human playtesting.

Edit `text` freely, retain the scene callback and final end control, and keep
`expect_sha1` as the hash of the original stream (including its terminator).
`\n` is a newline; `[page]` waits and clears; `[end]` waits and closes.
Window estimates default to this scene's 168 pixels and three visible lines.
Optional `width`, `lines`, `spacing`, and `font` fields adjust those estimates;
they do not change the game's window.

See [the editing guide](../../kb/text_dump.md#editing) for the changed-only
dump helper. Never commit extracted dumps, ROMs, screenshots, or savestates.
The BPS can be applied to your own verified USA ROM with any BPS patcher.
