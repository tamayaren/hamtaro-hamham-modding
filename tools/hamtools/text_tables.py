"""Bounded supplemental text tables; static evidence is in kb/text_tables.md.

No ROM scanning or event walking. Imports of the codec stay local so text.dump
can call this module without a circular import. Write ROM exports only beneath
gitignored extracted/; this module does not implement editing or reinsertion.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path

ROM_BASE = 0x08000000
EMPTY_STREAM = 0x08465510

# (three-row root, insertion controls, physical [start, end) for M=0/1/2).
# Ends include the final pointer to EMPTY_STREAM. These are explicit bounds,
# not a scan to the first invalid pointer or to the first empty string.
_VARIANT_LAYOUTS = (
    (0x08465df8, (0xf6, 0xfc), (
        (0x08465514, 0x08465538),
        (0x08465538, 0x0846555c),
        (0x0846555c, 0x08465580),
    )),
    (0x08465e04, (0xf6, 0xfc), (
        (0x08465580, 0x08465644),
        (0x08465644, 0x08465708),
        (0x08465708, 0x084657cc),
    )),
    (0x08465e10, (0xf7, 0xfd), (
        (0x084657cc, 0x0846584c),
        (0x0846584c, 0x084658cc),
        (0x084658cc, 0x0846594c),
    )),
    (0x08465e1c, (0xf8, 0xfe), (
        (0x08465b68, 0x08465cb0),
        (0x08465cb0, 0x08465df8),
        (0x08465cb0, 0x08465df8),  # M=1 and M=2 share a physical row.
    )),
    (0x08465e28, (0xf1, 0xfb), (
        (0x0846594c, 0x08465a00),
        (0x08465a00, 0x08465ab4),
        (0x08465ab4, 0x08465b68),
    )),
)


class TableError(ValueError):
    """The input does not match the evidenced USA table layout."""


@dataclass(frozen=True)
class VariantRow:
    variant: int
    address: int
    end: int                     # exclusive; includes the empty-stream slot
    pointers: tuple[int, ...]


@dataclass(frozen=True)
class VariantTable:
    address: int                 # root, containing three row pointers
    controls: tuple[int, int]
    rows: tuple[VariantRow, ...]
    confidence: str = "likely"   # static evidence; no emulator verification


def _offset(data: bytes, address: int, size: int, base: int) -> int:
    offset = address - base
    if offset < 0 or offset + size > len(data):
        raise TableError(f"range {address:#010x}+{size:#x} is outside the ROM image")
    return offset


def _u32(data: bytes, address: int, base: int) -> int:
    return struct.unpack_from("<I", data, _offset(data, address, 4, base))[0]


def variant_tables(data: bytes, base: int = ROM_BASE) -> tuple[VariantTable, ...]:
    """Read five known roots and all 15 logical rows, including empty slots.

    Validate the evidenced row anchors, fixed spans, sentinel, and every stream
    pointer. Unexpected roots or truncated/corrupt rows fail instead of widening
    the extraction. Bounds describe storage, not safe control-operand ranges.
    """
    if data[_offset(data, EMPTY_STREAM, 1, base)] != 0:
        raise TableError(f"empty stream at {EMPTY_STREAM:#010x} is not null")
    tables = []
    for root, controls, bounds in _VARIANT_LAYOUTS:
        rows = []
        for variant, (start, end) in enumerate(bounds):
            slot = root + 4 * variant
            if _u32(data, slot, base) != start:
                raise TableError(f"row pointer at {slot:#010x} does not match {start:#010x}")
            offset = _offset(data, start, end - start, base)
            pointers = struct.unpack_from(f"<{(end - start) // 4}I", data, offset)
            for index, pointer in enumerate(pointers):
                try:
                    _offset(data, pointer, 1, base)
                except TableError as exc:
                    raise TableError(f"stream pointer at {start + 4 * index:#010x}: {exc}") from exc
            if pointers[-1] != EMPTY_STREAM:
                raise TableError(f"row {start:#010x} lacks its final empty-stream pointer")
            rows.append(VariantRow(variant, start, end, pointers))
        tables.append(VariantTable(root, controls, tuple(rows)))
    return tuple(tables)


def dump_variants(data: bytes, out_dir: str | Path, base: int = ROM_BASE) -> dict[str, int]:
    """Write variants.txt and variants.json with LF; return supplemental counts.

    Text entries are unique by address. JSON preserves every root, logical row,
    slot and alias. Exports are source streams, before runtime helper transforms.
    The caller must verify the ROM and use a gitignored extracted/ destination.
    """
    from .text import format_entry, read_stream

    tables = variant_tables(data, base)
    references: dict[int, list[str]] = {}
    for table in tables:
        for row in table.rows:
            for index, pointer in enumerate(row.pointers):
                references.setdefault(pointer, []).append(
                    f"table {table.address:#010x} M={row.variant} i={index:02x} "
                    f"slot {row.address + 4 * index:#010x}"
                )
    streams = [read_stream(data, address, base) for address in sorted(references)]
    physical_rows = {row.address: row for table in tables for row in table.rows}
    counts = {
        "variant_tables": len(tables),
        "variant_rows": sum(len(table.rows) for table in tables),
        "variant_physical_rows": len(physical_rows),
        "variant_entries": sum(len(row.pointers) for table in tables for row in table.rows),
        "variant_pointer_slots": sum(len(row.pointers) for row in physical_rows.values()),
        "variant_streams": len(streams),
    }
    header = (
        "# Supplemental variant insertion strings: local ROM extraction, never commit.\n"
        "# Layout/bounds confidence: likely (static). See kb/text_tables.md.\n"
        "# Unique streams; variants.json preserves all rows/slots, including empty entries.\n"
        "# Stored source text, before helpers at 0x08006074 / 0x08005ffc.\n\n"
    )
    body = header + "\n".join(
        format_entry(stream, "; ".join(references[stream.address])) for stream in streams
    )
    metadata = {
        "confidence": "likely",
        "counts": counts,
        "tables": [
            {
                "address": f"{table.address:#010x}",
                "end": f"{table.address + 4 * len(table.rows):#010x}",
                "controls": [f"{control:#04x}" for control in table.controls],
                "confidence": table.confidence,
                "rows": [
                    {"variant": row.variant, "address": f"{row.address:#010x}",
                     "end": f"{row.end:#010x}", "count": len(row.pointers),
                     "empty_index": len(row.pointers) - 1, "confidence": table.confidence,
                     "pointers": [f"{pointer:#010x}" for pointer in row.pointers]}
                    for row in table.rows
                ],
            }
            for table in tables
        ],
        "streams": [{"address": f"{stream.address:#010x}", "length": len(stream.raw)}
                    for stream in streams],
    }
    index = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "variants.txt").write_text(body, encoding="utf-8", newline="\n")
    (out_dir / "variants.json").write_text(index, encoding="utf-8", newline="\n")
    return counts


# Fixed native-rendered tables, independently bounded by neighboring referenced
# tables or index loops. Sources and remaining uncertainty: kb/text_tables.md.
_NATIVE_LAYOUTS = (
    ("ham-chat-list", 0x084a7840, 0x084a799c, False, (0x08032ec4,)),
    ("ham-chat-companion", 0x084a799c, 0x084a7af8, False,
     (0x08033034, 0x080330a0)),
    ("menu-item-lines", 0x084a7ea8, 0x084a81f4, False,
     (0x08034e3c, 0x08034f50)),
    ("native-presentation", 0x084a9b60, 0x084a9d74, True, (0x0803fe10,)),
)
_NATIVE_LITERALS = (
    (0x0846c67a, (0x08013cf4, 0x08036918)),
    (0x0847a9df, (0x0801c5d8,)),
    (0x0847a9e5, (0x0801c5dc,)),
    (0x084a92b8, (0x08038c7c, 0x08038d6c)),
    (0x084a92c1, (0x08038ef0, 0x08038fc0)),
    (0x084a35bd, (0x08038ec4,)),
    (0x084a35c4, (0x08038fa8,)),
)


@dataclass(frozen=True)
class NativeTable:
    name: str
    address: int
    end: int
    pointers: tuple[int, ...]    # zero slots are preserved, not decoded as text
    sources: tuple[int, ...]     # literal-pool words selecting this table
    confidence: str = "likely"


def native_tables(data: bytes, base: int = ROM_BASE) -> tuple[NativeTable, ...]:
    """Read four evidenced native tables with fixed bounds and nullable slots."""
    tables = []
    for name, start, end, nullable, sources in _NATIVE_LAYOUTS:
        for source in sources:
            if _u32(data, source, base) != start:
                raise TableError(f"native table literal at {source:#010x} changed")
        offset = _offset(data, start, end - start, base)
        pointers = struct.unpack_from(f"<{(end - start) // 4}I", data, offset)
        for index, pointer in enumerate(pointers):
            if pointer == 0 and nullable:
                continue
            try:
                _offset(data, pointer, 1, base)
            except TableError as exc:
                raise TableError(f"native slot {start + 4 * index:#010x}: {exc}") from exc
        tables.append(NativeTable(name, start, end, pointers, sources))
    # Independent terminal item-offset value supports the 211-slot storage bound.
    offset = _offset(data, 0x084a7ea4, 2, base)
    if struct.unpack_from("<H", data, offset)[0] != 211:
        raise TableError("terminal menu-item offset at 0x084a7ea4 changed")
    return tuple(tables)


def dump_native(data: bytes, out_dir: str | Path, base: int = ROM_BASE) -> dict[str, int]:
    """Write native.txt/native.json, with table and literal refs kept out of dialogue."""
    from .text import format_entry, read_stream

    tables = native_tables(data, base)
    refs: dict[int, list[dict[str, str | int]]] = {}
    for table in tables:
        for index, pointer in enumerate(table.pointers):
            if pointer:
                refs.setdefault(pointer, []).append({
                    "kind": "table", "table": table.name, "index": index,
                    "slot": f"{table.address + 4 * index:#010x}",
                })
    for address, sources in _NATIVE_LITERALS:
        for source in sources:
            if _u32(data, source, base) != address:
                raise TableError(f"native stream literal at {source:#010x} changed")
            refs.setdefault(address, []).append({"kind": "literal", "slot": f"{source:#010x}"})
    streams = [read_stream(data, address, base) for address in sorted(refs)]
    counts = {
        "native_tables": len(tables),
        "native_pointer_slots": sum(len(t.pointers) for t in tables),
        "native_null_slots": sum(t.pointers.count(0) for t in tables),
        "native_literal_refs": sum(len(sources) for _, sources in _NATIVE_LITERALS),
        "native_streams": len(streams),
    }
    header = (
        "# Native-rendered source text: local ROM extraction, never commit.\n"
        "# Source/bounds confidence: likely (static). See kb/text_tables.md.\n"
        "# Native table/literal refs, separate from event dialogue operands.\n\n"
    )
    body = header + "\n".join(
        format_entry(s, f"native  from {refs[s.address][0]['slot']} "
                     f"({len(refs[s.address])} source refs)") for s in streams
    )
    metadata = {
        "confidence": "likely", "counts": counts,
        "tables": [{
            "name": t.name, "address": f"{t.address:#010x}", "end": f"{t.end:#010x}",
            "confidence": t.confidence, "count": len(t.pointers),
            "source_literals": [f"{s:#010x}" for s in t.sources],
            "pointers": [f"{p:#010x}" if p else None for p in t.pointers],
        } for t in tables],
        "streams": [{"address": f"{s.address:#010x}", "length": len(s.raw),
                     "refs": refs[s.address]} for s in streams],
    }
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "native.txt").write_text(body, encoding="utf-8", newline="\n")
    (out_dir / "native.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return counts
