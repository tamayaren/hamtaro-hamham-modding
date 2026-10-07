"""Headless Ghidra (via PyGhidra): project setup, symbol sync, decompile, disassemble, xrefs.

The Ghidra project lives in ghidra/projects/ (gitignored). It is opened per operation, so the
CLI and the Ghidra MCP server can take turns; a Ghidra GUI holding the project open will block them.
"""

from __future__ import annotations

import csv
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import paths, rom

PROJECT_DIR = Path(os.environ.get("HAMTARO_GHIDRA_PROJECT", paths.REPO_ROOT / "ghidra" / "projects"))
PROJECT_NAME = "hamtaro"
PROGRAM_NAME = "hamtaro.gba"
PROGRAM_PATH = "/" + PROGRAM_NAME
LANGUAGE = "ARM:LE:32:v4t"
SYMBOLS_CSV = paths.KB_DIR / "symbols.csv"

# name, start, size, permissions (r/w/x), volatile
GBA_MEMORY = [
    ("BIOS", 0x00000000, 0x4000, "rx", False),
    ("EWRAM", 0x02000000, 0x40000, "rwx", False),
    ("IWRAM", 0x03000000, 0x8000, "rwx", False),
    ("IO", 0x04000000, 0x400, "rw", True),
    ("PALETTE", 0x05000000, 0x400, "rw", False),
    ("VRAM", 0x06000000, 0x18000, "rw", False),
    ("OAM", 0x07000000, 0x400, "rw", False),
    ("SRAM", 0x0E000000, 0x8000, "rw", True),
]

IO_REGISTERS = {
    0x04000000: "REG_DISPCNT", 0x04000004: "REG_DISPSTAT", 0x04000006: "REG_VCOUNT",
    0x04000008: "REG_BG0CNT", 0x0400000A: "REG_BG1CNT", 0x0400000C: "REG_BG2CNT", 0x0400000E: "REG_BG3CNT",
    0x04000010: "REG_BG0HOFS", 0x04000012: "REG_BG0VOFS", 0x04000014: "REG_BG1HOFS", 0x04000016: "REG_BG1VOFS",
    0x04000018: "REG_BG2HOFS", 0x0400001A: "REG_BG2VOFS", 0x0400001C: "REG_BG3HOFS", 0x0400001E: "REG_BG3VOFS",
    0x04000040: "REG_WIN0H", 0x04000048: "REG_WININ", 0x0400004A: "REG_WINOUT", 0x0400004C: "REG_MOSAIC",
    0x04000050: "REG_BLDCNT", 0x04000052: "REG_BLDALPHA", 0x04000054: "REG_BLDY",
    0x04000060: "REG_SOUND1CNT_L", 0x04000080: "REG_SOUNDCNT_L", 0x04000082: "REG_SOUNDCNT_H",
    0x04000084: "REG_SOUNDCNT_X", 0x040000A0: "REG_FIFO_A", 0x040000A4: "REG_FIFO_B",
    0x040000B0: "REG_DMA0SAD", 0x040000B4: "REG_DMA0DAD", 0x040000B8: "REG_DMA0CNT",
    0x040000BC: "REG_DMA1SAD", 0x040000C0: "REG_DMA1DAD", 0x040000C4: "REG_DMA1CNT",
    0x040000C8: "REG_DMA2SAD", 0x040000CC: "REG_DMA2DAD", 0x040000D0: "REG_DMA2CNT",
    0x040000D4: "REG_DMA3SAD", 0x040000D8: "REG_DMA3DAD", 0x040000DC: "REG_DMA3CNT",
    0x04000100: "REG_TM0CNT", 0x04000104: "REG_TM1CNT", 0x04000108: "REG_TM2CNT", 0x0400010C: "REG_TM3CNT",
    0x04000130: "REG_KEYINPUT", 0x04000132: "REG_KEYCNT",
    0x04000200: "REG_IE", 0x04000202: "REG_IF", 0x04000204: "REG_WAITCNT", 0x04000208: "REG_IME",
}


class GhidraError(Exception):
    pass


# ---------------------------------------------------------------------------
# JVM / project plumbing
# ---------------------------------------------------------------------------
def start() -> None:
    import pyghidra
    if not pyghidra.started():
        pyghidra.start(install_dir=paths.ghidra_dir())


