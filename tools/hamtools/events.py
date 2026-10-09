"""Static walker over the event scripts, from every scene entry, without running the game.

The command lengths and flow rules are documented in kb/event_scripts.md, and the per-function
operand counts of native calls (command 0x1c) in kb/event_natives.csv. This module only
reads the ROM; it never stores ROM bytes.
"""

from __future__ import annotations

import bisect
import csv
import struct
from dataclasses import dataclass, field
from pathlib import Path

from .paths import KB_DIR
from .rom import ROM_BASE

SCENE_TABLE = 0x08466944
SCENE_COUNT = 11                 # 0x08466970 starts descriptors, not a twelfth pointer
DESCRIPTOR_SIZE = 0x10
LAST_OPCODE = 0x60

# Length of each command including the opcode byte (kb/event_scripts.md). 0x1c and 0x1d
# are variable: native call is 5 + the function's extra bytes, switch is 2 + 4 * N.
OPCODE_LENGTHS: dict[int, int] = {
    0x00: 1, 0x01: 1, 0x02: 3, 0x03: 1, 0x04: 1, 0x05: 1, 0x06: 9, 0x07: 9,
    0x08: 11, 0x09: 11, 0x0a: 4, 0x0b: 4, 0x0c: 5, 0x0d: 2, 0x0e: 2, 0x0f: 14,
    0x10: 6, 0x11: 7, 0x12: 7, 0x13: 7, 0x14: 9, 0x15: 6, 0x16: 2, 0x17: 2,
    0x18: 10, 0x19: 3, 0x1a: 6, 0x1b: 6, 0x1e: 5, 0x1f: 1,
    0x20: 18, 0x21: 1, 0x22: 9, 0x23: 5, 0x24: 10, 0x25: 6, 0x26: 6, 0x27: 1,
    0x28: 5, 0x29: 3, 0x2a: 3, 0x2b: 3, 0x2c: 11, 0x2d: 4, 0x2e: 5, 0x2f: 8,
    0x30: 10, 0x31: 10, 0x32: 10, 0x33: 8, 0x34: 15, 0x35: 15, 0x36: 4, 0x37: 2,
    0x38: 3, 0x39: 3, 0x3a: 8, 0x3b: 3, 0x3c: 10, 0x3d: 1, 0x3e: 5, 0x3f: 2,
    0x40: 2, 0x41: 8, 0x42: 8, 0x43: 2, 0x44: 8, 0x45: 6, 0x46: 4, 0x47: 3,
    0x48: 4, 0x49: 3, 0x4a: 4, 0x4b: 3, 0x4c: 2, 0x4d: 6, 0x4e: 5, 0x4f: 3,
    0x50: 8, 0x51: 5, 0x52: 2, 0x53: 7, 0x54: 3, 0x55: 2, 0x56: 5, 0x57: 3,
    0x58: 3, 0x59: 5, 0x5a: 1, 0x5b: 3, 0x5c: 12, 0x5d: 3, 0x5e: 4, 0x5f: 1,
    0x60: 1,
}
NATIVE_CALL, SWITCH, JUMP, CALL, CONTEXT = 0x1c, 0x1d, 0x0c, 0x1e, 0x26
SHOW_TEXT = (0x1a, 0x1b)            # text pointer u32 at +2
TERMINATORS = frozenset({0x01, 0x0c, 0x0d, 0x0e, 0x1f, 0x27})
BRANCH_TARGET = {0x22: 5, 0x30: 6, 0x31: 6, 0x32: 6, 0x33: 4, 0x3c: 6}
NATIVE_BRANCH_TARGET = 10           # conditional-jump natives: target u32 at +10
POINTER_REGISTERS = 0x10            # pointer operands below this index 0x03002ba0[]
SWITCH_HIDDEN_RANGE = 0x2000        # extra switch entries must point this close


@dataclass(frozen=True)
class Native:
    address: int
    extra: int | None               # None for scene-end natives
    kind: str                       # fixed / branch / scene-end
    confidence: str


