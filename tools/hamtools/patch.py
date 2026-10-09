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

    [[text]]                             # authored replacement in lossless tag notation
    address = 0x0846cc6b                  # original stream, as listed by hamtools text dump
    expect_sha1 = "<SHA1 of original stream including its end byte>"
    text = "[callback 08]Our new dialogue.[end]"

Text fits in place when its original allocation is unshared. Otherwise the builder
allocates after compiled code in free space and redirects every walked 0x1a/0x1b
operand. Hashes keep original dialogue out of public patch sources.

C code can call game functions and use RAM variables from kb/symbols.csv by name: each
symbol is passed to the linker (Thumb functions with bit 0 set). Declare them yourself, e.g.
`extern void Text_DrawGlyph(int c);` / `extern u16 gPlayerX;`.
"""

from __future__ import annotations

import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import bps, dialogue, events, paths, rom, text, text_layout

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
    texts: list[dict] = field(default_factory=list)


def _hex(text: str) -> bytes:
    return bytes.fromhex(text.replace(",", " "))


def load_mods(names: list[str] | None = None, root: Path = PATCHES_DIR) -> list[Mod]:
    mods = []
    for toml_path in sorted(root.glob("*/mod.toml")):
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        mod = Mod(name=data.get("name", toml_path.parent.name), path=toml_path.parent,
                  description=data.get("description", ""), enabled=data.get("enabled", True),
                  sources=[toml_path.parent / s for s in data.get("sources", [])],
                  edits=data.get("edit", []), hooks=data.get("hook", []), pointers=data.get("pointer", []),
                  texts=data.get("text", []))
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
    sources = [(m, s) for m in mods for s in m.sources]
    if not sources:
        return b"", {}, []
    workdir.mkdir(parents=True, exist_ok=True)
    gcc, objcopy, nm = paths.arm_tool("gcc"), paths.arm_tool("objcopy"), paths.arm_tool("nm")
    objs = []
    for index, (mod, src) in enumerate(sources):
        if not src.exists():
            raise PatchError(f"missing source {src}")
        generated = workdir / "generated" / mod.path.name / f"{index}_{src.name}"
        try:
            prepared = dialogue.prepare_source(src, generated)
        except dialogue.DialogueError as exc:
            raise PatchError(str(exc)) from exc
        obj = workdir / f"{src.parent.name}_{src.stem}.o"
        # Quoted mod includes must resolve from the editable source's directory.
        _run([gcc, *CFLAGS, f"-I{src.parent}", f"-I{root / 'include'}", f"-I{PATCHES_DIR / 'include'}", "-c", prepared, "-o", obj],
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
        if not data or off < 0 or end > len(original):
            raise PatchError(f"{who}: write at {address:#010x} is empty or outside the original ROM")
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

    # Explicit edits go first, so allocations can skip every claimed range, even
    # one declared in a later mod. Code and text share the same free-space pool.
    if any(m.texts for m in mods):
        _build_texts(original, mods, claimed, put, FREE_BASE + len(blob), log)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_rom, out_bps = out_dir / OUT_ROM.name, out_dir / OUT_BPS.name
    patch = bps.create(original, bytes(out), metadata="Hamtaro: Ham-Ham Heartbreak mods: "
                       + ", ".join(m.name for m in mods))
    if bps.apply(original, patch) != bytes(out):
        raise PatchError("BPS self-check failed")
    source = rom.rom_path().resolve()
    for output in (out_rom, out_bps):
        if output.resolve() == source or (output.exists() and source.exists() and output.samefile(source)):
            raise PatchError("build output would overwrite the original ROM")
    out_rom.write_bytes(out)
    out_bps.write_bytes(patch)
    changed = sum(1 for a, b in zip(original, out) if a != b)
    log += [f"wrote {out_rom} ({changed} bytes changed)", f"wrote {out_bps} ({len(patch)} bytes)"]
    return log


def _build_texts(original: bytes, mods: list[Mod], claimed: list[tuple[int, int, str]],
                 put, cursor: int, log: list[str]) -> None:
    walked = events.walk(original)
    if walked.problems or walked.unknown_natives:
        raise PatchError("event walk is incomplete; resolve problems and unknown natives before text edits")
    # Protect insert-table tails too, even though this feature only edits streams
    # with direct event-script references. Future walker roots are picked up here.
    addresses = set(walked.texts) | set(text.insert_table(original))
    streams: dict[int, text.Stream] = {}
    for address in sorted(addresses):
        if not rom.ROM_BASE <= address < rom.ROM_BASE + len(original):
            raise PatchError(f"text stream {address:#010x} is outside the ROM")
        try:
            streams[address] = text.read_stream(original, address)
        except text.TextError as exc:
            raise PatchError(f"cannot establish text allocation at {address:#010x}: {exc}") from exc
    intervals = [(a, a + len(s.raw)) for a, s in streams.items()]
    selected: set[int] = set()

    def allocate(raw: bytes, who: str) -> int:
        nonlocal cursor
        limit = min(FREE_END, rom.ROM_BASE + len(original))
        while True:
            cursor = (cursor + 3) & ~3
            end = cursor + len(raw)
            if cursor < FREE_BASE or end > limit:
                raise PatchError(f"{who}: text does not fit in ROM free space")
            collisions = [b + rom.ROM_BASE for a, b, _ in claimed
                          if cursor < b + rom.ROM_BASE and a + rom.ROM_BASE < end]
            if not collisions:
                break
            cursor = max(collisions)
        off = rom.to_offset(cursor)
        if any(byte != 0xFF for byte in original[off:off + len(raw)]):
            raise PatchError(f"{who}: free-space region at {cursor:#010x} is not all 0xFF")
        address = cursor
        put(address, raw, None, who)
        cursor = end
        return address

    for mod in mods:
        for index, entry in enumerate(mod.texts):
            who = f"{mod.name}.text[{index}]"
            address, raw = _text_entry(entry, who)
            if address in getattr(walked, "indirect", ()) or address in (0x080d9762, 0x080d9772):
                raise PatchError(f"{who}: {address:#010x} is a pointer-register command; "
                                 "its runtime-selected text cannot be repointed")
            if address not in walked.texts:
                raise PatchError(f"{who}: {address:#010x} is not a directly referenced text stream; "
                                 "use its address from hamtools text dump")
            if address in selected:
                raise PatchError(f"{who}: duplicate text replacement for {address:#010x}")
            selected.add(address)
            old = streams[address].raw
            if rom.sha1(old) != entry["expect_sha1"].lower():
                raise PatchError(f"{who}: original stream SHA1 mismatch at {address:#010x}")
            refs = {ref.command: ref for ref in walked.texts[address]}
            if not refs:
                raise PatchError(f"{who}: no direct references to {address:#010x}; cannot repoint")
            for command, ref in refs.items():
                off = command - rom.ROM_BASE
                if (ref.opcode not in (0x1a, 0x1b) or not 0 <= off <= len(original) - 6
                        or original[off] != ref.opcode
                        or original[off + 2:off + 6] != address.to_bytes(4, "little")):
                    raise PatchError(f"{who}: invalid text reference at {command:#010x}")
            for warning in text_layout.warnings(original, raw, **_layout_options(entry, who)):
                log.append(f"warning {who}: {warning}")
            if raw == old:
                log.append(f"text   {address:#010x} unchanged")
                continue
            # Even an in-place replacement owns its direct references: a manual
            # redirect would silently make the edited stream unreachable there.
            for command in refs:
                off = command + 2 - rom.ROM_BASE
                for a, b, other in claimed:
                    if off < b and a < off + 4:
                        raise PatchError(f"{who}.ref[{command:#010x}] overlaps {other} "
                                         f"at {command + 2:#010x}")
            start = rom.to_offset(address)
            for a, b, other in claimed:
                if start < b and a < start + len(old):
                    raise PatchError(f"{who} overlaps {other} at {address:#010x}")
            shared = any(a != address and a < address + len(old) and address < b
                         for a, b in intervals)
            if len(raw) <= len(old) and not shared:
                put(address, raw, None, who)
                log.append(f"text   {address:#010x} in place ({len(raw)}/{len(old)} bytes)")
            else:
                target = allocate(raw, who)
                for command in sorted(refs):
                    put(command + 2, target.to_bytes(4, "little"), address.to_bytes(4, "little"),
                        f"{who}.ref[{command:#010x}]")
                reason = "shared tail" if shared else "longer text"
                log.append(f"text   {address:#010x} -> {target:#010x} ({len(raw)} bytes; "
                           f"{len(refs)} reference(s); {reason})")


def _text_entry(entry: dict, who: str) -> tuple[int, bytes]:
    address = entry.get("address")
    if not isinstance(address, int) or isinstance(address, bool):
        raise PatchError(f"{who}: 'address' must be a full ROM address such as 0x0846cc6b")
    digest = entry.get("expect_sha1")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-fA-F]{40}", digest) is None:
        raise PatchError(f"{who}: 'expect_sha1' (40 hex digits; original stream including end) is required")
    authored = entry.get("text")
    if not isinstance(authored, str):
        raise PatchError(f"{who}: 'text' must be a string in hamtools text tag notation")
    try:
        raw = text.encode(authored)
        text.validate_stream(raw)
    except text.TextError as exc:
        raise PatchError(f"{who}: invalid text: {exc}") from exc
    return address, raw


def _layout_options(entry: dict, who: str) -> dict[str, int]:
    options = {key: entry.get(key, default) for key, default in
               (("width", 168), ("lines", 3), ("spacing", 1), ("font", 0))}
    for key, value in options.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < (1 if key in ("width", "lines") else 0):
            raise PatchError(f"{who}: invalid layout option {key!r}")
    if options["font"] not in (0, 1) or options["spacing"] > 0x7f:
        raise PatchError(f"{who}: font must be 0 or 1 and spacing must be 0..127")
    return options


def _required(who: str):
    raise PatchError(f"{who}: 'expect' (the original bytes) is required")