def project_exists() -> bool:
    return (PROJECT_DIR / f"{PROJECT_NAME}.gpr").exists()


@contextmanager
def open_program(write: bool = False, description: str = "hamtools"):
    """Yield (program, flat_api). With write=True the changes run in a transaction and are saved."""
    start()
    import pyghidra
    from ghidra.program.flatapi import FlatProgramAPI

    if not project_exists():
        raise GhidraError("no Ghidra project yet — run `uv run hamtools ghidra init`")
    try:
        project = pyghidra.open_project(PROJECT_DIR, PROJECT_NAME)
    except Exception as e:  # noqa: BLE001 — Java exceptions
        raise GhidraError(f"cannot open Ghidra project (open in the Ghidra GUI?): {e}") from None
    try:
        with pyghidra.program_context(project, PROGRAM_PATH) as program:
            flat = FlatProgramAPI(program)
            if write:
                with pyghidra.transaction(program, description):
                    yield program, flat
                program.save(description, pyghidra.task_monitor())
            else:
                yield program, flat
    finally:
        project.close()


def addr(program, value: int | str):
    if isinstance(value, str):
        value = resolve(program, value)
    return program.getAddressFactory().getDefaultAddressSpace().getAddress(value)


def resolve(program, text: str) -> int:
    """'0x0800961c', '0800961c', or a symbol name -> int address."""
    try:
        return int(text, 16) if not text.lower().startswith("0x") else int(text, 0)
    except ValueError:
        pass
    syms = list(program.getSymbolTable().getGlobalSymbols(text))
    if not syms:
        raise GhidraError(f"unknown address or symbol: {text}")
    return syms[0].getAddress().getOffset()


# ---------------------------------------------------------------------------
# symbols.csv
# ---------------------------------------------------------------------------
@dataclass
class Symbol:
    address: int
    name: str
    kind: str
    size: int | None
    mode: str
    confidence: str
    notes: str


def read_symbols(path: Path = SYMBOLS_CSV) -> list[Symbol]:
    out = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append(Symbol(
                address=int(row["address"], 0), name=row["name"], kind=row["kind"],
                size=int(row["size"], 0) if row.get("size") else None,
                mode=row.get("mode", ""), confidence=row.get("confidence", ""), notes=row.get("notes", "")))
    return out


def _set_thumb(program, start: int, end: int, thumb: bool) -> None:
    from java.math import BigInteger
    ctx = program.getProgramContext()
    reg = ctx.getRegister("TMode")
    ctx.setValue(reg, addr(program, start), addr(program, end), BigInteger.ONE if thumb else BigInteger.ZERO)


def make_function(program, address: int, thumb: bool, name: str | None = None) -> str:
    """Disassemble at address in the given mode and create (or rename) a function there."""
    import pyghidra
    from ghidra.app.cmd.disassemble import ArmDisassembleCommand
    from ghidra.app.cmd.function import CreateFunctionCmd
    from ghidra.program.model.symbol import SourceType

    monitor = pyghidra.task_monitor()
    a = addr(program, address)
    if program.getListing().getInstructionAt(a) is None:
        _set_thumb(program, address, address + 1, thumb)
        ArmDisassembleCommand(a, None, thumb).applyTo(program, monitor)
    func = program.getFunctionManager().getFunctionAt(a)
    if func is None:
        CreateFunctionCmd(a).applyTo(program, monitor)
        func = program.getFunctionManager().getFunctionAt(a)
    if func is None:
        return f"could not create function at {address:#010x}"
    if name:
        func.setName(name, SourceType.USER_DEFINED)
    return f"{func.getName()} @ {address:#010x} ({'thumb' if thumb else 'arm'})"


def apply_symbols(program, symbols: list[Symbol]) -> list[str]:
    from ghidra.program.model.symbol import SourceType

    log = []
    st = program.getSymbolTable()
    for s in symbols:
        if s.kind == "func":
            log.append(make_function(program, s.address, s.mode != "arm", s.name))
            continue
        a = addr(program, s.address)
        if program.getMemory().getBlock(a) is None:
            log.append(f"skip {s.name}: {s.address:#010x} not in any memory block")
            continue
        primary = st.getPrimarySymbol(a)
        if primary is not None and primary.getSource() == SourceType.USER_DEFINED:
            if primary.getName() != s.name:
                primary.setName(s.name, SourceType.USER_DEFINED)
        else:
            st.createLabel(a, s.name, SourceType.USER_DEFINED).setPrimary()
        log.append(f"label {s.name} @ {s.address:#010x}")
    return log


