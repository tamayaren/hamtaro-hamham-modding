# Open questions

- What compiler built the game? (Matters only for a later matching decomp; AlphaDream's
  *Superstar Saga* is a useful comparison.)
- Text encoding: custom character table? Compressed?
- Where is the main loop (`swi 0x05` VBlankIntrWait callers)?
- Is `0x086CC538–0x087FFFFF` truly unreferenced free space?
