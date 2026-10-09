"""Encode authored dialogue literals during patch compilation, without reading the ROM.

Each const byte array is a named text node. Branching, choices and tree mapping stay
in the game's event scripts; this helper does not implement arbitrary branches.
The native printable alphabet is accepted. Control bytes stay explicit in C.
"""

from __future__ import annotations

from pathlib import Path

from .glyphs import CHAR_TO_BYTE

_GLYPHS = {**CHAR_TO_BYTE, "\n": 0xE2}
_SIMPLE_ESCAPES = {
    "'": "'", '"': '"', "?": "?", "\\": "\\",
    "a": "\a", "b": "\b", "f": "\f", "n": "\n",
    "r": "\r", "t": "\t", "v": "\v",
}
_HEX = "0123456789abcdefABCDEF"


class DialogueError(ValueError):
    """Invalid authored text or DIALOGUE_TEXT argument."""


def _glyph(char: str) -> int:
    try:
        return _GLYPHS[char]
    except KeyError:
        raise DialogueError(f"unsupported dialogue glyph {char!r} (U+{ord(char):04X})") from None


def encode_text(text: str) -> bytes:
    """Encode supported glyphs only; do not append an end or other control byte."""
    return bytes(_glyph(char) for char in text)


class _CSource:
    def __init__(self, source: str, path: str | Path):
        self.original = source
        self.path = path
        # C removes backslash-newline pairs before recognizing comments or tokens.
        # Keep original offsets so diagnostics and untouched source remain exact.
        chars, self.offsets = [], []
        i = 0
        while i < len(source):
            if source.startswith("\\\r\n", i):
                i += 3
            elif source.startswith("\\\n", i):
                i += 2
            else:
                chars.append(source[i])
                self.offsets.append(i)
                i += 1
        self.text = "".join(chars)
        self.offsets.append(len(source))

    def error(self, pos: int, message: str):
        offset = self.offsets[pos]
        line = self.original.count("\n", 0, offset) + 1
        column = offset - self.original.rfind("\n", 0, offset)
        raise DialogueError(f"{self.path}:{line}:{column}: {message}")

    def token(self, pos: int, *, in_call: bool = False) -> tuple[int, int]:
        text = self.text
        while pos < len(text):
            if text[pos].isspace():
                pos += 1
            elif text.startswith("//", pos):
                end = text.find("\n", pos + 2)
                pos = len(text) if end < 0 else end + 1
            elif text.startswith("/*", pos):
                end = text.find("*/", pos + 2)
                if end < 0:
                    if in_call:
                        self.error(pos, "unterminated comment in DIALOGUE_TEXT")
                    return len(text), len(text)
                pos = end + 2
            else:
                break
        start = pos
        if pos < len(text):
            if text[pos] in "\"'":
                quote = text[pos]
                pos += 1
                while pos < len(text):
                    if text[pos] == "\\":
                        pos = min(pos + 2, len(text))
                    elif text[pos] == quote:
                        pos += 1
                        break
                    else:
                        pos += 1
            elif text[pos].isalnum() or text[pos] == "_":
                while pos < len(text) and (text[pos].isalnum() or text[pos] == "_"):
                    pos += 1
            else:
                pos += 1
        return start, pos

    def literal(self, start: int, end: int) -> bytes:
        text = self.text
        closing = end - 1
        while closing > start and text[closing - 1] == "\\":
            closing -= 1
        if end <= start + 1 or text[end - 1] != '"' or (end - 1 - closing) % 2:
            self.error(start, "unterminated C string literal in DIALOGUE_TEXT")
        encoded = bytearray()
        pos = start + 1
        while pos < end - 1:
            origin = pos
            char = text[pos]
            pos += 1
            if char in "\r\n":
                self.error(origin, r"unescaped newline in C string literal; use \n")
            if char == "\\":
                escape = text[pos]
                pos += 1
                if escape in _SIMPLE_ESCAPES:
                    char = _SIMPLE_ESCAPES[escape]
                elif escape in "01234567":
                    digits = escape
                    while pos < end - 1 and len(digits) < 3 and text[pos] in "01234567":
                        digits += text[pos]
                        pos += 1
                    value = int(digits, 8)
                    if value > 0xFF:
                        self.error(origin, "C byte escape exceeds 0xff")
                    char = chr(value)
                elif escape == "x":
                    first = pos
                    while pos < end - 1 and text[pos] in _HEX:
                        pos += 1
                    if pos == first:
                        self.error(origin, r"\x escape needs hexadecimal digits")
                    value = int(text[first:pos], 16)
                    if value > 0xFF:
                        self.error(origin, "C byte escape exceeds 0xff")
                    char = chr(value)
                elif escape in "uU":
                    count = 4 if escape == "u" else 8
                    digits = text[pos:pos + count]
                    if len(digits) != count or any(c not in _HEX for c in digits):
                        self.error(origin, f"\\{escape} escape needs {count} hexadecimal digits")
                    value = int(digits, 16)
                    if value > 0x10FFFF or 0xD800 <= value <= 0xDFFF:
                        self.error(origin, "invalid Unicode character escape")
                    char = chr(value)
                    pos += count
                else:
                    self.error(origin, f"unknown C escape \\{escape}")
            try:
                encoded.append(_glyph(char))
            except DialogueError as exc:
                self.error(origin, str(exc))
        return bytes(encoded)

    def call(self, opening: int) -> tuple[bytes, int]:
        pos = opening + 1
        encoded = bytearray()
        literals = 0
        while True:
            start, end = self.token(pos, in_call=True)
            token = self.text[start:end]
            if token.startswith('"'):
                encoded.extend(self.literal(start, end))
                literals += 1
                pos = end
            elif token == ")" and literals:
                if not encoded:
                    self.error(start, "DIALOGUE_TEXT must contain at least one glyph")
                return bytes(encoded), end
            else:
                self.error(start, "DIALOGUE_TEXT expects only adjacent ordinary C string literals"
                           + (" followed by ')'" if literals else ""))


