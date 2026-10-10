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
- Story meanings of event flags 0x0010, 0x017d, 0x0190, 0x0191 and of
  `0x08051baa`'s progression result; needs later-game savestates. Flag 0x007e
  belongs to learned word Rubrub (ID 0x38, likely complete word mapping),
  rather than an unnamed chapter flag. The other word flags it tests must
  retain their dictionary meaning. See [gameplay.md](gameplay.md).
- Confirm the guessed speaker/role names and expression meanings in the 136-entry
  [portrait catalogue](portraits.md), especially shared-image palette variants.
  Every standard-bank definition and every reached `0x06` portrait load is mapped;
  Hamtaro's left slot and Bijou's right slot have exact live comparisons and
  imported-edit tests. Boss's specific right routine remains likely. Six definitions
  have no reached root; their existence is static evidence, not runtime reachability.
  Native/computed portrait loads outside this evidence, other window geometry, later
  scenes, and remaining room-head pose/animation commands still need mapping.
- Complete the main-loop interpretation around `0x080001a4`: input call,
  normal updates and RNG call `0x08000250` are mapped, but this does not
  complete every callback/interrupt scheduling detail.
- Resolve remaining computed/unmapped accesses before claiming the entire padding
  universally unused. The startup end-bound and pointer-window audit are recorded
  in [rom_map.md](rom_map.md#free-space-audit-2026-10-10).

## Gameplay follow-up after the 2026-10-10/11 hunt

- Confirm natural gain/spend paths and ROM caps: seeds 999, acorns 50,
  rock records 64. Test boundary quantities, accepted/rejected spending,
  animation target and counter/record coherence. RAM totals are confirmed;
  these gain rules remain likely until pickup/shop states exist.
- Confirm normal word learning maintains bit/order/count together, skips
  duplicates, and performs the ten-word starter award. The displayed count
  and Bestest bit are confirmed separately; full learning and starter paths
  are static. A fresh starter state is needed before an all-words demo.
- Map key-item natural writers and IDs 45..47. Oilcan ID 1 / flag 0x009f
  is confirmed; the 48-slot menu list is a display copy, not stack capacity.
- Explain rock state bits and dedicated gem/accessory totals, if any. Need
  Rubrub/acquisition contexts before assigning durability or polish meanings.
- Confirm natural rescue awards and intended count maximum. Count word E,
  points word D and level word C have separate confirmed display effects.
  Likely award weights 2/3/4, point cap 56 and boundaries 14/28/42/56 await
  a natural award test. Map selector identities/repeat guards and Rubrub's
  four level-selected action scripts. See [love.md](love.md). No chapter/day
  scalar or separate ordinary dash/jump mode was established; don't infer
  one from dialogue words.
- Test Stickie elapsed ticks, score/record/prize boundaries and -600 bonus
  near zero; Digdig fourth attempt/matched pairs; Tic Tack-Q balls, lines,
  actor timers and difficulty. [challenges.md](challenges.md) names candidates
  and ROM sources, all likely until active states exist.
- Map Ham-Jam scores/timing and Scratch/Digdig/Rubrub action constants in
  their active contexts. Generic Entity acceleration is not proof of a
  standalone player jump mechanic.
- Extend save confirmation beyond gameplay blocks 1-3 and the selected
  fields: block-4 record meaning/padding, both banks invalid, signature
  repair, interrupted writes and exact autosave timing. Normal End Game,
  Continue, checksum spans and backup-bank recovery are confirmed. No
  general SRAM decoder/writer helper has been added.
- Check RNG boot seeds, signed edge inputs, weighted return and any
  reseeding at scene/Continue boundaries. Positive modular transitions and
  all-zero absorption are confirmed; idle frames and explicit requests
  share the generator. A fixed Boss script range was verified without
  changing global RNG code.

The human deferred named shop/pickup/challenge/polishing/dance/later-meter
states. Their exact names and required observations are in
[gameplay.md](gameplay.md#deferred-states-and-unresolved-work); do not play
blindly to obtain them or silently promote these candidates to confirmed.
