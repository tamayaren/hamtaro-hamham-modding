# Open questions

- What compiler built the game? (Matters only for a later matching decomp; AlphaDream's
  *Superstar Saga* is a useful comparison.)
- Complete the custom text glyph table and remaining control operands. The observed
  Boss response is an uncompressed one-byte stream; see [dialogue.md](dialogue.md).
- Establish true text-bank boundaries. How event scripts choose NPC responses is now
  mapped for Boss Hamha (flags, hint counter, random choice); see
  [event_scripts.md](event_scripts.md). Other NPCs' routes from dispatch `0x0804efbf`
  are unmapped.
- Meanings of most event commands (all 97 lengths are now known; see
  [event_scripts.md](event_scripts.md#complete-command-length-table)) and the 34 guessed
  native-call operand counts in [event_natives.csv](event_natives.csv).
- Which scripts are reached only from native code or tables (113 show-text-shaped byte
  patterns lie outside the static walk).
- Story meanings of event flags 0x0010, 0x007e, 0x017d, 0x0190, 0x0191 and of
  `0x08051baa`'s progression result; needs later-game savestates.
- Map portrait palettes, tile arrangement, blink/mouth overlays, and graphics upload.
  Boss's compressed portrait assets and their animation operands are located; see
  [portraits.md](portraits.md). Custom image import is not implemented.
- Where is the main loop (`swi 0x05` VBlankIntrWait callers)?
- Is `0x086CC538–0x087FFFFF` truly unreferenced free space?
