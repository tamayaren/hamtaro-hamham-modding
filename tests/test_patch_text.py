"""Synthetic placement/conflict tests, plus ROM-gated dialogue build checks."""

import json
import os

import pytest

from hamtools import bps, events, patch, rom, text, text_layout

BASE = rom.ROM_BASE
NODE = BASE + 0x100
COMMANDS = (BASE + 0x20, BASE + 0x37)


def _toml(root, entries, extra="", name="dialogue"):
    mod = root / name
    mod.mkdir(parents=True, exist_ok=True)
    body = f'name = "{name}"\n' + extra
    for entry in entries:
        body += "\n[[text]]\n"
        for key, value in entry.items():
            body += f"{key} = {json.dumps(value, ensure_ascii=False)}\n"
    (mod / "mod.toml").write_text(body, "utf-8", newline="\n")


@pytest.fixture
def image(monkeypatch, tmp_path):
    data = bytearray(b"\xff" * 0x1000)
    old = text.encode("An invented test line.[end]")
    data[NODE - BASE:NODE - BASE + len(old)] = old
    refs = []
    for command, opcode in zip(COMMANDS, (0x1a, 0x1b)):
        off = command - BASE
        data[off:off + 6] = bytes([opcode, 0]) + NODE.to_bytes(4, "little")
        refs.append(events.TextRef(command, opcode, "0.0"))
    walked = events.Walk({}, texts={NODE: refs})
    monkeypatch.setattr(events, "walk", lambda _: walked)
    monkeypatch.setattr(patch, "FREE_BASE", BASE + 0x400)
    monkeypatch.setattr(patch, "FREE_END", BASE + len(data))
    monkeypatch.setattr(text_layout, "GLYPH_WIDTHS", BASE + 0x200)
    data[0x200:0x400] = b"\x06" * 0x200
    original = bytes(data)
    monkeypatch.setattr(rom, "load_rom", lambda: original)
    monkeypatch.setattr(rom, "rom_path", lambda: tmp_path / "original.gba")
    monkeypatch.setattr(rom, "EXPECTED_SHA1", rom.sha1(original))
    return original, old, walked


def _entry(old, authored="New line.[end]", address=NODE, **options):
    return {"address": address, "expect_sha1": rom.sha1(old), "text": authored, **options}


def _build(tmp_path, entries, extra=""):
    root, out = tmp_path / "mods", tmp_path / "build"
    _toml(root, entries, extra)
    log = patch.build(root=root, out_dir=out)
    return (out / "hamtaro-mod.gba").read_bytes(), log


def test_shorter_text_in_place_preserves_neighbors_and_pointers(image, tmp_path):
    original, old, _ = image
    raw = text.encode("New line.[end]")
    built, log = _build(tmp_path, [_entry(old)])
    expected = bytearray(original)
    expected[0x100:0x100 + len(raw)] = raw
    assert built == expected
    assert any("in place" in line for line in log)
    assert bps.apply(original, (tmp_path / "build/hamtaro-mod.bps").read_bytes()) == built


def test_growth_repoints_all_unaligned_opcodes_and_deduplicates_roots(image, tmp_path):
    original, old, walked = image
    walked.texts[NODE].append(events.TextRef(COMMANDS[0], 0x1a, "1.0"))
    authored = "An authored line that needs much more room.[end]"
    built, log = _build(tmp_path, [_entry(old, authored)])
    raw = text.encode(authored)
    assert built[0x400:0x400 + len(raw)] == raw
    for command in COMMANDS:
        off = command - BASE
        assert built[off:off + 2] == original[off:off + 2]
        assert int.from_bytes(built[off + 2:off + 6], "little") == patch.FREE_BASE
    assert built[0x100:0x100 + len(old)] == old
    assert any("2 reference(s)" in line for line in log)


