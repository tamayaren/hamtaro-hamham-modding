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

See `kb/dialogue.md` for the addresses, encoding, and verification evidence.
