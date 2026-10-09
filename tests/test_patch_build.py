"""End-to-end mod build against the real ROM and ARM toolchain (skipped if either is missing)."""

import pytest

from hamtools import bps, paths, patch, rom

try:
    rom.rom_path()
    paths.arm_tool("gcc")
    HAVE_TOOLS = True
except Exception:  # noqa: BLE001
    HAVE_TOOLS = False

pytestmark = pytest.mark.skipif(not HAVE_TOOLS, reason="needs the ROM and arm-none-eabi toolchain")


def test_build_code_edit_hook_pointer(tmp_path):
    mod = tmp_path / "mods" / "selftest"
    mod.mkdir(parents=True)
    (mod / "main.c").write_text(
        '#include "gba.h"\n'
        "u32 Mod_Add(u32 a, u32 b) { return a + b; }\n"
        "const u16 Mod_Table[2] = { 0x1234, 0x5678 };\n")
    # targets live in the 0xFF tail so the test never touches real game data
    (mod / "mod.toml").write_text(
        'name = "selftest"\nsources = ["main.c"]\n'
        '[[edit]]\naddress = 0x087FFF00\nexpect = "ff ff"\nhex = "12 34"\n'
        '[[hook]]\naddress = 0x087FFF10\nexpect = "ff ff ff ff"\ntarget = "Mod_Add"\n'
        '[[pointer]]\naddress = 0x087FFF20\nexpect = "ff ff ff ff"\ntarget = "Mod_Table"\n')
    out = tmp_path / "build"
    log = patch.build(["selftest"], root=tmp_path / "mods", out_dir=out)
    built = (out / "hamtaro-mod.gba").read_bytes()
    original = rom.load_rom()
    assert built[0x7FFF00:0x7FFF02] == b"\x12\x34"
    # code was placed at FREE_BASE, the pointer targets the table inside it
    ptr = int.from_bytes(built[0x7FFF20:0x7FFF24], "little")
    assert patch.FREE_BASE <= ptr < patch.FREE_BASE + 0x100
    assert built[rom.to_offset(ptr):rom.to_offset(ptr) + 4] == b"\x34\x12\x78\x56"
    # BL encodes a jump into our code
    hi = int.from_bytes(built[0x7FFF10:0x7FFF12], "little")
    lo = int.from_bytes(built[0x7FFF12:0x7FFF14], "little")
    assert hi >> 11 == 0x1E and lo >> 11 == 0x1F
    assert bps.apply(original, (out / "hamtaro-mod.bps").read_bytes()) == built
    assert any("Mod_Add" in line or "hook" in line for line in log)


def test_expect_mismatch_fails(tmp_path):
    mod = tmp_path / "mods" / "bad"
    mod.mkdir(parents=True)
    (mod / "mod.toml").write_text('name = "bad"\n[[edit]]\naddress = 0x08000000\nexpect = "00 00"\nhex = "11 11"\n')
    with pytest.raises(patch.PatchError, match="original bytes"):
        patch.build(["bad"], root=tmp_path / "mods", out_dir=tmp_path / "build")


def test_build_authored_dialogue_keeps_local_includes_and_raw_source(tmp_path):
    mod = tmp_path / "mods" / "dialogue"
    srcdir = mod / "src"
    srcdir.mkdir(parents=True)
    # This quoted include must still resolve relative to the original source.
    (mod / "local.h").write_text(
        '#include "gba.h"\n#include "dialogue.h"\n#define SCENE_CALLBACK 7\n'
    )
    authored = (
        '#include "../local.h"\n'
        'const u8 Mod_Text[] = { DIALOGUE_TEXT("There is a new sunflower\\n"\n'
        '    "by the water."), DIALOGUE_WAIT_LINE(), DIALOGUE_CALL(SCENE_CALLBACK),\n'
        '    DIALOGUE_END() };\n'
    )
    (srcdir / "main.c").write_text(authored)
    legacy = (
        '#include "gba.h"\n'
        '/* DIALOGUE_TEXT("7") is only a comment. */\n'
        'const u8 Mod_Raw[] = { 0x1f, 0x01, 0xe0 };\n'
    )
    (mod / "legacy.c").write_text(legacy)
    (mod / "mod.toml").write_text(
        'name = "dialogue"\nsources = ["src/main.c", "legacy.c"]\n'
        '[[pointer]]\naddress = 0x087FFF20\nexpect = "ff ff ff ff"\ntarget = "Mod_Text"\n'
        '[[pointer]]\naddress = 0x087FFF24\nexpect = "ff ff ff ff"\ntarget = "Mod_Raw"\n'
    )
    out = tmp_path / "build"
    patch.build(["dialogue"], root=tmp_path / "mods", out_dir=out)
    built = (out / "hamtaro-mod.gba").read_bytes()
    text_pointer = int.from_bytes(built[0x7FFF20:0x7FFF24], "little")
    expected = b"\x1fhere\x01is\x01a\x01new\x01sunflower\xe2by\x01the\x01water\xca\xe3\xf4\x07\xe0"
    offset = rom.to_offset(text_pointer)
    assert built[offset:offset + len(expected)] == expected
    raw_pointer = int.from_bytes(built[0x7FFF24:0x7FFF28], "little")
    assert built[rom.to_offset(raw_pointer):rom.to_offset(raw_pointer) + 3] == b"\x1f\x01\xe0"
    assert (srcdir / "main.c").read_text() == authored
    assert (mod / "legacy.c").read_text() == legacy
    generated = list((out / "obj" / "generated" / "dialogue").rglob("*.c"))
    assert len(generated) == 1
    assert "DIALOGUE_TEXT" not in generated[0].read_text()
    assert bps.apply(rom.load_rom(), (out / "hamtaro-mod.bps").read_bytes()) == built
