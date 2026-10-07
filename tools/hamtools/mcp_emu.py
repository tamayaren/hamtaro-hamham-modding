"""MCP server exposing the live mGBA emulator (via tools/mgba/bridge.lua) to coding agents.

Run with `uv run hamtools-mcp-emu` (registered in .mcp.json and .codex/config.toml).
"""

from __future__ import annotations

import functools
import re
import time
from pathlib import Path

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import paths
from .emu import Emu, EmuError, RamSearch, key_mask

INSTRUCTIONS = """\
Live mGBA emulator running Hamtaro: Ham-Ham Heartbreak (USA). The game runs in real time in
a window the human can also see. Call emu_launch first (it reuses a running emulator).
Addresses are hex strings like "0x02001234". Buttons: A B SELECT START RIGHT LEFT UP DOWN R L.
Watchpoints/breakpoints never pause the game; they record which code (pc) touched an
address — collect with emu_hits. To reach a specific game situation, ask the human for a
savestate in states/ rather than playing there blind. Never copy dumped bytes into tracked files.
"""

mcp = MCPServer("hamtaro-emu", instructions=INSTRUCTIONS)


def tool(fn):
    """Register a tool, turning expected failures into readable tool errors."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (EmuError, paths.ToolNotFound, ValueError, OSError) as e:
            raise ToolError(f"{type(e).__name__}: {e}") from e
    return mcp.tool()(wrapper)

_emu = Emu()
_search: RamSearch | None = None

_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
_FORMATS = {"u8": (1, False), "s8": (1, True), "u16": (2, False), "s16": (2, True),
            "u32": (4, False), "s32": (4, True)}


def _addr(text: str | int) -> int:
    return text if isinstance(text, int) else int(str(text), 0)


def _state_path(name: str) -> Path:
    if not _NAME.match(name):
        raise EmuError("state names may use letters, digits, '_', '-', '.' only")
    return (paths.STATES_DIR / (name if name.endswith(".ss") else f"{name}.ss")).resolve()


def _shot(label: str = "shot") -> Image:
    _emu.ensure()
    path = paths.SCREENSHOTS_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{label}.png"
    _emu.screenshot(path)
    return Image(path=path)


@tool
def emu_launch(rom: str = "original", savestate: str | None = None) -> dict:
    """Start mGBA with the bridge (or reuse the running one).
    rom: "original" or a path to a built ROM (e.g. build/hamtaro-mod.gba).
    savestate: optional name of a state in states/ to load at boot."""
    rom_file = None if rom == "original" else (paths.REPO_ROOT / rom).resolve()
    state = _state_path(savestate) if savestate else None
    info = _emu.launch(rom_file, state)
    if info.get("reused") and state:
        _emu.call("load_state", state)
    return info


@tool
def emu_status() -> dict:
    """Bridge version, game title/code, current frame, keys held by the bridge."""
    _emu.ensure()
    return {**_emu.call("ping"), "keys": _emu.call("keys")}


@tool
def emu_screenshot() -> Image:
    """Capture the current screen (240x160). Saved under screenshots/ (gitignored)."""
    return _shot()


@tool
def emu_press(buttons: str, hold_frames: int = 6, wait_after: int = 30, screenshot: bool = True):
    """Press buttons (e.g. "A", "UP+B") for hold_frames, release, wait wait_after frames,
    then (by default) return a screenshot. 60 frames = 1 second."""
    _emu.ensure()
    frame = _emu.press(buttons, hold_frames, wait_after)
    return [f"frame {frame}", _shot("press")] if screenshot else {"frame": frame}


@tool
def emu_hold(buttons: str) -> dict:
    """Hold buttons down until emu_release (e.g. to walk). Returns the held mask."""
    _emu.ensure()
    return {"held_mask": _emu.call("hold", key_mask(buttons))}


@tool
def emu_release(buttons: str | None = None) -> dict:
    """Release the given buttons, or all bridge-held buttons if omitted."""
    _emu.ensure()
    args = [key_mask(buttons)] if buttons else []
    return {"held_mask": _emu.call("release", *args)}


@tool
def emu_wait(frames: int = 60, screenshot: bool = False):
    """Let the game run for N frames (60 = 1 second)."""
    _emu.ensure()
    frame = _emu.wait(frames)
    return [f"frame {frame}", _shot("wait")] if screenshot else {"frame": frame}


@tool
def emu_read(address: str, length: int = 16, fmt: str = "hex") -> dict:
    """Read memory at any bus address (EWRAM 0x02.., IWRAM 0x03.., IO 0x04.., ROM 0x08..).
    fmt: hex | u8 | s8 | u16 | s16 | u32 | s32 (little endian)."""
    _emu.ensure()
    a = _addr(address)
    data = _emu.read(a, length)
    if fmt == "hex":
        return {"address": f"{a:#010x}", "hex": data.hex(" ")}
    if fmt not in _FORMATS:
        raise EmuError(f"fmt must be hex or one of {list(_FORMATS)}")
    width, signed = _FORMATS[fmt]
    values = [int.from_bytes(data[i:i + width], "little", signed=signed)
              for i in range(0, len(data) - width + 1, width)]
    return {"address": f"{a:#010x}", fmt: values}


@tool
def emu_write(address: str, value: int | None = None, width: int = 1, hex_bytes: str | None = None) -> dict:
    """Write memory. Either value+width (1, 2 or 4 bytes, little endian) or hex_bytes ("01 02 ff").
    Use to test a theory (e.g. poke a coordinate and watch the sprite move)."""
    _emu.ensure()
    a = _addr(address)
    if hex_bytes is not None:
        data = bytes.fromhex(hex_bytes)
    elif value is not None:
        data = (value & ((1 << (8 * width)) - 1)).to_bytes(width, "little")
    else:
        raise EmuError("give value or hex_bytes")
    if width == 2 and hex_bytes is None:
        _emu.call("write16", f"{a:#x}", value)
    elif width == 4 and hex_bytes is None:
        _emu.call("write32", f"{a:#x}", value)
    else:
        _emu.write(a, data)
    return {"address": f"{a:#010x}", "wrote": data.hex(" ")}


@tool
def emu_regs() -> dict:
    """CPU registers right now (usually mid-frame or in the BIOS wait loop)."""
    _emu.ensure()
    regs = _emu.call("regs")
    return {k: f"{v:#010x}" if isinstance(v, int) else v for k, v in regs.items()}


@tool
def emu_save_state(name: str) -> str:
    """Save a savestate to states/<name>.ss."""
    _emu.ensure()
    path = _state_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    _emu.call("save_state", path)
    return str(path.relative_to(paths.REPO_ROOT))


@tool
def emu_load_state(name: str, screenshot: bool = True):
    """Load states/<name>.ss (the human makes these at interesting spots)."""
    _emu.ensure()
    path = _state_path(name)
    if not path.exists():
        raise EmuError(f"no state {path.name}; available: {emu_list_states()}")
    frame = _emu.call("load_state", path)
    _emu.wait(2)
    return [f"loaded {path.name} (frame {frame})", _shot("state")] if screenshot else {"frame": frame}


@tool
def emu_list_states() -> list[str]:
    """Savestates available in states/."""
    if not paths.STATES_DIR.exists():
        return []
    return sorted(p.stem for p in paths.STATES_DIR.iterdir() if p.is_file())


@tool
def emu_reset() -> str:
    """Hard-reset the game."""
    _emu.ensure()
    _emu.call("reset")
    return "reset"


@tool
def emu_watch(address: str, length: int = 1, kind: str = "write") -> dict:
    """Record which code touches memory: kind = write | read | rw | change (write that changes
    the value). Covers [address, address+length). Returns a probe id; collect with emu_hits."""
    _emu.ensure()
    return {"probe": _emu.call("watch", f"{_addr(address):#x}", length, kind)}


@tool
def emu_break(address: str) -> dict:
    """Record every time code executes the instruction at address (with registers).
    Does not pause. Returns a probe id; collect with emu_hits."""
    _emu.ensure()
    return {"probe": _emu.call("break", f"{_addr(address):#x}")}


@tool
def emu_hits(probe: int | None = None, clear: bool = True, run_frames: int = 0) -> list:
    """Collect probe results: for each probe, the distinct code sites (pc) that triggered it,
    with hit counts, first registers, and access details. Optionally run N frames first.
    pc is reported as mGBA gives it; verify the exact instruction in Ghidra."""
    _emu.ensure()
    if run_frames:
        _emu.wait(run_frames)
    raw = _emu.call("hits", probe if probe is not None else "all", "clear" if clear else "keep")
    for report in raw:
        report["address"] = f"{report['address']:#010x}"
        for site in report["sites"]:
            site["pc"] = f"{site['pc']:#010x}"
            site["regs"] = {k: f"{v:#010x}" if isinstance(v, int) else v for k, v in site["regs"].items()}
    return raw


@tool
def emu_unwatch(probe: int | None = None) -> list:
    """Remove a probe, or all probes if omitted."""
    _emu.ensure()
    return _emu.call("unprobe", *([probe] if probe is not None else []))


@tool
def ram_search_start(width: int = 1, signed: bool = False, regions: str = "ewram,iwram") -> dict:
    """Begin a cheat-search style RAM hunt: snapshot every value of the given width.
    Then change something in game and narrow with ram_search_filter."""
    global _search
    _emu.ensure()
    _search = RamSearch(width=width, signed=signed, regions=tuple(r.strip() for r in regions.split(",")))
    return {"candidates": _search.start(_emu)}


@tool
def ram_search_filter(op: str, value: int | None = None, show: int = 20) -> dict:
    """Narrow candidates by comparing current values to the previous snapshot:
    changed | unchanged | increased | decreased, or to a number: eq | ne | gt | lt (with value).
    Without value, eq/ne/gt/lt compare to the previous snapshot."""
    if _search is None:
        raise EmuError("call ram_search_start first")
    _emu.ensure()
    n = _search.filter(_emu, op, value)
    return {"candidates": n, "history": _search.history, "sample": _search.listing(show)}


@tool
def ram_search_results(limit: int = 50) -> dict:
    """Current candidates (address and latest value)."""
    if _search is None:
        raise EmuError("call ram_search_start first")
    return {"candidates": len(_search.candidates), "results": _search.listing(limit)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
