# Supplemental text tables (Step 4)

2026-10-09, re-analyst. All address/layout findings here are **likely**: strong
static evidence, with no emulator testing in this task. The original USA AH3E
ROM was verified using `hamtools rom verify`; SHA1
`2525cc23524068dfb3a2b4e0ce7b736f95023e82`, size `0x800000`.
The original ROM was read only. No live Ghidra or emulator was used.

The implementation in `tools/hamtools/text_tables.py` exports the five variant
families and four bounded native tables plus fixed native literal references.
Ohm mapped the variant families; the parent reviewed and integrated the native
sources. All exports remain separate from rooted event dialogue and Step 5 editing.

## Evidence

Paths in this list refer to the main checkout's existing, gitignored exports.
No decompiled code or extracted strings are reproduced here.

- `extracted/glyph-hunt-20261009/decompile-controls.txt`: handlers at
  `0x080054a0`, `0x08005684`, `0x080056ec`, `0x08005734`, `0x080057e8`,
  `0x08005830`, `0x08005898`, and `0x080058e0` select a row using `M`, then
  dereference a string pointer in that row. Existing `kb/text_controls.md`
  records the formulas, including the split F6/FC indices.
- Read-only `hamtools rom peek` of `0x08465500` through `0x08465e48`:
  row anchors, complete row spans, final empty-stream pointers, five roots,
  and the following non-string data layout. Literal-pool checks below connect
  those roots to the exported handler formulas.
- Native caller exports in `extracted/dialogue-coverage-20261009/`:
  `decompile-08013c18.txt`, `decompile-0801c560.txt`,
  `decompile-08032df0.txt`, `decompile-08032e3c.txt`,
  `decompile-08032e6c.txt`, `decompile-08032f64.txt`,
  `decompile-08034dac.txt`, `decompile-08034e94.txt`,
  `decompile-08035674.txt`, `decompile-080366ec.txt`,
  `decompile-08038b78.txt`, `decompile-08038c80.txt`,
  `decompile-08038dcc.txt`, `decompile-08038ef4.txt`,
  `decompile-0803b2d0.txt`, and `decompile-0803fd28.txt`.
- `hamtools rom peek/xrefs` resolves native literal pools and adjacent
  independently referenced table starts. Decoding small samples used the
  existing `hamtools text show`, rather than a new text decoder.

## Five variant insertion families

Each root stores exactly three little-endian u32 row pointers, indexed by
`M = 0, 1, 2`. Rows contain little-endian u32 string pointers. Every listed
physical row's final slot points to the same one-byte null stream at
`0x08465510`. This is an exported empty entry, not a non-ROM terminator.
The following row ends are exclusive and **include** that final pointer.

| Root | Controls | Slots per logical row | Evidence from handler literal pools |
|---|---|---:|---|
| `0x08465df8` | F6 / FC, first branch | 9 | `0x080056b4`, `0x08005860` |
| `0x08465e04` | F6 / FC, second branch | 49 | `0x080056e4`, `0x08005890` |
| `0x08465e10` | F7 / FD | 32 | `0x0800572c`, `0x080058d8` |
| `0x08465e1c` | F8 / FE | 82 | `0x08005774`, `0x08005920` |
| `0x08465e28` | F1 / FB | 45 | `0x080054e0`, `0x08005828` |

| Root | M | Row start | Row end | Slots |
|---|---:|---|---|---:|
| `0x08465df8` | 0 | `0x08465514` | `0x08465538` | 9 |
| `0x08465df8` | 1 | `0x08465538` | `0x0846555c` | 9 |
| `0x08465df8` | 2 | `0x0846555c` | `0x08465580` | 9 |
| `0x08465e04` | 0 | `0x08465580` | `0x08465644` | 49 |
| `0x08465e04` | 1 | `0x08465644` | `0x08465708` | 49 |
| `0x08465e04` | 2 | `0x08465708` | `0x084657cc` | 49 |
| `0x08465e10` | 0 | `0x084657cc` | `0x0846584c` | 32 |
| `0x08465e10` | 1 | `0x0846584c` | `0x084658cc` | 32 |
| `0x08465e10` | 2 | `0x084658cc` | `0x0846594c` | 32 |
| `0x08465e1c` | 0 | `0x08465b68` | `0x08465cb0` | 82 |
| `0x08465e1c` | 1 | `0x08465cb0` | `0x08465df8` | 82 |
| `0x08465e1c` | 2 | `0x08465cb0` | `0x08465df8` | 82 |
| `0x08465e28` | 0 | `0x0846594c` | `0x08465a00` | 45 |
| `0x08465e28` | 1 | `0x08465a00` | `0x08465ab4` | 45 |
| `0x08465e28` | 2 | `0x08465ab4` | `0x08465b68` | 45 |

