"""Address-only catalogue and audit of dialogue portrait loader routines.

Names are editorial labels with separate confidence. No game text, images or
compressed bytes are stored in the public catalogue. Reached script commands
come from events.walk; adjacent partner routines are explicitly audited static
definitions, never silently promoted to runtime scene roots.
"""

from __future__ import annotations

import csv
import re
import struct
from dataclasses import dataclass
from pathlib import Path

from . import events, gfx_codec as codec, paths, rom

CATALOGUE = paths.KB_DIR / "portrait_catalogue.csv"
LOADER_START = 0x084b1c65
LOADER_END = 0x084b3095             # exclusive; 136 definitions of 38 bytes
SLOTS = {"left": (0x06003b80, 0x05000060),
         "right": (0x06003700, 0x05000040)}


@dataclass(frozen=True)
class Portrait:
    name: str
    tiles_address: int
    palette_address: int
    tile_references: tuple[int, ...]
    palette_references: tuple[int, ...]
    slots: tuple[str, ...]
    roots: tuple[str, ...]
    name_confidence: str
    left_loader: int
    right_loader: int
    reached_slots: tuple[str, ...] = ()
    left_roots: tuple[str, ...] = ()
    right_roots: tuple[str, ...] = ()


@dataclass(frozen=True)
class Load:
    command: int
    source: int
    destination: int
    decoded_size: int
    compressed_size: int


def read_load(data: bytes, command: int) -> Load:
    """Decode 0x06 + inline little-endian source u32 + destination u32."""
    off = command - rom.ROM_BASE
    if not 0 <= off <= len(data) - 9 or data[off] != 0x06:
        raise codec.GfxError(f"invalid graphics command at {command:#010x}")
    source, destination = struct.unpack_from("<II", data, off + 1)
    raw, consumed = codec.decompress_lz77(data, source - rom.ROM_BASE)
    return Load(command, source, destination, len(raw), consumed)


def load_catalogue(path: Path | None = None) -> dict[str, Portrait]:
    """Load reviewed labels/addresses; each entry owns both defined slot loaders.

    The gfx layer unions references by source across entries, so shared images
    and palettes are edited globally and competing replacements are refused.
    """
    result: dict[str, Portrait] = {}
    loaders: set[int] = set()
    with (path or CATALOGUE).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            name = row["name"]
            confidence = row["name_confidence"]
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
                raise codec.GfxError(f"invalid portrait name {name!r}")
            if name in result or confidence not in {"confirmed", "likely", "guess"}:
                raise codec.GfxError(f"duplicate portrait or invalid confidence: {name}")
            left, right = int(row["left_loader"], 16), int(row["right_loader"], 16)
            tiles, palette = int(row["tiles"], 16), int(row["palette"], 16)
            if not (rom.ROM_BASE <= tiles < 0x08800000
                    and rom.ROM_BASE <= palette < 0x08800000
                    and LOADER_START <= left and right + 19 <= LOADER_END
                    and (left - LOADER_START) % 38 == 0 and right == left + 19
                    and left not in loaders):
                raise codec.GfxError(f"invalid portrait addresses: {name}")
            loaders.add(left)
            reached = tuple(row["reached_slots"].split())
            if any(slot not in SLOTS for slot in reached):
                raise codec.GfxError(f"invalid reached slot: {name}")
            result[name] = Portrait(name, tiles, palette, (left + 10, right + 10),
                                    (left + 1, right + 1), tuple(SLOTS),
                                    tuple(row["roots"].split()), confidence, left, right, reached,
                                    tuple(row.get("left_roots", "").split()),
                                    tuple(row.get("right_roots", "").split()))
    return result


def audit(data: bytes, catalogue: dict[str, Portrait] | None = None,
          walked: events.Walk | None = None) -> dict:
    """Validate every reached 0x06 and every catalogued partner definition.

    Nonportrait uses of the same destination are retained as exclusions. Every
    reached portrait tile load must belong to an audited palette/tile/return
    routine; invalid sizes or missing definitions are errors, not dropped rows.
    """
    catalogue = load_catalogue() if catalogue is None else catalogue
    walked = events.walk(data) if walked is None else walked
    if walked.problems or walked.unknown_natives:
        raise codec.GfxError("portrait audit needs a complete event walk")
    roots = events.command_roots(walked)
    loads = {a: read_load(data, a) for a, op in sorted(walked.commands.items()) if op == 0x06}
    covered: set[int] = set()
    definitions = []
    for portrait in catalogue.values():
        uses = {}
        for slot, loader in (("left", portrait.left_loader), ("right", portrait.right_loader)):
            palette, tiles = read_load(data, loader), read_load(data, loader + 9)
            tile_dest, palette_dest = SLOTS[slot]
            if (palette.source != portrait.palette_address or tiles.source != portrait.tiles_address
                    or palette.destination != palette_dest or tiles.destination != tile_dest
                    or palette.decoded_size != 0x20 or tiles.decoded_size != 0x480
                    or data[loader + 18 - rom.ROM_BASE] != 0x1f):
                raise codec.GfxError(f"{portrait.name}: invalid {slot} palette/tile/return loader")
            covered.update((loader, loader + 9))
            uses[slot] = roots.get(loader, ())
        reached_slots = tuple(slot for slot in SLOTS if uses[slot])
        all_roots = tuple(sorted({root for values in uses.values() for root in values}))
        definitions.append({"name": portrait.name, "reached_slots": reached_slots,
                            "roots": all_roots, "uses": uses})
    excluded = []
    for load in loads.values():
        if load.command in covered:
            continue
        if load.destination in {dest for pair in SLOTS.values() for dest in pair}:
            if (load.destination in {pair[0] for pair in SLOTS.values()}
                    or load.decoded_size == 0x20 and LOADER_START <= load.command < LOADER_END):
                raise codec.GfxError(f"uncatalogued portrait load at {load.command:#010x}")
            excluded.append(load.command)
    return {"root_count": len(walked.roots), "command_count": len(walked.commands),
            "graphics_load_count": len(loads), "portrait_load_count": len(set(loads) & covered),
            "excluded_destination_loads": excluded, "definitions": definitions}