# ---------------------------------------------------------------------------
# init: import ROM, build GBA memory map, seed code, analyze
# ---------------------------------------------------------------------------
def _progress(log: list[str], msg: str) -> None:
    log.append(msg)
    print(f"[ghidra] {msg}", flush=True)


def init(force: bool = False, analyze: bool = True) -> list[str]:
    log: list[str] = []
    _progress(log, "starting JVM")
    start()
    import pyghidra
    from ghidra.program.model.symbol import SourceType
    if project_exists() and not force:
        raise GhidraError("project already exists (use --force to rebuild it)")
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    if force:
        for p in PROJECT_DIR.glob(f"{PROJECT_NAME}.*"):
            if p.is_dir():
                import shutil
                shutil.rmtree(p)
            else:
                p.unlink()

    _progress(log, "creating project")
    project = pyghidra.open_project(PROJECT_DIR, PROJECT_NAME, create=True)
    monitor = pyghidra.task_monitor()
    try:
        results = (pyghidra.program_loader().source(str(rom.rom_path())).project(project)
                   .projectFolderPath("/").name(PROGRAM_NAME).language(LANGUAGE).compiler("default")
                   .loaders("BinaryLoader").addLoaderArg("-loader-baseAddr", f"{rom.ROM_BASE:#x}").load())
        try:
            results.save(monitor)
        finally:
            results.close()
        _progress(log, f"imported ROM at {rom.ROM_BASE:#010x} as {LANGUAGE}")

        with pyghidra.program_context(project, PROGRAM_PATH) as program:
            with pyghidra.transaction(program, "GBA memory map"):
                mem = program.getMemory()
                rom_block = mem.getBlock(addr(program, rom.ROM_BASE))
                rom_block.setName("ROM")
                rom_block.setPermissions(True, False, True)
                for name, start_addr, size, perms, volatile in GBA_MEMORY:
                    block = mem.createUninitializedBlock(name, addr(program, start_addr), size, False)
                    block.setPermissions("r" in perms, "w" in perms, "x" in perms)
                    block.setVolatile(volatile)
                st = program.getSymbolTable()
                for a, name in IO_REGISTERS.items():
                    st.createLabel(addr(program, a), name, SourceType.IMPORTED)
                _progress(log, "created GBA memory blocks and I/O register labels")

                # Entry: ARM branch at 0x08000000 -> startup code
                log.append(make_function(program, rom.ROM_BASE, False, "RomHeader_Entry"))
                program.getSymbolTable().addExternalEntryPoint(addr(program, rom.ROM_BASE))
                log += apply_symbols(program, read_symbols())
                _progress(log, "applied kb/symbols.csv")

            if analyze:
                _progress(log, "running auto-analysis (several minutes)...")
                _analyze(program, monitor)
                fm = program.getFunctionManager()
                _progress(log, f"analysis done: {fm.getFunctionCount()} functions")
            program.save("hamtools init", monitor)
    finally:
        project.close()
    return log


def _analyze(program, monitor) -> None:
    """Auto-analysis without pyghidra.analyze(), which first starts Ghidra's OSGi script
    bundle host — that hangs or fails here and is only needed by script-based analyzers."""
    import pyghidra
    from ghidra.app.plugin.core.analysis import AutoAnalysisManager
    from ghidra.program.util import GhidraProgramUtilities

    with pyghidra.transaction(program, "Analyze"):
        mgr = AutoAnalysisManager.getAnalysisManager(program)
        mgr.initializeOptions()
        mgr.reAnalyzeAll(None)
        mgr.startAnalysis(monitor, True)
        GhidraProgramUtilities.markProgramAnalyzed(program)


def analyze_again() -> str:
    """Re-run auto-analysis (e.g. after adding many functions by hand)."""
    import pyghidra
    with open_program(write=False) as (program, _):
        _analyze(program, pyghidra.task_monitor())
        program.save("hamtools analyze", pyghidra.task_monitor())
        return f"analysis done: {program.getFunctionManager().getFunctionCount()} functions"


def sync_symbols() -> list[str]:
    with open_program(write=True, description="sync kb/symbols.csv") as (program, _):
        return apply_symbols(program, read_symbols())


