"""Export the graphics present in one mGBA GBA savestate.

The PNG's gbAs chunk freezes palettes, OAM and VRAM together. ROM matches
describe identical content, not proof that a particular loader executed.
All game data is written under extracted/gfx/. No ROM-specific bytes here.
"""

from __future__ import annotations

import hashlib
import json
import struct
import zlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from . import gfx_codec as codec, paths, rom
from .gfx import require_inside

STATE_SIZE = 0x61000
STATE_MAGIC = 0x0100000B
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
OBJ_SIZES = (
    ((8, 8), (16, 16), (32, 32), (64, 64)),
    ((16, 8), (32, 8), (32, 16), (64, 32)),
    ((8, 16), (8, 32), (16, 32), (32, 64)),
)
# Address-only room-head format documented in kb/portraits.md and kb/structs.md.
ROOM_HEAD_RECORDS = 0x08469CDC


@dataclass
class Snapshot:
    state: bytes
    screen: Image.Image | None = None

    @classmethod
    def load(cls, path: Path) -> Snapshot:
        data = path.read_bytes()
        screen = None
        if data.startswith(PNG_MAGIC):
            state = None
            pos = 8
            ended = False
            while pos + 12 <= len(data):
                length, tag = struct.unpack_from(">I4s", data, pos)
                end = pos + 12 + length
                if end > len(data):
                    raise codec.GfxError("truncated savestate PNG chunk")
                chunk = data[pos + 8:pos + 8 + length]
                crc = struct.unpack_from(">I", data, pos + 8 + length)[0]
                if zlib.crc32(tag + chunk) != crc:
                    raise codec.GfxError("invalid savestate PNG checksum")
                if tag == b"gbAs":
                    if state is not None:
                        raise codec.GfxError("duplicate gbAs savestate chunks")
                    inflater = zlib.decompressobj()
                    try:
                        state = inflater.decompress(chunk, STATE_SIZE + 1)
                    except zlib.error as exc:
                        raise codec.GfxError(f"invalid compressed savestate: {exc}") from exc
                    if not inflater.eof or inflater.unused_data or len(state) != STATE_SIZE:
                        raise codec.GfxError("invalid or oversized GBA savestate payload")
                pos = end
                if tag == b"IEND":
                    if length or pos != len(data):
                        raise codec.GfxError("invalid savestate PNG end")
                    ended = True
                    break
            if not ended or state is None:
                raise codec.GfxError("PNG has no complete mGBA gbAs savestate")
            with Image.open(BytesIO(data)) as image:
                if image.size != (240, 160):
                    raise codec.GfxError("expected a 240x160 GBA state screenshot")
                screen = image.convert("RGB")
            data = state
        if len(data) != STATE_SIZE or struct.unpack_from("<I", data)[0] != STATE_MAGIC:
            raise codec.GfxError("expected mGBA GBA savestate version 11 (0x61000 bytes)")
        if data[0x1C:0x20] != b"AH3E":
            raise codec.GfxError("savestate is not Hamtaro USA (AH3E)")
        return cls(data, screen)

    @property
    def io(self) -> bytes:
        return self.state[0x400:0x800]

    @property
    def palette(self) -> bytes:
        return self.state[0x800:0xC00]

    @property
    def oam(self) -> bytes:
        return self.state[0xC00:0x1000]

    @property
    def vram(self) -> bytes:
        return self.state[0x1000:0x19000]

    @property
    def ewram(self) -> bytes:
        return self.state[0x21000:0x61000]

    def reg(self, offset: int) -> int:
        return struct.unpack_from("<H", self.io, offset)[0]


def colours(raw: bytes) -> list[tuple[int, int, int]]:
    return [colour for offset in range(0, len(raw), 32)
            for colour in codec.palette_rgb(raw[offset:offset + 32])]


def indexed(indices: bytes, size: tuple[int, int], palette: bytes) -> Image.Image:
    image = Image.frombytes("P", size, indices)
    image.putpalette([channel for colour in colours(palette) for channel in colour])
    image.info["transparency"] = 0
    return image


def decode_tiles(raw: bytes, width: int, height: int, bpp: int) -> bytes:
    if bpp == 4:
        return codec.decode_tiles_4bpp(raw, width, height)
    if bpp != 8 or width % 8 or height % 8 or len(raw) != width * height:
        raise codec.GfxError("invalid 8bpp tile geometry")
    output = bytearray(width * height)
    pos = 0
    for ty in range(0, height, 8):
        for tx in range(0, width, 8):
            for row in range(8):
                start = (ty + row) * width + tx
                output[start:start + 8] = raw[pos + row * 8:pos + row * 8 + 8]
            pos += 64
    return bytes(output)


