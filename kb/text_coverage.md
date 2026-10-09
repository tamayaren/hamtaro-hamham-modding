# Dialogue coverage sweep

Static investigation on 2026-10-09 for USA AH3E, SHA1
`2525cc23524068dfb3a2b4e0ce7b736f95023e82`. Findings here are **likely**,
not emulator-confirmed. The emulator and its state were not changed.

## Scene roots and the table boundary

The scene-pointer array starts at `0x08466944` and ends at `0x08466970`:
**11 pointer slots**, numbered 0 through 10. `0x08466970` is already the
first scene descriptor; its first word is the event entry `0x0804d420`.
The older count of 12 accidentally treated this descriptor word as another
scene-array pointer. That spurious array produced no valid roots, so fixing
the bound preserves the **148 unique entry scripts**, **98,214 commands**,
**4,144 direct show-text commands**, and **3,599 unique streams**.
Scene slot 8 aliases slot 0's descriptor array. Root labels retain the
first scene/subscene that discovers a shared entry.

Evidence: ROM pointer-array/descriptor layout and `Scene_Load` at
`0x080009f8`, which indexes a scene pointer then a 0x10-byte descriptor.

## What the 113 missing patterns establish

A broad byte search for `0x1a`/`0x1b`, a slot byte below `0x10`, and a
pointer anywhere in the 8 MB ROM finds **4,483 patterns**. Only **4,144**
are reached direct text commands; the other **339** include coincidences
inside code, animation data, and command operands. The earlier 4,257 total
described a narrower text-shaped subset, not all ROM-pointer patterns.

`events.stray_text_refs` narrows the search to the observed direct-text
address span `0x08465510` through `0x084a5d82`, excluding every decoded
command's full byte range. This reproduces **113 candidates**, all in the
event-script areas. Their **101 distinct targets** decode and re-encode
exactly; **83 targets** are absent from rooted dialogue and 18 are shared.
The filter describes the search, not a proven text-bank boundary or a
proof that an event can enter these commands.

These candidates occupy **63 gaps** between walked commands. Many gaps
begin immediately after a return or unconditional jump and contain the
same call/show/return structures as neighboring reached script blocks.
This supports **likely script fragments**. Runtime reachability remains
unproven; unused script content is a plausible explanation, not a finding
promoted to confirmed.

## Entry-point audit

The audit searched ROM words at **every byte alignment**, including native
literal pools, table entries, and unaligned script operands. A pointer is
useful evidence only when its source and the entry it selects are real.

- `0x08088ebc` and `0x08089317` have incoming script operands at
  `0x08087b00` and `0x08087b05`; those operands are themselves in an
  unwalked block following the unconditional jump at `0x08087af0`.
  They do not establish a path from a scene root.
- Apparent native-code pointer `0x0803064d` to `0x080c0d04` crosses two
  Thumb shift instructions. Ghidra's listing shows an instruction-byte
  coincidence, not a literal-pool/table reference.
- Root `0x0804d426` is referenced only from other unwalked script blocks
  at `0x0804d489`, `0x0804d607`, and `0x0804d775`. The scene descriptor
  enters `0x0804d420`, whose scene-change command ends that path first.
- Ghidra references to `gEventCursor` at `0x03002c50` were checked.
  The apparent native writers inside `0x08021404` and `0x0803c7ca`
  are tails of scene-change routines, restoring saved state around scene
  loads; their raw Ghidra function boundaries are misleading.
- `Scene_InvokeCallback` at `0x08001440` calls a function through the
  installed callback list. A callback pointer is a code pointer, not
  automatically an event-script root. Direct native entry into one of
  these gaps was not established by this sweep.

**No additional runtime-reached root is claimed.** `events.walk` now
accepts explicit `roots` and supplemental `extra_roots` with source labels
for future evidenced entries. Candidates are exported to
`unreferenced.txt` / `unreferenced.json`, separately from
`dialogue.txt` / `dialogue.json`. The latter keep their existing rooted
references for the separate edit/reinsert work. Candidate JSON records
`confidence: likely` and `reachability: unproven`.

## Runtime text slots and native UI

Show-text commands `0x080d9762` and `0x080d9772` use pointer registers
0 and 1. Native call `0x080d9757` invokes `0x0803b2d0`, which fills them.
Its literal pools identify RAM pointer arrays at `0x02001ab4` and
`0x02001c6c`, a selector at `0x020039f0`, and transformation output at
`0x03003ad0`. Slot 0 uses the first array directly below selector `0x1f`
and a generated/modified RAM string otherwise; slot 1 selects from the
second RAM array through a lookup. This is **likely** source tracing,
not a static enumeration of their current content. Their operands must
not be repointed as if they were direct ROM string pointers.

Native-rendered menu labels, Ham-Chat words, and item names belong in
**supplemental inventories** when their actual ROM sources and bounds are
established. They are not scene dialogue operands. The existing insert
export already captures the ROM insert-pointer table; the five variant
table families are now exported separately with every physical slot and
logical row alias. Four bounded native tables and seven fixed native sources
add an inventory of 448 native streams, with pointer-slot/literal provenance.
See [text_tables.md](text_tables.md). RAM-generated
names, formatted numbers, and user-edited text remain contextual.

## Evidence and remaining uncertainty

Local evidence is gitignored under the main checkout's
`extracted/dialogue-coverage-20261009/`: candidate and gap inventories,
unaligned pointer searches, cursor/caller references, and read-only Ghidra
exports. Earlier unfinished Claude coverage research in the
`coverage-sweep` worktree's `extracted/coverage/` informed the audit and
was preserved. No ROM text or decompiled bodies are tracked.

Negative xref evidence cannot exclude every computed entry point.
Later-game savestate sampling can test specific candidate blocks without
changing their present confidence. The 34 guessed native operand counts
and context-dependent `ef`/`f5` controls remain separate pending work.
