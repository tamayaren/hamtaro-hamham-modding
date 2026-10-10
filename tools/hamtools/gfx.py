"""Portrait export and source-only image deltas; game pixels stay in extracted/.

The portrait catalogue supplies dialogue-window assets and every mapped loader.
Shared streams are edited together; room-sprite animation tiles are separate.
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
    slots: tuple[str, ...] = ()
    roots: tuple[str, ...] = ()
    name_confidence: str = "guess"


def _catalogue_assets() -> dict[str, Asset]:
    from . import portraits
    return {
        key: Asset(portrait.name, portrait.tiles_address, portrait.palette_address,
                   portrait.tile_references, portrait.palette_references,
                   slots=portrait.slots, roots=portrait.roots,
                   name_confidence=portrait.name_confidence)
        for key, portrait in portraits.load_catalogue().items()
    }


ASSETS = _catalogue_assets()


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
    if not ASSETS:
        raise GfxError("portrait catalogue is unavailable or empty; install the portraits module and catalogue")
    try:
        return ASSETS[name]
    except KeyError:
        raise GfxError(f"unknown graphics asset {name!r}; supported: {', '.join(ASSETS)}") from None


def source_assets(address: int) -> tuple[Asset, ...]:
    """All defined uses, including other slots and loaders outside walked roots."""
    return tuple(sorted((asset for asset in ASSETS.values()
                         if address in (asset.tiles_address, asset.palette_address)),
                        key=lambda asset: asset.name))


def source_references(address: int) -> tuple[int, ...]:
    references = set()
    for asset in source_assets(address):
        if asset.tiles_address == address:
            references.update(asset.tile_references)
        if asset.palette_address == address:
            references.update(asset.palette_references)
    return tuple(sorted(references))


def asset_metadata(name: str) -> dict:
    asset = get_asset(name)
    sharing = {}
    for kind, address in (("tiles", asset.tiles_address), ("palette", asset.palette_address)):
        uses = source_assets(address)
        references = source_references(address)
        sharing[kind] = {
            "source_address": f"{address:#010x}",
            "affected_assets": [use.name for use in uses],
            "affected_asset_count": len(uses),
            "reference_count": len(references),
            "references": [f"{ref:#010x}" for ref in references],
            "uses": [{"asset": use.name, "slots": list(use.slots), "roots": list(use.roots),
                      "name_confidence": use.name_confidence,
                      "streams": [stream for stream, source in
                                  (("tiles", use.tiles_address), ("palette", use.palette_address))
                                  if source == address]}
                     for use in uses],
        }
    return {
        "asset": name, "width": asset.width, "height": asset.height,
        "tiles_address": f"{asset.tiles_address:#010x}",
        "palette_address": f"{asset.palette_address:#010x}",
        "tile_references": [f"{ref:#010x}" for ref in asset.tile_references],
        "palette_references": [f"{ref:#010x}" for ref in asset.palette_references],
        "slots": list(asset.slots), "roots": list(asset.roots), "name_confidence": asset.name_confidence,
        "sharing": sharing,
    }


def describe_sharing(name: str, kind: str) -> str:
    asset = get_asset(name)
    address = {"tiles": asset.tiles_address, "palette": asset.palette_address}[kind]
    assets = source_assets(address)
    uses = "; ".join(f"{use.name} (slots: {', '.join(use.slots) or 'unspecified'}; "
                     f"name confidence: {use.name_confidence})" for use in assets)
    return (f"{kind} {address:#010x}: {len(source_references(address))} mapped reference(s); "
            f"affects {len(assets)} asset(s): {uses}")


def _checked_references(data: bytes, name: str, address: int) -> tuple[int, ...]:
    references = source_references(address)
    for reference in references:
        off = reference - rom.ROM_BASE
        if not 0 <= off <= len(data) - 4 or data[off:off + 4] != address.to_bytes(4, "little"):
            raise GfxError(f"{name}: original pointer mismatch at {reference:#010x} "
                           f"for shared source {address:#010x}")
    return references


def _changed_references(data: bytes, name: str, kind: str, address: int) -> tuple[int, ...]:
    references = _checked_references(data, name, address)
    # GBA cartridge wait-state windows mirror the same 32 MB ROM address space.
    # Search every byte, since event operands can be unaligned. An unclassified
    # exact occurrence is conservatively unsafe even if it might be literal data.
    occurrences = set()
    for target in (address, address + 0x02000000, address + 0x04000000):
        pattern = target.to_bytes(4, "little")
        offset = data.find(pattern)
        while offset != -1:
            occurrences.add(rom.ROM_BASE + offset)
            offset = data.find(pattern, offset + 1)
    unknown = sorted(occurrences - set(references))
    affected = ", ".join(asset.name for asset in source_assets(address))
    if unknown:
        locations = ", ".join(f"{ref:#010x}" for ref in unknown[:8])
        if len(unknown) > 8:
            locations += ", ..."
        raise GfxError(f"{name}: changed {kind} source {address:#010x} has "
                       f"{len(unknown)} unmapped pointer occurrence(s) at {locations}; "
                       f"affected entries: {affected}. Map every reference before relocation")
    if not references:
        raise GfxError(f"{name}: changed {kind} source {address:#010x} has no mapped references; "
                       f"affected entries: {affected}; cannot relocate")
    return references


def read_asset(data: bytes, name: str) -> AssetData:
    asset = get_asset(name)
    blocks = []
    for address, size in (
        (asset.tiles_address, asset.width * asset.height // 2),
        (asset.palette_address, 32),
    ):
        offset = address - rom.ROM_BASE
        if not 0 <= offset < len(data):
            raise GfxError(f"{name}: source {address:#010x} is outside the ROM")
        raw, consumed = codec.decompress_lz77(data, offset)
        if len(raw) != size:
            raise GfxError(f"{name}: {address:#010x} expands to {len(raw)} bytes; expected {size}")
        _checked_references(data, name, address)
        blocks.append((raw, data[offset:offset + consumed]))
    return AssetData(asset, blocks[0][0], blocks[1][0], blocks[0][1], blocks[1][1])


def export_asset(data: bytes, name: str, path: Path) -> AssetData:
    _protect_original(path)
    _protect_original(path.with_suffix(".json"))
    source = read_asset(data, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    codec.export_png(source.tiles, source.palette, source.asset.width, source.asset.height, path)
    sidecar = {
        **asset_metadata(name), "schema": 1,
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
    raise GfxError("cannot identify the PNG; specify --asset <name> from hamtools gfx list")


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
    for kind, address, old_raw, new_raw, old_compressed in (
        ("tiles", source.asset.tiles_address, source.tiles, raw, source.compressed_tiles),
        ("palette", source.asset.palette_address, source.palette, bytes(palette), source.compressed_palette),
    ):
        if old_raw != new_raw:
            refs = _changed_references(data, source.asset.name, kind, address)
            replacements.append(Replacement(kind, address, old_compressed, codec.compress_lz77(new_raw), refs))
    return tuple(replacements)


def format_mod(entry: dict, name: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", name) is None:
        raise GfxError("mod name must use 1..80 letters, digits, '-' or '_'")
    lines = [f"name = {json.dumps(name)}", 'description = "Authored dialogue portrait image/palette edits."',
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
    replacements = prepare_entry(data, entry)
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
    metadata = {
        **asset_metadata(name), "schema": 1, "rom_sha1": rom.sha1(data),
        "tiles_sha1": entry["expect_tiles_sha1"], "palette_sha1": entry["expect_palette_sha1"],
        "imported_tiles_sha1": rom.sha1(changed.compressed_tiles),
        "imported_palette_sha1": rom.sha1(changed.compressed_palette),
        "changed_pixels": len(entry["pixels"]), "changed_colors": len(entry["colors"]),
        "changed_streams": [replacement.kind for replacement in replacements],
    }
    sidecar = require_inside(local / f"{name}.json", paths.EXTRACTED_DIR / "gfx", "import metadata")
    sidecar.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return len(entry["pixels"]), len(entry["colors"])
