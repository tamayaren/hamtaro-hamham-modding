# Loves Rescued and the love meter

USA AH3E, SHA1 `2525cc23524068dfb3a2b4e0ce7b736f95023e82`.
Investigation 2026-10-11. RAM/display meanings are confirmed by pokes;
natural awards, caps and progression gates are likely from code and scripts.

Status has three separate values. **Loves Rescued** counts rescue awards.
**Meter points** control fullness. **Meter level** controls its appearance
and some progression choices. Changing the count alone does not fill the meter.
Different rescues appear to award different amounts of meter points.

| Value | RAM / type | ROM source or writer | Cap / confidence |
|---|---|---|---|
| `gLovesRescued` | `0x0201d0cc`, u16, word 0x000e | Status pointer `0x080d11a9`; increment `0x08034554` | Display confirmed; natural increment likely; no count clamp established |
| `gLoveMeterLevel` | `0x0201d0c8`, u16, word 0x000c | Award write `0x0803474c`; frame reader `0x08033e30` | Appearance confirmed at 0/4; normal range 0..4 likely |
| `gLoveMeterPoints` | `0x0201d0ca`, u16, word 0x000d | Award write `0x08034738`; fill reader `0x0803426c` | Fullness confirmed at 28/56; natural cap 56 likely |
| Award selector | `0x02003a09`, u8, byte 0x0079 | Lookup `0x080344a2`..`0x080344aa`, weights `0x084a7b88` | Positive indexes 1..21 inspected; allowed selector range unproved; likely |
| Award phase | `0x020039f1`, u8, byte 0x0061 | `Event_UpdateRescueAward` `0x08034490` | Native phases 0..10; scripts also handle 11; reused scratch; likely |
| Counter display copy | `0x0201d0f4`, u16, word 0x0022 | Status copy; `Menu_DrawStatusCounter` `0x08033ba4` | Three display digits, not a storage cap; likely |
| Award animation timer | `0x0201d0f8`, u16, word 0x0024 | `0x08034490`; count committed at timer 48 | Animation polls; real time unit untested; likely |

## Display tests

From `inventory-screen.ss0`, a count-only poke to 7 followed by Status
reopening displayed Loves Rescued 7. A width-2 read at instruction
`0x08003a3c` (reported PC `0x08003a40`) loaded it. Words 6/7/8 did not
change this count in earlier candidate tests.

Three further trials reloaded that original-ROM state, removed probes,
wrote level/points, then opened Status:

| Level / points | Observed effect | Rescue count |
|---|---|---|
| 0 / 28 | Approximately half-full meter | Remained 0 |
| 0 / 56 | Full meter with level-0 appearance | Remained 0 |
| 4 / 56 | Full meter with level-4 frame/character appearance | Remained 0 |

Read watches reached `Menu_PositionLoveMeterSprites`, `Menu_DrawLoveMeterFill`
and `Menu_DrawLoveMeterFrame`. The inconsistent 0/56 pair shows that Status
does not recompute level from points. These tests confirm display sources,
not natural rescue awards or the cap.

Local evidence: `extracted/gameplay/loves-rescued-poke7.json`,
`status-parameter-trace.json`, `love-meter-pokes.json` and corresponding PNGs.
The emulator was restored to baseline original-ROM Status afterward.

## Natural awards and ROM modding points

`Event_UpdateRescueAward` (Thumb `0x08034490`) maintains count and meter.
At animation timer 48, phase zero increments word E by one at
`0x08034550`..`0x08034554`, copies it to word 0x0022 and redraws row zero.
No count clamp was found here. A u16 store does not establish an intended
maximum or 65,535 obtainable rescues.

The selector indexes the byte weights at `0x084a7b88`. Positive indexes
1..21 have weights 2/3/4 and sum to 56; index zero is zero. This suggests
a finite set of weighted story awards. It does not prove 21 is the rescue
cap: award identities and repeat guards are incompletely mapped, and no
selector bound check was found in this native.

For normally maintained inputs, an award exceeding 56 is reduced to the
remaining room. **56 instruction immediates at `0x080344b0` and `0x080344b4`**
drive the cap. Phase six commits points at `0x08034738`, compares them with
**`14 * (oldLevel + 1)`** at `0x0803473c`..`0x08034746`, and increments level
at `0x0803474c`. Normal boundaries are 14/28/42/56.

That formula uses shifts/subtraction plus an addition at `0x08034744`;
changing only its immediate would not change the entire 14-step rule.
Weight/cap mods also need graphics and story-gate checks. These sources
are likely modding points, not verified rescue mods.

Award scripts `0x080d160b` and `0x080d175d` repeatedly call the native at
`0x080d1610` / `0x080d1767`. The latter clears animation word 0x0024 and
handles phase 11. Complete animation-state reconstruction is pending.

## Drawing and progression

Status opcode 0x42 at `0x080d11a5` copies one u16 from word E to word
0x0022, selects row zero and calls `Menu_DrawStatusCounter` (`0x08033ba4`).
The next four commands use the same renderer for learned count, seeds,
acorns and rocks. It draws three decimal digits from the copy, rather
than counting story flags.

`Menu_DrawLoveMeterFill` (`0x0803426c`) reads points and calls
`Menu_PositionLoveMeterSprites` (`0x08033f94`). The latter selects level
graphics and uses `110 - 2 * (points & 0x007f)` for sprite Y. Frame renderer
`0x08033e30` also selects five level-specific graphics cases. No separate
percentage scalar was found in these readers.

**`0x08051baa` is an event script, not a Thumb function.** It selects byte
0x0060 results 0..4 using learned flags 0x0099/0x009a/0x0091/0x009b and
word-C comparisons with 1/2/3/4. Those flags are words 0x53/0x54/0x4b/0x55,
not chapter flags. The selector's exact story meaning needs later context.

Rubrub helper script `0x08055186` chooses actions by level:
0..1 -> `0x084b1a01`, 2 -> `0x084b1a45`, 3 -> `0x084b1a89`,
4 -> `0x084b1acd`. Dialogue context supports a polishing-ability connection.
These gates are likely; a universal strength multiplier and complete
rock-polishing calculation have not been established.

Static evidence stays in `extracted/gameplay-love/`: five Ghidra exports,
Thumb disassembly and script/table traces. Computed-switch branches were
checked against ROM jump tables where decompilation missed them.
Natural awards/count maximum and polishing mechanics await the deferred
later-meter/Rubrub states and a state immediately before an award.