def load_natives(path: Path | None = None) -> dict[int, Native]:
    path = path or KB_DIR / "event_natives.csv"
    natives = {}
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            addr = int(row["address"], 16)
            extra = int(row["extra_bytes"]) if row["extra_bytes"] else None
            natives[addr] = Native(addr, extra, row["kind"], row["confidence"])
    return natives


class _Rom:
    def __init__(self, data: bytes):
        self.data = data

    def ok(self, addr: int, size: int = 1) -> bool:
        return ROM_BASE <= addr and addr + size <= ROM_BASE + len(self.data)

    def u8(self, addr: int) -> int:
        return self.data[addr - ROM_BASE]

    def u32(self, addr: int) -> int:
        return struct.unpack_from("<I", self.data, addr - ROM_BASE)[0]


def scene_roots(data: bytes) -> dict[int, str]:
    """Entry script of every scene/subscene descriptor, labelled 'scene.subscene'.

    A scene's descriptor array ends where the next scene's array starts, or at the first
    entry that does not hold a ROM event pointer plus a ROM-or-zero callback pointer.
    """
    rom = _Rom(data)
    arrays = [(s, rom.u32(SCENE_TABLE + 4 * s)) for s in range(SCENE_COUNT)]
    arrays = [(s, p) for s, p in arrays if rom.ok(p, DESCRIPTOR_SIZE)]
    starts = sorted({p for _, p in arrays})
    roots: dict[int, str] = {}
    for scene, start in arrays:
        end = min([x for x in starts if x > start] + [start + 0x40 * DESCRIPTOR_SIZE])
        for sub, desc in enumerate(range(start, end, DESCRIPTOR_SIZE)):
            entry, callbacks = rom.u32(desc), rom.u32(desc + 4)
            if not (rom.ok(entry) and (callbacks == 0 or rom.ok(callbacks))):
                break
            roots.setdefault(entry, f"{scene}.{sub}")
    return roots


@dataclass
class TextRef:
    command: int                    # address of the 0x1a/0x1b command
    opcode: int
    root: str                       # scene.subscene label of the entry that reached it


@dataclass
class Walk:
    roots: dict[int, str]
    commands: dict[int, int] = field(default_factory=dict)     # address -> opcode
    sizes: dict[int, int] = field(default_factory=dict)        # address -> command length
    texts: dict[int, list[TextRef]] = field(default_factory=dict)
    problems: list[tuple[int, str]] = field(default_factory=list)
    indirect: list[int] = field(default_factory=list)          # commands using a pointer register
    unknown_natives: dict[int, list[int]] = field(default_factory=dict)


