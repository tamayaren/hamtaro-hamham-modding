"""Minimal BPS patch writer/reader — the format mods are shared in (no ROM data redistributed)."""

from __future__ import annotations

import zlib

SOURCE_READ, TARGET_READ, SOURCE_COPY, TARGET_COPY = range(4)


def _encode(n: int) -> bytes:
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def _decode(data: bytes, pos: int) -> tuple[int, int]:
    n, shift = 0, 1
    while True:
        x = data[pos]
        pos += 1
        n += (x & 0x7F) * shift
        if x & 0x80:
            return n, pos
        shift <<= 7
        n += shift


def _crc(b: bytes) -> bytes:
    return (zlib.crc32(b) & 0xFFFFFFFF).to_bytes(4, "little")


def create(source: bytes, target: bytes, metadata: str = "") -> bytes:
    """Encode target as SourceRead runs (unchanged bytes) and TargetRead runs (changed bytes)."""
    meta = metadata.encode("utf-8")
    out = bytearray(b"BPS1")
    out += _encode(len(source)) + _encode(len(target)) + _encode(len(meta)) + meta
    i, n = 0, len(target)
    while i < n:
        same = i < len(source) and source[i] == target[i]
        j = i
        while j < n and (j < len(source) and source[j] == target[j]) == same:
            j += 1
        out += _encode(((j - i - 1) << 2) | (SOURCE_READ if same else TARGET_READ))
        if not same:
            out += target[i:j]
        i = j
    out += _crc(source) + _crc(target)
    out += _crc(bytes(out))
    return bytes(out)


def apply(source: bytes, patch: bytes) -> bytes:
    if patch[:4] != b"BPS1":
        raise ValueError("not a BPS patch")
    if _crc(patch[:-4]) != patch[-4:]:
        raise ValueError("patch checksum mismatch")
    if _crc(source) != patch[-12:-8]:
        raise ValueError("source ROM does not match this patch")
    pos = 4
    src_size, pos = _decode(patch, pos)
    tgt_size, pos = _decode(patch, pos)
    meta_size, pos = _decode(patch, pos)
    pos += meta_size
    out = bytearray()
    src_rel = tgt_rel = 0
    end = len(patch) - 12
    while pos < end:
        data, pos = _decode(patch, pos)
        cmd, length = data & 3, (data >> 2) + 1
        if cmd == SOURCE_READ:
            out += source[len(out):len(out) + length]
        elif cmd == TARGET_READ:
            out += patch[pos:pos + length]
            pos += length
        else:
            off, pos = _decode(patch, pos)
            delta = (-1 if off & 1 else 1) * (off >> 1)
            if cmd == SOURCE_COPY:
                src_rel += delta
                out += source[src_rel:src_rel + length]
                src_rel += length
            else:
                tgt_rel += delta
                for _ in range(length):
                    out.append(out[tgt_rel])
                    tgt_rel += 1
    if len(out) != tgt_size or _crc(bytes(out)) != patch[-8:-4]:
        raise ValueError("patched output checksum mismatch")
    return bytes(out)