@pytest.mark.parametrize("edit_tail", [False, True])
def test_shared_tail_forces_relocation_even_when_new_text_fits(image, tmp_path, edit_tail):
    original, old, walked = image
    tail = NODE + 3
    walked.texts[tail] = [events.TextRef(COMMANDS[1], 0x1b, "0.0")]
    walked.texts[NODE] = [walked.texts[NODE][0]]
    # The fixture's second reference originally points at NODE. Keep it truthful.
    updated = bytearray(original)
    off = COMMANDS[1] - BASE + 2
    updated[off:off + 4] = tail.to_bytes(4, "little")
    from unittest.mock import patch as mock_patch
    with mock_patch.object(rom, "load_rom", return_value=bytes(updated)), \
            mock_patch.object(rom, "EXPECTED_SHA1", rom.sha1(updated)):
        source = old[3:] if edit_tail else old
        built, log = _build(tmp_path, [_entry(source, "X[end]", tail if edit_tail else NODE)])
    assert built[0x100:0x100 + len(old)] == old
    assert any("shared tail" in line for line in log)
    unchanged_command = COMMANDS[0] if edit_tail else COMMANDS[1]
    off = unchanged_command - BASE + 2
    assert built[off:off + 4] == updated[off:off + 4]


@pytest.mark.parametrize("extra", [
    '[[edit]]\naddress = 0x08000100\nexpect = "0c"\nhex = "0d"\n',
    '[[edit]]\naddress = 0x08000022\nexpect = "00 01 00 08"\nhex = "10 01 00 08"\n',
])
@pytest.mark.parametrize("authored", ["Short.[end]", "A much longer authored replacement line.[end]"])
def test_text_conflicts_with_manual_stream_or_reference_edit(image, tmp_path, extra, authored):
    _, old, _ = image
    with pytest.raises(patch.PatchError, match="overlaps"):
        _build(tmp_path, [_entry(old, authored)], extra)
    assert not (tmp_path / "build/hamtaro-mod.gba").exists()


def test_allocator_skips_manual_edits_from_later_mods(image, tmp_path):
    original, old, _ = image
    root, out = tmp_path / "mods", tmp_path / "build"
    _toml(root, [_entry(old, "A much longer authored replacement line.[end]")])
    _toml(root, [], '[[edit]]\naddress = 0x08000400\nexpect = "ff ff ff ff"\nhex = "12 34 56 78"\n', "z-other")
    patch.build(root=root, out_dir=out)
    built = (out / "hamtaro-mod.gba").read_bytes()
    assert built[0x400:0x404] == b"\x12\x34\x56\x78"
    assert int.from_bytes(built[0x22:0x26], "little") == patch.FREE_BASE + 4
    assert len(built) == len(original)


def test_allocator_shares_space_with_compiled_code(image, tmp_path, monkeypatch):
    _, old, _ = image
    blob = b"\x11\x22\x33\x44\x55"
    monkeypatch.setattr(patch, "compile_code", lambda *a: (blob, {}, []))
    built, _ = _build(tmp_path, [_entry(old, "A much longer authored replacement line.[end]")])
    assert built[0x400:0x405] == blob
    assert int.from_bytes(built[0x22:0x26], "little") == patch.FREE_BASE + 8


def test_multiple_texts_get_disjoint_allocations(image, tmp_path, monkeypatch):
    original, old, walked = image
    other = NODE + 0x60
    updated = bytearray(original)
    updated[0x160:0x160 + len(old)] = old
    off = COMMANDS[1] - BASE + 2
    updated[off:off + 4] = other.to_bytes(4, "little")
    walked.texts[other] = [walked.texts[NODE].pop()]
    monkeypatch.setattr(rom, "load_rom", lambda: bytes(updated))
    monkeypatch.setattr(rom, "EXPECTED_SHA1", rom.sha1(updated))
    authored = "A much longer authored replacement line.[end]"
    built, _ = _build(tmp_path, [_entry(old, authored), _entry(old, authored, other)])
    targets = [int.from_bytes(built[c - BASE + 2:c - BASE + 6], "little") for c in COMMANDS]
    assert targets[1] >= targets[0] + len(text.encode(authored))


