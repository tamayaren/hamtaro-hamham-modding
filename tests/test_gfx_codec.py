"""Synthetic-only coverage for the generic graphics codecs."""

import random
import struct
import zlib

import pytest
from PIL import Image

from hamtools.gfx_codec import (
    GfxError,
    compress_lz77,
    decode_tiles_4bpp,
    decompress_lz77,
    encode_tiles_4bpp,
    export_png,
    import_png,
    palette_rgb,
)


def _palette(words=None):
    if words is None:
        words = [(i | ((31 - i) << 5) | (((i * 3) % 32) << 10)
                  | ((i % 2) << 15)) for i in range(16)]
    assert len(words) == 16
    return b"".join(word.to_bytes(2, "little") for word in words)


def _rgb_word(rgb):
    return sum(((channel * 31 + 127) // 255) << shift
               for channel, shift in zip(rgb, (0, 5, 10)))


def _tokens(stream):
    """Inspect compressor choices independently of the production decoder."""
    size = int.from_bytes(stream[1:4], "little")
    pos, produced = 4, 0
    tokens = []
    while produced < size:
        flags = stream[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if produced == size:
                break
            if flags & (1 << bit):
                code = int.from_bytes(stream[pos:pos + 2], "big")
                length, distance = (code >> 12) + 3, (code & 0xFFF) + 1
                pos += 2
            else:
                length, distance = 1, None
                pos += 1
            tokens.append((produced, length, distance))
            produced += length
    return tokens


def test_lz77_known_literal_stream_offset_and_consumed():
    stream = b"\x10\x04\x00\x00\x00abcd"
    assert decompress_lz77(b"prefix" + stream + b"suffix", offset=6) == (b"abcd", 9)
    assert compress_lz77(b"abcd") == stream


@pytest.mark.parametrize("stream,raw", [
    (b"\x10\x13\x00\x00\x40A\xf0\x00", b"A" * 19),
    (b"\x10\x14\x00\x00\x20AB\xf0\x01", b"AB" * 10),
])
def test_lz77_overlapping_backrefs(stream, raw):
    assert decompress_lz77(stream) == (raw, len(stream))
    assert compress_lz77(raw) == stream


def test_lz77_empty_and_partial_flag_group():
    assert compress_lz77(b"") == b"\x10\x00\x00\x00"
    assert decompress_lz77(compress_lz77(b""), max_output=0) == (b"", 4)
    # Unused flag bits do not require payload after the declared output ends.
    assert decompress_lz77(b"\x10\x01\x00\x00\x7fZ") == (b"Z", 6)


@pytest.mark.parametrize("size", [1, 2, 3, 7, 8, 9, 31, 32, 63, 4095, 4096, 4097, 8192])
@pytest.mark.parametrize("kind", ["random", "periodic", "runs"])
def test_lz77_roundtrip(size, kind):
    rng = random.Random(1000 + size)
    if kind == "random":
        raw = rng.randbytes(size)
    elif kind == "periodic":
        raw = (bytes(range(251)) * ((size + 250) // 251))[:size]
    else:
        raw = bytes((i // 23) % 5 for i in range(size))
    compressed = compress_lz77(raw)
    assert compressed == compress_lz77(raw)
    assert compressed[0] == 0x10
    assert int.from_bytes(compressed[1:4], "little") == size
    assert decompress_lz77(compressed) == (raw, len(compressed))
    for _, length, distance in _tokens(compressed):
        if distance is not None:
            assert 3 <= length <= 18
            assert 1 <= distance <= 4096


def test_lz77_greedy_longest_and_nearest_tie():
    assert (8, 4, 8) in _tokens(compress_lz77(b"abcXabcYabcXq"))
    assert (8, 3, 4) in _tokens(compress_lz77(b"ABC0ABC1ABC2"))


def test_lz77_exact_window_boundary():
    prefix = b"\xff\xfe\xfd"
    raw = prefix + bytes(4093) + prefix
    assert (4096, 3, 4096) in _tokens(compress_lz77(raw))
    beyond = prefix + bytes(4094) + prefix
    tokens = _tokens(compress_lz77(beyond))
    assert (4097, 1, None) in tokens
    assert decompress_lz77(compress_lz77(beyond))[0] == beyond


@pytest.mark.parametrize("data,message", [
    (b"", "header"),
    (b"\x10\x01\x00", "header"),
    (b"\x11\x00\x00\x00", "signature"),
    (b"\x10\x01\x00\x00", "flag"),
    (b"\x10\x01\x00\x00\x00", "literal"),
    (b"\x10\x03\x00\x00\x80\x00", "back-reference"),
    (b"\x10\x03\x00\x00\x80\x00\x00", "precedes"),
    (b"\x10\x04\x00\x00\x40A\x00\x01", "precedes"),
    (b"\x10\x03\x00\x00\x40A\x00\x00", "exceeds declared"),
    (b"\x10\xff\xff\xff", "exceeds limit"),
])
def test_lz77_malformed(data, message):
    with pytest.raises(GfxError, match=message):
        decompress_lz77(data)


@pytest.mark.parametrize("offset", [-1, 1, 5, 0.0, True, "0"])
def test_lz77_bad_offset(offset):
    with pytest.raises(GfxError, match="offset"):
        decompress_lz77(b"\x10\x00\x00\x00", offset=offset)


@pytest.mark.parametrize("limit", [-1, 1.0, True, "4"])
def test_lz77_bad_limit(limit):
    with pytest.raises(GfxError, match="max_output"):
        decompress_lz77(b"\x10\x00\x00\x00", max_output=limit)


def test_lz77_output_limit_and_input_header_limit():
    stream = compress_lz77(b"A" * 20)
    assert decompress_lz77(stream, max_output=20)[0] == b"A" * 20
    with pytest.raises(GfxError, match="exceeds limit"):
        decompress_lz77(stream, max_output=19)
    with pytest.raises(GfxError, match="24-bit"):
        compress_lz77(bytes(1 << 24))


def test_tiles_known_nibble_order():
    indices = bytes(range(16)) * 4
    raw = bytes.fromhex("10 32 54 76 98 ba dc fe") * 4
    assert encode_tiles_4bpp(indices, 8, 8) == raw
    assert decode_tiles_4bpp(raw, 8, 8) == indices


def test_tiles_known_row_major_tile_order():
    indices = b"".join(bytes([1] * 8 + [2] * 8) if y < 8
                       else bytes([3] * 8 + [4] * 8) for y in range(16))
    raw = b"".join(bytes([index | index << 4]) * 32 for index in (1, 2, 3, 4))
    assert encode_tiles_4bpp(indices, 16, 16) == raw
    assert decode_tiles_4bpp(raw, 16, 16) == indices


@pytest.mark.parametrize("width,height", [(8, 8), (16, 8), (8, 24), (32, 40)])
def test_tiles_random_roundtrip(width, height):
    rng = random.Random(width * 100 + height)
    raw = rng.randbytes(width * height // 2)
    indices = bytes(rng.randrange(16) for _ in range(width * height))
    assert encode_tiles_4bpp(decode_tiles_4bpp(raw, width, height), width, height) == raw
    assert decode_tiles_4bpp(encode_tiles_4bpp(indices, width, height), width, height) == indices


@pytest.mark.parametrize("width,height", [(0, 8), (8, 0), (-8, 8), (7, 8), (8, 9),
                                           (8.0, 8), (True, 8), (8, "8")])
def test_tiles_reject_geometry(width, height):
    for codec in (encode_tiles_4bpp, decode_tiles_4bpp):
        with pytest.raises(GfxError, match="multiples of 8"):
            codec(b"", width, height)


@pytest.mark.parametrize("size", [0, 31, 33, 64])
def test_tiles_reject_raw_length(size):
    with pytest.raises(GfxError, match="exactly 32"):
        decode_tiles_4bpp(bytes(size), 8, 8)


@pytest.mark.parametrize("size", [0, 32, 63, 65])
def test_tiles_reject_indices_length(size):
    with pytest.raises(GfxError, match="exactly 64"):
        encode_tiles_4bpp(bytes(size), 8, 8)


@pytest.mark.parametrize("index", [16, 255])
def test_tiles_reject_out_of_range_index(index):
    with pytest.raises(GfxError, match="0..15"):
        encode_tiles_4bpp(bytes([index]) + bytes(63), 8, 8)


def test_palette_bgr555_channel_order_replication_and_unused_bit():
    words = [0, 0x001F, 0x03E0, 0x7C00, 0x7FFF, 0x8000, 0x8421] + [0] * 9
    assert palette_rgb(_palette(words))[:7] == [
        (0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 255), (0, 0, 0), (8, 8, 8),
    ]
    for channel in range(32):
        expected = (channel << 3) | (channel >> 2)
        rgb = palette_rgb(_palette([channel | channel << 5 | channel << 10] * 16))[0]
        assert rgb == (expected, expected, expected)


@pytest.mark.parametrize("size", [0, 30, 31, 33, 64])
def test_palette_reject_length(size):
    with pytest.raises(GfxError, match="32 bytes"):
        palette_rgb(bytes(size))


@pytest.mark.parametrize("mode", ["original", "new"])
def test_png_unchanged_duplicate_colours_roundtrip(tmp_path, mode):
    words = [0x001F, 0x801F, 0x001F, 0x801F] + [0xFFFF - i for i in range(12)]
    palette = _palette(words)
    indices = bytes(range(16)) * 8
    raw = encode_tiles_4bpp(indices, 16, 8)
    path = tmp_path / "duplicates.png"
    export_png(raw, palette, 16, 8, path)
    with Image.open(path) as image:
        assert image.mode == "P"
        assert image.tobytes() == indices
        assert image.getpalette() == [value for rgb in palette_rgb(palette) for value in rgb]
        assert image.info["transparency"] == 0
        assert image.convert("RGBA").tobytes()[3::4] == bytes(0 if i == 0 else 255 for i in indices)
    assert import_png(path, raw, palette, 16, 8, palette_mode=mode) == (raw, palette)


@pytest.mark.parametrize("start", [0, 16])
def test_png_all_replicated_channels_roundtrip_exact_words(tmp_path, start):
    palette = _palette([0x8000 | n | n << 5 | n << 10 for n in range(start, start + 16)])
    raw = encode_tiles_4bpp(bytes([2]) * 64, 8, 8)  # Most entries are unused.
    path = tmp_path / "rounding.png"
    export_png(raw, palette, 8, 8, path)
    assert import_png(path, raw, palette, 8, 8, "new") == (raw, palette)


def test_png_original_nearest_transparency_and_duplicate_identity(tmp_path):
    palette = _palette([0, 0x001F, 0x801F, 0x03E0, 0x7C00, 0x7FFF, 0x0421, 0] + [0x7FFF] * 8)
    raw = encode_tiles_4bpp(bytes([2]) * 64, 8, 8)
    path = tmp_path / "edited.png"
    export_png(raw, palette, 8, 8, path)
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
    rgba.putpixel((1, 0), (255, 255, 255, 0))
    rgba.putpixel((2, 0), (0, 0, 0, 255))
    rgba.putpixel((3, 0), (250, 2, 0, 255))
    rgba.save(path)
    changed, changed_palette = import_png(path, raw, palette, 8, 8)
    assert changed_palette == palette
    indices = decode_tiles_4bpp(changed, 8, 8)
    assert indices[:4] == bytes([2, 0, 7, 1])
    assert indices[4:] == bytes([2]) * 60


def test_png_palette_only_edit_preserves_pixels_and_untouched_unused_entries(tmp_path):
    palette = _palette()
    raw = encode_tiles_4bpp(bytes([3]) * 64, 8, 8)
    path = tmp_path / "palette-only.png"
    export_png(raw, palette, 8, 8, path)
    with Image.open(path) as image:
        changed = image.copy()
    table = changed.getpalette()
    table[9:12] = [5, 127, 250]
    table[42:45] = [250, 5, 127]  # An explicitly edited unused entry.
    changed.putpalette(table)
    changed.save(path, transparency=0, bits=4)
    result_raw, result_palette = import_png(path, raw, palette, 8, 8, "new")
    assert result_raw == raw
    for index in range(16):
        original_word = int.from_bytes(palette[index * 2:index * 2 + 2], "little")
        if index in (3, 14):
            colour = (5, 127, 250) if index == 3 else (250, 5, 127)
            expected = _rgb_word(colour) | (original_word & 0x8000)
            assert int.from_bytes(result_palette[index * 2:index * 2 + 2], "little") == expected
        else:
            assert result_palette[index * 2:index * 2 + 2] == palette[index * 2:index * 2 + 2]


def test_png_original_palette_only_edit_maps_to_original_colours(tmp_path):
    palette = _palette([0, 0x001F, 0x03E0] + [0x7C00] * 13)
    raw = encode_tiles_4bpp(bytes([1]) * 64, 8, 8)
    path = tmp_path / "keep-palette.png"
    export_png(raw, palette, 8, 8, path)
    with Image.open(path) as image:
        changed = image.copy()
    table = changed.getpalette()
    table[3:6] = [0, 255, 0]
    changed.putpalette(table)
    changed.save(path, transparency=0)
    result_raw, result_palette = import_png(path, raw, palette, 8, 8)
    assert result_palette == palette
    assert decode_tiles_4bpp(result_raw, 8, 8) == bytes([2]) * 64


def test_png_new_truecolour_palette_rounding_and_unused_preservation(tmp_path):
    palette = _palette()
    raw = bytes(32)
    colours = [(250, 2, 1), (0, 240, 10), (9, 8, 235)]
    pixels = [(*colours[i % 3], 255) for i in range(64)]
    pixels[0] = (123, 42, 111, 0)
    path = tmp_path / "truecolour.png"
    image = Image.new("RGBA", (8, 8))
    image.putdata(pixels)
    image.save(path)
    result_raw, result_palette = import_png(path, raw, palette, 8, 8, "new")
    indices = decode_tiles_4bpp(result_raw, 8, 8)
    assert indices[0] == 0
    assert set(indices[1:]) == {1, 2, 3}
    expected_words = {_rgb_word(rgb) for rgb in colours}
    actual_words = {int.from_bytes(result_palette[i * 2:i * 2 + 2], "little") & 0x7FFF
                    for i in (1, 2, 3)}
    assert actual_words == expected_words
    assert result_palette[:2] == palette[:2]
    assert result_palette[8:] == palette[8:]
    displayed = palette_rgb(result_palette)
    for index, pixel in zip(indices[1:], pixels[1:]):
        assert max(abs(a - b) for a, b in zip(displayed[index], pixel[:3])) <= 4


def test_png_new_deterministic_quantization_without_transparent_colour(tmp_path):
    palette = _palette()
    raw = bytes(32)
    colours = [(i * 4, (i * 37) % 256, (i * 71) % 256) for i in range(64)]
    path = tmp_path / "quantized.png"
    image = Image.new("RGB", (8, 8))
    image.putdata(colours)
    image.save(path)
    result = import_png(path, raw, palette, 8, 8, "new")
    assert import_png(path, raw, palette, 8, 8, "new") == result
    indices = decode_tiles_4bpp(result[0], 8, 8)
    assert 1 <= min(indices) <= max(indices) <= 15
    assert len(set(indices)) <= 15
    displayed = palette_rgb(result[1])
    error = sum(sum((a - b) ** 2 for a, b in zip(rgb, displayed[index]))
                for rgb, index in zip(colours, indices)) / 64
    assert error < 4000
    image.putdata(list(reversed(colours)))
    image.save(path)
    reversed_raw, reversed_palette = import_png(path, raw, palette, 8, 8, "new")
    assert reversed_palette == result[1]
    assert decode_tiles_4bpp(reversed_raw, 8, 8) == indices[::-1]


@pytest.mark.parametrize("transparent_index", [None, 3])
def test_png_new_remaps_opaque_zero_and_nonzero_transparency(tmp_path, transparent_index):
    palette = _palette()
    raw = bytes(32)
    source_indices = bytes([0, 3]) * 32
    image = Image.frombytes("P", (8, 8), source_indices)
    image.putpalette([channel for rgb in palette_rgb(palette) for channel in rgb])
    path = tmp_path / "remap.png"
    options = {} if transparent_index is None else {"transparency": transparent_index}
    image.save(path, **options)
    result_raw, result_palette = import_png(path, raw, palette, 8, 8, "new")
    indices = decode_tiles_4bpp(result_raw, 8, 8)
    assert all(index > 0 for index in indices[::2])
    if transparent_index is None:
        assert all(index > 0 for index in indices)
    else:
        assert indices[1::2] == bytes(32)
    assert result_palette[:2] == palette[:2]


def test_png_new_reduces_large_indexed_palette(tmp_path):
    palette = _palette()
    image = Image.frombytes("P", (8, 8), bytes([20, 250]) * 32)
    image.putpalette([channel for i in range(256) for channel in (i, 255 - i, (i * 7) % 256)])
    path = tmp_path / "large-palette.png"
    image.save(path, bits=8)
    result_raw, _ = import_png(path, bytes(32), palette, 8, 8, "new")
    assert set(decode_tiles_4bpp(result_raw, 8, 8)) == {1, 2}


@pytest.mark.parametrize("mode", ["original", "new"])
def test_png_all_transparent(tmp_path, mode):
    palette = _palette()
    image = Image.new("RGBA", (8, 8), (250, 123, 40, 0))
    path = tmp_path / "transparent.png"
    image.save(path)
    assert import_png(path, bytes([0xFF]) * 32, palette, 8, 8, mode) == (bytes(32), palette)


@pytest.mark.parametrize("mode", ["original", "new"])
@pytest.mark.parametrize("source_mode", ["RGBA", "P"])
def test_png_rejects_partial_alpha(tmp_path, mode, source_mode):
    palette = _palette()
    if source_mode == "RGBA":
        image = Image.new("RGBA", (8, 8), (255, 0, 0, 128))
        options = {}
    else:
        image = Image.frombytes("P", (8, 8), bytes([4]) * 64)
        image.putpalette([channel for rgb in palette_rgb(palette) for channel in rgb])
        options = {"transparency": bytes([0, 255, 255, 255, 128] + [255] * 11)}
    path = tmp_path / "partial-alpha.png"
    image.save(path, **options)
    with pytest.raises(GfxError, match="semi-transparent"):
        import_png(path, bytes(32), palette, 8, 8, mode)


@pytest.mark.parametrize("missing", [1, 4, 8, 12, 20])
def test_png_rejects_truncation(tmp_path, missing):
    palette = _palette()
    path = tmp_path / "truncated.png"
    export_png(bytes(32), palette, 8, 8, path)
    path.write_bytes(path.read_bytes()[:-missing])
    with pytest.raises(GfxError, match="PNG"):
        import_png(path, bytes(32), palette, 8, 8)


def test_png_rejects_crc_corruption(tmp_path):
    palette = _palette()
    path = tmp_path / "corrupt.png"
    export_png(bytes(32), palette, 8, 8, path)
    data = bytearray(path.read_bytes())
    data[data.index(b"IDAT") + 4] ^= 1
    path.write_bytes(data)
    with pytest.raises(GfxError, match="PNG"):
        import_png(path, bytes(32), palette, 8, 8)


def test_png_rejects_missing_palette_reference(tmp_path):
    def chunk(kind, payload):
        return (len(payload).to_bytes(4, "big") + kind + payload
                + (zlib.crc32(kind + payload) & 0xFFFFFFFF).to_bytes(4, "big"))

    # Valid PNG container, but pixel index 3 has no entry in its one-colour PLTE.
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 3, 0, 0, 0))
    data += chunk(b"PLTE", bytes(3))
    data += chunk(b"IDAT", zlib.compress((b"\x00" + bytes([3]) * 8) * 8))
    data += chunk(b"IEND", b"")
    path = tmp_path / "missing-colour.png"
    path.write_bytes(data)
    with pytest.raises(GfxError, match="missing palette"):
        import_png(path, bytes(32), _palette(), 8, 8)


@pytest.mark.parametrize("data", [b"", b"not a PNG", b"\x89PNG\r\n\x1a\n"])
def test_png_rejects_bad_signature_or_container(tmp_path, data):
    path = tmp_path / "invalid.png"
    path.write_bytes(data)
    with pytest.raises(GfxError, match="PNG"):
        import_png(path, bytes(32), _palette(), 8, 8)


def test_png_rejects_wrong_format_and_geometry(tmp_path):
    path = tmp_path / "wrong.png"
    Image.new("RGB", (8, 8)).save(path, format="JPEG")
    with pytest.raises(GfxError, match="signature"):
        import_png(path, bytes(32), _palette(), 8, 8)
    Image.new("RGB", (16, 8)).save(path, format="PNG")
    with pytest.raises(GfxError, match="dimensions"):
        import_png(path, bytes(32), _palette(), 8, 8)


def test_png_rejects_unsupported_mode_and_animation(tmp_path):
    path = tmp_path / "unsupported.png"
    Image.new("I;16", (8, 8)).save(path)
    with pytest.raises(GfxError, match="unsupported PNG mode"):
        import_png(path, bytes(32), _palette(), 8, 8)
    image = Image.new("RGBA", (8, 8), (255, 0, 0, 255))
    image.save(path, save_all=True, append_images=[Image.new("RGBA", (8, 8))])
    with pytest.raises(GfxError, match="animated"):
        import_png(path, bytes(32), _palette(), 8, 8)


def test_png_validates_arguments_and_file_errors(tmp_path):
    path = tmp_path / "missing.png"
    with pytest.raises(GfxError, match="palette_mode"):
        import_png(path, bytes(32), _palette(), 8, 8, "unexpected")
    with pytest.raises(GfxError, match="32 bytes"):
        import_png(path, bytes(32), bytes(30), 8, 8)
    with pytest.raises(GfxError, match="exactly 32"):
        import_png(path, bytes(33), _palette(), 8, 8)
    with pytest.raises(GfxError, match="multiples of 8"):
        export_png(bytes(32), _palette(), 7, 8, path)
    with pytest.raises(GfxError, match="PNG"):
        import_png(path, bytes(32), _palette(), 8, 8)
    with pytest.raises(GfxError, match="write PNG"):
        export_png(bytes(32), _palette(), 8, 8, tmp_path / "absent" / "out.png")


@pytest.mark.parametrize("damage", ["checksum", "trailing-data"])
def test_png_rejects_damaged_end_chunk(tmp_path, damage):
    palette = _palette()
    path = tmp_path / "bad-end.png"
    export_png(bytes(32), palette, 8, 8, path)
    data = bytearray(path.read_bytes())
    if damage == "checksum":
        data[-1] ^= 1
    else:
        data += b"unexpected trailing bytes"
    path.write_bytes(data)
    with pytest.raises(GfxError, match="PNG"):
        import_png(path, bytes(32), palette, 8, 8)


def _png_chunk(kind, payload):
    return (len(payload).to_bytes(4, "big") + kind + payload
            + (zlib.crc32(kind + payload) & 0xFFFFFFFF).to_bytes(4, "big"))


@pytest.mark.parametrize("damage", ["missing-byte", "missing-end", "adler-checksum",
                                    "trailing-stream", "oversized"])
def test_png_rejects_invalid_deflate_with_valid_chunk_checksums(tmp_path, damage):
    palette = _palette()
    path = tmp_path / "bad-deflate.png"
    export_png(bytes(32), palette, 8, 8, path)
    data = path.read_bytes()
    start = data.index(b"IDAT") - 4
    size = int.from_bytes(data[start:start + 4], "big")
    payload = data[start + 8:start + 8 + size]
    if damage == "missing-byte":
        payload = payload[:-1]
    elif damage == "missing-end":
        payload = payload[:-4]
    elif damage == "adler-checksum":
        payload = payload[:-1] + bytes([payload[-1] ^ 1])
    elif damage == "trailing-stream":
        payload += zlib.compress(b"extra stream")
    else:
        payload = zlib.compress(bytes(1000))
    path.write_bytes(data[:start] + _png_chunk(b"IDAT", payload) + data[start + size + 12:])
    with pytest.raises(GfxError, match="PNG"):
        import_png(path, bytes(32), palette, 8, 8)


def test_png_accepts_idat_split_across_chunks(tmp_path):
    palette = _palette()
    path = tmp_path / "split-stream.png"
    raw = encode_tiles_4bpp(bytes(range(16)) * 4, 8, 8)
    export_png(raw, palette, 8, 8, path)
    data = path.read_bytes()
    start = data.index(b"IDAT") - 4
    size = int.from_bytes(data[start:start + 4], "big")
    payload = data[start + 8:start + 8 + size]
    chunks = b"".join(_png_chunk(b"IDAT", payload[i:i + 1]) for i in range(len(payload)))
    path.write_bytes(data[:start] + chunks + data[start + size + 12:])
    assert import_png(path, raw, palette, 8, 8) == (raw, palette)


@pytest.mark.parametrize("width,height", [(8, 8), (16, 24)])
def test_png_accepts_interlaced_rgb(tmp_path, width, height):
    palette = _palette([0, 0x001F, 0x03E0, 0x7C00] + [0] * 12)
    colours = palette_rgb(palette)
    indices = bytes(1 + (x + y) % 3 for y in range(height) for x in range(width))
    scanlines = bytearray()
    for x_start, y_start, x_step, y_step in (
        (0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
        (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2),
    ):
        for y in range(y_start, height, y_step):
            scanlines.append(0)  # PNG filter: None.
            for x in range(x_start, width, x_step):
                scanlines.extend(colours[indices[y * width + x]])
    data = b"\x89PNG\r\n\x1a\n"
    data += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 1))
    data += _png_chunk(b"IDAT", zlib.compress(scanlines))
    data += _png_chunk(b"IEND", b"")
    path = tmp_path / "interlaced.png"
    path.write_bytes(data)
    result_raw, result_palette = import_png(path, bytes(width * height // 2),
                                            palette, width, height)
    assert result_palette == palette
    assert decode_tiles_4bpp(result_raw, width, height) == indices
