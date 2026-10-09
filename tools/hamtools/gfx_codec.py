"""Generic GBA LZ77, 4bpp tiles, and lossless indexed PNG editing.

No ROM-specific addresses or data belong here. PNG palette index 0 is always
transparent; partial alpha is rejected. New truecolour palettes use deterministic
weighted median-cut in BGR555 space, followed by nearest-colour mapping without
dithering. Unchanged palette words (including their unused high bit) survive
roundtrips, and unused entries survive unless explicitly edited in a P image.
"""

from __future__ import annotations

import zlib

from collections import Counter, deque
from io import BytesIO
from pathlib import Path

from PIL import Image


class GfxError(ValueError):
    """Invalid compressed graphics, tile geometry, palette, or PNG."""


def decompress_lz77(
    data: bytes, offset: int = 0, max_output: int = 1 << 20,
) -> tuple[bytes, int]:
    """Read one BIOS type-0x10 stream; consumed includes its four-byte header.

    Trailing bytes and optional alignment padding are not consumed. A match must
    fit the declared output exactly, and may copy bytes produced by that match.
    """
    if type(offset) is not int or offset < 0 or offset + 4 > len(data):
        raise GfxError("LZ77 offset must point to a complete four-byte header")
    if type(max_output) is not int or max_output < 0:
        raise GfxError("LZ77 max_output must be a nonnegative integer")
    if data[offset] != 0x10:
        raise GfxError("expected BIOS type-0x10 LZ77 signature")
    size = int.from_bytes(data[offset + 1:offset + 4], "little")
    if size > max_output:
        raise GfxError(f"LZ77 output size {size} exceeds limit {max_output}")
    pos = offset + 4
    out = bytearray()
    while len(out) < size:
        if pos >= len(data):
            raise GfxError("truncated LZ77 flag group")
        flags = data[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(out) == size:
                break
            if flags & (1 << bit):
                if pos + 2 > len(data):
                    raise GfxError("truncated LZ77 back-reference")
                first, second = data[pos:pos + 2]
                pos += 2
                length = (first >> 4) + 3
                distance = ((first & 0x0F) << 8 | second) + 1
                if distance > len(out):
                    raise GfxError("LZ77 back-reference precedes output start")
                if len(out) + length > size:
                    raise GfxError("LZ77 back-reference exceeds declared output size")
                for _ in range(length):
                    out.append(out[-distance])
            else:
                if pos >= len(data):
                    raise GfxError("truncated LZ77 literal")
                out.append(data[pos])
                pos += 1
    return bytes(out), pos - offset


def compress_lz77(raw: bytes) -> bytes:
    """Deterministic greedy type-0x10 compression, with nearest-match tie breaks.

    Matches span 3..18 bytes in a 4096-byte window, including overlapping copies.
    The result has no alignment padding; an empty input has a four-byte header.
    """
    if len(raw) > 0xFFFFFF:
        raise GfxError("LZ77 input exceeds the 24-bit header size")
    out = bytearray(b"\x10" + len(raw).to_bytes(3, "little"))
    positions: dict[bytes, deque[int]] = {}
    pos = 0
    while pos < len(raw):
        flag_pos = len(out)
        out.append(0)
        for bit in range(7, -1, -1):
            if pos == len(raw):
                break
            best_length, best_distance = 0, 0
            limit = min(18, len(raw) - pos)
            if limit >= 3:
                for previous in reversed(positions.get(raw[pos:pos + 3], ())):
                    length = 3
                    # Comparing the source ahead of pos also models overlap:
                    # each byte must equal the one distance bytes before it.
                    while length < limit and raw[previous + length] == raw[pos + length]:
                        length += 1
                    if length > best_length:
                        best_length, best_distance = length, pos - previous
                        if length == limit:
                            break
            if best_length >= 3:
                out[flag_pos] |= 1 << bit
                encoded_distance = best_distance - 1
                out.extend(((best_length - 3) << 4 | encoded_distance >> 8,
                            encoded_distance & 0xFF))
                end = pos + best_length
            else:
                out.append(raw[pos])
                end = pos + 1
            for current in range(pos, end):
                # Keep the index bounded, including on incompressible input.
                if current >= 4096:
                    stale_key = raw[current - 4096:current - 4093]
                    stale = positions[stale_key]
                    stale.popleft()
                    if not stale:
                        del positions[stale_key]
                if current + 3 <= len(raw):
                    key = raw[current:current + 3]
                    positions.setdefault(key, deque()).append(current)
            pos = end
    return bytes(out)


def _geometry(width: int, height: int) -> int:
    if (type(width) is not int or type(height) is not int
            or width <= 0 or height <= 0 or width % 8 or height % 8):
        raise GfxError("tile width and height must be positive integer multiples of 8")
    return width * height


def decode_tiles_4bpp(raw: bytes, width: int, height: int) -> bytes:
    """Unpack row-major 8x8 tiles to row-major pixels; low nibble is left."""
    pixels = _geometry(width, height)
    if len(raw) != pixels // 2:
        raise GfxError(f"4bpp data must contain exactly {pixels // 2} bytes")
    indices = bytearray(pixels)
    tile = 0
    for tile_y in range(0, height, 8):
        for tile_x in range(0, width, 8):
            for y in range(8):
                row = (tile_y + y) * width + tile_x
                for pair in range(4):
                    packed = raw[tile + y * 4 + pair]
                    indices[row + pair * 2] = packed & 0x0F
                    indices[row + pair * 2 + 1] = packed >> 4
            tile += 32
    return bytes(indices)


def encode_tiles_4bpp(indices: bytes, width: int, height: int) -> bytes:
    """Exact inverse of decode_tiles_4bpp; indices must all be in 0..15."""
    pixels = _geometry(width, height)
    if len(indices) != pixels:
        raise GfxError(f"pixel indices must contain exactly {pixels} bytes")
    if any(index > 15 for index in indices):
        raise GfxError("4bpp palette indices must be in 0..15")
    raw = bytearray()
    for tile_y in range(0, height, 8):
        for tile_x in range(0, width, 8):
            for y in range(8):
                row = (tile_y + y) * width + tile_x
                for x in range(0, 8, 2):
                    raw.append(indices[row + x] | indices[row + x + 1] << 4)
    return bytes(raw)


def _word_rgb(word: int) -> tuple[int, int, int]:
    channels = [(word >> shift) & 31 for shift in (0, 5, 10)]
    return tuple((value << 3) | (value >> 2) for value in channels)


def palette_rgb(palette: bytes) -> list[tuple[int, int, int]]:
    """Decode exactly sixteen little-endian BGR555 words by bit replication."""
    if len(palette) != 32:
        raise GfxError("a 4bpp palette must contain exactly 32 bytes (16 colours)")
    return [_word_rgb(int.from_bytes(palette[i:i + 2], "little"))
            for i in range(0, 32, 2)]


def _rgb_word(rgb: tuple[int, int, int]) -> int:
    # Round rather than truncate. Every bit-replicated source channel maps back
    # to its exact five-bit value.
    return sum(((channel * 31 + 127) // 255) << shift
               for channel, shift in zip(rgb, (0, 5, 10)))


def _set_colour(palette: bytearray, index: int, rgb: tuple[int, int, int]) -> None:
    start = index * 2
    original = int.from_bytes(palette[start:start + 2], "little")
    if _word_rgb(original) != rgb:
        word = _rgb_word(rgb) | (original & 0x8000)
        palette[start:start + 2] = word.to_bytes(2, "little")


def export_png(raw: bytes, palette: bytes, width: int, height: int, path: Path) -> None:
    """Export a P-mode PNG with sixteen entries and transparency only at index 0."""
    indices = decode_tiles_4bpp(raw, width, height)
    colours = palette_rgb(palette)
    with Image.frombytes("P", (width, height), indices) as image:
        image.putpalette([channel for rgb in colours for channel in rgb])
        try:
            image.save(path, format="PNG", transparency=0, bits=4)
        except OSError as exc:
            raise GfxError(f"could not write PNG: {exc}") from exc


def _check_png_chunks(data: bytes, width: int, height: int) -> None:
    """Require complete checksums and a complete, bounded IDAT zlib stream.

    Pillow accepts missing IEND checksums and missing IDAT end markers. The
    inflated-data bound allows four 8-bit channels plus all seven Adam7 passes'
    row filter bytes; Pillow handles the actual pixel/filter decoding.
    """
    pos = 8
    inflater = zlib.decompressobj()
    produced = 0
    limit = width * height * 4 + height * 7
    while pos < len(data):
        if pos + 12 > len(data):
            raise GfxError("truncated PNG chunk")
        size = int.from_bytes(data[pos:pos + 4], "big")
        end = pos + 12 + size
        if end > len(data):
            raise GfxError("truncated PNG chunk payload or checksum")
        kind = data[pos + 4:pos + 8]
        checksum = int.from_bytes(data[end - 4:end], "big")
        if (zlib.crc32(data[pos + 4:end - 4]) & 0xFFFFFFFF) != checksum:
            raise GfxError("invalid PNG chunk checksum")
        if kind == b"IHDR":
            if size != 13:
                raise GfxError("invalid PNG header size")
            dimensions = (int.from_bytes(data[pos + 8:pos + 12], "big"),
                          int.from_bytes(data[pos + 12:pos + 16], "big"))
            if dimensions != (width, height):
                raise GfxError(f"PNG dimensions must be exactly {width}x{height}")
            if data[pos + 16] == 16:
                raise GfxError("unsupported PNG mode: 16-bit channels")
        if kind == b"IDAT":
            produced += len(inflater.decompress(data[pos + 8:end - 4], limit - produced + 1))
            if produced > limit or inflater.unconsumed_tail:
                raise GfxError("PNG compressed pixel data exceeds image size limit")
            if inflater.unused_data:
                raise GfxError("invalid PNG: data after compressed pixel stream")
        if kind == b"IEND":
            if size or end != len(data):
                raise GfxError("invalid PNG IEND or trailing data")
            if not inflater.eof:
                raise GfxError("truncated PNG compressed pixel stream")
            return
        pos = end
    raise GfxError("truncated PNG: missing IEND chunk")


def _read_png(path: Path, width: int, height: int) -> Image.Image:
    try:
        data = Path(path).read_bytes()
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise GfxError("expected a PNG signature")
        _check_png_chunks(data, width, height)
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG":
                raise GfxError("expected a PNG image")
            if image.size != (width, height):
                raise GfxError(f"PNG dimensions must be exactly {width}x{height}")
            if getattr(image, "n_frames", 1) != 1:
                raise GfxError("animated PNGs are not supported")
            image.verify()
        with Image.open(BytesIO(data)) as image:
            if image.mode not in ("1", "L", "LA", "P", "RGB", "RGBA"):
                raise GfxError(f"unsupported PNG mode: {image.mode}")
            image.load()
            return image.copy()
    except GfxError:
        raise
    except (OSError, ValueError, SyntaxError, EOFError, zlib.error, Image.DecompressionBombError) as exc:
        raise GfxError(f"invalid PNG: {exc}") from exc


def _nearest(rgb: tuple[int, int, int], colours: list[tuple[int, int, int]]) -> int:
    """Choose an opaque palette entry; lower indices win equal-distance ties."""
    return min(range(1, len(colours)),
               key=lambda index: sum((a - b) ** 2 for a, b in zip(rgb, colours[index])))


def _quantize_words(histogram: Counter[int]) -> list[int]:
    """Weighted median-cut to at most fifteen deterministic BGR555 colours."""
    if len(histogram) <= 15:
        return sorted(histogram)
    boxes = [sorted(histogram)]
    while len(boxes) < 15:
        choices = []
        for index, box in enumerate(boxes):
            if len(box) < 2:
                continue
            ranges = [max((word >> shift) & 31 for word in box)
                      - min((word >> shift) & 31 for word in box)
                      for shift in (0, 5, 10)]
            axis = max(range(3), key=lambda item: ranges[item])
            choices.append((ranges[axis], sum(histogram[word] for word in box),
                            len(box), -index, axis))
        if not choices:
            break
        _, total, _, negative_index, axis = max(choices)
        index = -negative_index
        ordered = sorted(boxes[index], key=lambda word: ((word >> (axis * 5)) & 31, word))
        cumulative = 0
        split = 1
        for split, word in enumerate(ordered, 1):
            cumulative += histogram[word]
            if cumulative * 2 >= total:
                break
        split = min(split, len(ordered) - 1)
        boxes[index:index + 1] = [ordered[:split], ordered[split:]]
    words = set()
    for box in boxes:
        total = sum(histogram[word] for word in box)
        average = [sum(((word >> shift) & 31) * histogram[word] for word in box)
                   for shift in (0, 5, 10)]
        words.add(sum(((value + total // 2) // total) << shift
                      for value, shift in zip(average, (0, 5, 10))))
    return sorted(words)


def import_png(
    path: Path, original_raw: bytes, original_palette: bytes,
    width: int, height: int, palette_mode: str = "original",
) -> tuple[bytes, bytes]:
    """Import edits with binary transparency, without dithering.

    ``original`` keeps the palette, maps alpha 0 to index 0, and maps opaque RGB
    to its nearest entry in 1..15. If a pixel still displays its original RGB and
    alpha, its original index wins, even when palette colours are duplicated.

    ``new`` preserves P indices/table when used indices fit 0..15 and only index
    0 is transparent. Changed table entries are rounded to BGR555; untouched
    words and unused entries stay intact. Other images get at most fifteen opaque
    colours via weighted median-cut. Index 0 and remaining unused entries retain
    the original palette. Partial alpha and 16-bit-channel PNGs are rejected.
    """
    original_indices = decode_tiles_4bpp(original_raw, width, height)
    original_colours = palette_rgb(original_palette)
    if palette_mode not in ("original", "new"):
        raise GfxError("palette_mode must be 'original' or 'new'")
    with _read_png(path, width, height) as image:
        with image.convert("RGBA") as rgba_image:
            rgba = rgba_image.tobytes()
        if any(alpha not in (0, 255) for alpha in rgba[3::4]):
            raise GfxError("semi-transparent PNG pixels are not supported; alpha must be 0 or 255")
        source_indices = image.tobytes() if image.mode == "P" else None
        source_palette = image.getpalette("RGB") if image.mode == "P" else None
        if source_indices is not None:
            if not source_palette or max(source_indices) >= len(source_palette) // 3:
                raise GfxError("PNG pixel references a missing palette entry")
        if palette_mode == "new" and source_indices is not None:
            compatible = all(index <= 15 and (rgba[pixel * 4 + 3] == 0) == (index == 0)
                             for pixel, index in enumerate(source_indices))
            if compatible:
                palette = bytearray(original_palette)
                for index in range(min(16, len(source_palette) // 3)):
                    rgb = tuple(source_palette[index * 3:index * 3 + 3])
                    _set_colour(palette, index, rgb)
                return encode_tiles_4bpp(source_indices, width, height), bytes(palette)

    palette = bytearray(original_palette)
    colours = original_colours
    if palette_mode == "new":
        histogram = Counter(_rgb_word(tuple(rgba[pixel:pixel + 3]))
                            for pixel in range(0, len(rgba), 4) if rgba[pixel + 3])
        words = _quantize_words(histogram)
        colours = [original_colours[0]] + [_word_rgb(word) for word in words]
        for index, rgb in enumerate(colours[1:], 1):
            _set_colour(palette, index, rgb)
    indices = bytearray(width * height)
    nearest: dict[tuple[int, int, int], int] = {}
    for pixel, original_index in enumerate(original_indices):
        start = pixel * 4
        if rgba[start + 3] == 0:
            continue
        rgb = tuple(rgba[start:start + 3])
        if (palette_mode == "original" and original_index != 0
                and original_colours[original_index] == rgb):
            indices[pixel] = original_index
        else:
            if rgb not in nearest:
                nearest[rgb] = _nearest(rgb, colours)
            indices[pixel] = nearest[rgb]
    return encode_tiles_4bpp(bytes(indices), width, height), bytes(palette)
