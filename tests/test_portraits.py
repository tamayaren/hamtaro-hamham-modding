"""Inline graphics operands, shared root provenance, and a ROM-gated catalogue audit."""

import struct
import tempfile
from pathlib import Path

import pytest

from hamtools import events, gfx, gfx_codec as codec, paths, portraits, rom

BASE = rom.ROM_BASE


def _put(image, address, raw):
    off = address - BASE
    image[off:off + len(raw)] = raw


def _load(source, destination):
    return b"\x06" + struct.pack("<II", source, destination)


@pytest.fixture
def definition():
    left, right, palette, tiles = BASE + 0x21, BASE + 0x34, BASE + 0x200, BASE + 0x240
    image = bytearray(b"\xff" * 0x1000)
    colors = b"".join((i * 0x421).to_bytes(2, "little") for i in range(16))
    pixels = bytes(i % 16 for i in range(48 * 48))
    _put(image, palette, codec.compress_lz77(colors))
    _put(image, tiles, codec.compress_lz77(codec.encode_tiles_4bpp(pixels, 48, 48)))
    for loader, td, pd in ((left, *portraits.SLOTS["left"]), (right, *portraits.SLOTS["right"])):
        _put(image, loader, _load(palette, pd) + _load(tiles, td) + b"\x1f")
    portrait = portraits.Portrait("synthetic", tiles, palette, (left + 10, right + 10),
                                 (left + 1, right + 1), ("left", "right"), (), "guess", left, right)
    return bytes(image), portrait


def test_inline_u32_operands_can_be_unaligned_and_are_not_table_indices(definition):
    data, p = definition
    palette = portraits.read_load(data, p.left_loader)
    tiles = portraits.read_load(data, p.left_loader + 9)
    assert palette.source == p.palette_address
    assert palette.destination == 0x05000060 and palette.decoded_size == 0x20
    assert tiles.source == p.tiles_address
    assert tiles.destination == 0x06003b80 and tiles.decoded_size == 0x480
    assert portraits.read_load(data, p.right_loader).destination == 0x05000040


@pytest.mark.parametrize("raw, message", [
    (b"\x06" + b"\x00" * 7, "invalid graphics command"),
    (b"\x07" + b"\x00" * 8, "invalid graphics command"),
    (_load(0x03001234, 0x06003b80), "LZ77 offset"),
    (_load(BASE, 0x06003b80), "LZ77 signature"),
])
def test_invalid_and_truncated_inline_loads_are_errors(raw, message):
    with pytest.raises(codec.GfxError, match=message):
        portraits.read_load(raw, BASE)


def test_shared_callee_preserves_every_root_even_when_decoded_only_once(definition):
    data, p = definition
    image = bytearray(data)
    a, b, continuation = BASE + 0x80, BASE + 0xa0, BASE + 0xb0
    _put(image, a, b"\x1e" + struct.pack("<I", p.left_loader) + b"\x1f")
    _put(image, b, b"\x1e" + struct.pack("<I", p.left_loader)
         + b"\x0c" + struct.pack("<I", continuation))
    _put(image, continuation, b"\x0c" + struct.pack("<I", b))
    walked = events.walk(bytes(image), {}, roots={a: "first", b: "second"})
    assert not walked.problems
    provenance = events.command_roots(walked)
    assert provenance[p.left_loader] == ("first", "second")
    assert provenance[p.left_loader + 9] == ("first", "second")
    assert provenance[continuation] == ("second",)
    assert p.right_loader not in walked.commands  # Partner definition is not a runtime root.
    report = portraits.audit(bytes(image), {p.name: p}, walked)
    assert report["graphics_load_count"] == report["portrait_load_count"] == 2
    assert report["definitions"] == [{"name": "synthetic", "reached_slots": ("left",),
                                        "roots": ("first", "second"),
                                        "uses": {"left": ("first", "second"), "right": ()}}]


def test_branch_and_context_edges_include_all_possible_root_uses():
    image = bytearray(b"\xff" * 0x100)
    root, branch, context = BASE + 0x10, BASE + 0x40, BASE + 0x60
    _put(image, root, b"\x22" + struct.pack("<II", 0, branch)
         + b"\x26\x00" + struct.pack("<I", context) + b"\x1f")
    _put(image, branch, b"\x1f")
    _put(image, context, b"\x1f")
    w = events.walk(bytes(image), {}, roots={root: "source"})
    assert not w.problems
    roots = events.command_roots(w)
    assert roots[branch] == roots[context] == ("source",)


