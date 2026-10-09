"""Portrait export and source-only image deltas; game pixels stay in extracted/.

The first supported asset is Boss's dialogue-window portrait. The similarly
named Entity animation tiles in kb/portraits.md are a separate room sprite.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import gfx_codec as codec, paths, rom

GfxError = codec.GfxError


@dataclass(frozen=True)
class Asset:
    name: str
    tiles_address: int
    palette_address: int
    tile_references: tuple[int, ...]
    palette_references: tuple[int, ...]
    width: int = 48
    height: int = 48


ASSETS = {
    "boss-portrait": Asset(
        "boss-portrait", 0x080eb9bc, 0x080f437c,
        (0x084b1dc5, 0x084b1dd8), (0x084b1dbc, 0x084b1dcf)),
}


@dataclass(frozen=True)
class AssetData:
    asset: Asset
    tiles: bytes
    palette: bytes
    compressed_tiles: bytes
    compressed_palette: bytes


@dataclass(frozen=True)
class Replacement:
    kind: str
    source_address: int
    original: bytes
    data: bytes
    references: tuple[int, ...]


def get_asset(name: str) -> Asset:
    try:
        return ASSETS[name]
    except KeyError:
        raise GfxError(f"unknown graphics asset {name!r}; supported: {', '.join(ASSETS)}") from None


def read_asset(data: bytes, name: str) -> AssetData:
    asset = get_asset(name)
    blocks = []
    for address, references, size in (
        (asset.tiles_address, asset.tile_references, asset.width * asset.height // 2),
        (asset.palette_address, asset.palette_references, 32),
    ):
        offset = address - rom.ROM_BASE
        if not 0 <= offset < len(data):
            raise GfxError(f"{name}: source {address:#010x} is outside the ROM")
        raw, consumed = codec.decompress_lz77(data, offset)
        if len(raw) != size:
            raise GfxError(f"{name}: {address:#010x} expands to {len(raw)} bytes; expected {size}")
        for reference in references:
            off = reference - rom.ROM_BASE
            if not 0 <= off <= len(data) - 4 or data[off:off + 4] != address.to_bytes(4, "little"):
                raise GfxError(f"{name}: original pointer mismatch at {reference:#010x}")
        blocks.append((raw, data[offset:offset + consumed]))
    return AssetData(asset, blocks[0][0], blocks[1][0], blocks[0][1], blocks[1][1])


def export_asset(data: bytes, name: str, path: Path) -> AssetData:
    _protect_original(path)
    _protect_original(path.with_suffix(".json"))
    source = read_asset(data, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    codec.export_png(source.tiles, source.palette, source.asset.width, source.asset.height, path)
    sidecar = {
        "schema": 1, "asset": name, "width": source.asset.width, "height": source.asset.height,
        "rom_sha1": rom.sha1(data),
        "tiles_sha1": rom.sha1(source.compressed_tiles),
        "palette_sha1": rom.sha1(source.compressed_palette),
    }
    path.with_suffix(".json").write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
    return source


def infer_asset(path: Path) -> str:
    sidecar = path.with_suffix(".json")
    if sidecar.is_file():
        try:
            name = json.loads(sidecar.read_text(encoding="utf-8"))["asset"]
            get_asset(name)
            return name
        except (ValueError, KeyError, TypeError) as exc:
            raise GfxError(f"invalid asset sidecar {sidecar}: {exc}") from exc
    if path.stem in ASSETS:
        return path.stem
    raise GfxError("cannot identify the PNG; specify --asset boss-portrait")


def import_image(data: bytes, name: str, path: Path, palette_mode: str = "original") -> tuple[dict, AssetData]:
    source = read_asset(data, name)
    raw, palette = codec.import_png(path, source.tiles, source.palette,
                                    source.asset.width, source.asset.height, palette_mode)
    old_indices = codec.decode_tiles_4bpp(source.tiles, source.asset.width, source.asset.height)
    indices = codec.decode_tiles_4bpp(raw, source.asset.width, source.asset.height)
    # A public mod contains authored differences and hashes, never a full image,
    # copied palette, compressed blob, or a reference to an uncommitted PNG.
    entry = {
        "asset": name,
        "expect_tiles_sha1": rom.sha1(source.compressed_tiles),
        "expect_palette_sha1": rom.sha1(source.compressed_palette),
        "pixels": [{"offset": i, "index": b} for i, (a, b) in enumerate(zip(old_indices, indices)) if a != b],
        "colors": [{"index": i, "bgr555": int.from_bytes(palette[i * 2:i * 2 + 2], "little")}
                   for i in range(16) if palette[i * 2:i * 2 + 2] != source.palette[i * 2:i * 2 + 2]],
    }
    changed = AssetData(source.asset, raw, palette,
                        source.compressed_tiles if raw == source.tiles else codec.compress_lz77(raw),
                        source.compressed_palette if palette == source.palette else codec.compress_lz77(palette))
    return entry, changed


def _checked_int(value, minimum: int, maximum: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise GfxError(f"{label} must be an integer in {minimum}..{maximum}")
    return value


def prepare_entry(data: bytes, entry: dict) -> tuple[Replacement, ...]:
    if not isinstance(entry.get("asset"), str):
        raise GfxError("graphics entry requires an 'asset' name")
    source = read_asset(data, entry["asset"])
    for key, original in (("expect_tiles_sha1", source.compressed_tiles),
                          ("expect_palette_sha1", source.compressed_palette)):
        digest = entry.get(key)
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-fA-F]{40}", digest) is None:
            raise GfxError(f"{source.asset.name}: {key} (original compressed stream SHA1) is required")
        if rom.sha1(original) != digest.lower():
            raise GfxError(f"{source.asset.name}: {key} mismatch")
    unknown = set(entry) - {"asset", "expect_tiles_sha1", "expect_palette_sha1", "pixels", "colors"}
    if unknown:
        raise GfxError(f"unsupported graphics fields: {', '.join(sorted(unknown))}")
    indices = bytearray(codec.decode_tiles_4bpp(source.tiles, source.asset.width, source.asset.height))
    palette = bytearray(source.palette)
    for field, destination in (("pixels", indices), ("colors", palette)):
        entries = entry.get(field, [])
        if not isinstance(entries, list):
            raise GfxError(f"{field} must be a list of authored differences")
        selected: set[int] = set()
        for item in entries:
            if not isinstance(item, dict):
                raise GfxError(f"invalid {field} difference")
            if field == "pixels":
                if set(item) != {"offset", "index"}:
                    raise GfxError("pixel differences require only 'offset' and 'index'")
                offset = _checked_int(item.get("offset"), 0, len(indices) - 1, "pixel offset")
                value = _checked_int(item.get("index"), 0, 15, "pixel palette index")
                destination[offset] = value
            else:
                if set(item) != {"index", "bgr555"}:
                    raise GfxError("colour differences require only 'index' and 'bgr555'")
                offset = _checked_int(item.get("index"), 0, 15, "colour index")
                value = _checked_int(item.get("bgr555"), 0, 0x7fff, "BGR555 colour")
                destination[offset * 2:offset * 2 + 2] = value.to_bytes(2, "little")
            if offset in selected:
                raise GfxError(f"duplicate {field} difference at {offset}")
            selected.add(offset)
    raw = codec.encode_tiles_4bpp(bytes(indices), source.asset.width, source.asset.height)
    replacements = []
    for kind, address, old_raw, new_raw, old_compressed, refs in (
        ("tiles", source.asset.tiles_address, source.tiles, raw, source.compressed_tiles, source.asset.tile_references),
        ("palette", source.asset.palette_address, source.palette, bytes(palette),
         source.compressed_palette, source.asset.palette_references),
    ):
        if old_raw != new_raw:
            replacements.append(Replacement(kind, address, old_compressed, codec.compress_lz77(new_raw), refs))
    return tuple(replacements)


def format_mod(entry: dict, name: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", name) is None:
        raise GfxError("mod name must use 1..80 letters, digits, '-' or '_'")
    lines = [f"name = {json.dumps(name)}", 'description = "Authored Boss dialogue portrait image/palette edits."',
             "enabled = false", "", "# Generated changed-only graphics recipe. No game image or original bytes are embedded.",
             "# The builder reconstructs it from your verified original ROM, then allocates and repoints.",
             "[[gfx]]"]
    for key in ("asset", "expect_tiles_sha1", "expect_palette_sha1"):
        lines.append(f"{key} = {json.dumps(entry[key])}")
    for key, a, b in (("colors", "index", "bgr555"), ("pixels", "offset", "index")):
        if entry[key]:
            lines.append(f"{key} = [")
            for item in entry[key]:
                value = f"0x{item[b]:04x}" if b == "bgr555" else str(item[b])
                lines.append(f"  {{ {a} = {item[a]}, {b} = {value} }},")
            lines.append("]")
    return "\n".join(lines) + "\n"


def require_inside(path: Path, root: Path, label: str) -> Path:
    resolved, base = path.resolve(), root.resolve()
    if not resolved.is_relative_to(base):
        raise GfxError(f"{label} must be under {base}")
    if resolved.exists() and resolved.stat().st_nlink > 1:
        raise GfxError(f"{label} must not be a hard-linked file")
    _protect_original(resolved)
    return resolved


def _protect_original(path: Path) -> None:
    # HAMTARO_ROM may point anywhere, even inside an otherwise permitted output
    # directory. Location restrictions alone do not protect an overridden ROM.
    try:
        source = rom.rom_path().resolve()
    except rom.RomError:
        return
    destination = path.resolve()
    if (destination == source
            or (destination.exists() and source.exists() and destination.samefile(source))):
        raise GfxError("graphics output would overwrite the original ROM")


def write_import(data: bytes, name: str, image: Path, mod_path: Path,
                 palette_mode: str = "original", force: bool = False) -> tuple[int, int]:
    mod_path = require_inside(mod_path, paths.REPO_ROOT / "patches", "mod output")
    entry, changed = import_image(data, name, image, palette_mode)
    body = format_mod(entry, mod_path.parent.name)
    if mod_path.exists() and not force:
        raise GfxError(f"output already exists: {mod_path}; use --force to replace it")
    mod_path.parent.mkdir(parents=True, exist_ok=True)
    with mod_path.open("w" if force else "x", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
    # Derived binaries are useful for inspecting roundtrips, but never patch inputs.
    local = require_inside(paths.EXTRACTED_DIR / "gfx" / "imports" / mod_path.parent.name,
                           paths.EXTRACTED_DIR / "gfx", "compressed export directory")
    local.mkdir(parents=True, exist_ok=True)
    for kind, compressed in (("tiles", changed.compressed_tiles), ("palette", changed.compressed_palette)):
        destination = require_inside(local / f"{name}.{kind}.lz", paths.EXTRACTED_DIR / "gfx", "compressed export")
        destination.write_bytes(compressed)
    return len(entry["pixels"]), len(entry["colors"])
