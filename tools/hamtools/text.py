"""Lossless text codec: game text bytes <-> readable strings with tags.

Glyphs become their characters, newline control 0xe2 becomes a line break, other controls
become [tags] (kb/text_controls.md), and any byte without a better spelling becomes {xx}.
encode(decode(b)) == b for every stream that decode accepts.
"""

from __future__ import annotations

import json
import re
import tomllib
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
    if not 0 <= offset < len(data):
        raise TextError(f"stream offset {offset:#x} outside data")
    if limit <= 0:
        raise TextError("stream limit must be positive")
    pos = offset
    while pos < len(data) and pos - offset < limit:
        byte = data[pos]
        if byte in END_BYTES:
            return pos + 1 - offset
        count = _BY_BYTE[byte][1] if byte in _BY_BYTE else 0
        if pos + 1 + count > len(data):
            raise TextError(f"truncated control at offset {pos:#x}: needs {count} operand(s)")
        pos += 1 + count
    raise TextError(f"no end byte within {limit:#x} bytes of offset {offset:#x}")


def validate_stream(raw: bytes) -> None:
    """Require exactly one terminated stream, with complete control operands.

    Raises TextError on empty, unterminated, overlong, truncated, or trailing data.
    End-looking operand bytes are skipped, just as they are in read_stream().
    """
    length = stream_length(raw, 0)
    if length != len(raw):
        raise TextError(f"data after end byte at offset {length - 1:#x}; expected one stream")


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
_HEADER = re.compile(r"@(0x[0-9a-fA-F]{8})(?:[ \t].*)?$")


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
    """Read complete entries; reject duplicates and malformed or missing terminals.

    A subset is valid syntax. edits() requires --partial to export that subset.
    Removing a whole entry never means deleting its text from the ROM.
    """
    entries: dict[int, str] = {}
    lines = iter(enumerate(text.replace("\r\n", "\n").split("\n"), 1))
    for line_number, line in lines:
        m = _HEADER.fullmatch(line)
        if not m:
            if line.strip() and not line.startswith("#"):
                raise TextError(f"unexpected line outside an entry at line {line_number}")
            continue
        address = int(m.group(1), 16)
        if address in entries:
            raise TextError(f"duplicate entry {address:#010x} at line {line_number}")
        body = []
        for body_number, body_line in lines:
            if body_line.startswith("@"):
                raise TextError(f"entry {address:#010x} has no end tag before line {body_number}")
            body.append(body_line)
            if body_line.endswith(_END_TAGS):
                break
        else:
            raise TextError(f"entry {address:#010x} has no end tag")
        decoded = "\n".join(body)
        try:
            validate_stream(encode(decoded))
        except TextError as exc:
            raise TextError(f"entry {address:#010x}: {exc}") from exc
        entries[address] = decoded
    return entries


def edits(data: bytes, edited_dump: str, *, partial: bool = False) -> list[dict]:
    """Compare a readable dump to the verified original, returning changed streams.

    Only addresses found by events.walk() are accepted (not insert-table entries).
    By default every walked stream must be present. partial=True explicitly leaves
    omitted entries untouched; an omitted entry is never a text deletion.
    Each expect_sha1 covers the original bytes including the terminating byte.
    Replacements are whole streams: review them before committing, and commit only
    text you authored. A changed stream may still contain copied ROM dialogue.
    """
    from . import events, rom

    if rom.sha1(data) != rom.EXPECTED_SHA1:
        raise TextError("original ROM does not match the expected USA dump")
    entries = parse_dump(edited_dump)
    walked = events.walk(data)
    if walked.problems or walked.unknown_natives:
        raise TextError("event walk is incomplete; resolve problems and unknown natives first")
    unknown = sorted(entries.keys() - walked.texts.keys())
    if unknown:
        raise TextError(f"entry {unknown[0]:#010x} is not a text address found by events.walk()")
    missing = sorted(walked.texts.keys() - entries.keys())
    if missing and not partial:
        raise TextError(f"dump is missing {len(missing)} entry(s), first {missing[0]:#010x}; "
                        "use --partial for an intentional subset (omitted entries stay untouched)")
    changed = []
    for address, replacement in sorted(entries.items()):
        original = read_stream(data, address)
        if encode(replacement) != original.raw:
            changed.append({"address": address, "text": replacement,
                            "expect_sha1": rom.sha1(original.raw)})
    return changed


def format_edits(changed: list[dict]) -> str:
    """Deterministic TOML containing only replacement text and original hashes."""
    lines = ["# Changed streams only; omitted entries stay untouched, never deletions.",
             "# Commit only text you authored; replacements may still contain ROM dialogue."]
    if not changed:
        lines.append("text = []")
    for entry in sorted(changed, key=lambda e: e["address"]):
        # JSON's string escapes also work in TOML. Keep Unicode scalar characters
        # literal to avoid JSON surrogate-pair escapes, which TOML does not allow.
        quoted = json.dumps(entry["text"], ensure_ascii=False)
        lines.extend(["", "[[text]]", f"address = {entry['address']:#010x}",
                      f"text = {quoted}", f"expect_sha1 = {json.dumps(entry['expect_sha1'])}"])
    rendered = "\n".join(lines) + "\n"
    try:
        tomllib.loads(rendered)
    except tomllib.TOMLDecodeError as exc:
        raise TextError(f"cannot represent text edits as TOML: {exc}") from exc
    return rendered


def dump(data: bytes, out_dir) -> dict[str, int]:
    """Write rooted dialogue and separate tentative/table inventories; return counts."""
    from pathlib import Path

    from . import events, text_tables

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

    # Keep these apart from dialogue.json: its refs are reached script operands
    # that the rooted editing workflow can check. An unreferenced command-shaped
    # fragment alone does not establish a safe runtime entry point.
    candidates: dict[int, list[events.TextCandidate]] = {}
    for candidate in events.stray_text_refs(data, walked):
        candidates.setdefault(candidate.target, []).append(candidate)
    tentative, tentative_index = [], []
    for address, refs in sorted(candidates.items()):
        stream = read_stream(data, address)
        note = f"unreferenced candidate  from {refs[0].command:#010x}"
        if len(refs) > 1:
            note += f" +{len(refs) - 1} more"
        tentative.append(format_entry(stream, note))
        tentative_index.append({
            "address": f"{address:#010x}", "length": len(stream.raw),
            "confidence": "likely", "reachability": "unproven",
            "refs": [f"{r.command:#010x}" for r in refs],
            "also_in_dialogue": address in walked.texts, "text": stream.text,
        })
    (out_dir / "unreferenced.txt").write_text(
        header + "# Likely script fragments; runtime reachability unproven.\n"
        "# Separate from editable rooted dialogue. Evidence: kb/text_coverage.md\n\n"
        + "\n".join(tentative), "utf-8", newline="\n")
    (out_dir / "unreferenced.json").write_text(
        json.dumps(tentative_index, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    variant_counts = text_tables.dump_variants(data, out_dir)
    native_counts = text_tables.dump_native(data, out_dir)
    return {"streams": len(entries), "inserts": len(inserts), "commands": len(walked.commands),
            "scene_entries": len(walked.roots), "scene_table_slots": events.SCENE_COUNT,
            "problems": len(walked.problems), "indirect": len(walked.indirect),
            "unknown_natives": len(walked.unknown_natives),
            "unreferenced_streams": len(tentative),
            "unreferenced_commands": sum(map(len, candidates.values())),
            **variant_counts, **native_counts}