def walk(data: bytes, natives: dict[int, Native] | None = None,
         roots: dict[int, str] | None = None, *,
         extra_roots: dict[int, str] | None = None) -> Walk:
    """Decode scripts from scene entries, or from explicit roots for analysis.

    Extra roots supplement the selected roots. Their labels identify their source;
    the caller must establish that source before claiming runtime reachability.
    No byte-pattern candidate is automatically promoted to a scene entry.
    """
    rom = _Rom(data)
    natives = load_natives() if natives is None else natives
    selected = scene_roots(data) if roots is None else dict(roots)
    for address, label in (extra_roots or {}).items():
        selected.setdefault(address, label)
    result = Walk(selected)
    todo = [(addr, label) for addr, label in result.roots.items()]
    todo.reverse()
    while todo:
        addr, label = todo.pop()
        pending: list[tuple[int, str]] = []

        def follow(command: int, target: int) -> None:
            if target < POINTER_REGISTERS:
                result.indirect.append(command)
            elif rom.ok(target):
                pending.append((target, label))
            else:
                result.problems.append((command, f"target {target:#x} outside ROM"))

        while addr not in result.commands:
            if not rom.ok(addr):
                result.problems.append((addr, "cursor outside ROM"))
                break
            op = rom.u8(addr)
            if op > LAST_OPCODE:
                result.problems.append((addr, f"invalid opcode {op:#04x}"))
                break
            stop = op in TERMINATORS
            if op == NATIVE_CALL:
                if not rom.ok(addr, 5):
                    result.problems.append((addr, "truncated native-call pointer"))
                    break
                fn = rom.u32(addr + 1) & ~1
                native = natives.get(fn)
                if native is None:
                    result.unknown_natives.setdefault(fn, []).append(addr)
                    result.commands[addr] = op
                    result.sizes[addr] = 5
                    break
                if native.kind == "scene-end":
                    result.commands[addr] = op
                    result.sizes[addr] = 5
                    break
                if native.kind == "branch":
                    if not rom.ok(addr, NATIVE_BRANCH_TARGET + 4):
                        result.problems.append((addr, "truncated native branch target"))
                        break
                    follow(addr, rom.u32(addr + NATIVE_BRANCH_TARGET))
                length = 5 + native.extra
            elif op == SWITCH:
                if not rom.ok(addr, 2):
                    result.problems.append((addr, "truncated switch count"))
                    break
                count = rom.u8(addr + 1)
                length = 2 + 4 * count
                if not rom.ok(addr, length):
                    result.problems.append((addr, "switch table runs past ROM end"))
                    break
                for k in range(count):
                    follow(addr, rom.u32(addr + 2 + 4 * k))
                # 0x1d does not bounds-check; extra valid pointers mean the
                # fall-through is never taken (kb/event_scripts.md, script quirks).
                k, hidden = count, 0
                while rom.ok(addr + 6 + 4 * k):
                    t = rom.u32(addr + 2 + 4 * k)
                    if not (rom.ok(t) and abs(t - addr) < SWITCH_HIDDEN_RANGE):
                        break
                    follow(addr, t)
                    k, hidden = k + 1, hidden + 1
                stop = stop or hidden > 0
            else:
                length = OPCODE_LENGTHS[op]
            if not rom.ok(addr, length):
                result.problems.append((addr, "command runs past ROM end"))
                break
            result.commands[addr] = op
            result.sizes[addr] = length
            if op in SHOW_TEXT:
                t = rom.u32(addr + 2)
                if t < POINTER_REGISTERS:
                    result.indirect.append(addr)
                elif rom.ok(t):
                    result.texts.setdefault(t, []).append(TextRef(addr, op, label))
                else:
                    result.problems.append((addr, f"text {t:#x} outside ROM"))
            if op in BRANCH_TARGET:
                follow(addr, rom.u32(addr + BRANCH_TARGET[op]))
            if op in (JUMP, CALL):
                follow(addr, rom.u32(addr + 1))
            if op == CONTEXT and rom.u32(addr + 2) != 0xFFFFFFFF:
                follow(addr, rom.u32(addr + 2))
            if stop:
                break
            addr += length
        # Depth-first in program order: the first target found is decoded next.
        todo.extend(reversed(pending))
    return result


@dataclass(frozen=True)
class TextCandidate:
    command: int
    opcode: int
    slot: int
    target: int


def stray_text_refs(data: bytes, walked: Walk) -> list[TextCandidate]:
    """Find unreached text-shaped commands for a separate, tentative inventory.

    Require a slot below 0x10 and a pointer within the observed text-address span.
    Exclude patterns inside decoded command operands. These are likely script
    fragments, not proven roots: see kb/text_coverage.md for the entry-point audit.
    The observed span is a search filter, not a claim about text-bank boundaries.
    """
    if not walked.texts:
        return []
    rom = _Rom(data)
    low, high = min(walked.texts), max(walked.texts)
    starts = sorted(walked.commands)
    found = []
    for op in SHOW_TEXT:
        pos = data.find(bytes([op]))
        while pos >= 0:
            address = ROM_BASE + pos
            pos = data.find(bytes([op]), pos + 1)
            if address in walked.commands or not rom.ok(address, 6):
                continue
            slot, target = rom.u8(address + 1), rom.u32(address + 2)
            if slot >= POINTER_REGISTERS or not low <= target <= high:
                continue
            previous = bisect.bisect_right(starts, address) - 1
            if previous >= 0:
                owner = starts[previous]
                if address < owner + walked.sizes.get(owner, 1):
                    continue
            found.append(TextCandidate(address, op, slot, target))
    return sorted(found, key=lambda candidate: candidate.command)
