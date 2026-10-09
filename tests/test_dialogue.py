"""Authored-text encoding and C-source preparation; no game assets needed."""

from pathlib import Path

import pytest

from hamtools import dialogue, patch


def test_supported_alphabet_and_explicit_controls():
    text = " ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.!?\n"
    assert dialogue.encode_text(text) == (
        b"\x01" + bytes(range(0x0C, 0x26)) + b"abcdefghijklmnopqrstuvwxyz"
        + b"\xca\xd8\xd9\xe2"
    )
    assert dialogue.encode_text("T") == b"\x1f"
    assert dialogue.encode_text("") == b""  # encoding never adds an end control


@pytest.mark.parametrize("char", ["=", "@", "$", "~", "^", "\t", "\r", "\u20ac", "\0"])
def test_unknown_glyphs_are_conservative_errors(char):
    with pytest.raises(dialogue.DialogueError, match="unsupported dialogue glyph"):
        dialogue.encode_text(char)


def test_adjacent_literals_comments_and_c_escapes():
    source = r'DIALOGUE_TEXT("T\150e\162e\x20" /* join */ "is\040a" "\n\x62" "y.")'
    assert dialogue.expand_source(source) == (
        "0x1f, 0x68, 0x65, 0x72, 0x65, 0x01, 0x69, 0x73, 0x01, 0x61, "
        "0xe2, 0x62, 0x79, 0xca"
    )
    assert dialogue.expand_source(r'DIALOGUE_TEXT("\?")') == "0xd9"


def test_only_calls_are_rewritten():
    source = r"""// DIALOGUE_TEXT("unsupported &")
/* DIALOGUE_TEXT("unsupported ;") */
const char *note = "DIALOGUE_TEXT(\"unsupported %\")";
int character = 'DIALOGUE_TEXT("other")';
int quote = '\"', slash = '\\';
int DIALOGUE_TEXT_suffix, prefix_DIALOGUE_TEXT;
int DIALOGUE_TEXT;
const unsigned char first[] = { DIALOGUE_TEXT("A."), 0xe0 };
const unsigned char second[] = { DIALOGUE_TEXT("B!"), DIALOGUE_END() };
"""
    expected = source.replace('DIALOGUE_TEXT("A.")', "0x0c, 0xca").replace(
        'DIALOGUE_TEXT("B!")', "0x0d, 0xd8"
    )
    assert dialogue.expand_source(source) == expected


def test_line_splicing_happens_before_comments_and_literals():
    source = '// ignore \\\nDIALOGUE_TEXT("&")\nDIALOGUE_\\\nTEXT("Hel\\\nlo")'
    expanded = dialogue.expand_source(source)
    assert expanded == '// ignore \\\nDIALOGUE_TEXT("&")\n0x13, 0x65, 0x6c, 0x6c, 0x6f\\\n\\\n'
    assert expanded.count("\n") == source.count("\n")
    assert dialogue.expand_source('DIALOGUE_TEXT("A\\\r\nB")') == "0x0c, 0x0d\\\n"


@pytest.mark.parametrize(
    ("call", "message"),
    [
        ('DIALOGUE_TEXT()', "ordinary C string"),
        ('DIALOGUE_TEXT(name)', "ordinary C string"),
        ('DIALOGUE_TEXT(("Hi"))', "ordinary C string"),
        ('DIALOGUE_TEXT("Hi" + name)', "ordinary C string"),
        ('DIALOGUE_TEXT("Hi", "There")', "ordinary C string"),
        ('DIALOGUE_TEXT(L"Hi")', "ordinary C string"),
        ('DIALOGUE_TEXT(u8"Hi")', "ordinary C string"),
        ('DIALOGUE_TEXT("Hi"', "followed by"),
        ('DIALOGUE_TEXT("Hi)', "unterminated C string"),
        ('DIALOGUE_TEXT("Hi\\', "unterminated C string"),
        (r'DIALOGUE_TEXT("Hi\"', "unterminated C string"),
        ('DIALOGUE_TEXT("Hi\nthere")', "unescaped newline"),
        ('DIALOGUE_TEXT("Hi" /* open)', "unterminated comment"),
        ('DIALOGUE_TEXT("")', "at least one glyph"),
        (r'DIALOGUE_TEXT("\z")', "unknown C escape"),
        (r'DIALOGUE_TEXT("\x")', "hexadecimal digits"),
        (r'DIALOGUE_TEXT("\x100")', "exceeds 0xff"),
        (r'DIALOGUE_TEXT("\777")', "exceeds 0xff"),
        (r'DIALOGUE_TEXT("\u12")', "4 hexadecimal digits"),
        (r'DIALOGUE_TEXT("\U00110000")', "invalid Unicode"),
        (r'DIALOGUE_TEXT("\uD800")', "invalid Unicode"),
    ],
)
def test_malformed_or_nonliteral_calls_have_source_positions(call, message):
    with pytest.raises(dialogue.DialogueError) as error:
        dialogue.expand_source("/* before */\n" + call, Path("editable.c"))
    assert str(error.value).startswith("editable.c:2:")
    assert message in str(error.value)


@pytest.mark.parametrize("escape", [r"\t", r"\0", r"\x00", r"\a", r"\b", r"\f", r"\r", r"\v"])
def test_valid_c_escapes_can_still_be_unsupported_glyphs(escape):
    with pytest.raises(dialogue.DialogueError, match="unsupported dialogue glyph"):
        dialogue.expand_source(f'DIALOGUE_TEXT("{escape}")')