@pytest.mark.parametrize("change, error", [
    ({"expect_sha1": "0" * 40}, "SHA1 mismatch"),
    ({"expect_sha1": ""}, "expect_sha1"),
    ({"text": "No terminator"}, "invalid text"),
    ({"text": "First[end]unreachable[end]"}, "one stream"),
    ({"text": "[unknown][end]"}, "unknown tag"),
    ({"text": "{f0}[end]"}, "invalid text"),
    ({"text": "[word 00]Test[end]", "font": 2}, "font must"),
    ({"address": BASE + 0x50}, "not a directly referenced"),
    ({"address": 0x080d9762}, "pointer-register"),
    ({"address": 0x080d9772}, "pointer-register"),
])
def test_invalid_entries_fail_before_outputs(image, tmp_path, change, error):
    _, old, _ = image
    entry = _entry(old)
    entry.update(change)
    with pytest.raises(patch.PatchError, match=error):
        _build(tmp_path, [entry])
    assert not (tmp_path / "build/hamtaro-mod.gba").exists()


def test_terminator_looking_control_operand_is_allowed(image, tmp_path):
    _, old, _ = image
    built, _ = _build(tmp_path, [_entry(old, "[callback e0]Hi[null]")])
    assert built[0x100:0x105] == text.encode("[callback e0]Hi[null]")


def test_duplicate_and_invalid_reference_are_rejected(image, tmp_path):
    _, old, walked = image
    with pytest.raises(patch.PatchError, match="duplicate text"):
        _build(tmp_path, [_entry(old), _entry(old)])
    walked.texts[NODE][0].command += 1
    with pytest.raises(patch.PatchError, match="invalid text reference"):
        _build(tmp_path, [_entry(old)])


def test_incomplete_walk_is_rejected(image, tmp_path):
    _, old, walked = image
    walked.problems.append((COMMANDS[0], "synthetic missing opcode"))
    with pytest.raises(patch.PatchError, match="event walk is incomplete"):
        _build(tmp_path, [_entry(old)])


def test_insert_table_shared_tail_is_protected(image, tmp_path, monkeypatch):
    _, old, _ = image
    monkeypatch.setattr(text, "insert_table", lambda _: [NODE + 3])
    built, log = _build(tmp_path, [_entry(old)])
    assert built[0x100:0x100 + len(old)] == old
    assert any("shared tail" in line for line in log)


@pytest.mark.parametrize("output_name", ["hamtaro-mod.gba", "hamtaro-mod.bps"])
def test_original_rom_hardlink_is_never_overwritten(image, tmp_path, output_name):
    original, old, _ = image
    source, out = tmp_path / "original.gba", tmp_path / "build"
    source.write_bytes(original)
    out.mkdir()
    try:
        os.link(source, out / output_name)
    except OSError:
        pytest.skip("hard links not supported in this test directory")
    with pytest.raises(patch.PatchError, match="overwrite the original"):
        _build(tmp_path, [_entry(old)])
    assert source.read_bytes() == original


def test_free_space_exhaustion_and_nonpadding_fail(image, tmp_path, monkeypatch):
    original, old, _ = image
    entry = _entry(old, "A much longer authored replacement line.[end]")
    monkeypatch.setattr(patch, "FREE_END", patch.FREE_BASE + 4)
    with pytest.raises(patch.PatchError, match="does not fit"):
        _build(tmp_path, [entry])
    monkeypatch.setattr(patch, "FREE_END", BASE + len(original))
    updated = bytearray(original)
    updated[0x400] = 1
    monkeypatch.setattr(rom, "load_rom", lambda: bytes(updated))
    monkeypatch.setattr(rom, "EXPECTED_SHA1", rom.sha1(updated))
    with pytest.raises(patch.PatchError, match="not all 0xFF"):
        _build(tmp_path, [entry])


