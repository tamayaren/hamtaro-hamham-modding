# Text glyph table (USA, `AH3E`)

One byte per glyph in dialogue streams. Both font banks (normal/alternate,
see the `+0x0b` flag in [structs.md](structs.md)) use the same IDs. The
machine-readable table is `tools/hamtools/glyphs.py`; the authoring helper
(`patches/include/dialogue.h` + `tools/hamtools/dialogue.py`) uses it.

Confidence: every printable row below is **confirmed**. A probe build drew each
byte `0x01`–`0xdf` with a label, in both font banks, in the Boss/Hamha scene
(2026-10-09); all 33 pages displayed and the dialogue closed normally. The two
banks show identical shapes. Accent *placement* on accented letters was read at
native 240x160 resolution; the letter order is certain, individual accents are
best re-checked if a mod depends on one.

| Byte(s) | Meaning | Confidence |
|---|---|---|
| `0x00` | Control (treated as `0xe1`, end inserted stream) | confirmed (static) |
| `0x01` | Space | confirmed |
| `0x02`–`0x0b` | `0`–`9` | confirmed |
| `0x0c`–`0x25` | `A`–`Z` | confirmed |
| `0x26`–`0x3c` | `Ä Á À Â Ï Í Ì Î Ü Ú Ù Û Ë É È Ê Ö Ó Ò Ô Ç Ñ Œ` | confirmed |
| `0x3d`–`0x5d` | Blank slots | confirmed |
| `0x5e` | Insert/style prefix, handled separately by the reader (skipped by the probe) | likely |
| `0x5f` | Blank slot | confirmed |
| `0x60` | Boxed `E` (named `BOXED_E`) | confirmed |
| `0x61`–`0x7a` | `a`–`z` | confirmed |
| `0x7b`–`0x92` | `ä á à â ï í ì î ü ú ù û ë é è ê ö ó ò ô ç ñ œ ß` | confirmed |
| `0x93`–`0xbf` | Blank slots | confirmed |
| `0xc0` | `;` | confirmed |
| `0xc1` | `°` (`DEGREE`) | confirmed |
| `0xc2` | Small raised `à` (`RAISED_A_GRAVE`; not the same as `0x7d`) | confirmed |
| `0xc3`, `0xc4` | `¿`, `¡` | confirmed |
| `0xc5` | `‘` opening single quote | confirmed |
| `0xc6`–`0xc9` | `%`, `*`, `+`, `:` | confirmed |
| `0xca` | `.` | confirmed |
| `0xcb`, `0xcc` | `-`, `_` | confirmed |
| `0xcd`, `0xce` | `“`, `”` | confirmed |
| `0xcf` | `,` | confirmed |
| `0xd0` | `’` apostrophe / closing single quote | confirmed |
| `0xd1` | `…` ellipsis (one glyph; an earlier KB entry wrongly called it the apostrophe) | confirmed |
| `0xd2`–`0xd9` | `( ) < > / \ ! ?` | confirmed |
| `0xda`, `0xdb` | `#`, `&` | confirmed |
| `0xdc`–`0xde` | Heart, star, music note | confirmed |
| `0xdf` | Outlined cross (no Unicode equivalent) | confirmed |
| `0xe0`–`0xff` | Controls; see [dialogue.md](dialogue.md) | partly confirmed |

## Authoring

- ASCII `'` encodes as `0xd0`, ASCII `"` as `0xce` (closing quote). Write
  `“`/`‘` explicitly for opening quotes. `♥` is accepted as an alias for `0xdc`.
- Shapes without a clean Unicode character use `DIALOGUE_GLYPH(BOXED_E)`,
  `DEGREE`, `RAISED_A_GRAVE`, `HEART`, `STAR`, `MUSIC_NOTE`, `OUTLINE_CROSS`.
- Not in the font: `= @ $ ~ ^ [ ] { } |` and tabs; the helper rejects them.

## Still open

- Operands of controls `0xe4`–`0xff` other than `0xe6`/`0xf4`; the probe used
  `0xeb`/`0xee` around pages but their exact semantics are not recorded here.
