"""Synthetic graphics tests: no copyrighted game bytes or emulator dependency."""

import struct
import zlib

import pytest
from PIL import Image

from hamtools import gfx_codec as codec, screen_gfx as screen


def snapshot():
    raw = bytearray(screen.STATE_SIZE)
    struct.pack_into("<I", raw, 0, screen.STATE_MAGIC)
    raw[0x1C:0x20] = b"AH3E"
    for i in range(128):
        struct.pack_into("<H", raw, 0xC00 + i * 8, 0x200)
    # Four distinguishable colours; tile transparency uses index zero.
    struct.pack_into("<4H", raw, 0x800, 0, 0x001F, 0x03E0, 0x7C00)
    struct.pack_into("<4H", raw, 0xA00, 0, 0x001F, 0x03E0, 0x7C00)
    return raw


def test_state_raw_validation(tmp_path):
    path = tmp_path / "state.ss0"
    raw = snapshot()
    path.write_bytes(raw)
    assert len(screen.Snapshot.load(path).vram) == 0x18000
    raw[0x1C:0x20] = b"NOPE"
    path.write_bytes(raw)
    with pytest.raises(codec.GfxError, match="AH3E"):
        screen.Snapshot.load(path)


def png_chunk(tag, raw):
    return struct.pack(">I", len(raw)) + tag + raw + struct.pack(">I", zlib.crc32(tag + raw))


def test_png_state_frozen_memory_and_crc(tmp_path):
    path = tmp_path / "state.ss0"
    Image.new("RGB", (240, 160), "red").save(path, format="PNG")
    data = path.read_bytes()
    chunk = png_chunk(b"gbAs", zlib.compress(snapshot()))
    path.write_bytes(data[:-12] + chunk + data[-12:])
    state = screen.Snapshot.load(path)
    assert state.screen.getpixel((1, 1)) == (255, 0, 0)
    assert state.reg(0) == 0
    damaged = bytearray(path.read_bytes())
    damaged[-13] ^= 1  # Last gbAs CRC byte.
    path.write_bytes(damaged)
    with pytest.raises(codec.GfxError, match="checksum"):
        screen.Snapshot.load(path)


def test_png_state_rejects_oversized_inflation(tmp_path):
    path = tmp_path / "state.ss0"
    Image.new("RGB", (240, 160)).save(path, format="PNG")
    data = path.read_bytes()
    path.write_bytes(data[:-12] + png_chunk(b"gbAs", zlib.compress(bytes(screen.STATE_SIZE + 1))) + data[-12:])
    with pytest.raises(codec.GfxError, match="oversized"):
        screen.Snapshot.load(path)


@pytest.mark.parametrize("mapping_1d,second_row", [(False, 32), (True, 2)])
def test_obj_row_stride(mapping_1d, second_row):
    vram = bytearray(0x18000)
    for tile in range(64):
        vram[0x10000 + tile * 32:0x10000 + (tile + 1) * 32] = bytes([tile]) * 32
    raw, addresses = screen.sprite_tiles(vram, 0, 16, 16, 4, mapping_1d)
    assert [raw[i * 32] for i in range(4)] == [0, 1, second_row, second_row + 1]
    assert addresses[2] == f"{0x06010000 + second_row * 32:#010x}"


def test_obj_2d_eight_bit_alignment_and_row_wrap():
    vram = bytes(0x18000)
    _, addresses = screen.sprite_tiles(vram, 31, 16, 8, 8, False)
    assert addresses == ["0x060103c0", "0x06010000"]


def test_obj_eight_bit_1d_wrap_at_end_of_vram():
    vram = bytearray(0x18000)
    vram[0x17FE0:] = bytes([1]) * 32
    vram[0x10000:0x10020] = bytes([2]) * 32
    raw, _ = screen.sprite_tiles(vram, 1023, 8, 8, 8, True)
    assert raw == bytes([1]) * 32 + bytes([2]) * 32


def test_sprite_visibility_native_orientation_and_display_flip():
    raw = snapshot()
    struct.pack_into("<H", raw, 0x400, 0x1000)
    struct.pack_into("<3H", raw, 0xC00, 5, 0x1000 | 7, 0)
    raw[0x11000] = 0x21
    sprites = screen.extract_sprites(screen.Snapshot(bytes(raw)))
    assert len(sprites) == 1
    sprite = sprites[0]
    assert sprite["image"].getpixel((0, 0)) == 1
    assert sprite["display"].getpixel((7, 0)) == (255, 0, 0, 255)
    assert sprite["display"].getpixel((0, 0))[3] == 0
    struct.pack_into("<H", raw, 0xC02, 240)
    assert not screen.extract_sprites(screen.Snapshot(bytes(raw)))