def expand_source(source: str, path: str | Path = "<source>") -> str:
    """Replace literal DIALOGUE_TEXT calls with comma-separated byte initializer tokens.

    This runs before the C preprocessor: identifiers, expressions and prefixed/wide
    strings are not text arguments. Comments, other strings and character literals
    are untouched. Empty text is rejected because it supplies no initializer token.
    """
    c = _CSource(source, path)
    pieces = []
    pos = last = 0
    while pos < len(c.text):
        start, pos = c.token(pos)
        if c.text[start:pos] != "DIALOGUE_TEXT":
            continue
        opening, end = c.token(pos)
        if c.text[opening:end] != "(":
            continue
        encoded, pos = c.call(opening)
        first, after = c.offsets[start], c.offsets[pos]
        pieces.append(source[last:first])
        replacement = ", ".join(f"0x{value:02x}" for value in encoded)
        # Keep subsequent compiler line numbers aligned with the editable source.
        # Continue physical lines so calls inside #define also keep their meaning.
        pieces.append(replacement + "\\\n" * source[first:after].count("\n"))
        last = after
    pieces.append(source[last:])
    return "".join(pieces)


def prepare_source(source: Path, generated: Path) -> Path:
    """Write a generated C copy only when a text call expands; otherwise use source."""
    if source.suffix.lower() != ".c":
        return source
    original = source.read_bytes().decode("utf-8", errors="surrogateescape")
    expanded = expand_source(original, source)
    if expanded == original:
        return source
    generated.parent.mkdir(parents=True, exist_ok=True)
    filename = source.resolve().as_posix().replace("\\", "\\\\").replace('"', '\\"')
    prepared = f'#line 1 "{filename}"\n' + expanded
    generated.write_bytes(prepared.encode("utf-8", errors="surrogateescape"))
    return generated
