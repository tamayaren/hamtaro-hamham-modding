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
