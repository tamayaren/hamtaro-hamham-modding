"""Client for the mGBA Lua bridge (tools/mgba/bridge.lua) plus RAM search.

The emulator runs as a normal mGBA window the human can also see and play. The bridge
never pauses the game; frame-based commands (wait, press) return after the frames ran.
"""

from __future__ import annotations

import itertools
import json
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import paths, rom

PORTS = range(61337, 61347)

KEYS = {"A": 0, "B": 1, "SELECT": 2, "START": 3, "RIGHT": 4, "LEFT": 5, "UP": 6, "DOWN": 7, "R": 8, "L": 9}

REGIONS = {
    "ewram": (0x02000000, 0x40000),
    "iwram": (0x03000000, 0x8000),
}


class EmuError(Exception):
    pass


def key_mask(buttons: list[str] | str) -> int:
    if isinstance(buttons, str):
        buttons = buttons.replace("+", " ").replace(",", " ").split()
    mask = 0
    for b in buttons:
        name = b.strip().upper()
        if name not in KEYS:
            raise EmuError(f"unknown button {b!r}; use {', '.join(KEYS)}")
        mask |= 1 << KEYS[name]
    return mask


class Emu:
    def __init__(self) -> None:
        self.sock: socket.socket | None = None
        self.port: int | None = None
        self._buf = b""
        self._ids = itertools.count(1)
        self.process: subprocess.Popen | None = None

    # -- connection -------------------------------------------------------
    def connect(self, timeout: float = 0.5) -> bool:
        for port in PORTS:
            try:
                s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
            except OSError:
                continue
            self.sock, self.port, self._buf = s, port, b""
            try:
                self.call("ping", timeout=3)
                return True
            except (EmuError, OSError):
                self.close()
        return False

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None

    def ensure(self) -> None:
        if self.sock is None and not self.connect():
            raise EmuError("emulator not running — launch it first (emu_launch / `hamtools emu launch`)")

    def launch(self, rom_file: Path | None = None, savestate: Path | None = None, wait: float = 20.0) -> dict:
        """Start mGBA with the bridge, or reuse a running one."""
        if savestate and not Path(savestate).exists():
            raise EmuError(f"savestate not found: {savestate}")
        if self.connect():
            return {"reused": True, **self.call("ping")}
        exe = paths.mgba_exe()
        (paths.REPO_ROOT / ".cache").mkdir(exist_ok=True)
        rom_file = rom_file or rom.rom_path()
        args = [str(exe), "--script", str(paths.BRIDGE_LUA)]
        if savestate:
            args += ["-t", str(savestate)]
        args.append(str(rom_file))
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        self.process = subprocess.Popen(args, cwd=str(exe.parent), creationflags=flags,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            time.sleep(0.5)
            if self.connect():
                return {"reused": False, **self.call("ping")}
        raise EmuError("mGBA started but the bridge did not answer; check mGBA's scripting console")

    # -- protocol ---------------------------------------------------------
    def call(self, cmd: str, *args: object, timeout: float = 10.0):
        if self.sock is None:
            self.ensure()
        assert self.sock is not None
        rid = next(self._ids)
        line = " ".join([str(rid), cmd, *(str(a) for a in args)]) + "\n"
        try:
            self.sock.settimeout(timeout)
            self.sock.sendall(line.encode("utf-8"))
            while True:
                nl = self._buf.find(b"\n")
                if nl < 0:
                    chunk = self.sock.recv(1 << 20)
                    if not chunk:
                        raise EmuError("bridge closed the connection")
                    self._buf += chunk
                    continue
                raw, self._buf = self._buf[:nl], self._buf[nl + 1:]
                msg = json.loads(raw)
                if msg.get("id") != rid:
                    continue  # stale reply from a timed-out request
                if not msg.get("ok"):
                    raise EmuError(msg.get("error", "unknown bridge error"))
                return msg.get("result")
        except socket.timeout:
            raise EmuError(f"'{cmd}' timed out after {timeout}s (is the game paused?)") from None
        except OSError as e:
            self.close()
            raise EmuError(f"connection lost: {e}") from None

    # -- conveniences -----------------------------------------------------
    def read(self, address: int, length: int) -> bytes:
        out = bytearray()
        for off in range(0, length, 0x8000):
            n = min(0x8000, length - off)
            out += bytes.fromhex(self.call("read", f"{address + off:#x}", n, timeout=30))
        return bytes(out)

    def write(self, address: int, data: bytes) -> None:
        self.call("write", f"{address:#x}", data.hex())

    def wait(self, frames: int) -> int:
        return self.call("wait", frames, timeout=10 + frames / 30)

    def press(self, buttons: list[str] | str, hold: int = 6, after: int = 0) -> int:
        return self.call("press", key_mask(buttons), hold, after, timeout=10 + (hold + after) / 30)

    def screenshot(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.call("screenshot", str(path.resolve()))
        for _ in range(20):  # the frontend may write the file a moment later
            if path.exists() and path.stat().st_size > 0:
                break
            time.sleep(0.05)
        return path


# ---------------------------------------------------------------------------
# RAM search (cheat-search style): snapshot, then narrow by how values change
# ---------------------------------------------------------------------------
FILTERS = ("changed", "unchanged", "increased", "decreased", "eq", "ne", "gt", "lt")


@dataclass
class RamSearch:
    width: int = 1
    signed: bool = False
    regions: tuple[str, ...] = ("ewram", "iwram")
    candidates: dict[int, int] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)

    def _snapshot(self, emu: Emu) -> dict[int, int]:
        values: dict[int, int] = {}
        for name in self.regions:
            base, size = REGIONS[name]
            data = emu.read(base, size)
            for off in range(0, size - self.width + 1, self.width):
                values[base + off] = int.from_bytes(data[off:off + self.width], "little", signed=self.signed)
        return values

    def start(self, emu: Emu) -> int:
        self.candidates = self._snapshot(emu)
        self.history = [f"start width={self.width} signed={self.signed} regions={','.join(self.regions)}"]
        return len(self.candidates)

    def filter(self, emu: Emu, op: str, value: int | None = None) -> int:
        if op not in FILTERS:
            raise EmuError(f"filter must be one of {FILTERS}")
        now = self._snapshot(emu)
        keep: dict[int, int] = {}
        for addr, old in self.candidates.items():
            new = now[addr]
            ref = old if value is None else value
            ok = {
                "changed": new != old, "unchanged": new == old,
                "increased": new > old, "decreased": new < old,
                "eq": new == ref, "ne": new != ref, "gt": new > ref, "lt": new < ref,
            }[op]
            if ok:
                keep[addr] = new
        self.candidates = keep
        self.history.append(f"{op}{'' if value is None else ' ' + str(value)} -> {len(keep)}")
        return len(keep)

    def listing(self, limit: int = 50) -> list[dict]:
        return [{"address": f"{a:#010x}", "value": v} for a, v in sorted(self.candidates.items())[:limit]]
