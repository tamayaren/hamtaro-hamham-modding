"""Read-only access to the original ROM: locating, verifying, header parsing, searching."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

ROM_BASE = 0x08000000
EXPECTED_SHA1 = "2525cc23524068dfb3a2b4e0ce7b736f95023e82"
EXPECTED_SIZE = 8 * 1024 * 1024
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROM = REPO_ROOT / "gba" / "Hamtaro - Ham-Ham Heartbreak (USA).gba"

SAVE_TAGS = (b"EEPROM_V", b"SRAM_F_V", b"SRAM_V", b"FLASH1M_V", b"FLASH512_V", b"FLASH_V")


class RomError(Exception):
    pass


def rom_path() -> Path:
    env = os.environ.get("HAMTARO_ROM")
    path = Path(env) if env else DEFAULT_ROM
    if not path.is_file():
        raise RomError(f"ROM not found at {path} (set HAMTARO_ROM to override)")
    return path


def load_rom() -> bytes:
    return rom_path().read_bytes()


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def to_offset(addr: int) -> int:
    """Accept a ROM bus address (0x08xxxxxx) or a raw file offset; return the file offset."""
    if ROM_BASE <= addr < ROM_BASE + 0x02000000:
        return addr - ROM_BASE
    if 0 <= addr < 0x02000000:
        return addr
    raise RomError(f"{addr:#010x} is not a ROM address or file offset")


def to_addr(offset: int) -> int:
    return ROM_BASE + offset


@dataclass
class Header:
    title: str
    game_code: str
    maker: str
    version: int
    checksum: int
    checksum_ok: bool
    entry_target: int | None


def parse_header(data: bytes) -> Header:
    checksum = (-sum(data[0xA0:0xBD]) - 0x19) & 0xFF
    word = int.from_bytes(data[0:4], "little")
    entry = None
    if word >> 24 == 0xEA:  # ARM unconditional branch
        imm = word & 0x00FFFFFF
        if imm & 0x800000:
            imm -= 0x1000000
        entry = ROM_BASE + 8 + imm * 4
    return Header(
        title=data[0xA0:0xAC].rstrip(b"\0").decode("ascii", "replace"),
        game_code=data[0xAC:0xB0].decode("ascii", "replace"),
        maker=data[0xB0:0xB2].decode("ascii", "replace"),
        version=data[0xBC],
        checksum=data[0xBD],
        checksum_ok=checksum == data[0xBD],
        entry_target=entry,
    )


def find_save_tag(data: bytes) -> tuple[int, str] | None:
    for tag in SAVE_TAGS:
        i = data.find(tag)
        if i >= 0:
            end = data.find(b"\0", i, i + 32)
            return i, data[i : end if end > 0 else i + 16].decode("ascii", "replace")
    return None


def used_end(data: bytes, pad: int = 0xFF) -> int:
    """File offset one past the last byte that isn't trailing padding."""
    end = len(data)
    while end > 0 and data[end - 1] == pad:
        end -= 1
    return end


def parse_pattern(hex_pattern: str) -> re.Pattern[bytes]:
    """'11 DF ?? 08' -> regex over bytes; '??' is a single-byte wildcard."""
    tokens = hex_pattern.replace(",", " ").split()
    if len(tokens) == 1 and len(tokens[0]) > 2:  # allow '11DF??08'
        t = tokens[0]
        tokens = [t[i : i + 2] for i in range(0, len(t), 2)]
    parts = []
    for tok in tokens:
        if tok in ("??", "?"):
            parts.append(b".")
        else:
            parts.append(re.escape(bytes([int(tok, 16)])))
    return re.compile(b"".join(parts), re.DOTALL)


def find(data: bytes, pattern: re.Pattern[bytes], align: int = 1, limit: int | None = None) -> list[int]:
    hits = []
    pos = 0
    while (m := pattern.search(data, pos)) is not None:
        if m.start() % align == 0:
            hits.append(m.start())
            if limit and len(hits) >= limit:
                break
        pos = m.start() + 1
    return hits


def u32_pattern(value: int) -> re.Pattern[bytes]:
    return re.compile(re.escape(value.to_bytes(4, "little")))
