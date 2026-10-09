"""Changed-only text edit export: synthetic fixtures and optional verified-ROM checks."""

import os
import struct
import tempfile
import tomllib
from pathlib import Path

import pytest

from hamtools import cli, events, paths, rom, text


FIRST, SECOND = 0x08000200, 0x08000240
ORIGINALS = {FIRST: 'Old "line"\\\n[callback 00][end]', SECOND: "'♥[end-nowait]"}


def _dump(entries):
    return "# Synthetic dump\n\n" + "\n".join(
        text.format_entry(text.Stream(address, text.encode(body), body), "synthetic")
        for address, body in entries.items())


@pytest.fixture
def original(monkeypatch):
    """Use the real walker with a tiny authored ROM; override only its table and hash."""
    monkeypatch.setattr(events, "SCENE_TABLE", rom.ROM_BASE + 0x10)
    data = bytearray(0x300)

    def put(address, raw):
        offset = address - rom.ROM_BASE
        data[offset:offset + len(raw)] = raw

    descriptor, script = rom.ROM_BASE + 0x80, rom.ROM_BASE + 0x100
    put(events.SCENE_TABLE, struct.pack("<I", descriptor))
    put(descriptor, struct.pack("<II", script, 0))
    put(script, b"\x1a\x00" + struct.pack("<I", FIRST)
        + b"\x1b\x00" + struct.pack("<I", SECOND) + b"\x01")
    for address, body in ORIGINALS.items():
        put(address, text.encode(body))
    original = bytes(data)
    monkeypatch.setattr(rom, "EXPECTED_SHA1", rom.sha1(original))
    assert set(events.walk(original).texts) == set(ORIGINALS)
    return original


@pytest.mark.parametrize("raw", [b"\x00", b"\xe0", b"\xe1", b"\xf0\x00\xe0",
                                b"\xf2\xe0\xe1\x0c\xe1"])
def test_validate_stream_accepts_one_stream_and_skips_operands(raw):
    assert text.validate_stream(raw) is None


@pytest.mark.parametrize("raw", [b"", b"\x0c", b"\xf0\x00", b"\xe0\x0c", b"\xe0\xe1",
                                b"\x00\xe0", b"\xf0", b"\xf2\xe0"])
def test_validate_stream_rejects_missing_internal_and_truncated_terminals(raw):
    with pytest.raises(text.TextError):
        text.validate_stream(raw)


def test_validate_stream_bounds():
    text.validate_stream(b"\x0c" * (text.MAX_STREAM - 1) + b"\xe0")
    with pytest.raises(text.TextError, match="no end byte"):
        text.validate_stream(b"\x0c" * text.MAX_STREAM + b"\xe0")


@pytest.mark.parametrize("offset, limit", [(-1, 20), (1, 20), (0, 0), (0, -1)])
def test_stream_length_rejects_invalid_bounds(offset, limit):
    with pytest.raises(text.TextError):
        text.stream_length(b"\xe0", offset, limit)


def test_read_stream_rejects_address_below_base():
    with pytest.raises(text.TextError, match="outside data"):
        text.read_stream(b"\xe0", rom.ROM_BASE - 1)


def test_parse_dump_rejects_even_identical_duplicates():
    with pytest.raises(text.TextError, match="duplicate entry 0x08000200"):
        text.parse_dump(_dump({FIRST: "A[end]"}) * 2)


@pytest.mark.parametrize("body", ["[end]A[end]", "{00}A[end]", "[end-nowait][end]",
                                 "[word][end]", "[word 00 01][end]", "[nope][end]",
                                 "[word zz][end]", "{zz}[end]", "[End][end]"])
def test_parse_dump_rejects_malformed_tags_and_multiple_streams(body):
    with pytest.raises(text.TextError, match="entry 0x08000200"):
        text.parse_dump(f"@{FIRST:#010x}\n{body}\n")


@pytest.mark.parametrize("dump", ["@0x08000200suffix\nA[end]\n", "@0x08000200\nA\n",
                                 "@0x08000200\nA\n@0x08000240\nB[end]\n",
                                 "@0x08000200\nA[end]\nextra\n"])
def test_parse_dump_rejects_bad_header_missing_terminal_and_stray_lines(dump):
    with pytest.raises(text.TextError):
        text.parse_dump(dump)


def test_parse_dump_accepts_crlf_and_comments_inside_text():
    dump = "# comment\r\n@0x08000200 note\r\n#body\r\n[word 00][end]\r\n"
    assert text.parse_dump(dump) == {FIRST: "#body\n[word 00][end]"}


