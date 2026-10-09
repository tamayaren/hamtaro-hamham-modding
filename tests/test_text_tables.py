"""Supplemental table boundaries/aliases and lossless export on synthetic bytes."""

import json
import struct

import pytest

from hamtools import rom, text, text_tables

BASE = 0x08465500
# Synthetic fixture uses independently specified roots/rows, not a pointer scan.
TABLES = (
    (0x08465df8, (0x08465514, 0x08465538, 0x0846555c), 9),
    (0x08465e04, (0x08465580, 0x08465644, 0x08465708), 49),
    (0x08465e10, (0x084657cc, 0x0846584c, 0x084658cc), 32),
    (0x08465e1c, (0x08465b68, 0x08465cb0, 0x08465cb0), 82),
    (0x08465e28, (0x0846594c, 0x08465a00, 0x08465ab4), 45),
)
SOURCES = {
    0x08465f00: b"\x0c\xf0\x00\xe2\x60\xe1",
    0x08465f20: b"\xea\x0d\xf2\xe0\xe1\x00",
    0x08465f40: b"\xff\xf6\x00\xe0",
}


def _put(image, address, raw):
    offset = address - BASE
    assert 0 <= offset <= len(image) - len(raw)
    image[offset : offset + len(raw)] = raw


def _pointer(image, address, value):
    _put(image, address, struct.pack("<I", value))


@pytest.fixture
def image():
    data = bytearray(0x1000)
    for address, raw in SOURCES.items():
        _put(data, address, raw)
    sources = tuple(SOURCES)
    for root, rows, count in TABLES:
        for variant, start in enumerate(rows):
            _pointer(data, root + 4 * variant, start)
            for index in range(count - 1):
                _pointer(data, start + 4 * index, sources[index % len(sources)])
            _pointer(data, start + 4 * (count - 1), text_tables.EMPTY_STREAM)
    return data


def test_metadata_keeps_logical_rows_aliases_and_empty_slots(image):
    tables = text_tables.variant_tables(bytes(image), BASE)
    assert len(tables) == 5
    assert sum(len(table.rows) for table in tables) == 15
    assert sum(len(row.pointers) for table in tables for row in table.rows) == 651
    physical = {row.address: row for table in tables for row in table.rows}
    assert len(physical) == 14
    assert sum(len(row.pointers) for row in physical.values()) == 569
    assert all(table.confidence == "likely" for table in tables)
    assert all(row.end == row.address + 4 * len(row.pointers)
               for table in tables for row in table.rows)
    assert all(row.pointers[-1] == text_tables.EMPTY_STREAM
               for table in tables for row in table.rows)
    by_root = {table.address: table for table in tables}
    shared = by_root[0x08465e1c].rows
    assert [row.variant for row in shared] == [0, 1, 2]
    assert shared[1].address == shared[2].address
    assert shared[1].pointers == shared[2].pointers
    assert by_root[0x08465df8].controls == (0xf6, 0xfc)
    # F6/FC's runtime split does not discard physically stored slots 4..8.
    assert len(by_root[0x08465df8].rows[0].pointers) == 9


def test_an_early_empty_pointer_does_not_terminate_a_row(image):
    _pointer(image, 0x0846551c, text_tables.EMPTY_STREAM)
    row = text_tables.variant_tables(bytes(image), BASE)[0].rows[0]
    assert row.pointers[2] == text_tables.EMPTY_STREAM
    assert len(row.pointers) == 9
    assert row.pointers[3] in SOURCES


@pytest.mark.parametrize("address,value,message", [
    (0x08465df8, 0x08465518, "row pointer"),
    (0x08465518, 0x03000100, "stream pointer"),
    (0x08465518, BASE - 1, "outside"),
    (0x08465518, BASE + 0x1000, "outside"),
    (0x08465534, 0x08465f00, "final empty-stream"),
])
def test_corrupt_roots_pointers_and_last_slots_fail(image, address, value, message):
    _pointer(image, address, value)
    with pytest.raises(text_tables.TableError, match=message):
        text_tables.variant_tables(bytes(image), BASE)


def test_truncated_root_and_nonempty_sentinel_fail(image):
    with pytest.raises(text_tables.TableError, match="outside"):
        text_tables.variant_tables(bytes(image[:0x08465e28 - BASE + 10]), BASE)
    _put(image, text_tables.EMPTY_STREAM, b"\xe1")
    with pytest.raises(text_tables.TableError, match="is not null"):
        text_tables.variant_tables(bytes(image), BASE)


def test_export_is_lossless_and_preserves_root_and_slot_bytes(image, tmp_path):
    counts = text_tables.dump_variants(bytes(image), tmp_path, BASE)
    assert counts == {
        "variant_tables": 5, "variant_rows": 15, "variant_physical_rows": 14,
        "variant_entries": 651, "variant_pointer_slots": 569, "variant_streams": 4,
    }
    for filename in ("variants.txt", "variants.json"):
        raw_file = (tmp_path / filename).read_bytes()
        assert b"\r" not in raw_file
        assert raw_file.endswith(b"\n")
    decoded = text.parse_dump((tmp_path / "variants.txt").read_text("utf-8"))
    assert set(decoded) == set(SOURCES) | {text_tables.EMPTY_STREAM}
    for address, raw in SOURCES.items():
        assert text.encode(decoded[address]) == raw
    assert text.encode(decoded[text_tables.EMPTY_STREAM]) == b"\x00"
    metadata = json.loads((tmp_path / "variants.json").read_text("utf-8"))
    assert metadata["counts"] == counts
    assert metadata["confidence"] == "likely"
    for table in metadata["tables"]:
        start, end = int(table["address"], 16) - BASE, int(table["end"], 16) - BASE
        roots = [int(row["address"], 16) for row in table["rows"]]
        assert struct.pack("<3I", *roots) == image[start:end]
        for row in table["rows"]:
            pointers = [int(pointer, 16) for pointer in row["pointers"]]
            start, end = int(row["address"], 16) - BASE, int(row["end"], 16) - BASE
            assert struct.pack(f"<{len(pointers)}I", *pointers) == image[start:end]
            assert row["empty_index"] == row["count"] - 1
    assert "table 0x08465e1c M=1" in (tmp_path / "variants.txt").read_text("utf-8")
    assert "table 0x08465e1c M=2" in (tmp_path / "variants.txt").read_text("utf-8")


def test_bad_stream_creates_no_partial_export(image, tmp_path):
    _pointer(image, 0x08465514, BASE + len(image) - 1)
    image[-1] = 0xf2  # truncated two-byte operand; no terminator
    destination = tmp_path / "unwritten"
    with pytest.raises(text.TextError):
        text_tables.dump_variants(bytes(image), destination, BASE)
    assert not destination.exists()


def _rom_or_skip():
    try:
        data = rom.load_rom()
    except rom.RomError:
        pytest.skip("needs the ROM")
    if rom.sha1(data) != rom.EXPECTED_SHA1:
        pytest.skip("not the expected ROM")
    return data


def test_real_table_layout_and_every_source_stream_round_trip():
    # Read-only: real ROM text never goes to pytest's temporary output directory.
    data = _rom_or_skip()
    tables = text_tables.variant_tables(data)
    assert [len(table.rows[0].pointers) for table in tables] == [9, 49, 32, 82, 45]
    pointers = {pointer for table in tables for row in table.rows for pointer in row.pointers}
    assert len(pointers) == 556
    for address in pointers:
        stream = text.read_stream(data, address)
        assert text.encode(stream.text) == stream.raw
    assert text.read_stream(data, text_tables.EMPTY_STREAM).raw == b"\x00"
