"""Synthetic graphics patch checks and an optional verified-ROM PNG roundtrip.

No game data is embedded in tests. ROM-derived test images stay in extracted/.
"""

import json
import tempfile
import tomllib
from pathlib import Path

import pytest
from PIL import Image

from hamtools import bps, events, gfx, gfx_codec as codec, patch, paths, rom, text, text_layout

BASE = rom.ROM_BASE


@pytest.fixture
def image(monkeypatch, tmp_path):
    asset = gfx.Asset("synthetic", BASE + 0x100, BASE + 0x180,
                      (BASE + 0x23, BASE + 0x37), (BASE + 0x43, BASE + 0x55), 8, 8)
    indices = bytes(i % 16 for i in range(64))
    raw = codec.encode_tiles_4bpp(indices, 8, 8)
    palette = b"".join((i * 0x421).to_bytes(2, "little") for i in range(16))
    data = bytearray(b"\xff" * 0x1000)
    for address, raw_data, refs in ((asset.tiles_address, raw, asset.tile_references),
                                    (asset.palette_address, palette, asset.palette_references)):
        compressed = codec.compress_lz77(raw_data)
        off = address - BASE
        data[off:off + len(compressed)] = compressed
        for ref in refs:
            data[ref - BASE:ref - BASE + 4] = address.to_bytes(4, "little")
    original = bytes(data)
    monkeypatch.setattr(gfx, "ASSETS", {"synthetic": asset})
    monkeypatch.setattr(rom, "load_rom", lambda: original)
    monkeypatch.setattr(rom, "rom_path", lambda: tmp_path / "original.gba")
    monkeypatch.setattr(rom, "EXPECTED_SHA1", rom.sha1(original))
    monkeypatch.setattr(patch, "FREE_BASE", BASE + 0x400)
    monkeypatch.setattr(patch, "FREE_END", BASE + len(original))
    return original, gfx.read_asset(original, "synthetic")


def _entry(source, **changes):
    return {
        "asset": source.asset.name,
        "expect_tiles_sha1": rom.sha1(source.compressed_tiles),
        "expect_palette_sha1": rom.sha1(source.compressed_palette),
        "pixels": [], "colors": [], **changes,
    }


def _mod(tmp_path, entry, extra="", name="portrait"):
    root = tmp_path / "mods"
    mod = root / name
    mod.mkdir(parents=True, exist_ok=True)
    (mod / "mod.toml").write_text(gfx.format_mod(entry, name) + extra, encoding="utf-8")
    return root


def _build(tmp_path, entry, extra=""):
    root = _mod(tmp_path, entry, extra)
    out = tmp_path / "build"
    log = patch.build(["portrait"], root=root, out_dir=out)
    return (out / "hamtaro-mod.gba").read_bytes(), log


def test_palette_relocation_checks_both_unaligned_references_and_preserves_tiles(image, tmp_path):
    original, source = image
    entry = _entry(source, colors=[{"index": 3, "bgr555": 0x7d00}])
    built, log = _build(tmp_path, entry)
    destinations = [int.from_bytes(built[a - BASE:a - BASE + 4], "little")
                    for a in source.asset.palette_references]
    assert destinations == [patch.FREE_BASE, patch.FREE_BASE]
    palette, _ = codec.decompress_lz77(built, patch.FREE_BASE - BASE)
    expected = bytearray(source.palette)
    expected[6:8] = (0x7d00).to_bytes(2, "little")
    assert palette == expected
    assert built[0x100:0x100 + len(source.compressed_tiles)] == source.compressed_tiles
    assert built[0x180:0x180 + len(source.compressed_palette)] == source.compressed_palette
    assert bps.apply(original, (tmp_path / "build/hamtaro-mod.bps").read_bytes()) == built
    assert any("2 checked reference(s)" in row for row in log)


def test_pixels_and_palette_allocate_separately_around_explicit_claims(image, tmp_path):
    original, source = image
    entry = _entry(source, colors=[{"index": 4, "bgr555": 0x1234}], pixels=[{"offset": 31, "index": 7}])
    built, _ = _build(tmp_path, entry,
                      '\n[[edit]]\naddress = 0x08000400\nexpect = "ff ff ff ff"\nhex = "12 34 56 78"\n')
    targets = [int.from_bytes(built[refs[0] - BASE:refs[0] - BASE + 4], "little")
               for refs in (source.asset.tile_references, source.asset.palette_references)]
    assert all(a >= patch.FREE_BASE + 4 and a % 4 == 0 for a in targets)
    assert targets[0] != targets[1]
    raw, _ = codec.decompress_lz77(built, targets[0] - BASE)
    indices = bytearray(codec.decode_tiles_4bpp(source.tiles, 8, 8))
    indices[31] = 7
    assert codec.decode_tiles_4bpp(raw, 8, 8) == indices
    assert built[0x400:0x404] == b"\x12\x34\x56\x78"
    assert len(built) == len(original)


