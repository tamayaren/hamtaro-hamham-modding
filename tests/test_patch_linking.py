"""Link a large synthetic symbol catalogue; no ROM or emulator needed."""

import pytest

from hamtools import patch, paths


def test_large_symbol_catalogue_preserves_function_rom_and_ram_addresses(tmp_path, monkeypatch):
    try:
        for tool in ("gcc", "objcopy", "nm"):
            paths.arm_tool(tool)
    except paths.ToolNotFound:
        pytest.skip("needs arm-none-eabi toolchain")

    # These definitions previously overflowed Windows' 32,767-character command line.
    game_symbols = [(f"Synthetic_UnusedSymbol_{i:04d}", 0x08010000 + i * 4)
                    for i in range(1500)]
    game_symbols += [("Synthetic_ThumbFunction", 0x08001235),
                     ("Synthetic_RomData", 0x08002000),
                     ("Synthetic_RamData", 0x02003000)]
    monkeypatch.setattr(patch, "_game_symbols", lambda: game_symbols)
    mod_dir = tmp_path / "synthetic mod with spaces"
    mod_dir.mkdir()
    source = mod_dir / "main.c"
    source.write_text(
        "extern void Synthetic_ThumbFunction(void);\n"
        "extern const unsigned char Synthetic_RomData[];\n"
        "extern unsigned char Synthetic_RamData[];\n"
        "const void *const Mod_Addresses[] = { (const void *)Synthetic_ThumbFunction,\n"
        "  Synthetic_RomData, Synthetic_RamData };\n",
        encoding="utf-8",
    )
    mod = patch.Mod(name="synthetic", path=mod_dir, sources=[source])
    blob, symbols, _ = patch.compile_code([mod], tmp_path / "build with spaces")
    offset = symbols["Mod_Addresses"] - patch.FREE_BASE
    pointers = [int.from_bytes(blob[offset + i:offset + i + 4], "little")
                for i in range(0, 12, 4)]
    assert pointers == [0x08001235, 0x08002000, 0x02003000]