The physical rows tile `0x08465514` through `0x08465df8`. The five roots
occupy `0x08465df8` through `0x08465e34`. The following five-pointer directory
at `0x08465e34` through `0x08465e48` references these roots; ROM xrefs find
literal references at `0x080060e4` and `0x0800612c`. It is not another string
row and is not decoded by this exporter.

M=1 and M=2 of `0x08465e1c` alias the same physical row. There are 15 logical
rows but 14 physical rows. Counts from the verified ROM:

| Measure | Count |
|---|---:|
| Families / roots | 5 |
| Logical rows | 15 |
| Physical rows | 14 |
| Logical string slots, including empty entries and the alias | 651 |
| Physical pointer slots | 569 |
| Unique stream addresses | 556 |
| Unique nonempty stream addresses | 555 |

The F6/FC formula selects the first family only for operands below four, and
otherwise selects the second family with **operand minus three**. Storage
widths above do not establish safe operand ranges. The exporter intentionally
retains all physical slots, including those not reachable by that one branch.
For example, ROM xrefs also find `0x08465514` at `0x08468094`; this task does
not assign semantics to that additional reader.

The other families contain item, gem, and accessory terminology in sampled
source streams. Exact item IDs, grammatical meaning of M, and runtime helper
transforms remain outside this mapping. Both insertion helpers
`0x08006074` and `0x08005ffc` are treated as unresolved: the export contains
the original pointed-to source streams, not simulated runtime text.

## Export API and verification

- `variant_tables(data, base=0x08000000)` returns immutable `VariantTable`
  objects containing root address, control pair, confidence, and `VariantRow`
  objects with M, row address, exclusive end, and the full pointer tuple.
- `dump_variants(data, out_dir, base=0x08000000)` writes `variants.txt` and
  `variants.json`, UTF-8 with LF, then returns six supplemental counts:
  `variant_tables`, `variant_rows`, `variant_physical_rows`,
  `variant_entries`, `variant_pointer_slots`, and `variant_streams`.
- `variants.txt` has one `text.format_entry` entry per unique address, with all
  table/M/index/pointer-slot references retained in its note. JSON preserves
  all three root entries, all row slots, empty-entry indices, and aliases.
  It records stream lengths without copying text into the index again.
- Explicit row bounds and expected row anchors are checked. Every pointer
  must lie in the supplied ROM image; truncated rows, changed roots, changed
  final empty pointers, or a non-null empty stream raise `TableError`.
  There is no ROM pointer-run scan. Codec imports stay local to avoid a
  circular import when the parent calls this module from `text.dump`.
- All streams are read before creating output files. A malformed source
  stream therefore cannot produce a partial export from that failure.
- Helper validation output: `extracted/text-tables/variants.txt` and
  `extracted/text-tables/variants.json` in the helper checkout (gitignored).
  Integrated `hamtools text dump` writes `variants.txt` / `variants.json`
  under `extracted/text/`. No ROM-derived output
  is stored in tracked files. The parent should keep the destination below
  `extracted/` and verify the ROM before calling the API.
- `uv run --no-sync pytest tests/test_text_tables.py -q`: **11 passed**,
  including the optional verified-ROM test. Synthetic checks cover early
  empty entries, shared rows, null-looking control operands, unknown glyph
  escapes, LF output, exact reconstruction of every root/row pointer word,
  malformed pointers, truncation, and failure before output is created.
  Every one of the ROM's 556 pointed-to streams passed codec round-trip.

## Native tables and fixed literals

These remain separate from event-script dialogue refs and Step 5 editing.
The following are exported fixed storage spans, all
**likely**, with no claim about runtime selector safety or total UI coverage.

| Candidate | Fixed storage span | Slots | Static evidence |
|---|---|---:|---|
| Ham-Chat list | `0x084a7840` to `0x084a799c` | 87 | `0x08032e3c` loop below 86 reads index+1, with fallback index 0; literal `0x08032ec4`. Next independent root is `0x084a799c`. |
| Ham-Chat companion labels | `0x084a799c` to `0x084a7af8` | 87 | `0x08032f64`; literals `0x08033004`, `0x08033034`, `0x080330a0`. Next different data table at `0x084a7af8` has xref `0x0803333c`. |
| Menu item description lines | `0x084a7ea8` to `0x084a81f4` | 211 | `0x08034dac` / `0x08034e94`; literals `0x08034e3c` / `0x08034f50`. u16 offset block starts `0x084a7e4a`; its final offset at `0x084a7ea4` is 211. Next graphics table at `0x084a81f4` has xref `0x080353c4`. |
| Seven-column native presentation | `0x084a9b60` to `0x084a9d74` | 133 (19 by 7) | `0x0803fd28` indexes by row*7+column and checks null. Literal `0x0803fe10` points to strings; literal `0x0803fd7c` points to the following byte timing matrix at `0x084a9d74`. |

