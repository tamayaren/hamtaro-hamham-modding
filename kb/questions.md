# Open questions

- What compiler built the game? (Matters only for a later matching decomp; AlphaDream's
  *Superstar Saga* is a useful comparison.)
- Complete the custom text glyph table and remaining control operands. The observed
  Boss response is an uncompressed one-byte stream; see [dialogue.md](dialogue.md).
- Establish true text-bank boundaries and how event scripts choose other NPC responses.
- Where is the main loop (`swi 0x05` VBlankIntrWait callers)?
- Is `0x086CC538–0x087FFFFF` truly unreferenced free space?
