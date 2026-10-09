# Sunflower dialogue

Replaces Boss's response to Hamha in the supplied clubhouse scene with:

> There is a new sunflower by the water.

The sentence appears on two lines. The mod places our text in ROM free space and
redirects one event-script pointer; the original dialogue remains in the source ROM.
It does not create a sunflower or change the quest.

Build this mod on its own from the repository root:

```powershell
$env:UV_CACHE_DIR = '.cache/uv'
uv run hamtools patch build sunflower-dialogue
```

Outputs: `build/hamtaro-mod.gba` and `build/hamtaro-mod.bps`.
The build checks the original ROM SHA1 and the four original pointer bytes.
Use any BPS patcher to apply the patch to your own verified USA AH3E ROM.

Playtest: open the built ROM, load `states/dialogue-state.ss0` (or the local
`dialogue-hunt-base.ss` copy), press A to open Ham-Chat, then A to choose Hamha.
After the greeting, Boss should say the new sentence with a normal portrait.
Press A to close the dialogue; repeat the conversation and check movement and menus.

## Editing the dialogue in C

Edit `dialogue.c`. Its named node is `Mod_BossSunflowerDialogue`, reached through
**Clubhouse -> Boss -> Hamha -> response**. The event command is at `0x0804ffb4`;
`mod.toml` redirects its text operand at `0x0804ffb6` from `0x0846cc6b` to our node.
The trigger and the rest of the event script are still handled by the game.

```c
const u8 Mod_BossSunflowerDialogue[] = {
    DIALOGUE_CALL(Boss_IdleCallback),
    DIALOGUE_TEXT("There is a new sunflower\n"
                  "by the water."),
    DIALOGUE_END(),
};
```

The shared helper is `patches/include/dialogue.h`. The patch builder translates
literal `DIALOGUE_TEXT(...)` calls into the game's bytes in a generated C copy
under `build/obj/generated/`; your editable source stays readable. Adjacent C
string literals work. Use `hamtools patch build` to compile these files.

| Helper | Effect |
|---|---|
| `DIALOGUE_TEXT("...")` | Encode supported letters, digits, punctuation, and `\n`; no implicit end |
| `\n` inside text | Start another line; choose breaks to fit the box |
| `DIALOGUE_WAIT_LINE()` | Wait for input, then advance or scroll one line |
| `DIALOGUE_END()` | Wait for input, then finish the message |
| `DIALOGUE_CALL(id)` | Invoke a callback installed by the current scene |

For more text after an input wait, put `DIALOGUE_WAIT_LINE()` between two text
calls. It advances one line rather than clearing an entire page. End the node
with `DIALOGUE_END()`. The original conversation already exercises the same
wait/scroll control, but every new layout needs a visual playtest.

Supported glyphs are space, A-Z, a-z, 0-9, newline, `.`, `!`, `?`, `-`, `_`,
comma, apostrophe, parentheses, angle signs, slashes, curly double quotes,
and closing single quote. Use curly quotes for quoted speech; ASCII double
quote, colon, semicolon, and other unmapped glyphs give a file/line/column
error. A displayed backslash needs C's `\\` escape. This helper runs before
the C preprocessor: supply ordinary literal
strings, not variables or macro names. Raw byte initializers remain supported.
Controls belong outside text strings; a C numeric escape represents a character,
not a raw game control byte. The full glyph table is still being mapped.

Each additional `const u8` array can name another text node. A checked
`[[pointer]]` entry must bind that node to a **located event operand**. Array
order does not create a branch. Choices, conditions, quest flags, and routes
between nodes belong to the event scripts and are not yet fully decoded.

Callback `0x08` is Boss's idle animation in this clubhouse scene. It is not a
global portrait number; callbacks can also change a character's room animation
or event timing. Keep this callback when editing this response.

## Optional room-head frame demonstration

`patches/boss-portrait-demo/mod.toml` redirects the idle animation's room-head
operand to another existing Boss frame. The dialogue face is separate.
It is disabled by default. Build both
examples explicitly to try it:

```powershell
uv run hamtools patch build sunflower-dialogue boss-portrait-demo
```

The room-head operand is at `0x08687e18`; the normal compressed asset starts at
`0x081bfc74`, and the alternative starts at `0x081bfa60`. This affects uses of
that animation, so it is broader than replacing this one message. Rebuild with
only `sunflower-dialogue` to restore the normal room head in the output.

See [dialogue findings](../../kb/dialogue.md) and
[portrait findings](../../kb/portraits.md) for the addresses, confidence, and
verification evidence. [The graphics guide](../../kb/graphics.md) now supports
Boss dialogue PNG/palette editing; arbitrary dialogue branching remains separate work.
