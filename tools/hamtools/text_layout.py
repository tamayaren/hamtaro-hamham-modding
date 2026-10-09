"""Advisory layout checks using the ROM's two glyph-width banks.

Defaults describe the observed Boss response window, not every game window.
Scene callbacks, inserted strings, icons and fixed-width modes need a playtest.
No font bytes are stored here; widths are read from the verified source ROM.
"""

from . import rom, text

GLYPH_WIDTHS = 0x08653040
_OPERANDS = {code: count for code, count in text.TAGS.values()}
_INSERTS = {0xe6, 0xe7, 0xf0, 0xf1, 0xf2, 0xf3, 0xf5,
            0xf6, 0xf7, 0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe}


def warnings(data: bytes, raw: bytes, *, width: int = 168, lines: int = 3,
             spacing: int = 1, font: int = 0) -> list[str]:
    """Warn about literal line widths and unpaced line advances; never reflow text.

    Inserted text/icons are excluded, so widths containing them are lower bounds.
    Explicit wait/scroll/page controls pace the line-count check. Plain newlines
    can auto-scroll in the game; the warning describes that risk, not a hard cap.
    """
    offset = GLYPH_WIDTHS - rom.ROM_BASE + font * 0x100
    widths = data[offset:offset + 0x100]
    if len(widths) != 0x100:
        return ["glyph width table unavailable; check layout in the emulator"]
    result: list[str] = []
    x, row, unpaced, page, pos = 0, 1, 1, 1, 0
    dynamic = False

    def line_end() -> None:
        if x > width:
            result.append(f"page {page} line {row}: literal glyphs need {x}px, "
                          f"window estimate is {width}px")

    def page_end() -> None:
        if unpaced > lines:
            result.append(f"page {page}: {unpaced} lines without an explicit wait/scroll; "
                          f"window estimate shows {lines} (may auto-scroll)")

    while pos < len(raw):
        code = raw[pos]
        if code in text.END_BYTES:
            break
        if 0 < code < 0xe0 and code != 0x5e:
            x += widths[code - 1] + spacing
        elif code in (0xe2, 0xe3, 0xe4, 0xee):
            line_end()
            x = 0
            if code == 0xee:
                page_end()
                page += 1
                row, unpaced = 1, 1
            else:
                row += 1
                if code == 0xe2:
                    unpaced += 1
                else:
                    page_end()
                    unpaced = 1
        elif code in _INSERTS:
            dynamic = True
        pos += 1 + _OPERANDS.get(code, 0)
    line_end()
    page_end()
    if dynamic:
        result.append("layout estimate excludes inserted text/icons; verify their expanded width on screen")
    return result