def test_unchanged_recipe_produces_identical_rom(image, tmp_path):
    original, source = image
    built, log = _build(tmp_path, _entry(source))
    assert built == original
    assert any("unchanged" in line for line in log)


def test_graphics_and_text_share_space_after_code_and_later_explicit_edits(image, tmp_path, monkeypatch):
    original, source = image
    old_text = text.encode("Hi[end]")
    data = bytearray(original)
    data[0x220:0x220 + len(old_text)] = old_text
    data[0x72:0x76] = (BASE + 0x220).to_bytes(4, "little")
    data[0x70:0x72] = bytes([0x1a, 0])
    original = bytes(data)
    monkeypatch.setattr(rom, "load_rom", lambda: original)
    monkeypatch.setattr(rom, "EXPECTED_SHA1", rom.sha1(original))
    monkeypatch.setattr(events, "walk", lambda _: events.Walk({}, texts={
        BASE + 0x220: [events.TextRef(BASE + 0x70, 0x1a, "synthetic")]}))
    monkeypatch.setattr(text, "insert_table", lambda _: [])
    monkeypatch.setattr(text_layout, "warnings", lambda *args, **kwargs: [])
    code = bytes(range(16))
    monkeypatch.setattr(patch, "compile_code", lambda *args: (code, {}, []))
    entry = _entry(source, colors=[{"index": 4, "bgr555": 0x1234}])
    root = _mod(tmp_path, entry,
                '\n[[text]]\naddress = 0x08000220\n'
                f'expect_sha1 = "{rom.sha1(old_text)}"\n'
                'text = "An authored longer synthetic line.[end]"\n')
    other = root / "later"
    other.mkdir()
    (other / "mod.toml").write_text(
        '[[edit]]\naddress = 0x08000410\nexpect = "ff ff ff ff"\nhex = "12 34 56 78"\n')
    out = tmp_path / "build"
    patch.build(["portrait", "later"], root=root, out_dir=out)
    built = (out / "hamtaro-mod.gba").read_bytes()
    palette_address = int.from_bytes(built[0x43:0x47], "little")
    text_address = int.from_bytes(built[0x72:0x76], "little")
    assert built[0x400:0x410] == code
    assert palette_address == BASE + 0x414
    _, consumed = codec.decompress_lz77(built, palette_address - BASE)
    assert text_address >= palette_address + consumed
    assert text.read_stream(built, text_address).raw == text.encode("An authored longer synthetic line.[end]")
    assert bps.apply(original, (out / "hamtaro-mod.bps").read_bytes()) == built


@pytest.mark.parametrize("field", ["expect_tiles_sha1", "expect_palette_sha1"])
def test_missing_or_wrong_original_hash_fails_before_outputs(image, tmp_path, field):
    _, source = image
    entry = _entry(source)
    entry[field] = "0" * 40
    with pytest.raises(patch.PatchError, match="mismatch"):
        _build(tmp_path, entry)
    assert not (tmp_path / "build" / "hamtaro-mod.gba").exists()
    del entry[field]
    with pytest.raises(gfx.GfxError, match="required"):
        gfx.prepare_entry(image[0], entry)


def test_graphics_ref_and_source_conflicts_are_rejected(image, tmp_path):
    _, source = image
    entry = _entry(source, colors=[{"index": 1, "bgr555": 0x0123}])
    pointer = source.asset.palette_address.to_bytes(4, "little").hex(" ")
    with pytest.raises(patch.PatchError, match="overlaps"):
        _build(tmp_path, entry, f'\n[[edit]]\naddress = 0x08000043\nexpect = "{pointer}"\nhex = "11 22 33 44"\n')
    with pytest.raises(patch.PatchError, match="overlaps"):
        _build(tmp_path, entry, '\n[[edit]]\naddress = 0x08000180\nexpect = "10"\nhex = "11"\n')


