"""Native table/literal provenance, interior nulls, and safe export failures."""

import json
import struct

import pytest

from hamtools import rom, text, text_tables

BASE = 0x08000000
TABLES = (
    (0x084a7840, 87, (0x08032ec4,)),
    (0x084a799c, 87, (0x08033034, 0x080330a0)),
    (0x084a7ea8, 211, (0x08034e3c, 0x08034f50)),
    (0x084a9b60, 133, (0x0803fe10,)),
)
LITERALS = (
    (0x0846c67a, (0x08013cf4, 0x08036918)),
    (0x0847a9df, (0x0801c5d8,)), (0x0847a9e5, (0x0801c5dc,)),
    (0x084a92b8, (0x08038c7c, 0x08038d6c)),
    (0x084a92c1, (0x08038ef0, 0x08038fc0)),
    (0x084a35bd, (0x08038ec4,)), (0x084a35c4, (0x08038fa8,)),
)


def _word(image, address, value):
    struct.pack_into("<I", image, address - BASE, value)


@pytest.fixture
def image():
    data = bytearray(0x4aa000)
    target = BASE + 0x180
    data[0x180:0x185] = b"\xf0\x00\xe2\x0c\xe1"
    data[0x1a0:0x1a3] = b"\xea\x0d\xe0"
    for table, count, sources in TABLES:
        for source in sources:
            _word(data, source, table)
        for index in range(count):
            _word(data, table + 4 * index, target)
    _word(data, 0x084a9b64, 0)         # Interior null must not truncate the table.
    _word(data, 0x084a9b68, BASE + 0x1a0)
    struct.pack_into("<H", data, 0x084a7ea4 - BASE, 211)
    for address, refs in LITERALS:
        data[address - BASE:address - BASE + 3] = b"\xff\xf1\x00"
        data[address - BASE + 3] = 0xe1
        for ref in refs:
            _word(data, ref, address)
    return data


def test_native_export_keeps_nulls_later_slots_and_literal_aliases(image, tmp_path):
    counts = text_tables.dump_native(bytes(image), tmp_path)
    assert counts == {"native_tables": 4, "native_pointer_slots": 518,
                      "native_null_slots": 1, "native_literal_refs": 10, "native_streams": 9}
    catalog = json.loads((tmp_path / "native.json").read_text("utf-8"))
    presentation = catalog["tables"][3]
    assert len(presentation["pointers"]) == 133
    assert presentation["pointers"][1] is None
    assert presentation["pointers"][2] == "0x080001a0"
    decoded = text.parse_dump((tmp_path / "native.txt").read_text("utf-8"))
    assert set(decoded) == {BASE + 0x180, BASE + 0x1a0} | {a for a, _ in LITERALS}
    for address, body in decoded.items():
        assert text.encode(body) == text.read_stream(bytes(image), address).raw
    by_address = {s["address"]: s for s in catalog["streams"]}
    assert by_address["0x0846c67a"]["refs"] == [
        {"kind": "literal", "slot": "0x08013cf4"},
        {"kind": "literal", "slot": "0x08036918"},
    ]
    assert all(b"\r" not in (tmp_path / name).read_bytes()
               for name in ("native.txt", "native.json"))


@pytest.mark.parametrize("address,value", [
    (0x084a7840, 0),                # Only the presentation table allows nulls.
    (0x084a7840, 0x03000100),       # RAM is not a static native-ROM string.
    (0x08032ec4, 0x084a7844),       # Source literal must select the evidenced table.
    (0x08013cf4, 0x0846c67b),       # Fixed string literal provenance also matters.
])
def test_invalid_native_source_fails_before_creating_export(image, tmp_path, address, value):
    _word(image, address, value)
    out = tmp_path / "unwritten"
    with pytest.raises(text_tables.TableError):
        text_tables.dump_native(bytes(image), out)
    assert not out.exists()


def test_bad_native_stream_fails_before_creating_export(image, tmp_path):
    _word(image, 0x084a7840, BASE + len(image) - 1)
    image[-1] = 0xf2
    out = tmp_path / "unwritten"
    with pytest.raises(text.TextError):
        text_tables.dump_native(bytes(image), out)
    assert not out.exists()


def test_real_native_layout_and_streams_round_trip():
    try:
        data = rom.load_rom()
    except rom.RomError:
        pytest.skip("needs the ROM")
    if rom.sha1(data) != rom.EXPECTED_SHA1:
        pytest.skip("not the expected ROM")
    tables = text_tables.native_tables(data)
    assert [len(t.pointers) for t in tables] == [87, 87, 211, 133]
    assert sum(t.pointers.count(0) for t in tables) == 73
    pointers = {p for t in tables for p in t.pointers if p}
    assert len(pointers) == 441
    for address in pointers | {a for a, _ in LITERALS}:
        stream = text.read_stream(data, address)
        assert text.encode(stream.text) == stream.raw