def test_out_of_bounds_edit_and_original_output_are_rejected(image, tmp_path, monkeypatch):
    _, old, _ = image
    extra = '[[edit]]\naddress = 0x08000fff\nexpect = "ff ff"\nhex = "12 34"\n'
    with pytest.raises(patch.PatchError, match="outside"):
        _build(tmp_path, [_entry(old)], extra)
    monkeypatch.setattr(rom, "rom_path", lambda: tmp_path / "build/hamtaro-mod.gba")
    with pytest.raises(patch.PatchError, match="overwrite the original"):
        _build(tmp_path, [_entry(old)])


def test_layout_warnings_and_explicit_page_controls(image, tmp_path):
    original, _, _ = image
    raw = text.encode("WWWW\nA\nB\nC[end]")
    warnings = text_layout.warnings(original, raw, width=20, lines=3)
    assert any("28px" in w for w in warnings)
    assert any("4 lines" in w for w in warnings)
    assert not text_layout.warnings(original, text.encode("A\nB[page]C\nD[end]"))
    assert any("inserted" in w for w in text_layout.warnings(original, text.encode("[word 00][end]")))


def _real_rom():
    try:
        data = rom.load_rom()
    except rom.RomError:
        pytest.skip("needs the original ROM")
    if rom.sha1(data) != rom.EXPECTED_SHA1:
        pytest.skip("not the expected ROM")
    return data


@pytest.mark.parametrize("authored", [
    "[callback 08]A new test line.[end]",
    "[callback 08]A new test line.\nAnother authored line.[page]"
    "This needs a larger stream.\nIt must be relocated.[page]Final test page.[end]",
])
def test_real_rom_build_text_and_bps(tmp_path, authored):
    original = _real_rom()
    address = 0x0846cc6b
    old = text.read_stream(original, address).raw
    root, out = tmp_path / "mods", tmp_path / "build"
    _toml(root, [_entry(old, authored, address)])
    patch.build(root=root, out_dir=out)
    built = (out / "hamtaro-mod.gba").read_bytes()
    refs = {r.command for r in events.walk(original).texts[address]}
    targets = {int.from_bytes(built[r - BASE + 2:r - BASE + 6], "little") for r in refs}
    assert len(targets) == 1
    target = targets.pop()
    raw = text.encode(authored)
    off = target - BASE
    assert built[off:off + len(raw)] == raw
    assert (target == address) == (len(raw) <= len(old))
    assert len(built) == len(original)
    assert bps.apply(original, (out / "hamtaro-mod.bps").read_bytes()) == built
    assert rom.load_rom() == original


def test_real_rom_text_coexists_with_c_dialogue(tmp_path):
    original = _real_rom()
    try:
        patch.paths.arm_tool("gcc")
    except patch.paths.ToolNotFound:
        pytest.skip("needs arm-none-eabi toolchain")
    root, out = tmp_path / "mods", tmp_path / "build"
    old = text.read_stream(original, 0x0846cc6b).raw
    authored = "[callback 08]" + ("An authored page.[page]" * 8) + "Done.[end]"
    extra = ('sources = ["main.c"]\n[[pointer]]\naddress = 0x087fff20\n'
             'expect = "ff ff ff ff"\ntarget = "Mod_Text"\n')
    _toml(root, [_entry(old, authored, 0x0846cc6b)], extra)
    (root / "dialogue/main.c").write_text(
        '#include "gba.h"\n#include "dialogue.h"\n'
        'const u8 Mod_Text[] = { DIALOGUE_TEXT("Separate C text."), DIALOGUE_END() };\n',
        "utf-8", newline="\n")
    patch.build(root=root, out_dir=out)
    built = (out / "hamtaro-mod.gba").read_bytes()
    cptr = int.from_bytes(built[0x7fff20:0x7fff24], "little")
    tptr = int.from_bytes(built[0x4ffb6:0x4ffba], "little")
    assert patch.FREE_BASE <= cptr < tptr < patch.FREE_END
    assert text.read_stream(built, cptr).raw == text.encode("Separate C text.[end]")
    assert text.read_stream(built, tptr).raw == text.encode(authored)
