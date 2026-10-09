# Open questions

- What compiler built the game? (Matters only for a later matching decomp; AlphaDream's
  *Superstar Saga* is a useful comparison.)
- Map the remaining text control operands (`0xe4`–`0xff` except `0xe6`, `0xf4`) and
  what `0xeb`/`0xee` do. The glyph table is complete; see [glyphs.md](glyphs.md).
- Establish true text-bank boundaries and how event scripts choose other NPC responses.
- Decode the event tree's conditional/choice commands beyond the mapped Boss Hamha node.
- Map portrait palettes, tile arrangement, blink/mouth overlays, and graphics upload.
  Boss's compressed portrait assets and their animation operands are located; see
  [portraits.md](portraits.md). Custom image import is not implemented.
- Where is the main loop (`swi 0x05` VBlankIntrWait callers)?
- Is `0x086CC538–0x087FFFFF` truly unreferenced free space?