def encode_tiles(indices: bytes, width: int, height: int, bpp: int) -> bytes:
    if bpp == 4:
        return codec.encode_tiles_4bpp(indices, width, height)
    return b"".join(indices[(ty + row) * width + tx:(ty + row) * width + tx + 8]
                    for ty in range(0, height, 8) for tx in range(0, width, 8)
                    for row in range(8))


def sprite_tiles(vram: bytes, tile: int, width: int, height: int,
                 bpp: int, mapping_1d: bool) -> tuple[bytes, list[str]]:
    """Gather an OBJ's tiles, accounting for its 1D/2D row stride and wrap."""
    unit = 32 if bpp == 4 else 64
    base = (tile & ~1 if bpp == 8 and not mapping_1d else tile) * 32
    chunks, addresses = [], []
    storage = vram[0x10000:0x18000] + vram[0x10000:0x10040]
    for ty in range(height // 8):
        for tx in range(width // 8):
            if mapping_1d:
                offset = (base + (ty * (width // 8) + tx) * unit) & 0x7FFF
            else:
                offset = (ty * 0x400 + (base & 0x7C00)
                          + ((base + tx * unit) & 0x3FF)) & 0x7FFF
            chunks.append(storage[offset:offset + unit])
            addresses.append(f"{0x06010000 + offset:#010x}")
    return b"".join(chunks), addresses


def extract_sprites(snapshot: Snapshot) -> list[dict]:
    output = []
    dispcnt = snapshot.reg(0)
    if not dispcnt & 0x1000:
        return output
    for index in range(128):
        a, b, c = struct.unpack_from("<3H", snapshot.oam, index * 8)
        affine = bool(a & 0x100)
        if not affine and a & 0x200:
            continue
        shape = a >> 14
        if shape == 3:
            continue
        width, height = OBJ_SIZES[shape][b >> 14]
        x, y = b & 0x1FF, a & 0xFF
        x = x - 512 if x >= 256 else x
        y = y - 256 if y >= 160 else y
        footprint = 2 if affine and a & 0x200 else 1
        if x >= 240 or y >= 160 or x + width * footprint <= 0 or y + height * footprint <= 0:
            continue
        if dispcnt & 7 >= 3 and (c & 0x3FF) < 512:
            continue
        bpp, bank = (8 if a & 0x2000 else 4), c >> 12
        raw, addresses = sprite_tiles(snapshot.vram, c & 0x3FF, width, height,
                                      bpp, bool(dispcnt & 0x40))
        palette_offset = 0x200 + (bank * 32 if bpp == 4 else 0)
        palette = snapshot.palette[palette_offset:palette_offset + (32 if bpp == 4 else 512)]
        image = indexed(decode_tiles(raw, width, height, bpp), (width, height), palette)
        # The native PNG/raw stream retains source orientation; display.png applies flips.
        display = image.convert("RGBA")
        if not affine and b & 0x1000:
            display = display.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if not affine and b & 0x2000:
            display = display.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        bbox = image.getbbox()
        crop = None
        if bbox:
            left, top, right, bottom = bbox
            bbox = (left // 8 * 8, top // 8 * 8, (right + 7) // 8 * 8, (bottom + 7) // 8 * 8)
            crop = image.crop(bbox)
        output.append({
            "id": f"obj-{index:03d}", "oam_index": index,
            "oam_address": f"{0x07000000 + index * 8:#010x}",
            "attributes": [f"{v:#06x}" for v in (a, b, c)],
            "x": x, "y": y, "width": width, "height": height, "bpp": bpp,
            "tile_index": c & 0x3FF, "tile_addresses": addresses,
            "palette_bank": bank if bpp == 4 else None,
            "palette_address": f"{0x05000000 + palette_offset:#010x}",
            "priority": (c >> 10) & 3, "affine": affine, "obj_mode": (a >> 10) & 3,
            "mosaic": bool(a & 0x1000), "tile_crop_box": bbox,
            "raw": raw, "image": image, "display": display, "crop": crop,
        })
    return output


def extract_room_heads(data: bytes, snapshot: Snapshot, sprites: list[dict]) -> list[dict]:
    """Recover complete source frames before the 2D OBJ canvas adds padding."""
    heads = []
    for slot in range(4):
        offset = ROOM_HEAD_RECORDS - rom.ROM_BASE + slot * 0x11C
        buffer, destination = struct.unpack_from("<II", data, offset)
        width, height = data[offset + 0x118:offset + 0x11A]
        if not (0x02000000 <= buffer < 0x02040000 and 0x06010000 <= destination < 0x06018000
                and 1 <= width <= 8 and 1 <= height <= 8):
            continue
        raw = snapshot.ewram[buffer - 0x02000000:buffer - 0x02000000 + width * height * 32]
        uploaded = b"".join(snapshot.vram[destination - 0x06000000 + row * 0x400:
                                           destination - 0x06000000 + row * 0x400 + width * 32]
                             for row in range(height))
        consumers = [sprite for sprite in sprites if f"{destination:#010x}" in sprite["tile_addresses"]
                     and sprite["bpp"] == 4]
        banks = {sprite["palette_bank"] for sprite in consumers}
        if not consumers or len(banks) != 1 or raw != uploaded:
            continue
        bank = banks.pop()
        palette = snapshot.palette[0x200 + bank * 32:0x220 + bank * 32]
        heads.append({"id": f"room-head-slot-{slot}", "slot": slot,
                      "record_address": f"{ROOM_HEAD_RECORDS + slot * 0x11C:#010x}",
                      "buffer_address": f"{buffer:#010x}", "vram_row_address": f"{destination:#010x}",
                      "row_stride": 0x400, "width": width * 8, "height": height * 8,
                      "palette_bank": bank, "oam_consumers": [sprite["id"] for sprite in consumers],
                      "uploaded_rows_match": True, "raw": raw,
                      "image": indexed(codec.decode_tiles_4bpp(raw, width * 8, height * 8),
                                       (width * 8, height * 8), palette)})
    return heads


def extract_background(snapshot: Snapshot, index: int) -> dict:
    control = snapshot.reg(8 + index * 2)
    bpp = 8 if control & 0x80 else 4
    char_base, map_base = ((control >> 2) & 3) * 0x4000, ((control >> 8) & 31) * 0x800
    size = control >> 14
    width, height = (512 if size & 1 else 256), (512 if size & 2 else 256)
    map_bytes = snapshot.vram[map_base:map_base + width * height // 32]
    if len(map_bytes) != width * height // 32 or map_base + len(map_bytes) > 0x10000:
        raise codec.GfxError("background map runs outside supported BG VRAM")
    image = Image.new("RGBA", (width, height))
    cache, used = {}, set()
    for ty in range(height // 8):
        for tx in range(width // 8):
            block = (ty // 32) * (width // 256) + tx // 32
            word = struct.unpack_from("<H", map_bytes, block * 0x800 + ((ty % 32) * 32 + tx % 32) * 2)[0]
            tile, bank = word & 0x3FF, (word >> 12 if bpp == 4 else 0)
            used.add((tile, bank))
            if word not in cache:
                offset = char_base + tile * (32 if bpp == 4 else 64)
                if offset + (32 if bpp == 4 else 64) > 0x10000:
                    raise codec.GfxError("background tile runs outside supported BG VRAM")
                raw = snapshot.vram[offset:offset + (32 if bpp == 4 else 64)]
                palette = snapshot.palette[bank * 32:bank * 32 + 32] if bpp == 4 else snapshot.palette[:512]
                tile_image = indexed(decode_tiles(raw, 8, 8, bpp), (8, 8), palette).convert("RGBA")
                if word & 0x400:
                    tile_image = tile_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                if word & 0x800:
                    tile_image = tile_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                cache[word] = tile_image
            image.paste(cache[word], (tx * 8, ty * 8))
    scroll_x, scroll_y = snapshot.reg(0x10 + index * 4) & 511, snapshot.reg(0x12 + index * 4) & 511
    tiled = Image.new("RGBA", (width * 2, height * 2))
    for y in (0, height):
        for x in (0, width):
            tiled.paste(image, (x, y))
    sx, sy = scroll_x % width, scroll_y % height
    viewport = tiled.crop((sx, sy, sx + 240, sy + 160))
    count = max(tile for tile, _ in used) + 1
    unit = 32 if bpp == 4 else 64
    raw_tiles = snapshot.vram[char_base:char_base + count * unit]
    return {
        "id": f"bg{index}", "bg_index": index, "control": f"{control:#06x}",
        "priority": control & 3, "bpp": bpp, "width": width, "height": height,
        "scroll_x": scroll_x, "scroll_y": scroll_y,
        "tile_address": f"{0x06000000 + char_base:#010x}",
        "map_address": f"{0x06000000 + map_base:#010x}",
        "used_tiles": sorted({tile for tile, _ in used}),
        "palette_banks": sorted({bank for _, bank in used}),
        "mosaic": bool(control & 0x40), "image": image, "viewport": viewport,
        "map_raw": map_bytes, "raw": raw_tiles,
    }


def _public(record: dict) -> dict:
    return {key: value for key, value in record.items()
            if key not in {"raw", "image", "display", "crop", "viewport", "map_raw"}}


def _json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def match_rom(data: bytes, snapshot: Snapshot, targets: dict[str, bytes], out: Path) -> dict:
    """Search aligned BIOS LZ77 blocks and raw ROM; retain all exact candidates."""
    targets = {name: raw for name, raw in targets.items() if len(raw) >= 30 and len(set(raw)) >= 4}
    matches = {name: [] for name in targets}
    blocks = []
    for name, raw in targets.items():
        pos = data.find(raw)
        while pos >= 0:
            matches[name].append({"encoding": "raw", "address": f"{rom.ROM_BASE + pos:#010x}"})
            pos = data.find(raw, pos + 1)
    valid = 0
    for offset in range(0, len(data) - 4, 4):
        if data[offset] != 0x10:
            continue
        size = int.from_bytes(data[offset + 1:offset + 4], "little")
        if size < 32 or size > 0x18000 or size % 32:
            continue
        try:
            raw, consumed = codec.decompress_lz77(data, offset, 0x18000)
        except codec.GfxError:
            continue
        valid += 1
        if len(set(raw)) < 4:
            continue
        selected = []
        for name, target in targets.items():
            pos = raw.find(target)
            while pos >= 0:
                matches[name].append({"encoding": "lz77", "address": f"{rom.ROM_BASE + offset:#010x}",
                                      "decoded_offset": pos, "decoded_size": size,
                                      "compressed_size": consumed})
                selected.append(name)
                pos = raw.find(target, pos + 1)
        # Full blocks can identify room tiles/maps even when a sprite uses a subrectangle.
        memory_matches = []
        if len(raw) >= 256:
            for region, base, memory in (("vram", 0x06000000, snapshot.vram),
                                         ("ewram", 0x02000000, snapshot.ewram)):
                pos = memory.find(raw)
                if pos >= 0:
                    memory_matches.append({"region": region, "address": f"{base + pos:#010x}"})
        if selected or memory_matches:
            name = f"{rom.ROM_BASE + offset:#010x}"
            (out / f"{name}.lz").write_bytes(data[offset:offset + consumed])
            (out / f"{name}.bin").write_bytes(raw)
            blocks.append({"address": name, "decoded_size": size, "compressed_size": consumed,
                           "sha1": hashlib.sha1(raw).hexdigest(), "targets": sorted(set(selected)),
                           "memory_matches": memory_matches})
    return {"confidence": "likely: exact content matches; loader execution not observed",
            "coverage": "raw exact matches and 4-byte-aligned type-0x10 headers; decoded sizes 32..0x18000 in multiples of 32",
            "valid_lz77_blocks": valid, "matches": matches, "blocks": blocks}


def export_screen(data: bytes, snapshot: Snapshot, out: Path, *, scan_rom: bool = True,
                  force: bool = False) -> dict:
    if len(data) != rom.EXPECTED_SIZE or rom.sha1(data) != rom.EXPECTED_SHA1:
        raise codec.GfxError("original ROM does not match expected AH3E SHA1")
    out = require_inside(out, paths.EXTRACTED_DIR / "gfx", "screen graphics output")
    if (out / "manifest.json").exists() and not force:
        raise codec.GfxError("screen export already exists; use --force or choose a new directory")
    for directory in ("raw", "palettes", "sprites", "room-heads", "backgrounds", "rom"):
        (out / directory).mkdir(parents=True, exist_ok=True)
    warnings = []
    state_crc = struct.unpack_from("<I", snapshot.state, 8)[0]
    if state_crc != zlib.crc32(data):
        warnings.append("Savestate ROM CRC differs from the original; graphics describe this snapshot and ROM matches are candidates only.")
    for name in ("io", "palette", "oam", "vram"):
        (out / "raw" / f"{name}.bin").write_bytes(getattr(snapshot, name))
    if snapshot.screen:
        snapshot.screen.save(out / "screen.png")
    targets, palettes = {}, []
    swatches = Image.new("RGB", (440, 32 * 22 + 26), (26, 29, 36))
    draw = ImageDraw.Draw(swatches)
    draw.text((8, 6), "BG / OBJ palettes; index 0 is transparent in tile images", fill="white")
    for i in range(32):
        kind, bank = ("bg" if i < 16 else "obj"), i % 16
        name, raw = f"{kind}-{bank:02d}", snapshot.palette[i * 32:i * 32 + 32]
        palette = colours(raw)
        y = 26 + i * 22
        draw.text((8, y + 3), name.upper(), fill="white")
        for index, colour in enumerate(palette):
            draw.rectangle((72 + index * 22, y, 92 + index * 22, y + 19), fill=colour)
        strip = Image.new("RGB", (16 * 16, 16))
        for index, colour in enumerate(palette):
            strip.paste(colour, (index * 16, 0, index * 16 + 16, 16))
        strip.save(out / "palettes" / f"{name}.png")
        (out / "palettes" / f"{name}.pal").write_bytes(raw)
        entry = {"id": name, "address": f"{0x05000000 + i * 32:#010x}",
                 "bgr555": list(struct.unpack("<16H", raw)), "rgb": palette}
        palettes.append(entry)
        _json(out / "palettes" / f"{name}.json", entry)
        targets[f"palette:{name}"] = raw
        # Games sometimes overwrite the transparent colour during upload/fades.
        targets[f"palette-opaque:{name}"] = raw[2:]
    swatches.save(out / "palettes.png")
    sprites = extract_sprites(snapshot)
    for sprite in sprites:
        name = sprite["id"]
        sprite["image"].save(out / "sprites" / f"{name}.png", transparency=0)
        sprite["display"].save(out / "sprites" / f"{name}-display.png")
        (out / "sprites" / f"{name}.{sprite['bpp']}bpp").write_bytes(sprite["raw"])
        targets[f"sprite:{name}"] = sprite["raw"]
        if sprite["crop"]:
            crop = sprite["crop"]
            crop.save(out / "sprites" / f"{name}-crop.png", transparency=0)
            targets[f"sprite-crop:{name}"] = encode_tiles(crop.tobytes(), *crop.size, sprite["bpp"])
        _json(out / "sprites" / f"{name}.json", _public(sprite))
        if sprite["affine"] or sprite["obj_mode"] or sprite["mosaic"]:
            warnings.append(f"{name}: source pixels exported; affine/blending/OBJ-window/mosaic effects are not applied.")
    room_heads = extract_room_heads(data, snapshot, sprites)
    for head in room_heads:
        name = head["id"]
        head["image"].save(out / "room-heads" / f"{name}.png", transparency=0)
        (out / "room-heads" / f"{name}.4bpp").write_bytes(head["raw"])
        _json(out / "room-heads" / f"{name}.json", _public(head))
        targets[f"room-head:{name}"] = head["raw"]
    backgrounds = []
    mode = snapshot.reg(0) & 7
    supported = range(4) if mode == 0 else range(2) if mode == 1 else ()
    for index in range(4):
        if not snapshot.reg(0) & (0x100 << index):
            continue
        if index not in supported:
            warnings.append(f"BG{index}: affine/bitmap layer unsupported in display mode {mode}; raw VRAM retained.")
            continue
        bg = extract_background(snapshot, index)
        backgrounds.append(bg)
        name = bg["id"]
        bg["image"].save(out / "backgrounds" / f"{name}-map.png")
        bg["viewport"].save(out / "backgrounds" / f"{name}-viewport.png")
        (out / "backgrounds" / f"{name}-tilemap.bin").write_bytes(bg["map_raw"])
        (out / "backgrounds" / f"{name}-tiles.{bg['bpp']}bpp").write_bytes(bg["raw"])
        targets[f"background-map:{name}"] = bg["map_raw"]
        targets[f"background-tiles:{name}"] = bg["raw"]
        unit, count = (32 if bg["bpp"] == 4 else 64), len(bg["raw"]) // (32 if bg["bpp"] == 4 else 64)
        rows = (count + 15) // 16
        atlas = bg["raw"] + bytes(rows * 16 * unit - len(bg["raw"]))
        for bank in bg["palette_banks"]:
            palette = snapshot.palette[bank * 32:bank * 32 + 32] if bg["bpp"] == 4 else snapshot.palette[:512]
            indexed(decode_tiles(atlas, 128, rows * 8, bg["bpp"]), (128, rows * 8), palette).save(
                out / "backgrounds" / f"{name}-tiles-palette-{bank:02d}.png", transparency=0)
        _json(out / "backgrounds" / f"{name}.json", _public(bg))
    composite = Image.new("RGBA", (240, 160), colours(snapshot.palette[:32])[0] + (255,))
    for priority in range(3, -1, -1):
        for bg in reversed(backgrounds):
            if bg["priority"] == priority:
                composite.alpha_composite(bg["viewport"])
        for sprite in reversed(sprites):
            if sprite["priority"] == priority and not sprite["affine"] and sprite["obj_mode"] != 2:
                composite.alpha_composite(sprite["display"], (sprite["x"], sprite["y"]))
    composite.convert("RGB").save(out / "reconstructed-screen.png")
    if snapshot.reg(0) & 0xE000 or snapshot.reg(0x50) & 0xC0 or any(bg["mosaic"] for bg in backgrounds):
        warnings.append("Reconstruction omits display windows, blending and mosaic. Native images/raw data remain lossless.")
    comparison = None
    if snapshot.screen:
        reference = list(snapshot.screen.getdata())
        rebuilt = list(composite.convert("RGB").getdata())
        comparison = {"pixels": 240 * 160, "different_pixels": sum(a != b for a, b in zip(reference, rebuilt)),
                      "reference": "embedded savestate screenshot; may precede the saved memory by a frame"}
    sources = match_rom(data, snapshot, targets, out / "rom") if scan_rom else None
    if sources:
        _json(out / "rom-sources.json", sources)
    manifest = {
        "format": "hamtools-screen-gfx-v1", "rom_sha1": rom.sha1(data),
        "state_rom_crc32": f"{state_crc:#010x}", "original_rom_crc32": f"{zlib.crc32(data):#010x}",
        "frame": struct.unpack_from("<I", snapshot.state, 0x1FC)[0],
        "display_control": f"{snapshot.reg(0):#06x}",
        "obj_mapping": "1d" if snapshot.reg(0) & 0x40 else "2d",
        "palettes": palettes, "sprites": [_public(s) for s in sprites],
        "room_heads": [_public(head) for head in room_heads],
        "backgrounds": [_public(bg) for bg in backgrounds], "comparison": comparison,
        "warnings": warnings,
        "raw_sha1": {name: hashlib.sha1(getattr(snapshot, name)).hexdigest()
                     for name in ("io", "palette", "oam", "vram")},
    }
    _json(out / "manifest.json", manifest)
    _overview(out, snapshot, sprites, backgrounds, swatches)
    return manifest


def _overview(out: Path, snapshot: Snapshot, sprites: list[dict],
              backgrounds: list[dict], swatches: Image.Image) -> None:
    columns, cell_width, cell_height = 5, 150, 180
    rows = (len(sprites) + columns - 1) // columns
    sheet = Image.new("RGB", (970, max(760, 350 + rows * cell_height)), (26, 29, 36))
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 14), "Hamtaro screen graphics: sprites, backgrounds and palettes", fill="white")
    if snapshot.screen:
        sheet.paste(snapshot.screen.resize((480, 320), Image.Resampling.NEAREST), (18, 38))
    for n, bg in enumerate(backgrounds):
        draw.text((518 + n * 225, 38), f"{bg['id'].upper()} viewport", fill="white")
        preview = Image.new("RGBA", (240, 160), (70, 73, 80, 255))
        preview.alpha_composite(bg["viewport"])
        sheet.paste(preview.convert("RGB").resize((216, 144), Image.Resampling.NEAREST), (518 + n * 225, 58))
    for n, sprite in enumerate(sprites):
        x, y = 18 + n % columns * cell_width, 380 + n // columns * cell_height
        draw.text((x, y), f"{sprite['id']} / pal {sprite['palette_bank']}", fill="white")
        draw.text((x, y + 14), f"{sprite['width']}x{sprite['height']} @ {sprite['x']},{sprite['y']}", fill=(170, 183, 201))
        display = sprite["display"]
        scale = min(3, 132 // max(display.size))
        display = display.resize((display.width * scale, display.height * scale), Image.Resampling.NEAREST)
        sheet.paste(display, (x, y + 34), display)
    draw.text((768, 380), "All palette banks", fill="white")
    sheet.paste(swatches.resize((196, 325), Image.Resampling.NEAREST), (768, 402))
    sheet.save(out / "overview.png")