def test_edits_exports_only_changed_streams_with_original_terminal_hash(original):
    entries = {SECOND: ORIGINALS[SECOND], FIRST: 'New "line"\\\n[callback 00][end]'}
    changed = text.edits(original, _dump(entries))
    assert changed == [{"address": FIRST, "text": entries[FIRST],
                        "expect_sha1": rom.sha1(text.encode(ORIGINALS[FIRST]))}]
    assert changed[0]["expect_sha1"] != rom.sha1(text.encode(ORIGINALS[FIRST])[:-1])
    exported = text.format_edits(changed)
    assert tomllib.loads(exported) == {"text": changed}
    assert "Old" not in exported and "0x08000240" not in exported
    assert "\r" not in exported


def test_edits_aliases_are_byte_identical_no_ops(original):
    entries = {address: text.read_stream(original, address).text for address in ORIGINALS}
    entries[SECOND] = "'♥[end-nowait]"
    assert text.edits(original, _dump(entries)) == []
    assert tomllib.loads(text.format_edits([])) == {"text": []}


def test_format_edits_is_sorted_and_toml_strings_round_trip(original):
    replacements = {SECOND: '"♥\\\n[end-nowait]', FIRST: "Éé[end]"}
    changed = text.edits(original, _dump(replacements))
    assert [entry["address"] for entry in changed] == [FIRST, SECOND]
    assert text.format_edits(changed) == text.format_edits(list(reversed(changed)))
    assert tomllib.loads(text.format_edits(changed))["text"] == changed


def test_format_edits_checks_json_escapes_are_valid_toml():
    with pytest.raises(text.TextError, match="TOML"):
        text.format_edits([{"address": FIRST, "text": "\x7f", "expect_sha1": "a" * 40}])


def test_edits_requires_verified_original_before_walk(original, monkeypatch):
    def unexpected_walk(data):
        pytest.fail("wrong ROM must fail before walking")

    monkeypatch.setattr(events, "walk", unexpected_walk)
    with pytest.raises(text.TextError, match="expected USA dump"):
        text.edits(original + b"\x00", _dump(ORIGINALS))


@pytest.mark.parametrize("partial", [False, True])
def test_edits_rejects_unknown_addresses_even_for_no_ops(original, partial):
    with pytest.raises(text.TextError, match="not a text address"):
        text.edits(original, _dump({**ORIGINALS, FIRST + 1: "[end]"}), partial=partial)


@pytest.mark.parametrize("entries", [{FIRST: ORIGINALS[FIRST]}, {}])
def test_edits_missing_entries_need_explicit_partial(original, entries):
    with pytest.raises(text.TextError, match="use --partial"):
        text.edits(original, _dump(entries))
    assert text.edits(original, _dump(entries), partial=True) == []


def test_edits_partial_does_not_delete_omitted_entry(original):
    changed = text.edits(original, _dump({FIRST: "Replacement[end]"}), partial=True)
    assert len(changed) == 1 and changed[0]["address"] == FIRST
    assert all(entry["address"] != SECOND for entry in changed)


@pytest.mark.parametrize("kind", ["problems", "unknown_natives"])
def test_edits_rejects_incomplete_walk(original, monkeypatch, kind):
    walked = events.walk(original)
    setattr(walked, kind, [(FIRST, "synthetic problem")] if kind == "problems"
            else {rom.ROM_BASE + 1: [FIRST]})
    monkeypatch.setattr(events, "walk", lambda data: walked)
    with pytest.raises(text.TextError, match="event walk is incomplete"):
        text.edits(original, _dump(ORIGINALS))


@pytest.fixture
def cli_files(original, tmp_path, monkeypatch):
    source = tmp_path / "synthetic-original.gba"
    source.write_bytes(original)
    monkeypatch.setenv("HAMTARO_ROM", str(source))
    edited = tmp_path / "edited.txt"
    edited.write_text(_dump({**ORIGINALS, FIRST: 'New "line"\\\n[end]'}), encoding="utf-8")
    out = tmp_path / "mods" / "mod.toml"
    return source, edited, out


def test_cli_exports_lf_without_changing_original_or_dump(cli_files, capsys):
    source, edited, out = cli_files
    before = source.read_bytes(), edited.read_bytes()
    assert cli.main(["text", "edits", str(edited), "--out", str(out)]) == 0
    assert b"\r" not in out.read_bytes()
    assert len(tomllib.loads(out.read_text(encoding="utf-8"))["text"]) == 1
    assert (source.read_bytes(), edited.read_bytes()) == before
    assert "1 changed stream(s)" in capsys.readouterr().out


def test_cli_refuses_existing_output_and_accepts_explicit_force(cli_files, capsys):
    _, edited, out = cli_files
    out.parent.mkdir()
    out.write_bytes(b"keep this\r\n")
    argv = ["text", "edits", str(edited), "--out", str(out)]
    assert cli.main(argv) == 2
    assert out.read_bytes() == b"keep this\r\n"
    assert "--force" in capsys.readouterr().err
    assert cli.main(argv + ["--force"]) == 0
    assert b"\r" not in out.read_bytes()


