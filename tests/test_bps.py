import os

import pytest

from hamtools import bps


def test_roundtrip_small():
    src = bytes(range(256)) * 4
    tgt = bytearray(src)
    tgt[10:14] = b"\x00\x11\x22\x33"
    tgt[700] = 0xAA
    patch = bps.create(src, bytes(tgt))
    assert bps.apply(src, patch) == bytes(tgt)


def test_roundtrip_grow():
    src = b"\xff" * 100
    tgt = src + b"extra"
    assert bps.apply(src, bps.create(src, tgt)) == tgt


def test_rejects_wrong_source():
    patch = bps.create(b"abc", b"abd")
    with pytest.raises(ValueError):
        bps.apply(b"xyz", patch)


def test_random_roundtrip():
    src = os.urandom(5000)
    tgt = bytearray(src)
    for i in range(0, 5000, 97):
        tgt[i] ^= 0x5A
    assert bps.apply(src, bps.create(src, bytes(tgt))) == bytes(tgt)
