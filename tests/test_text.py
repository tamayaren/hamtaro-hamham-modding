"""Text codec and event-script walker: synthetic bytes, plus checks against the real ROM."""

import re
import struct

import pytest

from hamtools import events, paths, rom, text
from hamtools.glyphs import GLYPH_TABLE


def test_every_byte_round_trips_alone_and_in_context():
    for byte in range(256):
        for raw in (bytes([byte]), bytes([byte, 0x41, 0x42]), bytes([0x41, byte])):
            assert text.encode(text.decode(raw)) == raw, raw.hex()


def test_glyph_characters_are_unique_and_not_tag_delimiters():
    chars = [g.char for g in GLYPH_TABLE if g.kind == "glyph" and g.char]
    assert len(chars) == len(set(chars))
    assert not set("[]{}\n") & set(chars)


def test_decode_tags_and_glyphs():
    raw = bytes([0xEA, 0x0C, 0xE8, 0xE2, 0xF0, 0x00, 0xF2, 0x03, 0x06, 0x5E, 0xF6, 0x01, 0x60, 0xE0])
    assert text.decode(raw) == "[red]A[normal]\n[word 00][value62 03 06][v2][f6 01]{60}[end]"
    assert text.encode("[red]A[normal]\n[word 00][value62 03 06][v2][f6 01]{60}[end]") == raw


def test_authoring_aliases_encode_to_native_glyphs():
    assert text.encode("'\"♥") == text.encode("’”♡")


@pytest.mark.parametrize("bad", ["[nope]", "[word]", "[word 01 02]", "[", "~"])
def test_encode_rejects_bad_input(bad):
    with pytest.raises(text.TextError):
        text.encode(bad)


def test_stream_length_skips_operands_that_look_like_end_bytes():
    data = bytes([0x99, 0xF0, 0x00, 0xF2, 0xE0, 0xE1, 0x41, 0xE0, 0x41])
    assert text.stream_length(data, 1) == 7
    with pytest.raises(text.TextError):
        text.stream_length(bytes([0x41, 0x42]), 0)


def test_dump_format_round_trips():
    streams = {0x08000010: "#not a comment\nline two[end]", 0x08000020: "[null]",
               0x08000030: "x\n\n[end-nowait]"}
    body = "# header\n\n" + "\n".join(
        text.format_entry(text.Stream(a, text.encode(t), t), "note") for a, t in streams.items())
    assert text.parse_dump(body) == streams


# ---------------------------------------------------------------------------
# Walker on a synthetic ROM image
# ---------------------------------------------------------------------------
def _put(img, addr, data):
    img[addr - rom.ROM_BASE : addr - rom.ROM_BASE + len(data)] = data


def _ptr(v):
    return struct.pack("<I", v)


def test_walker_follows_flow_on_synthetic_rom():
    img = bytearray(0x00480000)
    descriptors, script = 0x08400000, 0x08410000
    _put(img, events.SCENE_TABLE, _ptr(descriptors))
    _put(img, descriptors, _ptr(script) + _ptr(0))         # scene 0.0; next entry is invalid
    sub, sw_a, sw_b, branch, after_native = (script + 0x100, script + 0x200, script + 0x210,
                                             script + 0x300, script + 0x400)
    _put(img, script,
         b"\x1a\x00" + _ptr(0x08420000)                     # show text
         + b"\x1e" + _ptr(sub)                              # call
         + b"\x1c" + _ptr(0x08001235) + b"\x07\x00"          # native with 2 extra bytes
         + b"\x1c" + _ptr(0x08001001) + b"\0" * 5 + _ptr(branch)  # conditional-jump native
         + b"\x1d\x02" + _ptr(sw_a) + _ptr(sw_b))           # switch, falls through
    _put(img, script + 42, b"\x0c" + _ptr(after_native))    # jump
    _put(img, sub, b"\x1b\x00" + _ptr(0x08420010) + b"\x1f")
    _put(img, sw_a, b"\x27")
    _put(img, sw_b, b"\x1b\x00" + _ptr(0x03))               # pointer-register text operand
    _put(img, branch, b"\x00\x01")
    _put(img, after_native, b"\x1c" + _ptr(0x08002001))     # scene-end native
    natives = {0x08001234: events.Native(0x08001234, 2, "fixed", "likely"),
               0x08001000: events.Native(0x08001000, 9, "branch", "likely"),
               0x08002000: events.Native(0x08002000, None, "scene-end", "likely")}
    w = events.walk(bytes(img), natives)
    assert w.roots == {script: "0.0"}
    assert set(w.texts) == {0x08420000, 0x08420010}
    assert w.texts[0x08420010][0].command == sub
    assert w.indirect == [sw_b]
    assert not w.problems and not w.unknown_natives
    assert {sub + 6, sw_a, branch + 1, after_native, script + 42} <= set(w.commands)
    assert after_native + 5 not in w.commands


def test_opcode_lengths_match_the_kb_table():
    rows = re.findall(r"^\| (0x[0-9a-f]{2}) \| `0x[0-9a-f]{8}` \| ([^|]+) \|",
                      (paths.KB_DIR / "event_scripts.md").read_text("utf-8"), re.M)
    kb = {int(op, 16): n.strip() for op, n in rows}
    assert sorted(kb) == list(range(events.LAST_OPCODE + 1))
    for op, n in kb.items():
        if op in (events.NATIVE_CALL, events.SWITCH):
            assert op not in events.OPCODE_LENGTHS
        else:
            assert events.OPCODE_LENGTHS[op] == int(n), hex(op)


def test_natives_csv_loads():
    natives = events.load_natives()
    assert len(natives) == 602
    assert {n.kind for n in natives.values()} == {"fixed", "branch", "scene-end"}


# ---------------------------------------------------------------------------
# Real ROM (skipped without it): counts recorded in kb/event_scripts.md
# ---------------------------------------------------------------------------
def _rom_or_skip():
    try:
        data = rom.load_rom()
    except rom.RomError:
        pytest.skip("needs the ROM")
    if rom.sha1(data) != rom.EXPECTED_SHA1:
        pytest.skip("not the expected ROM")
    return data


def test_walk_of_real_rom_matches_kb_counts():
    w = events.walk(_rom_or_skip())
    assert (len(w.roots), len(w.commands), len(w.texts)) == (148, 98214, 3599)
    assert not w.problems and not w.unknown_natives


def test_every_real_stream_round_trips(tmp_path):
    data = _rom_or_skip()
    counts = text.dump(data, tmp_path)
    assert counts["streams"] == 3599 and counts["inserts"] == 248
    parsed = text.parse_dump((tmp_path / "dialogue.txt").read_text("utf-8"))
    assert len(parsed) == 3599
    for address, decoded in parsed.items():
        assert text.encode(decoded) == text.read_stream(data, address).raw
