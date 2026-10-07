"""Where things live: repo directories and external tools (overridable by environment variables)."""

from __future__ import annotations

import glob
import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_DIR = REPO_ROOT / "build"
STATES_DIR = REPO_ROOT / "states"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"
EXTRACTED_DIR = REPO_ROOT / "extracted"
KB_DIR = REPO_ROOT / "kb"
BRIDGE_LUA = REPO_ROOT / "tools" / "mgba" / "bridge.lua"

_LOCAL_PROGRAMS = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Programs"


class ToolNotFound(Exception):
    pass


def _first(paths: list[str | Path]) -> Path | None:
    for p in paths:
        if p and Path(p).exists():
            return Path(p)
    return None


def mgba_exe() -> Path:
    """mGBA 0.11+ (dev build) — needed for --script and scripted watchpoints."""
    found = _first([
        os.environ.get("HAMTARO_MGBA", ""),
        _LOCAL_PROGRAMS / "mGBA-dev" / "mGBA.exe",
        shutil.which("mgba-qt") or "",
    ])
    if not found:
        raise ToolNotFound("mGBA 0.11+ not found; set HAMTARO_MGBA to mGBA.exe "
                           "(dev builds: https://mgba.io/downloads.html#development-downloads)")
    return found


def ghidra_dir() -> Path:
    candidates = [os.environ.get("GHIDRA_INSTALL_DIR", "")]
    candidates += sorted(glob.glob(str(_LOCAL_PROGRAMS / "ghidra_*_PUBLIC")), reverse=True)
    found = _first(candidates)
    if not found:
        raise ToolNotFound("Ghidra not found; set GHIDRA_INSTALL_DIR")
    return found


def arm_bin() -> Path:
    """Directory holding arm-none-eabi-gcc/as/ld/objcopy."""
    if env := os.environ.get("ARM_TOOLCHAIN_BIN"):
        return Path(env)
    if which := shutil.which("arm-none-eabi-gcc"):
        return Path(which).parent
    for base in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", "")):
        hits = sorted(glob.glob(str(Path(base) / "Arm GNU Toolchain arm-none-eabi" / "*" / "bin")), reverse=True)
        if hits:
            return Path(hits[0])
    raise ToolNotFound("arm-none-eabi toolchain not found; set ARM_TOOLCHAIN_BIN")


def arm_tool(name: str) -> Path:
    exe = arm_bin() / f"arm-none-eabi-{name}{'.exe' if os.name == 'nt' else ''}"
    if not exe.exists():
        raise ToolNotFound(f"{exe} missing")
    return exe
