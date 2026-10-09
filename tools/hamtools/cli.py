"""`hamtools` command-line entry point. Every subcommand is read-only on the original ROM."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import rom


def _int(text: str) -> int:
    return int(text, 0)


def cmd_rom_verify(args: argparse.Namespace) -> int:
    path = rom.rom_path()
    data = path.read_bytes()
    digest = rom.sha1(data)
    ok = digest == rom.EXPECTED_SHA1 and len(data) == rom.EXPECTED_SIZE
    print(f"path:  {path}")
    print(f"size:  {len(data):#x}")
    print(f"sha1:  {digest}")
    print("OK: expected Hamtaro: Ham-Ham Heartbreak (USA) dump" if ok
          else f"MISMATCH: expected sha1 {rom.EXPECTED_SHA1} — addresses in kb/ may not apply")
    return 0 if ok else 1


def cmd_rom_info(args: argparse.Namespace) -> int:
    data = rom.load_rom()
    h = rom.parse_header(data)
    end = rom.used_end(data)
    print(f"title:        {h.title}")
    print(f"game code:    {h.game_code}  maker: {h.maker}  version: {h.version}")
    print(f"header csum:  {h.checksum:#04x} ({'ok' if h.checksum_ok else 'BAD'})")
    if h.entry_target is not None:
        print(f"entry:        branch to {h.entry_target:#010x}")
    tag = rom.find_save_tag(data)
    print(f"save type:    {tag[1]} at {rom.to_addr(tag[0]):#010x}" if tag else "save type:    (no tag found)")
    print(f"rom size:     {len(data):#x} ({len(data) // 1024} KB)")
    print(f"used through: {rom.to_addr(end - 1):#010x}")
    free = len(data) - end
    if free:
        print(f"free (0xFF):  {rom.to_addr(end):#010x}-{rom.to_addr(len(data) - 1):#010x} ({free:#x} bytes, ~{free // 1024} KB)")
    return 0


def cmd_rom_peek(args: argparse.Namespace) -> int:
    data = rom.load_rom()
    start = rom.to_offset(args.address)
    chunk = data[start : start + args.len]
    for i in range(0, len(chunk), 16):
        row = chunk[i : i + 16]
        hexpart = " ".join(f"{b:02x}" for b in row)
        text = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in row)
        print(f"{rom.to_addr(start + i):08x}  {hexpart:<47}  {text}")
    return 0


def _print_hits(hits: list[int], label: str = "") -> None:
    for off in hits:
        print(f"{rom.to_addr(off):#010x}{label}")


def cmd_rom_find(args: argparse.Namespace) -> int:
    data = rom.load_rom()
    if args.hex:
        pattern = rom.parse_pattern(args.hex)
    elif args.ascii:
        pattern = re.compile(re.escape(args.ascii.encode("ascii")))
    else:
        pattern = rom.u32_pattern(args.u32)
    hits = rom.find(data, pattern, align=args.align, limit=args.limit)
    _print_hits(hits)
    print(f"# {len(hits)} hit(s)", file=sys.stderr)
    return 0


def cmd_rom_xrefs(args: argparse.Namespace) -> int:
    data = rom.load_rom()
    values = [(args.address, "")]
    is_rom = rom.ROM_BASE <= args.address < rom.ROM_BASE + 0x02000000
    if is_rom and args.address % 2 == 0:
        values.append((args.address | 1, "  (thumb ptr +1)"))
    total = 0
    for value, label in values:
        hits = rom.find(data, rom.u32_pattern(value), align=4, limit=args.limit)
        _print_hits(hits, label)
        total += len(hits)
    print(f"# {total} aligned reference(s) to {args.address:#010x}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hamtools", description=__doc__)
    sub = p.add_subparsers(dest="group", required=True)

    rom_p = sub.add_parser("rom", help="read-only ROM inspection")
    rsub = rom_p.add_subparsers(dest="cmd", required=True)

    rsub.add_parser("verify", help="check the ROM is the expected dump").set_defaults(func=cmd_rom_verify)
    rsub.add_parser("info", help="header, save type, used/free space").set_defaults(func=cmd_rom_info)

    peek = rsub.add_parser("peek", help="hexdump at a ROM address or file offset")
    peek.add_argument("address", type=_int)
    peek.add_argument("--len", type=_int, default=64)
    peek.set_defaults(func=cmd_rom_peek)

    find = rsub.add_parser("find", help="search for bytes, ASCII, or a 32-bit value")
    what = find.add_mutually_exclusive_group(required=True)
    what.add_argument("--hex", help="byte pattern, e.g. '11 DF' or '10 ?? ?? 00'")
    what.add_argument("--ascii")
    what.add_argument("--u32", type=_int, help="32-bit little-endian value")
    find.add_argument("--align", type=_int, default=1)
    find.add_argument("--limit", type=_int)
    find.set_defaults(func=cmd_rom_find)

    xrefs = rsub.add_parser("xrefs", help="find 4-byte-aligned words pointing at an address")
    xrefs.add_argument("address", type=_int)
    xrefs.add_argument("--limit", type=_int)
    xrefs.set_defaults(func=cmd_rom_xrefs)

    _add_ghidra(sub)
    _add_emu(sub)
    _add_patch(sub)
    _add_text(sub)
    return p


# ---------------------------------------------------------------------------
# patch
# ---------------------------------------------------------------------------
def _add_text(sub) -> None:
    t = sub.add_parser("text", help="decode game text or export edited streams as mod sources").add_subparsers(
        dest="cmd", required=True)

    p = t.add_parser("dump", help="walk all event scripts and write extracted/text/*")
    p.add_argument("--out", type=Path, help="output directory (default: extracted/text)")
    p.set_defaults(func=cmd_text_dump)

    p = t.add_parser("show", help="decode the text stream at a ROM address")
    p.add_argument("address", type=_int, nargs="+")
    p.set_defaults(func=cmd_text_show)

    p = t.add_parser("edits", help="export changed dialogue streams from an edited dump",
                     description="Compare a dump against the verified original ROM. Only changed "
                                 "streams are exported. Review replacement text before committing; "
                                 "commit only dialogue you authored.")
    p.add_argument("edited_dump", type=Path)
    p.add_argument("--out", type=Path, required=True, help="output mod.toml path")
    p.add_argument("--partial", action="store_true",
                   help="intentional subset: omitted entries stay untouched, never deletions")
    p.add_argument("--force", action="store_true", help="explicitly replace an existing output file")
    p.set_defaults(func=cmd_text_edits)


def _verified_rom() -> bytes:
    data = rom.load_rom()
    if rom.sha1(data) != rom.EXPECTED_SHA1:
        raise rom.RomError("ROM does not match the expected USA dump; text addresses would be wrong")
    return data


def cmd_text_dump(args: argparse.Namespace) -> int:
    from . import text
    from .paths import EXTRACTED_DIR
    out = args.out or EXTRACTED_DIR / "text"
    counts = text.dump(_verified_rom(), out)
    print(f"wrote {out}: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    return 0 if counts["problems"] == 0 else 1


def cmd_text_show(args: argparse.Namespace) -> int:
    from . import text
    data = _verified_rom()
    for address in args.address:
        stream = text.read_stream(data, address)
        sys.stdout.reconfigure(encoding="utf-8")
        print(text.format_entry(stream, f"{len(stream.raw)} bytes"))
    return 0


def cmd_text_edits(args: argparse.Namespace) -> int:
    from . import patch, text

    try:
        out = args.out.resolve()
        for source in (rom.rom_path().resolve(), args.edited_dump.resolve()):
            if out == source or (out.exists() and source.exists() and out.samefile(source)):
                raise patch.PatchError("output must not overwrite the original ROM or edited dump")
        if out.exists() and not args.force:
            raise patch.PatchError(f"output already exists: {out}; use --force to replace it")
        changed = text.edits(_verified_rom(), args.edited_dump.read_text(encoding="utf-8"),
                             partial=args.partial)
        rendered = text.format_edits(changed)
        out.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation also protects against an output appearing after the
        # initial check. --force is the only path that truncates an existing file.
        with out.open("w" if args.force else "x", encoding="utf-8", newline="\n") as fh:
            fh.write(rendered)
    except (OSError, UnicodeError) as exc:
        raise patch.PatchError(f"cannot export text edits: {exc}") from exc
    print(f"wrote {out}: {len(changed)} changed stream(s)")
    return 0


def _add_patch(sub) -> None:
    g = sub.add_parser("patch", help="build mods into build/").add_subparsers(dest="cmd", required=True)

    def do_list(args):
        from . import patch
        for m in patch.load_mods(names=[p.parent.name for p in patch.PATCHES_DIR.glob("*/mod.toml")]):
            print(f"{'on ' if m.enabled else 'off'}  {m.path.name:<24} {m.description}")
        return 0

    def do_build(args):
        from . import patch
        print("\n".join(patch.build(args.mods or None)))
        return 0

    g.add_parser("list", help="list mods").set_defaults(func=do_list)
    p = g.add_parser("build", help="build enabled mods (or the named ones)")
    p.add_argument("mods", nargs="*")
    p.set_defaults(func=do_build)


# ---------------------------------------------------------------------------
# ghidra
# ---------------------------------------------------------------------------
def _add_ghidra(sub) -> None:
    g = sub.add_parser("ghidra", help="headless Ghidra analysis").add_subparsers(dest="cmd", required=True)

    def run(fn):
        def wrapped(args):
            from . import ghidra
            out = fn(ghidra, args)
            print("\n".join(out) if isinstance(out, list) else out)
            return 0
        return wrapped

    p = g.add_parser("init", help="create the Ghidra project from the ROM and analyze it")
    p.add_argument("--force", action="store_true", help="delete and rebuild an existing project")
    p.add_argument("--no-analyze", action="store_true")
    p.set_defaults(func=run(lambda gh, a: gh.init(force=a.force, analyze=not a.no_analyze)))

    g.add_parser("sync", help="push kb/symbols.csv names into the project").set_defaults(
        func=run(lambda gh, a: gh.sync_symbols()))
    g.add_parser("stats", help="function/instruction counts").set_defaults(func=run(lambda gh, a: gh.stats()))
    g.add_parser("analyze", help="re-run auto-analysis (after adding functions)").set_defaults(
        func=run(lambda gh, a: gh.analyze_again()))

    p = g.add_parser("decompile", help="decompile the function containing an address or symbol")
    p.add_argument("target")
    p.set_defaults(func=run(lambda gh, a: gh.decompile(a.target)))

    p = g.add_parser("disasm", help="disassembly listing from an address")
    p.add_argument("target")
    p.add_argument("--count", type=int, default=40)
    p.set_defaults(func=run(lambda gh, a: gh.disassemble(a.target, a.count)))

    p = g.add_parser("func", help="function info: size, callers, callees")
    p.add_argument("target")
    p.set_defaults(func=run(lambda gh, a: gh.function_info(a.target)))

    p = g.add_parser("xrefs", help="references Ghidra knows to an address")
    p.add_argument("target")
    p.set_defaults(func=run(lambda gh, a: gh.xrefs(a.target)))

    p = g.add_parser("make-func", help="disassemble and create a function at an address")
    p.add_argument("target")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--thumb", action="store_true")
    mode.add_argument("--arm", action="store_true")
    p.add_argument("--name")
    p.set_defaults(func=run(lambda gh, a: gh.create_function(a.target, a.thumb, a.name)))


# ---------------------------------------------------------------------------
# emu (same bridge the MCP server uses; handy from a shell or script)
# ---------------------------------------------------------------------------
def _add_emu(sub) -> None:
    e = sub.add_parser("emu", help="drive the live mGBA emulator").add_subparsers(dest="cmd", required=True)

    def run(fn):
        def wrapped(args):
            from .emu import Emu
            emu = Emu()
            if args.cmd != "launch":
                emu.ensure()
            out = fn(emu, args)
            if out is not None:
                print(out if isinstance(out, str) else json.dumps(out, indent=2))
            return 0
        return wrapped

    p = e.add_parser("launch", help="start mGBA with the bridge (or reuse it)")
    p.add_argument("--rom", help="ROM path (default: original)")
    p.add_argument("--state", help="savestate path to load at boot")
    p.set_defaults(func=run(lambda emu, a: emu.launch(Path(a.rom) if a.rom else None,
                                                      Path(a.state) if a.state else None)))
    e.add_parser("status").set_defaults(func=run(lambda emu, a: emu.call("ping")))

    p = e.add_parser("shot", help="save a screenshot")
    p.add_argument("path", nargs="?", default="screenshots/shot.png")
    p.set_defaults(func=run(lambda emu, a: str(emu.screenshot(Path(a.path).resolve()))))

    p = e.add_parser("press", help="press buttons, e.g. 'A' or 'UP+B'")
    p.add_argument("buttons")
    p.add_argument("--hold", type=int, default=6)
    p.add_argument("--after", type=int, default=30)
    p.set_defaults(func=run(lambda emu, a: {"frame": emu.press(a.buttons, a.hold, a.after)}))

    p = e.add_parser("wait", help="run N frames")
    p.add_argument("frames", type=int)
    p.set_defaults(func=run(lambda emu, a: {"frame": emu.wait(a.frames)}))

    p = e.add_parser("read", help="hexdump live memory")
    p.add_argument("address", type=_int)
    p.add_argument("--len", type=_int, default=64)
    p.set_defaults(func=run(lambda emu, a: _hexdump(a.address, emu.read(a.address, a.len))))

    e.add_parser("regs").set_defaults(func=run(lambda emu, a: {k: f"{v:#010x}" for k, v in emu.call("regs").items()}))

    p = e.add_parser("watch", help="record which code touches an address over N frames")
    p.add_argument("address", type=_int)
    p.add_argument("--len", type=_int, default=1)
    p.add_argument("--kind", choices=["write", "read", "rw", "change"], default="write")
    p.add_argument("--frames", type=int, default=60)
    p.set_defaults(func=run(_watch))


def _watch(emu, a):
    probe = emu.call("watch", f"{a.address:#x}", a.len, a.kind)
    try:
        emu.wait(a.frames)
        report = emu.call("hits", probe)[0]
    finally:
        emu.call("unprobe", probe)
    lines = [f"{a.kind} {a.address:#010x}+{a.len}: {report['total']} hit(s) in {a.frames} frames"]
    for s in report["sites"]:
        lines.append(f"  pc {s['pc']:#010x}  x{s['count']}  lr {s['regs'].get('lr', 0):#010x}  {s.get('extra') or ''}")
    return "\n".join(lines)


def _hexdump(base: int, data: bytes) -> str:
    rows = []
    for i in range(0, len(data), 16):
        row = data[i:i + 16]
        rows.append(f"{base + i:08x}  {' '.join(f'{b:02x}' for b in row):<47}")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:  # noqa: BLE001 — report tool errors plainly to agents
        known = {"RomError", "TextError", "EmuError", "GhidraError", "ToolNotFound", "PatchError"}
        if type(e).__name__ not in known:
            raise
        print(f"error: {e}", file=sys.stderr)
        return 2
    finally:
        if args.group == "ghidra":
            _exit_jvm()


def _exit_jvm() -> None:
    """Ghidra's non-daemon Java threads keep the process alive after we're done (or after an
    error), leaving a zombie that holds the project lock. Exit hard once output is flushed."""
    import os
    import traceback
    exc = sys.exc_info()[1]
    if exc is not None and type(exc).__name__ not in {"GhidraError", "ToolNotFound"}:
        traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if exc is not None else 0)


if __name__ == "__main__":
    sys.exit(main())
