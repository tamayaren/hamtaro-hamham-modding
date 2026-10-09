"""Lossless text codec: game text bytes <-> readable strings with tags.

Glyphs become their characters, newline control 0xe2 becomes a line break, other controls
become [tags] (kb/text_controls.md), and any byte without a better spelling becomes {xx}.
encode(decode(b)) == b for every stream that decode accepts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .glyphs import GLYPH_TABLE

NEWLINE = 0xE2
END_BYTES = frozenset({0x00, 0xE0, 0xE1})
MAX_STREAM = 0x4000

# Tag name -> (byte, operand count). Operands are written as two-digit hex.
TAGS: dict[str, tuple[int, int]] = {
    "null": (0x00, 0),          # end or return (alias of e1)
    "end": (0xE0, 0),           # wait for A, then end or return
    "end-nowait": (0xE1, 0),
    "wait-line": (0xE3, 0),     # wait for A, then next line
    "scroll": (0xE4, 0),        # next line without waiting
    "wait": (0xE5, 0),          # wait for A in place
    "insert-e6": (0xE6, 0),     # RAM stream 0x03001f60
    "insert-e7": (0xE7, 0),     # RAM stream 0x03002b90
    "normal": (0xE8, 0),
    "blue": (0xE9, 0),
    "red": (0xEA, 0),
    "fast": (0xEB, 0),          # glyph delay 0
    "delay6": (0xEC, 0),
    "delay2": (0xED, 0),
    "page": (0xEE, 0),          # wait for A, then clear the page
    "wait-anim": (0xEF, 0),
    "word": (0xF0, 1),          # insert entry of table 0x084aa740
    "f1": (0xF1, 1),
    "value62": (0xF2, 2),
    "value77": (0xF3, 2),
    "callback": (0xF4, 1),      # scene callback id
    "icon": (0xF5, 1),          # inline entity
    "f6": (0xF6, 1),
    "f7": (0xF7, 1),
    "f8": (0xF8, 1),
    "slot": (0xF9, 1),
    "fa": (0xFA, 1),
    "fb": (0xFB, 1),
    "fc": (0xFC, 1),
    "fd": (0xFD, 1),
    "fe": (0xFE, 1),
    "v1": (0xFF, 0),            # variant prefix, lookahead only
    "v2": (0x5E, 0),            # variant prefix, lookahead only
}
_BY_BYTE = {byte: (name, count) for name, (byte, count) in TAGS.items()}
_CHARS = {g.code: g.char for g in GLYPH_TABLE
          if g.kind == "glyph" and g.char is not None and g.code != 0x5E}
_CHAR_BYTES = {char: code for code, char in _CHARS.items()}
# Same authoring aliases as glyphs.CHAR_TO_BYTE; decode always writes the native glyph.
_CHAR_BYTES.update({"'": 0xD0, '"': 0xCE, "♥": 0xDC})
_TOKEN = re.compile(r"\[([a-z0-9-]+)((?: [0-9a-fA-F]{2})*)\]|\{([0-9a-fA-F]{2})\}|(\n)|(.)", re.S)


class TextError(ValueError):
    pass


@dataclass(frozen=True)
class Stream:
    address: int
    raw: bytes                   # including the end byte
    text: str


def stream_length(data: bytes, offset: int, limit: int = MAX_STREAM) -> int:
    """Bytes from offset through the first end byte, skipping control operands."""
    pos = offset
    while pos < len(data) and pos - offset < limit:
        byte = data[pos]
        if byte in END_BYTES:
            return pos + 1 - offset
        pos += 1 + (_BY_BYTE[byte][1] if byte in _BY_BYTE else 0)
    raise TextError(f"no end byte within {limit:#x} bytes of offset {offset:#x}")


def decode(raw: bytes) -> str:
    out = []
    pos = 0
    while pos < len(raw):
        byte = raw[pos]
        if byte in _CHARS:
            out.append(_CHARS[byte])
            pos += 1
        elif byte == NEWLINE:
            out.append("\n")
            pos += 1
        elif byte in _BY_BYTE and pos + 1 + _BY_BYTE[byte][1] <= len(raw):
            name, count = _BY_BYTE[byte]
            operands = raw[pos + 1 : pos + 1 + count]
            out.append("[" + " ".join([name] + [f"{b:02x}" for b in operands]) + "]")
            pos += 1 + count
        else:
            out.append(f"{{{byte:02x}}}")
            pos += 1
    return "".join(out)


def encode(text: str) -> bytes:
    out = bytearray()
    for m in _TOKEN.finditer(text):
        name, operands, raw, newline, char = m.groups()
        if name is not None:
            if name not in TAGS:
                raise TextError(f"unknown tag [{name}] at character {m.start()}")
            byte, count = TAGS[name]
            values = [int(x, 16) for x in operands.split()]
            if len(values) != count:
                raise TextError(f"[{name}] takes {count} operand(s), got {len(values)}")
            out.append(byte)
            out.extend(values)
        elif raw is not None:
            out.append(int(raw, 16))
        elif newline is not None:
            out.append(NEWLINE)
        elif char in _CHAR_BYTES:
            out.append(_CHAR_BYTES[char])
        else:
            raise TextError(f"no glyph for {char!r} at character {m.start()}; use {{xx}}")
    return bytes(out)


def read_stream(data: bytes, address: int, base: int = 0x08000000) -> Stream:
    offset = address - base
    raw = bytes(data[offset : offset + stream_length(data, offset)])
    return Stream(address, raw, decode(raw))


# ---------------------------------------------------------------------------
# Dump files (gitignored extracted/text/): one entry per stream, sorted by address.
#
#   @0x0846cc6b  scene 1.1  from 0x0804ffb4
#   ...decoded text, real line breaks for 0xe2...[end]
#
# An entry's text runs until a line ending in an end tag; '#' lines between entries are
# comments. parse_dump(format_dump(...)) gives back every stream's exact text.
# ---------------------------------------------------------------------------
INSERT_TABLE = 0x084aa740       # pointer table used by [word] (0xf0) and [fa] (0xfa)
_END_TAGS = ("[null]", "[end]", "[end-nowait]")
_HEADER = re.compile(r"@(0x[0-9a-fA-F]{8})\b")


def insert_table(data: bytes, base: int = 0x08000000) -> list[int]:
    """Pointers of the 0xf0/0xfa insert table, up to the first non-ROM word."""
    out = []
    while True:
        offset = INSERT_TABLE - base + 4 * len(out)
        pointer = int.from_bytes(data[offset : offset + 4], "little")
        if not base <= pointer < base + len(data):
            return out
        out.append(pointer)


def format_entry(stream: Stream, note: str = "") -> str:
    return f"@{stream.address:#010x}{'  ' + note if note else ''}\n{stream.text}\n"


def parse_dump(text: str) -> dict[int, str]:
    entries: dict[int, str] = {}
    lines = iter(text.split("\n"))
    for line in lines:
        m = _HEADER.match(line)
        if not m:
            if line.strip() and not line.startswith("#"):
                raise TextError(f"unexpected line outside an entry: {line[:40]!r}")
            continue
        body = []
        for body_line in lines:
            body.append(body_line)
            if body_line.endswith(_END_TAGS):
                break
        else:
            raise TextError(f"entry {m.group(1)} has no end tag")
        entries[int(m.group(1), 16)] = "\n".join(body)
    return entries


def dump(data: bytes, out_dir) -> dict[str, int]:
    """Walk all event scripts and write the readable text files; return counts."""
    import json
    from pathlib import Path

    from . import events

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    walked = events.walk(data)
    header = ("# Hamtaro: Ham-Ham Heartbreak (USA) text, decoded by `hamtools text dump`.\n"
              "# Extracted from the ROM: local only, never commit. Tags: kb/text_dump.md\n")
    entries, index = [], []
    for address in sorted(walked.texts):
        stream = read_stream(data, address)
        refs = sorted(walked.texts[address], key=lambda r: r.command)
        scenes = sorted({r.root for r in refs}, key=lambda s: tuple(map(int, s.split("."))))
        note = f"scene {','.join(scenes)}  from {refs[0].command:#010x}"
        if len(refs) > 1:
            note += f" +{len(refs) - 1} more"
        entries.append(format_entry(stream, note))
        index.append({"address": f"{address:#010x}", "length": len(stream.raw),
                      "scenes": scenes, "refs": [f"{r.command:#010x}" for r in refs],
                      "text": stream.text})
    (out_dir / "dialogue.txt").write_text(header + "\n" + "\n".join(entries), "utf-8", newline="\n")
    (out_dir / "dialogue.json").write_text(json.dumps(index, ensure_ascii=False, indent=1),
                                           "utf-8", newline="\n")
    inserts = [format_entry(read_stream(data, p), f"[word {i:02x}] / [fa {i:02x}]")
               for i, p in enumerate(insert_table(data))]
    (out_dir / "inserts.txt").write_text(header + f"# Insert table {INSERT_TABLE:#010x}\n\n"
                                         + "\n".join(inserts), "utf-8", newline="\n")
    return {"streams": len(entries), "inserts": len(inserts), "commands": len(walked.commands),
            "scene_entries": len(walked.roots), "problems": len(walked.problems),
            "indirect": len(walked.indirect), "unknown_natives": len(walked.unknown_natives)}
