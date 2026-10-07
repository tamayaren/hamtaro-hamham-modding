"""`hamtools` command-line entry point. Every subcommand is read-only on the original ROM."""

from __future__ import annotations

import argparse
import re
import sys

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
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except rom.RomError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
