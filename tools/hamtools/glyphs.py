"""The USA ROM's native glyph vocabulary, described without any game assets.

This is a byte classification, not a text-stream decoder: control operands and
inserted strings must be parsed by their handlers. Both font banks use these IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata
from typing import Literal


@dataclass(frozen=True)
class Glyph:
    code: int
    kind: Literal["glyph", "blank", "prefix", "control"]
    name: str
    char: str | None = None


# These sequences describe letter identities, not extracted dialogue or bitmaps.
_ALPHABETS = (
    (0x02, "0123456789"),
    (0x0C, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    (0x26, "ÄÁÀÂÏÍÌÎÜÚÙÛËÉÈÊÖÓÒÔÇÑŒ"),
    (0x61, "abcdefghijklmnopqrstuvwxyz"),
    (0x7B, "äáàâïíìîüúùûëéèêöóòôçñœß"),
)
_PUNCTUATION = {
    0x01: " ",
    0xC0: ";", 0xC1: "°", 0xC3: "¿", 0xC4: "¡", 0xC5: "‘",
    0xC6: "%", 0xC7: "*", 0xC8: "+", 0xC9: ":", 0xCA: ".",
    0xCB: "-", 0xCC: "_", 0xCD: "“", 0xCE: "”", 0xCF: ",",
    0xD0: "’", 0xD1: "…", 0xD2: "(", 0xD3: ")", 0xD4: "<",
    0xD5: ">", 0xD6: "/", 0xD7: "\\", 0xD8: "!", 0xD9: "?",
    0xDA: "#", 0xDB: "&", 0xDC: "♡", 0xDD: "★", 0xDE: "♪",
}

# Shapes whose meaning is context dependent have explicit names. The raised
# grave-accented a is smaller than the ordinary à at 0x7d; do not alias them.
NAMED_GLYPHS = {
    "BOXED_E": 0x60,
    "RAISED_A_GRAVE": 0xC2,
    "DEGREE": 0xC1,
    "HEART": 0xDC,
    "STAR": 0xDD,
    "MUSIC_NOTE": 0xDE,
    "OUTLINE_CROSS": 0xDF,
}


def _table() -> tuple[Glyph, ...]:
    slots = []
    for code in range(256):
        if code == 0 or code >= 0xE0:
            slots.append(Glyph(code, "control", f"CONTROL_{code:02X}"))
        elif code == 0x5E:
            slots.append(Glyph(code, "prefix", "INSERT_STYLE_PREFIX"))
        else:
            slots.append(Glyph(code, "blank", "BLANK_SLOT"))
    characters = dict(_PUNCTUATION)
    for start, text in _ALPHABETS:
        characters.update({start + i: char for i, char in enumerate(text)})
    for code, char in characters.items():
        slots[code] = Glyph(code, "glyph", unicodedata.name(char).replace(" ", "_"), char)
    for name, code in NAMED_GLYPHS.items():
        slots[code] = Glyph(code, "glyph", name, slots[code].char)
    return tuple(slots)


GLYPH_TABLE = _table()
CHAR_TO_BYTE = {glyph.char: glyph.code for glyph in GLYPH_TABLE if glyph.char is not None}
# Authoring aliases choose the native closing quotes / outlined heart explicitly.
CHAR_TO_BYTE.update({"'": 0xD0, '"': 0xCE, "♥": 0xDC})