@pytest.mark.parametrize("change", ["size", "destination", "source", "return"])
def test_audit_validates_unreached_partner_instead_of_promoting_it(definition, change):
    data, p = definition
    image = bytearray(data)
    if change == "size":
        _put(image, p.palette_address, codec.compress_lz77(bytes(64)))
    elif change == "destination":
        _put(image, p.right_loader + 5, (0x05000240).to_bytes(4, "little"))
    elif change == "source":
        _put(image, p.right_loader + 1, p.tiles_address.to_bytes(4, "little"))
    else:
        _put(image, p.right_loader + 18, b"\x00")
    w = events.walk(bytes(image), {}, roots={p.left_loader: "scene"})
    with pytest.raises(codec.GfxError, match="invalid .* palette/tile/return"):
        portraits.audit(bytes(image), {p.name: p}, w)


def test_uncatalogued_reached_tile_load_fails_but_large_destination_reuse_is_excluded(definition):
    data, p = definition
    image = bytearray(data)
    other = BASE + 0xc0
    _put(image, other, _load(p.tiles_address, 0x06003700) + b"\x1f")
    w = events.walk(bytes(image), {}, roots={p.left_loader: "first", other: "second"})
    with pytest.raises(codec.GfxError, match="uncatalogued portrait load"):
        portraits.audit(bytes(image), {p.name: p}, w)
    _put(image, other, _load(p.tiles_address, 0x05000040) + b"\x1f")
    w = events.walk(bytes(image), {}, roots={p.left_loader: "first", other: "second"})
    report = portraits.audit(bytes(image), {p.name: p}, w)
    assert report["excluded_destination_loads"] == [other]


def test_incomplete_walk_cannot_claim_catalogue_coverage(definition):
    data, p = definition
    w = events.Walk({})
    w.unknown_natives[BASE] = [BASE]
    with pytest.raises(codec.GfxError, match="complete event walk"):
        portraits.audit(data, {p.name: p}, w)


def test_catalogue_metadata_is_address_only_unique_and_sorted_by_loader():
    c = portraits.load_catalogue()
    assert len(c) == 136
    assert list(p.left_loader for p in c.values()) == list(range(portraits.LOADER_START, portraits.LOADER_END, 38))
    assert len({(p.tiles_address, p.palette_address) for p in c.values()}) == 135
    assert {p.name for p in c.values() if p.name_confidence == "confirmed"} == {
        "hamtaro-portrait", "bijou-portrait", "boss-portrait"}


def _verified_rom():
    try:
        data = rom.load_rom()
    except rom.RomError:
        pytest.skip("local ROM not available")
    if rom.sha1(data) != rom.EXPECTED_SHA1:
        pytest.skip("local ROM does not match the expected USA dump")
    return data


def test_real_rom_catalogue_covers_every_reached_portrait_and_all_partner_loaders():
    data = _verified_rom()
    c = portraits.load_catalogue()
    report = portraits.audit(data, c)
    assert (report["root_count"], report["command_count"], report["graphics_load_count"],
            report["portrait_load_count"]) == (148, 98214, 2711, 336)
    assert len(report["excluded_destination_loads"]) == 5
    assert sum(bool(row["roots"]) for row in report["definitions"]) == 130
    for definition in report["definitions"]:
        p = c[definition["name"]]
        assert definition["roots"] == p.roots
        assert definition["reached_slots"] == p.reached_slots
        assert definition["uses"] == {"left": p.left_roots, "right": p.right_roots}


def test_real_rom_all_portraits_roundtrip_and_authored_edits_cover_every_source():
    data = _verified_rom()
    local = paths.EXTRACTED_DIR / "gfx" / "catalogue-roundtrip-tests"
    local.mkdir(parents=True, exist_ok=True)
    seen = set()
    with tempfile.TemporaryDirectory(dir=local) as temp:
        for name, asset in gfx.ASSETS.items():
            png = Path(temp) / f"{name}.png"
            original = gfx.export_asset(data, name, png)
            for mode in ("original", "new"):
                entry, imported = gfx.import_image(data, name, png, mode)
                assert entry["pixels"] == entry["colors"] == []
                assert imported.compressed_tiles == original.compressed_tiles
                assert imported.compressed_palette == original.compressed_palette
                assert not gfx.prepare_entry(data, entry)
            for kind, address in (("tiles", asset.tiles_address), ("palette", asset.palette_address)):
                if address in seen:
                    continue
                seen.add(address)
                edited = dict(entry)
                if kind == "tiles":
                    index = codec.decode_tiles_4bpp(original.tiles, 48, 48)[0] ^ 1
                    edited["pixels"] = [{"offset": 0, "index": index}]
                else:
                    color = int.from_bytes(original.palette[2:4], "little") ^ 1
                    edited["colors"] = [{"index": 1, "bgr555": color & 0x7fff}]
                replacement, = gfx.prepare_entry(data, edited)
                assert replacement.source_address == address
                assert replacement.references == gfx.source_references(address)
                assert codec.decompress_lz77(replacement.data)[0] != (
                    original.tiles if kind == "tiles" else original.palette)
    assert len(seen) == 187
