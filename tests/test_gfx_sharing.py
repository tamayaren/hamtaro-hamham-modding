"""Synthetic catalogue sharing checks; no ROM, emulator, or game data required."""

import argparse
import builtins
import json
import sys
import tomllib
from dataclasses import replace
from types import ModuleType, SimpleNamespace

import pytest
from PIL import Image

import hamtools
from hamtools import bps, cli, gfx, gfx_codec as codec, patch, paths, rom

BASE = rom.ROM_BASE


@pytest.fixture
def shared(monkeypatch, tmp_path):
    assets = {
        "alpha": gfx.Asset("alpha", BASE + 0x200, BASE + 0x380,
                           (BASE + 0x21, BASE + 0x35), (BASE + 0x49,), 8, 8,
                           slots=("left",), roots=("intro",), name_confidence="likely"),
        "beta": gfx.Asset("beta", BASE + 0x200, BASE + 0x400,
                          (BASE + 0x35, BASE + 0x5d), (BASE + 0x71,), 8, 8,
                          slots=("right",), roots=("other-scene",), name_confidence="guess"),
        "defined-loader": gfx.Asset("defined-loader", BASE + 0x280, BASE + 0x380,
                                    (BASE + 0x85,), (BASE + 0x99, BASE + 0xad), 8, 8,
                                    slots=("right",), roots=(), name_confidence="likely"),
    }
    indices = bytes(i % 16 for i in range(64))
    tiles = codec.encode_tiles_4bpp(indices, 8, 8)
    other_tiles = codec.encode_tiles_4bpp(bytes(reversed(indices)), 8, 8)
    palette = b"".join((i * 0x421).to_bytes(2, "little") for i in range(16))
    other_palette = b"".join((i * 31).to_bytes(2, "little") for i in range(16))
    data = bytearray(b"\xff" * 0x1800)
    for off, raw in ((0x200, tiles), (0x280, other_tiles), (0x380, palette), (0x400, other_palette)):
        compressed = codec.compress_lz77(raw)
        data[off:off + len(compressed)] = compressed
    for asset in assets.values():
        for address, refs in ((asset.tiles_address, asset.tile_references),
                              (asset.palette_address, asset.palette_references)):
            for ref in refs:
                data[ref - BASE:ref - BASE + 4] = address.to_bytes(4, "little")
    original = bytes(data)
    source_path = tmp_path / "original.gba"
    source_path.write_bytes(original)
    monkeypatch.setattr(gfx, "ASSETS", assets)
    monkeypatch.setattr(rom, "load_rom", lambda: original)
    monkeypatch.setattr(rom, "rom_path", lambda: source_path)
    monkeypatch.setattr(rom, "EXPECTED_SHA1", rom.sha1(original))
    monkeypatch.setattr(patch, "FREE_BASE", BASE + 0x800)
    monkeypatch.setattr(patch, "FREE_END", BASE + len(original))
    monkeypatch.setattr(paths, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(paths, "EXTRACTED_DIR", tmp_path / "extracted")
    return original


def _entry(data, name="alpha", kind=None):
    source = gfx.read_asset(data, name)
    return {
        "asset": name,
        "expect_tiles_sha1": rom.sha1(source.compressed_tiles),
        "expect_palette_sha1": rom.sha1(source.compressed_palette),
        "pixels": [{"offset": 5, "index": 6}] if kind == "tiles" else [],
        "colors": [{"index": 3, "bgr555": 0x1234}] if kind == "palette" else [],
    }


def _build(tmp_path, entries, extra=""):
    root = tmp_path / "mods"
    names = []
    for i, entry in enumerate(entries):
        name = f"change-{i}"
        mod = root / name
        mod.mkdir(parents=True, exist_ok=True)
        (mod / "mod.toml").write_text(gfx.format_mod(entry, name) + (extra if i == 0 else ""),
                                      encoding="utf-8")
        names.append(name)
    log = patch.build(names, root=root, out_dir=tmp_path / "build")
    return (tmp_path / "build/hamtaro-mod.gba").read_bytes(), log


def _source(kind):
    asset = gfx.ASSETS["alpha"]
    return asset.tiles_address if kind == "tiles" else asset.palette_address


def _pointer(data, ref):
    return int.from_bytes(data[ref - BASE:ref - BASE + 4], "little")


@pytest.mark.parametrize("kind, affected", [
    ("tiles", ("alpha", "beta")),
    ("palette", ("alpha", "defined-loader")),
])
def test_shared_change_repoints_every_loader_and_preserves_other_streams(shared, tmp_path, kind, affected):
    original = shared
    address = _source(kind)
    references = gfx.source_references(address)
    replacement, = gfx.prepare_entry(original, _entry(original, kind=kind))
    assert replacement.references == references
    assert len(references) == 3  # The duplicate mapped tile operand is written once.
    built, log = _build(tmp_path, [_entry(original, kind=kind)])
    target, = {_pointer(built, ref) for ref in references}
    assert target == patch.FREE_BASE
    assert built[:0x200] != original[:0x200]
    assert built[0x200:0x800] == original[0x200:0x800]  # Original streams stay intact.
    expected = bytearray(codec.decompress_lz77(original, address - BASE)[0])
    if kind == "tiles":
        indices = bytearray(codec.decode_tiles_4bpp(bytes(expected), 8, 8))
        indices[5] = 6
        expected = codec.encode_tiles_4bpp(bytes(indices), 8, 8)
    else:
        expected[6:8] = (0x1234).to_bytes(2, "little")
    assert codec.decompress_lz77(built, target - BASE)[0] == expected
    for asset in gfx.ASSETS.values():
        for source, refs in ((asset.tiles_address, asset.tile_references),
                             (asset.palette_address, asset.palette_references)):
            if source != address:
                assert all(_pointer(built, ref) == source for ref in refs)
    assert any(all(name in line for name in affected) and "3 checked reference(s)" in line for line in log)
    assert bps.apply(original, (tmp_path / "build/hamtaro-mod.bps").read_bytes()) == built
    assert rom.rom_path().read_bytes() == original


@pytest.mark.parametrize("kind", ["tiles", "palette"])
def test_selection_from_other_shared_asset_has_same_reference_union(shared, kind):
    name = "beta" if kind == "tiles" else "defined-loader"
    primary, = gfx.prepare_entry(shared, _entry(shared, kind=kind))
    other, = gfx.prepare_entry(shared, _entry(shared, name, kind))
    assert other.source_address == primary.source_address
    assert other.references == primary.references
    assert other.data == primary.data


@pytest.mark.parametrize("kind", ["tiles", "palette"])
@pytest.mark.parametrize("mirror", [0, 0x02000000, 0x04000000])
def test_unknown_unaligned_base_and_mirror_pointers_refuse_changed_streams(shared, tmp_path, monkeypatch,
                                                                         kind, mirror):
    entry = _entry(shared, kind=kind)
    changed = bytearray(shared)
    unknown = BASE + 0x121
    changed[0x121:0x125] = (_source(kind) + mirror).to_bytes(4, "little")
    monkeypatch.setattr(rom, "load_rom", lambda: bytes(changed))
    monkeypatch.setattr(rom, "EXPECTED_SHA1", rom.sha1(changed))
    with pytest.raises(patch.PatchError, match="unmapped pointer occurrence") as error:
        _build(tmp_path, [entry])
    assert f"{unknown:#010x}" in str(error.value)
    assert f"{_source(kind):#010x}" in str(error.value)
    assert "affected entries:" in str(error.value)
    assert not (tmp_path / "build/hamtaro-mod.gba").exists()
    assert not (tmp_path / "build/hamtaro-mod.bps").exists()


@pytest.mark.parametrize("kind", ["tiles", "palette"])
def test_unchanged_missing_refs_allowed_but_changed_refuses_omitted_uses(shared, tmp_path, monkeypatch, kind):
    entry = _entry(shared, kind=kind)
    field = "tile_references" if kind == "tiles" else "palette_references"
    affected = gfx.source_assets(_source(kind))
    assets = dict(gfx.ASSETS)
    for asset in affected:
        assets[asset.name] = replace(asset, **{field: ()})
    monkeypatch.setattr(gfx, "ASSETS", assets)
    assert not gfx.prepare_entry(shared, _entry(shared))
    built, _ = _build(tmp_path, [_entry(shared)])
    assert built == shared
    with pytest.raises(gfx.GfxError, match="unmapped pointer occurrence"):
        gfx.prepare_entry(shared, entry)


@pytest.mark.parametrize("kind", ["tiles", "palette"])
def test_per_asset_omitted_reference_is_not_silently_lost(shared, monkeypatch, kind):
    entry = _entry(shared, kind=kind)
    asset = gfx.ASSETS["alpha"]
    field = "tile_references" if kind == "tiles" else "palette_references"
    assets = dict(gfx.ASSETS)
    assets["alpha"] = replace(asset, **{field: ()})
    monkeypatch.setattr(gfx, "ASSETS", assets)
    with pytest.raises(gfx.GfxError, match="unmapped pointer occurrence"):
        gfx.prepare_entry(shared, entry)


@pytest.mark.parametrize("kind", ["tiles", "palette"])
def test_changed_unreferenced_source_has_clear_refusal(shared, monkeypatch, kind):
    entry = _entry(shared, kind=kind)
    data = bytearray(shared)
    address = _source(kind)
    for ref in gfx.source_references(address):
        data[ref - BASE:ref - BASE + 4] = b"\xff" * 4
    field = "tile_references" if kind == "tiles" else "palette_references"
    assets = dict(gfx.ASSETS)
    for asset in gfx.source_assets(address):
        assets[asset.name] = replace(asset, **{field: ()})
    monkeypatch.setattr(gfx, "ASSETS", assets)
    assert not gfx.prepare_entry(bytes(data), _entry(bytes(data)))
    with pytest.raises(gfx.GfxError, match="no mapped references"):
        gfx.prepare_entry(bytes(data), entry)


@pytest.mark.parametrize("kind", ["tiles", "palette"])
def test_unknown_pointers_to_unchanged_stream_do_not_block_a_different_change(shared, kind):
    data = bytearray(shared)
    other = "palette" if kind == "tiles" else "tiles"
    data[0x121:0x125] = _source(other).to_bytes(4, "little")
    replacement, = gfx.prepare_entry(bytes(data), _entry(bytes(data), kind=kind))
    assert replacement.kind == kind


@pytest.mark.parametrize("kind", ["tiles", "palette"])
def test_stale_pointer_in_other_registry_entry_is_checked(shared, tmp_path, monkeypatch, kind):
    entry = _entry(shared, kind=kind)
    # This operand belongs only to the other slot/unreached defined loader.
    reference = BASE + (0x5d if kind == "tiles" else 0xad)
    data = bytearray(shared)
    data[reference - BASE:reference - BASE + 4] = (BASE + 0x600).to_bytes(4, "little")
    monkeypatch.setattr(rom, "load_rom", lambda: bytes(data))
    monkeypatch.setattr(rom, "EXPECTED_SHA1", rom.sha1(data))
    with pytest.raises(patch.PatchError, match="original pointer mismatch") as error:
        _build(tmp_path, [entry])
    assert f"{reference:#010x}" in str(error.value)
    assert not (tmp_path / "build/hamtaro-mod.gba").exists()


@pytest.mark.parametrize("field", ["expect_tiles_sha1", "expect_palette_sha1"])
def test_shared_changes_still_require_both_original_stream_hashes(shared, tmp_path, field):
    entry = _entry(shared, kind="tiles")
    entry[field] = "0" * 40
    with pytest.raises(patch.PatchError, match=f"{field} mismatch"):
        _build(tmp_path, [entry])
    assert not (tmp_path / "build/hamtaro-mod.gba").exists()


@pytest.mark.parametrize("kind, other", [("tiles", "beta"), ("palette", "defined-loader")])
def test_competing_mods_on_shared_source_name_source_and_affected_entries(shared, tmp_path, kind, other):
    with pytest.raises(patch.PatchError, match="duplicate graphics replacement") as error:
        _build(tmp_path, [_entry(shared, kind=kind), _entry(shared, other, kind)])
    message = str(error.value)
    assert f"{_source(kind):#010x}" in message
    assert "alpha" in message and other in message
    assert "change-0.gfx[0]" in message and "change-1.gfx[0]" in message
    assert not (tmp_path / "build/hamtaro-mod.gba").exists()
    assert not (tmp_path / "build/hamtaro-mod.bps").exists()


def test_independent_shared_stream_changes_can_coexist(shared, tmp_path):
    built, log = _build(tmp_path, [_entry(shared, kind="tiles"), _entry(shared, kind="palette")])
    tiles_target, = {_pointer(built, ref) for ref in gfx.source_references(_source("tiles"))}
    palette_target, = {_pointer(built, ref) for ref in gfx.source_references(_source("palette"))}
    assert tiles_target != palette_target
    assert tiles_target % 4 == palette_target % 4 == 0
    assert len([line for line in log if line.startswith("gfx")]) == 2


def test_explicit_edit_overlapping_other_asset_reference_still_rejected(shared, tmp_path):
    source = _source("tiles")
    expect = source.to_bytes(4, "little").hex(" ")
    extra = ('\n[[edit]]\naddress = 0x0800005d\n'
             f'expect = "{expect}"\nhex = "11 22 33 44"\n')
    with pytest.raises(patch.PatchError, match="overlaps"):
        _build(tmp_path, [_entry(shared, kind="tiles")], extra)
    assert not (tmp_path / "build/hamtaro-mod.gba").exists()


def test_export_and_import_metadata_keep_schema_and_show_all_shared_uses(shared, tmp_path):
    image = tmp_path / "extracted/gfx/alpha.png"
    source = gfx.export_asset(shared, "alpha", image)
    exported = json.loads(image.with_suffix(".json").read_text(encoding="utf-8"))
    assert exported["schema"] == 1
    assert exported["asset"] == "alpha"
    assert exported["width"] == exported["height"] == 8
    assert exported["rom_sha1"] == rom.sha1(shared)
    assert exported["tiles_sha1"] == rom.sha1(source.compressed_tiles)
    assert exported["palette_sha1"] == rom.sha1(source.compressed_palette)
    assert exported["tiles_address"] == "0x08000200"
    assert exported["palette_address"] == "0x08000380"
    assert exported["slots"] == ["left"]
    assert exported["name_confidence"] == "likely"
    assert exported["roots"] == ["intro"]
    assert exported["tile_references"] == ["0x08000021", "0x08000035"]
    assert exported["sharing"]["tiles"]["references"] == ["0x08000021", "0x08000035", "0x0800005d"]
    assert exported["sharing"]["tiles"]["affected_assets"] == ["alpha", "beta"]
    assert exported["sharing"]["tiles"]["affected_asset_count"] == 2
    assert exported["sharing"]["tiles"]["reference_count"] == 3
    assert exported["sharing"]["palette"]["affected_assets"] == ["alpha", "defined-loader"]
    assert exported["sharing"]["palette"]["affected_asset_count"] == 2
    assert exported["sharing"]["palette"]["reference_count"] == 3
    tiles_uses = exported["sharing"]["tiles"]["uses"]
    assert [use["asset"] for use in tiles_uses] == ["alpha", "beta"]
    assert tiles_uses[1]["slots"] == ["right"]
    assert tiles_uses[1]["name_confidence"] == "guess"
    palette_uses = exported["sharing"]["palette"]["uses"]
    assert palette_uses[1]["asset"] == "defined-loader"
    assert palette_uses[1]["roots"] == []
    with Image.open(image) as png:
        changed = png.copy()
    changed.putpixel((5, 0), 6)
    changed.save(image)
    mod = tmp_path / "patches/shared-import/mod.toml"
    assert gfx.write_import(shared, "alpha", image, mod) == (1, 0)
    entry, = tomllib.loads(mod.read_text(encoding="utf-8"))["gfx"]
    assert entry == {key: value for key, value in _entry(shared, kind="tiles").items() if value != []}
    assert "Boss" not in mod.read_text(encoding="utf-8")
    imported = json.loads((tmp_path / "extracted/gfx/imports/shared-import/alpha.json").read_text(encoding="utf-8"))
    assert imported["sharing"] == exported["sharing"]
    assert imported["tiles_sha1"] == exported["tiles_sha1"]
    assert imported["palette_sha1"] == exported["palette_sha1"]
    assert imported["changed_streams"] == ["tiles"]
    assert imported["changed_pixels"] == 1 and imported["changed_colors"] == 0
    compressed = (tmp_path / "extracted/gfx/imports/shared-import/alpha.tiles.lz").read_bytes()
    assert imported["imported_tiles_sha1"] == rom.sha1(compressed)


def test_import_unknown_reference_fails_before_writing_recipe(shared, tmp_path):
    image = tmp_path / "alpha.png"
    gfx.export_asset(shared, "alpha", image)
    with Image.open(image) as png:
        changed = png.copy()
    changed.putpixel((5, 0), 6)
    changed.save(image)
    data = bytearray(shared)
    data[0x121:0x125] = _source("tiles").to_bytes(4, "little")
    mod = tmp_path / "patches/refused/mod.toml"
    with pytest.raises(gfx.GfxError, match="unmapped pointer occurrence"):
        gfx.write_import(bytes(data), "alpha", image, mod)
    assert not mod.exists()
    assert not (tmp_path / "extracted/gfx/imports/refused").exists()


def test_list_verifies_rom_and_reports_sharing_addresses_slots_and_confidence(shared, capsys, monkeypatch):
    calls = []
    monkeypatch.setattr(rom, "load_rom", lambda: calls.append(True) or shared)
    assert cli.cmd_gfx_list(argparse.Namespace()) == 0
    assert calls == [True]
    output = capsys.readouterr().out
    for value in ("alpha", "beta", "defined-loader", "0x08000200", "0x08000380", "left", "right",
                  "name confidence: likely", "name confidence: guess", "3 mapped reference(s)",
                  "affects 2 asset(s)"):
        assert value in output
    monkeypatch.setattr(rom, "EXPECTED_SHA1", "0" * 40)
    with pytest.raises(rom.RomError, match="does not match"):
        cli.cmd_gfx_list(argparse.Namespace())
    assert not capsys.readouterr().out


def test_export_and_import_cli_report_sharing(shared, tmp_path, capsys):
    image = tmp_path / "extracted/gfx/alpha.png"
    assert cli.cmd_gfx_export(argparse.Namespace(asset="alpha", out=image, force=False)) == 0
    output = capsys.readouterr().out
    assert "0x08000200" in output and "beta" in output
    assert "0x08000380" in output and "defined-loader" in output
    with Image.open(image) as png:
        changed = png.copy()
    changed.putpixel((5, 0), 6)
    changed.save(image)
    mod = tmp_path / "patches/from-cli/mod.toml"
    assert cli.cmd_gfx_import(argparse.Namespace(asset="alpha", png=image, out=mod,
                                                palette="original", force=False)) == 0
    output = capsys.readouterr().out
    assert "1 changed pixels, 0 changed colours" in output
    assert "0x08000200" in output and "beta" in output
    assert "sharing metadata" in output


def test_unknown_png_inference_message_is_generic(shared, tmp_path):
    with pytest.raises(gfx.GfxError, match="--asset <name> from hamtools gfx list") as error:
        gfx.infer_asset(tmp_path / "unknown.png")
    assert "boss" not in str(error.value).lower()


def _mock_catalogue(monkeypatch, loader):
    module = ModuleType("hamtools.portraits")
    module.load_catalogue = loader
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(hamtools, "portraits", module, raising=False)


def test_catalogue_records_map_to_asset_without_changing_positional_geometry(monkeypatch):
    portrait = SimpleNamespace(name="example", tiles_address=BASE + 0x100,
                               palette_address=BASE + 0x180, tile_references=(BASE + 0x21,),
                               palette_references=(BASE + 0x35,), slots=("left", "right"),
                               roots=("scene",), name_confidence="likely")
    calls = []
    _mock_catalogue(monkeypatch, lambda: calls.append(True) or {portrait.name: portrait})
    assets = gfx._catalogue_assets()
    assert calls == [True]
    assert assets == {"example": gfx.Asset("example", BASE + 0x100, BASE + 0x180,
                                          (BASE + 0x21,), (BASE + 0x35,),
                                          slots=("left", "right"), roots=("scene",), name_confidence="likely")}
    assert assets["example"].width == assets["example"].height == 48
    synthetic = gfx.Asset("small", BASE + 0x100, BASE + 0x180, (), (), 8, 16)
    assert (synthetic.width, synthetic.height) == (8, 16)


@pytest.mark.parametrize("error", [ValueError("malformed catalogue"), FileNotFoundError("missing catalogue CSV")])
def test_catalogue_errors_are_never_replaced_by_silent_fallback(monkeypatch, error):
    def load():
        raise error
    _mock_catalogue(monkeypatch, load)
    with pytest.raises(type(error), match=str(error)):
        gfx._catalogue_assets()


def test_installed_catalogue_import_errors_propagate(monkeypatch):
    original_import = builtins.__import__
    def broken_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 1 and "portraits" in fromlist:
            raise ImportError("catalogue dependency failed")
        return original_import(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, "__import__", broken_import)
    with pytest.raises(ImportError, match="catalogue dependency failed"):
        gfx._catalogue_assets()
