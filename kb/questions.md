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
- Can any of the 113 likely script fragments outside the static walk execute? The
  Step 4 xref/native audit found no evidenced new runtime root; 101 source streams
  are now preserved in a separate local inventory. See [text_coverage.md](text_coverage.md).
- Enumerate remaining native-rendered menu/item/word text from evidenced ROM tables or
  embedded records. Five variant families and four fixed native tables are exported; RAM-generated inserts
  and the runtime dialogue pointer arrays remain contextual. See [text_tables.md](text_tables.md).
- Story meanings of event flags 0x0010, 0x007e, 0x017d, 0x0190, 0x0191 and of
  `0x08051baa`'s progression result; needs later-game savestates.
- Confirm the guessed speaker/role names and expression meanings in the 136-entry
  [portrait catalogue](portraits.md), especially shared-image palette variants.
  Every standard-bank definition and every reached `0x06` portrait load is mapped;
  Hamtaro's left slot and Bijou's right slot now have exact live comparisons and
  imported-edit tests. Boss's specific right routine remains likely. Six definitions
  have no reached root; their existence is static evidence, not runtime reachability.
  Native/computed portrait loads outside this evidence, other window geometry, later
  scenes, and remaining room-head pose/animation commands still need mapping.
- Where is the main loop (`swi 0x05` VBlankIntrWait callers)?
- Resolve remaining computed/unmapped accesses before claiming the entire padding
  universally unused. The startup end-bound and pointer-window audit are recorded
  in [rom_map.md](rom_map.md#free-space-audit-2026-10-10).
