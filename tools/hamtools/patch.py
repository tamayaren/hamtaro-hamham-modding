"""Build mods from patches/<mod>/mod.toml into build/hamtaro-mod.gba + .bps.

mod.toml:

    name = "example"
    description = "what it does"
    enabled = true
    sources = ["main.c", "hooks.s"]      # optional; compiled to Thumb into ROM free space

    [[edit]]                             # replace bytes in place
    address = 0x08012344
    expect = "00 20"                     # original bytes — required, build fails if they differ
    hex = "01 20"
    comment = "start with 1 life"

    [[hook]]                             # point a Thumb BL (4 bytes) at one of our functions
    address = 0x08012350
    expect = "ff f7 e6 ff"
    target = "Mod_MyFunction"

    [[pointer]]                          # overwrite a 4-byte pointer with our symbol's address
    address = 0x08123450
    expect = "35 12 01 08"
    target = "Mod_MyTable"
    thumb = false                        # true adds 1 (Thumb function pointer)

C code can call game functions and use RAM variables from kb/symbols.csv by name: each
symbol is passed to the linker (Thumb functions with bit 0 set). Declare them yourself, e.g.
`extern void Text_DrawGlyph(int c);` / `extern u16 gPlayerX;`.
"""

from __future__ import annotations

import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import bps, paths, rom

PATCHES_DIR = paths.REPO_ROOT / "patches"
FREE_BASE = 0x086D0000          # inside the verified 0xFF tail (kb/rom_map.md)
FREE_END = 0x08800000
OUT_ROM = paths.BUILD_DIR / "hamtaro-mod.gba"
OUT_BPS = paths.BUILD_DIR / "hamtaro-mod.bps"
CFLAGS = ["-mthumb", "-mthumb-interwork", "-mcpu=arm7tdmi", "-mlong-calls", "-O2", "-ffreestanding",
          "-fno-builtin", "-nostdlib", "-Wall"]


class PatchError(Exception):
    pass


@dataclass
class Mod:
    name: str
    path: Path
    description: str = ""
    enabled: bool = True
    sources: list[Path] = field(default_factory=list)
    edits: list[dict] = field(default_factory=list)
    hooks: list[dict] = field(default_factory=list)
    pointers: list[dict] = field(default_factory=list)


def _hex(text: str) -> bytes:
    return bytes.fromhex(text.replace(",", " "))


def load_mods(names: list[str] | None = None, root: Path = PATCHES_DIR) -> list[Mod]:
    mods = []
    for toml_path in sorted(root.glob("*/mod.toml")):
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        mod = Mod(name=data.get("name", toml_path.parent.name), path=toml_path.parent,
                  description=data.get("description", ""), enabled=data.get("enabled", True),
                  sources=[toml_path.parent / s for s in data.get("sources", [])],
                  edits=data.get("edit", []), hooks=data.get("hook", []), pointers=data.get("pointer", []))
        if names is not None:
            if toml_path.parent.name in names or mod.name in names:
                mods.append(mod)
        elif mod.enabled:
            mods.append(mod)
    if names:
        found = {m.path.name for m in mods} | {m.name for m in mods}
        missing = [n for n in names if n not in found]
        if missing:
            raise PatchError(f"unknown mod(s): {', '.join(missing)}")
    return mods


def _game_symbols() -> list[tuple[str, int]]:
    from .ghidra import read_symbols  # csv parsing only; does not start Ghidra
    out = []
    for s in read_symbols():
        value = s.address | 1 if s.kind == "func" and s.mode == "thumb" else s.address
        out.append((s.name, value))
    return out


def _run(cmd: list, what: str) -> str:
    proc = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if proc.returncode != 0:
        raise PatchError(f"{what} failed:\n{proc.stdout}{proc.stderr}")
    return proc.stdout


def compile_code(mods: list[Mod], workdir: Path, root: Path = PATCHES_DIR) -> tuple[bytes, dict[str, int], list[str]]:
    """Compile and link all mod sources at FREE_BASE. Returns (blob, symbols, log)."""
    sources = [s for m in mods for s in m.sources]
    if not sources:
        return b"", {}, []
    workdir.mkdir(parents=True, exist_ok=True)
    gcc, objcopy, nm = paths.arm_tool("gcc"), paths.arm_tool("objcopy"), paths.arm_tool("nm")
    objs = []
    for src in sources:
        if not src.exists():
            raise PatchError(f"missing source {src}")
        obj = workdir / f"{src.parent.name}_{src.stem}.o"
        _run([gcc, *CFLAGS, f"-I{src.parent}", f"-I{root / 'include'}", f"-I{PATCHES_DIR / 'include'}", "-c", src, "-o", obj],
             f"compile {src.name}")
        objs.append(obj)

    ld_script = workdir / "mod.ld"
    ld_script.write_text(
        "SECTIONS {\n"
        f"  . = {FREE_BASE:#x};\n"
        "  .text : { *(.text*) *(.rodata*) *(.data*) }\n"
        "  /DISCARD/ : { *(.bss*) *(COMMON) *(.ARM.attributes) *(.comment) }\n"
        "}\n", encoding="utf-8")
    defsyms = []
    for name, value in _game_symbols():
        defsyms.append(f"-Wl,--defsym={name}={value:#x}")
    elf = workdir / "mod.elf"
    _run([gcc, *CFLAGS, "-T", ld_script, *objs, *defsyms,
          "-Wl,-Map=" + str(workdir / "mod.map"), "-o", elf, "-lgcc"], "link")
    blob_path = workdir / "mod.bin"
    _run([objcopy, "-O", "binary", "-j", ".text", elf, blob_path], "objcopy")
    blob = blob_path.read_bytes()

    symbols = {}
    for line in _run([nm, "--defined-only", elf], "nm").splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1] in "TtDdRr":
            value = int(parts[0], 16)
            if FREE_BASE <= value < FREE_END:
                symbols[parts[2]] = value
    if FREE_BASE + len(blob) > FREE_END:
        raise PatchError("mod code does not fit in free space")
    return blob, symbols, [f"code: {len(blob):#x} bytes at {FREE_BASE:#010x}, {len(symbols)} symbols"]


