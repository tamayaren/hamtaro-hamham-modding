"""Explicit entry provenance, operand coincidences, and truncated script headers."""

import struct

import pytest

from hamtools import events

BASE = 0x08000000


def _put(image, address, raw):
    offset = address - BASE
    image[offset:offset + len(raw)] = raw


def _show(target, slot=0):
    return bytes([0x1a, slot]) + struct.pack("<I", target)


def test_extra_root_preserves_source_and_does_not_scan_unrelated_bytes():
    image = bytearray(b"\xff" * 0x200)
    _put(image, BASE + 0x10, _show(BASE + 0x100) + b"\x1f")
    _put(image, BASE + 0x30, _show(BASE + 0x110) + b"\x1f")
    root = BASE + 0x10
    reached = events.walk(bytes(image), {}, roots={root: "scene-source"},
                          extra_roots={root: "alias", BASE + 0x30: "native-source"})
    assert reached.roots == {root: "scene-source", BASE + 0x30: "native-source"}
    assert reached.texts[BASE + 0x110][0].root == "native-source"
    assert not reached.problems
    assert BASE + 0x40 not in reached.commands
    assert events.walk(bytes(image), {}, roots={}).commands == {}


def test_audit_excludes_native_operands_unrelated_targets_and_invalid_slots():
    image = bytearray(b"\xff" * 0x200)
    root, target, native = BASE + 0x10, BASE + 0x100, BASE + 0x1000
    # The native's six operand bytes happen to look exactly like a text command.
    _put(image, root, _show(target) + b"\x1c" + struct.pack("<I", native | 1)
         + _show(target) + b"\x1f")
    _put(image, BASE + 0x40, _show(target) + b"\x1f")
    _put(image, BASE + 0x60, _show(BASE + 0x180) + b"\x1f")
    _put(image, BASE + 0x80, _show(target, 16) + b"\x1f")
    _put(image, BASE + len(image) - 3, b"\x1a\x00\x01")
    natives = {native: events.Native(native, 6, "fixed", "likely")}
    reached = events.walk(bytes(image), natives, roots={root: "test"})
    refs = events.stray_text_refs(bytes(image), reached)
    assert [(r.command, r.target) for r in refs] == [(BASE + 0x40, target)]
    assert reached.sizes[root + 6] == 11
    assert not reached.problems
    assert events.stray_text_refs(bytes(image), events.Walk({})) == []


@pytest.mark.parametrize("raw,natives,message", [
    (b"\x1c\x01\x00\x00", {}, "truncated native-call pointer"),
    (b"\x1d", {}, "truncated switch count"),
    (b"\x1d\x02\x00", {}, "switch table runs past ROM end"),
    (b"\x1c\x01\x10\x00\x08",
     {0x08001000: events.Native(0x08001000, 9, "branch", "likely")},
     "truncated native branch target"),
])
def test_explicit_root_with_truncated_variable_command_reports_problem(raw, natives, message):
    reached = events.walk(raw, natives, roots={BASE: "candidate"})
    assert reached.problems == [(BASE, message)]
    assert not reached.commands