def test_cli_refuses_output_created_after_initial_check(cli_files, monkeypatch, capsys):
    _, edited, out = cli_files
    format_edits = text.format_edits

    def competing_writer(changed):
        out.parent.mkdir()
        out.write_bytes(b"another writer's output")
        return format_edits(changed)

    monkeypatch.setattr(text, "format_edits", competing_writer)
    assert cli.main(["text", "edits", str(edited), "--out", str(out)]) == 2
    assert out.read_bytes() == b"another writer's output"
    assert "cannot export text edits" in capsys.readouterr().err


@pytest.mark.parametrize("target", ["rom", "dump"])
def test_cli_never_overwrites_original_or_input_even_with_force(cli_files, capsys, target):
    source, edited, _ = cli_files
    out = source if target == "rom" else edited
    before = out.read_bytes()
    assert cli.main(["text", "edits", str(edited), "--out", str(out), "--force"]) == 2
    assert out.read_bytes() == before
    assert "must not overwrite" in capsys.readouterr().err


def test_cli_protects_hard_link_to_original(cli_files, tmp_path, capsys):
    source, edited, _ = cli_files
    linked = tmp_path / "mod.toml"
    try:
        os.link(source, linked)
    except OSError:
        pytest.skip("hard links unavailable")
    before = source.read_bytes()
    assert cli.main(["text", "edits", str(edited), "--out", str(linked), "--force"]) == 2
    assert source.read_bytes() == before
    assert "must not overwrite" in capsys.readouterr().err


def test_cli_partial_is_explicit_and_deleted_entry_is_not_deletion(cli_files, capsys):
    _, edited, out = cli_files
    edited.write_text(_dump({FIRST: "New[end]"}), encoding="utf-8")
    argv = ["text", "edits", str(edited), "--out", str(out)]
    assert cli.main(argv) == 2
    assert not out.exists()
    assert "--partial" in capsys.readouterr().err
    assert cli.main(argv + ["--partial"]) == 0
    entries = tomllib.loads(out.read_text(encoding="utf-8"))["text"]
    assert [entry["address"] for entry in entries] == [FIRST]


def test_cli_validation_failure_preserves_existing_output_with_force(cli_files, capsys):
    _, edited, out = cli_files
    edited.write_text(_dump(ORIGINALS) * 2, encoding="utf-8")
    out.parent.mkdir()
    out.write_bytes(b"keep this")
    assert cli.main(["text", "edits", str(edited), "--out", str(out), "--force"]) == 2
    assert out.read_bytes() == b"keep this"
    assert "duplicate" in capsys.readouterr().err


@pytest.mark.parametrize("bad_input", [b"\xff", None])
def test_cli_reports_unreadable_dump_without_output(cli_files, capsys, bad_input):
    _, edited, out = cli_files
    if bad_input is None:
        edited.unlink()
    else:
        edited.write_bytes(bad_input)
    assert cli.main(["text", "edits", str(edited), "--out", str(out)]) == 2
    assert not out.exists()
    assert "cannot export text edits" in capsys.readouterr().err


def test_cli_checks_wrong_rom_before_writing(cli_files, capsys):
    source, edited, out = cli_files
    source.write_bytes(source.read_bytes() + b"\x00")
    assert cli.main(["text", "edits", str(edited), "--out", str(out)]) == 2
    assert not out.exists()
    assert "expected USA dump" in capsys.readouterr().err


def _rom_or_skip():
    try:
        data = rom.load_rom()
    except rom.RomError:
        pytest.skip("needs the ROM")
    if rom.sha1(data) != rom.EXPECTED_SHA1:
        pytest.skip("not the expected ROM")
    return data


def test_real_rom_unchanged_full_dump_exports_no_text():
    data = _rom_or_skip()
    entries = {address: text.read_stream(data, address).text for address in events.walk(data).texts}
    assert len(entries) == 3599
    assert text.edits(data, _dump(entries)) == []


def test_real_rom_authored_partial_edit_hash_and_cli():
    data = _rom_or_skip()
    address = min(events.walk(data).texts)
    original = text.read_stream(data, address)
    authored = "Authored helper test[end]"
    assert text.encode(authored) != original.raw
    # Even temporary files with copied ROM dialogue must remain in an ignored directory.
    paths.EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="text-edits-test-", dir=paths.EXTRACTED_DIR) as temp:
        edited, out = Path(temp) / "edited.txt", Path(temp) / "mod.toml"
        edited.write_text(_dump({address: authored}), encoding="utf-8")
        assert cli.main(["text", "edits", str(edited), "--out", str(out), "--partial"]) == 0
        assert tomllib.loads(out.read_text(encoding="utf-8"))["text"] == [
            {"address": address, "text": authored, "expect_sha1": rom.sha1(original.raw)}]
        assert b"\r" not in out.read_bytes()
    assert rom.sha1(rom.load_rom()) == rom.EXPECTED_SHA1