def _thumb_bl(src: int, dst: int) -> bytes:
    off = (dst & ~1) - (src + 4)
    if not -(1 << 22) <= off < (1 << 22):
        raise PatchError(f"BL from {src:#010x} to {dst:#010x} out of range (±4 MB) — use a pointer or veneer")
    off >>= 1
    hi = 0xF000 | ((off >> 11) & 0x7FF)
    lo = 0xF800 | (off & 0x7FF)
    return hi.to_bytes(2, "little") + lo.to_bytes(2, "little")


def build(names: list[str] | None = None, root: Path = PATCHES_DIR,
          out_dir: Path = paths.BUILD_DIR) -> list[str]:
    original = rom.load_rom()
    if rom.sha1(original) != rom.EXPECTED_SHA1:
        raise PatchError("original ROM does not match the expected dump")
    mods = load_mods(names, root)
    if not mods:
        raise PatchError("no mods selected (none enabled in patches/*/mod.toml)")
    out = bytearray(original)
    log = [f"mods: {', '.join(m.name for m in mods)}"]
    claimed: list[tuple[int, int, str]] = []

    def put(address: int, data: bytes, expect: bytes | None, who: str) -> None:
        off = rom.to_offset(address)
        end = off + len(data)
        for a, b, other in claimed:
            if off < b and a < end:
                raise PatchError(f"{who} overlaps {other} at {address:#010x}")
        if expect is not None:
            if len(expect) != len(data):
                raise PatchError(f"{who}: expect and new bytes differ in length")
            actual = bytes(original[off:end])
            if actual != expect:
                raise PatchError(f"{who}: original bytes at {address:#010x} are {actual.hex(' ')}, "
                                 f"mod expects {expect.hex(' ')} — wrong address?")
        out[off:end] = data
        claimed.append((off, end, who))

    blob, symbols, clog = compile_code(mods, out_dir / "obj", root)
    log += clog
    if blob:
        start = rom.to_offset(FREE_BASE)
        if any(b != 0xFF for b in original[start:start + len(blob)]):
            raise PatchError("free-space region is not all 0xFF in the original ROM")
        put(FREE_BASE, blob, None, "mod code")

    def sym(target: str, who: str) -> int:
        if target in symbols:
            return symbols[target]
        raise PatchError(f"{who}: unknown symbol {target!r} (defined: {', '.join(sorted(symbols)) or 'none'})")

    for m in mods:
        for i, e in enumerate(m.edits):
            who = f"{m.name}.edit[{i}]"
            put(int(e["address"]), _hex(e["hex"]), _hex(e["expect"]) if "expect" in e else _required(who), who)
            log.append(f"edit   {int(e['address']):#010x} {e.get('comment', '')}")
        for i, h in enumerate(m.hooks):
            who = f"{m.name}.hook[{i}]"
            a = int(h["address"])
            put(a, _thumb_bl(a, sym(h["target"], who)), _hex(h["expect"]) if "expect" in h else _required(who), who)
            log.append(f"hook   {a:#010x} -> {h['target']}")
        for i, p in enumerate(m.pointers):
            who = f"{m.name}.pointer[{i}]"
            a = int(p["address"])
            value = sym(p["target"], who) | (1 if p.get("thumb") else 0)
            put(a, value.to_bytes(4, "little"), _hex(p["expect"]) if "expect" in p else _required(who), who)
            log.append(f"ptr    {a:#010x} -> {p['target']}")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_rom, out_bps = out_dir / OUT_ROM.name, out_dir / OUT_BPS.name
    out_rom.write_bytes(out)
    patch = bps.create(original, bytes(out), metadata="Hamtaro: Ham-Ham Heartbreak mods: "
                       + ", ".join(m.name for m in mods))
    if bps.apply(original, patch) != bytes(out):
        raise PatchError("BPS self-check failed")
    out_bps.write_bytes(patch)
    changed = sum(1 for a, b in zip(original, out) if a != b)
    log += [f"wrote {out_rom} ({changed} bytes changed)", f"wrote {out_bps} ({len(patch)} bytes)"]
    return log


def _required(who: str):
    raise PatchError(f"{who}: 'expect' (the original bytes) is required")