def test_duplicate_entries_and_non_padding_space_fail(image, tmp_path, monkeypatch):
    original, source = image
    entry = _entry(source, colors=[{"index": 1, "bgr555": 0x0123}])
    root = _mod(tmp_path, entry)
    _mod(tmp_path, entry, name="duplicate")
    with pytest.raises(patch.PatchError, match="duplicate graphics"):
        patch.build(["portrait", "duplicate"], root=root, out_dir=tmp_path / "build")
    altered = bytearray(original)
    altered[0x400] = 0
    monkeypatch.setattr(rom, "load_rom", lambda: bytes(altered))
    monkeypatch.setattr(rom, "EXPECTED_SHA1", rom.sha1(bytes(altered)))
    with pytest.raises(patch.PatchError, match="not all 0xFF"):
        patch.build(["portrait"], root=root, out_dir=tmp_path / "build")


@pytest.mark.parametrize("changes", [
    {"pixels": [{"offset": 64, "index": 1}]},
    {"pixels": [{"offset": 1, "index": 16}]},
    {"pixels": [{"offset": True, "index": 1}]},
    {"colors": [{"index": 3, "bgr555": 0xffff}]},
    {"colors": [{"index": 3, "bgr555": 0}, {"index": 3, "bgr555": 1}]},
    {"colors": [{"index": 1, "bgr555": 1, "ignored": 2}]},
    {"pixels": "not a list"},
    {"unknown_field": 3},
])
def test_invalid_authored_deltas_are_rejected(image, changes):
    original, source = image
    with pytest.raises(gfx.GfxError):
        gfx.prepare_entry(original, _entry(source, **changes))


def test_export_import_recipe_contains_only_changed_values(image, tmp_path):
    original, source = image
    path = tmp_path / "synthetic.png"
    gfx.export_asset(original, "synthetic", path)
    assert gfx.infer_asset(path) == "synthetic"
    metadata = json.loads(path.with_suffix(".json").read_text())
    assert metadata["tiles_sha1"] == rom.sha1(source.compressed_tiles)
    entry, imported = gfx.import_image(original, "synthetic", path)
    assert entry["pixels"] == entry["colors"] == []
    assert imported.compressed_tiles == source.compressed_tiles
    assert imported.compressed_palette == source.compressed_palette
    with Image.open(path) as image_file:
        edited = image_file.copy()
    old = edited.getpixel((1, 0))
    edited.putpixel((1, 0), 2 if old != 2 else 3)
    edited.save(path)
    entry, _ = gfx.import_image(original, "synthetic", path)
    assert entry["pixels"] == [{"offset": 1, "index": 2}]
    assert entry["colors"] == []
    assert tomllib.loads(gfx.format_mod(entry, "edited"))["gfx"] == [
        {key: value for key, value in entry.items() if value != []}]


def test_extraction_output_cannot_escape_or_overwrite_a_linked_source(tmp_path):
    root = tmp_path / "extracted"
    root.mkdir()
    with pytest.raises(gfx.GfxError, match="must be under"):
        gfx.require_inside(tmp_path / "outside.png", root, "export")
    source = tmp_path / "source"
    source.write_bytes(b"authored synthetic bytes")
    linked = root / "linked.png"
    linked.hardlink_to(source)
    with pytest.raises(gfx.GfxError, match="hard-linked"):
        gfx.require_inside(linked, root, "export")


def test_overridden_original_is_protected_even_inside_extraction_directory(image, tmp_path, monkeypatch):
    original, _ = image
    root = tmp_path / "extracted"
    root.mkdir()
    source = root / "original.png"
    source.write_bytes(original)
    monkeypatch.setattr(rom, "rom_path", lambda: source)
    with pytest.raises(gfx.GfxError, match="original ROM"):
        gfx.require_inside(source, root, "PNG output")
    with pytest.raises(gfx.GfxError, match="original ROM"):
        gfx.export_asset(original, "synthetic", source)
    assert source.read_bytes() == original


def test_boss_verified_rom_png_roundtrip():
    try:
        data = rom.load_rom()
    except (rom.RomError, OSError):
        pytest.skip("needs the local original ROM; no game data is committed")
    if len(data) != rom.EXPECTED_SIZE or rom.sha1(data) != rom.EXPECTED_SHA1:
        pytest.skip("needs the verified USA AH3E ROM")
    local = paths.EXTRACTED_DIR / "gfx" / "roundtrip-tests"
    local.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=local) as work:
        path = Path(work) / "boss-portrait.png"
        source = gfx.export_asset(data, "boss-portrait", path)
        for mode in ("original", "new"):
            entry, imported = gfx.import_image(data, "boss-portrait", path, mode)
            assert imported.tiles == source.tiles
            assert imported.palette == source.palette
            assert imported.compressed_tiles == source.compressed_tiles
            assert imported.compressed_palette == source.compressed_palette
            assert not entry["pixels"] and not entry["colors"]