def test_numeric_escape_is_a_character_not_a_raw_game_byte():
    # C's 'A' (0x41) encodes as uppercase A (0x0c); raw controls stay outside text.
    assert dialogue.expand_source(r'DIALOGUE_TEXT("\101\x41")') == "0x0c, 0x0c"
    with pytest.raises(dialogue.DialogueError, match="unsupported dialogue glyph"):
        dialogue.expand_source(r'DIALOGUE_TEXT("\x7e")')


def test_verified_digits_punctuation_and_escaped_backslash():
    assert dialogue.encode_text("0123456789") == bytes(range(0x02, 0x0C))
    source = r'''DIALOGUE_TEXT("0,9-_()<>/\\'\u201cHi\u201d")'''
    expected = [0x02, 0xCF, 0x0B, 0xCB, 0xCC, 0xD2, 0xD3, 0xD4,
                0xD5, 0xD6, 0xD7, 0xD0, 0xCD, 0x13, 0x69, 0xCE]
    assert dialogue.expand_source(source) == ", ".join(f"0x{value:02x}" for value in expected)
    assert dialogue.encode_text("’") == b"\xd0"
    assert dialogue.encode_text("…") == b"\xd1"


def test_hex_escape_consumes_all_digits_like_c():
    with pytest.raises(dialogue.DialogueError, match="exceeds 0xff"):
        dialogue.expand_source(r'DIALOGUE_TEXT("\x41b")')
    assert dialogue.expand_source(r'DIALOGUE_TEXT("\x41" "b")') == "0x0c, 0x62"


def test_error_points_to_glyph_in_adjacent_literal_and_escape():
    with pytest.raises(dialogue.DialogueError) as error:
        dialogue.expand_source('DIALOGUE_TEXT("Hi"\n    "=")', "node.c")
    assert str(error.value) == "node.c:2:6: unsupported dialogue glyph '=' (U+003D)"
    with pytest.raises(dialogue.DialogueError) as error:
        dialogue.expand_source('DIALOGUE_TEXT("Hi"\n    "\\t")', "node.c")
    assert str(error.value) == r"node.c:2:6: unsupported dialogue glyph '\t' (U+0009)"


def test_spliced_error_points_to_original_source():
    with pytest.raises(dialogue.DialogueError) as error:
        dialogue.expand_source('DIALOGUE_\\\nTEXT("=")', "node.c")
    assert str(error.value) == "node.c:2:7: unsupported dialogue glyph '=' (U+003D)"


def test_prepare_generated_copy_preserves_original_and_line_numbers(tmp_path):
    source = tmp_path / "mod" / "main.c"
    source.parent.mkdir()
    authored = b'const unsigned char node[] = { DIALOGUE_TEXT("A"\r\n"B"), 0xe0 };\r\n'
    source.write_bytes(authored)
    generated = tmp_path / "build" / "obj" / "generated" / "mod" / "main.c"
    assert dialogue.prepare_source(source, generated) == generated
    assert source.read_bytes() == authored
    prepared = generated.read_text()
    assert prepared.startswith(f'#line 1 "{source.resolve().as_posix()}"\n')
    assert '0x0c, 0x0d\\\n, 0xe0' in prepared
    assert "DIALOGUE_TEXT" not in prepared


@pytest.mark.parametrize("filename", ["main.c", "hooks.s"])
def test_unchanged_sources_are_compiled_from_original_path(tmp_path, filename):
    source = tmp_path / filename
    original = b'/* DIALOGUE_TEXT("&") */\r\nconst unsigned char raw[] = { 0xe0 };\r\n'
    source.write_bytes(original)
    generated = tmp_path / "generated" / filename
    assert dialogue.prepare_source(source, generated) == source
    assert source.read_bytes() == original
    assert not generated.exists()


def test_non_utf8_comments_without_calls_pass_through(tmp_path):
    source = tmp_path / "main.c"
    source.write_bytes(b"/* \xe9 */\r\n")
    assert dialogue.prepare_source(source, tmp_path / "generated.c") == source


def test_compile_step_reports_editable_source_error(tmp_path, monkeypatch):
    mod = tmp_path / "mods" / "bad"
    mod.mkdir(parents=True)
    source = mod / "main.c"
    source.write_text('const char node[] = { DIALOGUE_TEXT("=") };')
    monkeypatch.setattr(patch.paths, "arm_tool", lambda name: Path(name))

    def unexpected_compile(*args):
        pytest.fail("invalid text must fail before running the compiler")

    monkeypatch.setattr(patch, "_run", unexpected_compile)
    with pytest.raises(patch.PatchError) as error:
        patch.compile_code([patch.Mod(name="bad", path=mod, sources=[source])], tmp_path / "obj")
    assert str(error.value) == f"{source}:1:38: unsupported dialogue glyph '=' (U+003D)"


def test_multiline_macro_definition_keeps_its_trailing_controls():
    source = '#define NODE DIALOGUE_TEXT("A" \\\n"B"), DIALOGUE_END()\n'
    assert dialogue.expand_source(source) == '#define NODE 0x0c, 0x0d\\\n, DIALOGUE_END()\n'


def test_native_accents_symbols_and_named_glyphs():
    from hamtools.glyphs import GLYPH_TABLE, NAMED_GLYPHS
    assert dialogue.encode_text("Éé&;:%\"♥") == bytes([0x33, 0x88, 0xDB, 0xC0, 0xC9, 0xC6, 0xCE, 0xDC])
    assert GLYPH_TABLE[NAMED_GLYPHS["OUTLINE_CROSS"]].char is None
    assert GLYPH_TABLE[0x5E].kind == "prefix" and GLYPH_TABLE[0xE0].kind == "control"