The 87-slot first table includes a fallback entry plus 86 enumerated entries.
`0x084a77bc` is the byte ordering/index list, not a string-pointer table;
`0x084a7820` holds VRAM destinations, also not strings. Its ordering IDs must
not be decoded as text or confused with the list-position index.
The 211-slot bound is supported by the terminal offset and independent next
table, but the offset sentinel interpretation and runtime item-ID range still
need review. The 133-slot table has **73 null slots** and 57 distinct non-null
targets. The exporter preserves interior nulls and later entries instead of
stopping at the first null.

Useful directly referenced ROM streams for a native literal export:

| Stream | Native literal references | Description |
|---|---|---|
| `0x0846c67a` | `0x08013cf4`, `0x08036918` | Wrapper inserting the selected entry through FE with operand FF; used by `0x08013c18` / `0x080366ec`. |
| `0x0847a9df`, `0x0847a9e5` | `0x0801c5d8`, `0x0801c5dc` | Paired fixed labels in one branch of `0x0801c560`. Other branch is RAM text. |
| `0x084a92b8` | `0x08038c7c`, `0x08038d6c` | Padded menu/record fallback. |
| `0x084a92c1` | `0x08038ef0`, `0x08038fc0` | Another padded fallback, distinct address. |
| `0x084a35bd` | `0x08038ec4` | Record action label. |
| `0x084a35c4` | `0x08038fa8` | Unknown/unavailable-selection label. |

The existing `text.insert_table` already exports 248 pointers at
`0x084aa740` to `0x084aab20`, where non-pointer menu-ID bytes begin. That
count remains likely. Native word/list sources may overlap its streams;
record separate references without assuming that every source is a new
unique string. The menu list at `0x084aab26` is a byte ID list, not another
text pointer table. `0x08035674` also selects five-column rows from
`0x084a8544` (literal `0x08035718`); its RAM group index has no established
upper bound in this export, so no count is proposed here.

## Indirect event sources and remaining limitations

`0x0803b2d0` supplies the two pointer-register streams used by indirect
show commands `0x080d9762` and `0x080d9772`; the native-call site is
`0x080d9757`. Its exported formulas and ROM literal pools establish:

- Pointer-register base: `0x03002ba0`, resolved at `0x0803b324`.
- Selector pair: bytes at `0x020039f0`, resolved at `0x0803b328`; call the
  first byte k and the second byte n.
- **Slot 0 pointer array is RAM `0x02001ab4`**, resolved at `0x0803b330`,
  indexed by `k-1`. For k below 31 its selected pointer is assigned directly.
  For k at least 31 the pointed-to string is copied/transformed into the
  32-byte RAM buffer `0x03003ad0`, resolved at `0x0803b358`, with the final
  buffer byte forced to null. Its source pointer is still taken from RAM.
- Count bytes are in ROM at `0x084a92f0`, resolved at `0x0803b32c`; this
  address is **not a string-pointer table**. For valid k at least one, the
  exported decrement loop sums count bytes 2 through k modulo 256; call that
  sum S. A ROM byte at `0x084a9652 + S + n - 1` (`0x0803b338`) gives the
  slot 1 pointer index.
- **Slot 1 pointer array is RAM `0x02001c6c`**, resolved at `0x0803b334`.
  Slot 1 is the u32 at that RAM base plus four times the lookup byte. The
  code supplies no upper bound for k or n, and initialization of both RAM
  arrays is not established here. No direct ROM string-pointer tables,
  table sizes, or additional export are inferred from these formulas.

Other unresolved runtime sources include `0x08032df0`'s stream at
`0x03002b90`, generated numeric text in `0x08013c18`, and record bodies used
by `0x08038b78` / `0x08038c80`. The former record body's source is a RAM slot
at `0x03002ba0`, plus record*`0x44c` + subentry*`0xdc` + 3. The latter export
includes questionable overlapping-function recovery; only its explicit ROM
fallback above is adopted. `0x08038244` passes a caller-supplied pointer.
A ROM-only exporter cannot identify the current body behind those pointers.

`native_tables` validates the fixed spans, table-selecting literal pools,
every non-null pointer, and the terminal item-offset value of 211.
`dump_native` writes `native.txt` / `native.json`, deduplicated by stream address.
The four tables preserve **518 pointer slots** including 73 nulls, and point
to **441 distinct streams**. Seven directly referenced sources add seven more
streams, with **10 literal references**, for **448 native source streams**.
JSON preserves table/index/slot provenance and every fixed literal word.
Table/literal references are not event-command references and do not enter
`dialogue.json`. Storage bounds are likely, not a promise that every stored
index is safe or reachable in the native UI.

These static native references establish source relationships, not live
missing scene roots or executed UI paths. Parent follow-up: review candidate
native table bounds, trace initialization of `0x02001ab4` and `0x02001c6c`,
and verify variant selector/index semantics and helper transforms in a later
emulator session. Do not promote these findings to confirmed without that
verification.