def test_text_background_screen_blocks_flips_and_scroll_wrap():
    raw = snapshot()
    # BG1: 512x512, char block 0, screen blocks 16..19, 4bpp.
    struct.pack_into("<H", raw, 0x40A, 0xD000)
    # Native tile 1 has red at left, green at right.
    raw[0x1000 + 32] = 1
    raw[0x1000 + 35] = 0x20
    for block in range(4):
        struct.pack_into("<H", raw, 0x1000 + 0x8000 + block * 0x800, 1 | (0x400 if block == 1 else 0))
    struct.pack_into("<2H", raw, 0x414, 511, 511)
    bg = screen.extract_background(screen.Snapshot(bytes(raw)), 1)
    assert bg["image"].getpixel((0, 0)) == (255, 0, 0, 255)
    assert bg["image"].getpixel((256, 0)) == (0, 255, 0, 255)
    assert bg["image"].getpixel((0, 256)) == (255, 0, 0, 255)
    assert bg["image"].getpixel((256, 256)) == (255, 0, 0, 255)
    assert bg["viewport"].getpixel((1, 1)) == (255, 0, 0, 255)


def test_eight_bit_tile_layout():
    raw = bytes([1] * 64 + [2] * 64 + [3] * 64 + [4] * 64)
    pixels = screen.decode_tiles(raw, 16, 16, 8)
    assert pixels[0] == 1 and pixels[8] == 2 and pixels[8 * 16] == 3
    assert screen.encode_tiles(pixels, 16, 16, 8) == raw


def test_exact_source_match_preserves_ambiguity(tmp_path):
    raw = bytes(range(32))
    compressed = codec.compress_lz77(raw)
    padded = compressed + bytes((-len(compressed)) % 4)
    data = padded + padded
    result = screen.match_rom(data, screen.Snapshot(bytes(snapshot())), {"synthetic": raw}, tmp_path)
    matches = [match for match in result["matches"]["synthetic"] if match["encoding"] == "lz77"]
    assert len(matches) == 2
    assert matches[0]["address"] == "0x08000000"
    assert matches[1]["address"] == f"{0x08000000 + len(padded):#010x}"
    assert "likely" in result["confidence"]


def test_room_head_source_rows_and_visible_consumer():
    raw = snapshot()
    data = bytearray(0x46A14C)
    offset = screen.ROOM_HEAD_RECORDS - 0x08000000
    struct.pack_into("<II", data, offset, 0x02000100, 0x06010420)
    data[offset + 0x118:offset + 0x11A] = bytes([2, 2])
    tiles = bytes(range(128))
    raw[0x21100:0x21180] = tiles
    raw[0x11420:0x11460] = tiles[:64]
    raw[0x11820:0x11860] = tiles[64:]
    sprites = [{"id": "synthetic", "tile_addresses": ["0x06010420"], "bpp": 4, "palette_bank": 0}]
    heads = screen.extract_room_heads(data, screen.Snapshot(bytes(raw)), sprites)
    assert len(heads) == 1 and heads[0]["raw"] == tiles
    assert heads[0]["image"].size == (16, 16)
    raw[0x11820] ^= 1
    assert not screen.extract_room_heads(data, screen.Snapshot(bytes(raw)), sprites)


def test_export_refuses_unverified_rom_and_external_output(tmp_path, monkeypatch):
    with pytest.raises(codec.GfxError, match="SHA1"):
        screen.export_screen(b"invalid", screen.Snapshot(bytes(snapshot())), tmp_path)
    monkeypatch.setattr(screen.rom, "EXPECTED_SIZE", 32)
    monkeypatch.setattr(screen.rom, "EXPECTED_SHA1", screen.rom.sha1(bytes(32)))
    monkeypatch.setattr(screen.paths, "EXTRACTED_DIR", tmp_path / "extracted")
    with pytest.raises(codec.GfxError, match="under"):
        screen.export_screen(bytes(32), screen.Snapshot(bytes(snapshot())), tmp_path / "public")