# ---------------------------------------------------------------------------
# queries
# ---------------------------------------------------------------------------
def decompile(target: str, timeout: int = 60) -> str:
    import pyghidra
    from ghidra.app.decompiler import DecompInterface

    with open_program() as (program, _):
        a = addr(program, target)
        func = program.getFunctionManager().getFunctionContaining(a)
        if func is None:
            raise GhidraError(f"no function contains {a} — create one with `ghidra make-func`")
        ifc = DecompInterface()
        ifc.openProgram(program)
        try:
            res = ifc.decompileFunction(func, timeout, pyghidra.task_monitor())
            if not res.decompileCompleted():
                raise GhidraError(f"decompile failed: {res.getErrorMessage()}")
            header = f"// {func.getName()} @ {func.getEntryPoint()} ({_mode(program, func.getEntryPoint())})\n"
            return header + res.getDecompiledFunction().getC()
        finally:
            ifc.dispose()


def _mode(program, a) -> str:
    reg = program.getProgramContext().getRegister("TMode")
    v = program.getProgramContext().getValue(reg, a, False)
    return "thumb" if v is not None and v.intValue() == 1 else "arm"


def disassemble(target: str, count: int = 40) -> str:
    with open_program() as (program, _):
        a = addr(program, target)
        listing = program.getListing()
        lines = []
        it = listing.getInstructions(a, True)
        while it.hasNext() and len(lines) < count:
            ins = it.next()
            label = program.getSymbolTable().getPrimarySymbol(ins.getAddress())
            if label is not None and not label.getName().startswith(("LAB_", "FUN_")):
                lines.append(f"{label.getName()}:")
            raw = " ".join(f"{b & 0xFF:02x}" for b in ins.getBytes())
            lines.append(f"  {ins.getAddress()}  {raw:<12} {ins}")
        if not lines:
            return f"no instructions at/after {a} (not disassembled yet?)"
        return "\n".join(lines)


def function_info(target: str) -> str:
    import pyghidra

    with open_program() as (program, _):
        a = addr(program, target)
        func = program.getFunctionManager().getFunctionContaining(a)
        if func is None:
            raise GhidraError(f"no function contains {a}")
        mon = pyghidra.task_monitor()
        body = func.getBody()
        out = [f"{func.getName()} @ {func.getEntryPoint()} ({_mode(program, func.getEntryPoint())}), "
               f"{body.getNumAddresses()} bytes, signature: {func.getSignature()}"]
        out.append("callers:")
        out += [f"  {f.getName()} @ {f.getEntryPoint()}" for f in func.getCallingFunctions(mon)] or ["  (none found)"]
        out.append("callees:")
        out += [f"  {f.getName()} @ {f.getEntryPoint()}" for f in func.getCalledFunctions(mon)] or ["  (none)"]
        return "\n".join(out)


def xrefs(target: str, limit: int = 100) -> str:
    with open_program() as (program, _):
        a = addr(program, target)
        fm = program.getFunctionManager()
        out = []
        for ref in program.getReferenceManager().getReferencesTo(a):
            src = ref.getFromAddress()
            func = fm.getFunctionContaining(src)
            out.append(f"  {src}  {str(ref.getReferenceType()):<16} in {func.getName() if func else '?'}")
            if len(out) >= limit:
                break
        head = f"references to {a}: {len(out)}{'+' if len(out) >= limit else ''}"
        return "\n".join([head, *out]) if out else head + "\n  (none — try `hamtools rom xrefs` for literal-pool hits)"


def create_function(target: str, thumb: bool, name: str | None = None) -> str:
    with open_program(write=True, description=f"make function {target}") as (program, _):
        return make_function(program, resolve(program, target), thumb, name)


def stats() -> str:
    with open_program() as (program, _):
        fm = program.getFunctionManager()
        thumb = arm = 0
        for f in fm.getFunctions(True):
            if _mode(program, f.getEntryPoint()) == "thumb":
                thumb += 1
            else:
                arm += 1
        user = sum(1 for f in fm.getFunctions(True) if not f.getName().startswith("FUN_"))
        return (f"functions: {fm.getFunctionCount()} (thumb {thumb}, arm {arm}); named: {user}\n"
                f"instructions: {program.getListing().getNumInstructions()}")
