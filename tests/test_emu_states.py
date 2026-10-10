"""Savestate filenames route correctly without running an emulator or using game data."""

from unittest.mock import Mock

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from hamtools import mcp_emu


@pytest.fixture
def state_environment(tmp_path, monkeypatch):
    states = tmp_path / "states"
    states.mkdir()
    bridge = Mock()
    bridge.call.return_value = 42
    monkeypatch.setattr(mcp_emu.paths, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(mcp_emu.paths, "STATES_DIR", states)
    monkeypatch.setattr(mcp_emu, "_emu", bridge)
    return states, bridge


@pytest.mark.parametrize(
    ("name", "filename"),
    [("demo", "demo.ss0"), ("demo.ss", "demo.ss"),
     ("demo.ss0", "demo.ss0"), ("demo.ss9", "demo.ss9")],
)
def test_save_uses_gui_suffix_and_preserves_explicit_names(state_environment, name, filename):
    states, bridge = state_environment
    assert mcp_emu.emu_save_state(name) == str((states / filename).relative_to(states.parent))
    bridge.call.assert_called_once_with("save_state", states / filename)


def test_bare_load_accepts_legacy_and_prefers_native_copy(state_environment):
    states, bridge = state_environment
    legacy = states / "demo.ss"
    legacy.write_bytes(b"synthetic legacy state")
    assert mcp_emu.emu_load_state("demo", screenshot=False) == {"frame": 42}
    bridge.call.assert_called_once_with("load_state", legacy)

    bridge.reset_mock()
    native = states / "demo.ss0"
    native.write_bytes(b"synthetic native state")
    mcp_emu.emu_load_state("demo", screenshot=False)
    bridge.call.assert_called_once_with("load_state", native)


@pytest.mark.parametrize("suffix", ["ss", *(f"ss{slot}" for slot in range(10)), "SS0"])
def test_explicit_load_does_not_append_another_suffix(state_environment, suffix):
    states, bridge = state_environment
    target = states / f"demo.{suffix}"
    target.write_bytes(b"synthetic state")
    mcp_emu.emu_load_state(target.name, screenshot=False)
    bridge.call.assert_called_once_with("load_state", target)


def test_missing_explicit_native_state_does_not_load_different_legacy_file(state_environment):
    states, bridge = state_environment
    (states / "demo.ss").write_bytes(b"synthetic legacy state")
    with pytest.raises(ToolError, match=r"no state demo\.ss0"):
        mcp_emu.emu_load_state("demo.ss0", screenshot=False)
    bridge.call.assert_not_called()


@pytest.mark.parametrize("reused", [False, True])
@pytest.mark.parametrize("name", ["demo", "demo.ss7", "legacy"])
def test_launch_resolves_states_for_new_and_running_emulators(state_environment, reused, name):
    states, bridge = state_environment
    target = states / {"demo": "demo.ss0", "demo.ss7": "demo.ss7", "legacy": "legacy.ss"}[name]
    target.write_bytes(b"synthetic state")
    bridge.launch.return_value = {"reused": reused}
    assert mcp_emu.emu_launch(savestate=name) == {"reused": reused}
    bridge.launch.assert_called_once_with(None, target)
    if reused:
        bridge.call.assert_called_once_with("load_state", target)
    else:
        bridge.call.assert_not_called()


def test_list_returns_unambiguous_loadable_filenames(state_environment):
    states, _ = state_environment
    for name in ("demo.ss", "demo.ss0", "demo.ss9", "upper.SS1", "notes.txt", "not-a-slot.ss10"):
        (states / name).write_bytes(b"synthetic data")
    (states / "directory.ss0").mkdir()
    assert mcp_emu.emu_list_states() == ["demo.ss", "demo.ss0", "demo.ss9", "upper.SS1"]


@pytest.mark.parametrize("name", ["../demo", r"..\demo", "demo\n", "demo state"])
def test_invalid_names_never_reach_the_bridge(state_environment, name):
    _, bridge = state_environment
    with pytest.raises(ToolError, match="state names may use"):
        mcp_emu.emu_save_state(name)
    bridge.call.assert_not_called()
