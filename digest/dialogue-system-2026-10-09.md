# Dialogue, Event Scripts & Portraits (2026-10-09)

A plain-language guide to how characters talk, how event scripts decide what they say, and how portrait art is displayed in *Hamtaro: Ham-Ham Heartbreak*.

---

## 1. The Three Talking Interpreters

When you speak to a character in *Ham-Ham Heartbreak*, the game is not simply printing a text file. Three separate engines coordinate to produce the conversation:

1. **The Room Event Interpreter**:
   Runs bytecode controlling the room's logic. It monitors player proximity to NPCs, detects when the player presses **A**, displays the 4-choice Ham-Chat vocabulary menu (e.g. *Hamha*), evaluates player progress flags and hint counters, and selects which dialogue stream to trigger.
2. **The Dialogue Stream Reader**:
   Takes a raw ROM pointer passed by the event interpreter and steps through a custom one-byte encoded stream. It formats lines, manages text delay, waits for button presses, and calls callbacks.
3. **The Animation Engine**:
   Runs character animation scripts. When dialogue requests a portrait, an animation command triggers BIOS LZ77 decompression to load the character's facial tiles into RAM.

---

## 2. How the Game Picks Boss's Response to "Hamha"

Our investigation traced the exact decision tree for speaking to Boss in the Clubhouse:

```
Player presses A near Boss (Interaction record 0x080e2150, selector 9)
                   │
                   ▼
       Ham-Chat Menu (Opcode 0x24)
       Player selects "Hamha"
                   │
                   ▼
       Is Flag 0x0010 set? (Byte 0x03002172 bit 0)
         ├── NO  ──► Familiar Default Line (Pointer 0x0804ffb6 -> 0x0846cc6b)
         │           [Replaced by our sunflower-dialogue mod]
         │
         └── YES ──► Alternate Route (0x0804ffe7)
                       │
                       ├─► First meeting? (Flag 0x017d clear):
                       │     Shows first-time line (0x0846ccc3) and sets Flag 0x017d
                       │
                       └─► Repeat greeting? (0x08050079):
                             Checks Hint Counter (Byte var 0x003b at 0x020039cb)
                             • Counter = 0: Plays Hint #1, increments counter to 1
                             • Counter = 1: Plays Hint #2, increments counter to 2
                             • Counter = 2: Plays Hint #3, increments counter to 3
                             • Counter >= 3: Opcode 0x50 picks Hint #1, #2, or #3 at random!
```

All parts of this route were **confirmed in mGBA** by poking flags and memory variables.

---

## 3. The Custom Text Encoding & Complete Glyph Table

The game uses its own **one-byte character encoding** rather than standard ASCII or Shift-JIS. Lowercase letters match standard ASCII byte values, but uppercase letters, numbers, punctuation, and accented characters are mapped differently.

Both in-game font banks (normal and alternate) share the same glyph mapping. Every printable byte from `0x01` through `0xdf` has been **confirmed by an in-game visual probe**:

### Character Categories

| Byte Range | Meaning | Details |
|---|---|---|
| `0x01` | Space | Regular word spacing. |
| `0x02`–`0x0b` | Digits `0`–`9` | Confirmed by visual test. |
| `0x0c`–`0x25` | `A`–`Z` | Uppercase letters (offset by `-0x35` relative to ASCII). |
| `0x26`–`0x3c` | Accented Uppercase | `Ä Á À Â Ï Í Ì Î Ü Ú Ù Û Ë É È Ê Ö Ó Ò Ô Ç Ñ Œ` |
| `0x60` | Boxed `E` | Special icon: `[E]` (`BOXED_E`). |
| `0x61`–`0x7a` | `a`–`z` | Lowercase letters (matches ASCII values). |
| `0x7b`–`0x92` | Accented Lowercase | `ä á à â ï í ì î ü ú ù û ë é è ê ö ó ò ô ç ñ œ ß` |
| `0xc0`–`0xdb` | Punctuation | `;`, `°`, small raised `à`, `¿`, `¡`, `‘`, `%`, `*`, `+`, `:`, `.`, `-`, `_`, `“`, `”`, `,`, `’`, `…`, `(`, `)`, `<`, `>`, `/`, `\`, `!`, `?`, `#`, `&` |
| `0xdc`–`0xde` | Symbols | `♡` (Heart), `★` (Star), `♪` (Music note) |
| `0xdf` | Symbol | Outlined decorative cross |
| `0xe0`–`0xff` | Control codes | Handled by interpreter dispatch tables; see below. |

> [!NOTE]
> **Apostrophe vs. Ellipsis Correction**:
> An early reverse-engineering note mistook `0xd1` for the apostrophe. Comprehensive probing confirmed that `0xd0` is the apostrophe / closing single quote (`’`), while `0xd1` is a dedicated three-dot ellipsis character (`…`).

---

## 4. Dialogue Control Codes

Control bytes in the `0xe0`–`0xff` range tell the text reader what to do next:

| Opcode | Handler | Action |
|---|---|---|
| `0xe0` | `0x08004f34` | **Finish & Close**: Waits for the player to press **A**, then closes the dialogue window and unlinks the text state. |
| `0xe1` / `0x00` | `0x08004fb8` | **Return from Substring**: Restores the previous cursor position if dynamic text was inserted; otherwise ends the stream. |
| `0xe2` | `0x08005050` | **Newline**: Moves rendering cursor to the next line. |
| `0xe3` | `0x080050f0` | **Wait & Advance**: Waits for the player to press **A**, then scrolls down or advances to the next line. |
| `0xe6` | `0x08005210` | **Insert Dynamic String**: Temporarily redirects reading to a RAM buffer (at `0x03001f60`), saving the current cursor. |
| `0xf4 [id]` | `0x08005558` | **Scene Callback**: Calls callback `[id]` from the scene's function table at `0x03001fb0`. In the Clubhouse, callback `0x08` sets Boss's idle animation. |

---

## 5. Character Portraits & Graphics

Character portraits are rendered through character animation scripts, rather than being hardcoded to text boxes:

1. **Compressed Assets in ROM**:
   Boss's portraits are stored in ROM as LZ77-compressed tile blocks:
   - **Idle portrait**: `0x081bfc74` (`0x222` compressed bytes).
   - **Alternate portrait**: `0x081bfa60` (`0x213` compressed bytes).
   Both decompress to `0x480` bytes (36 4bpp tiles = 48x48 pixel square).
2. **Animation Command `0xcb`**:
   The script at `0x08687e17` runs opcode `0xcb`, followed by a 4-byte unaligned pointer to the compressed asset.
3. **Slot Math**:
   The loader determines the destination RAM slot via integer division:
   $$\text{Slot} = \frac{\text{Entity Index} - 10}{3}$$
   Boss is Entity 16, yielding Slot 2. The tiles are unpacked directly into RAM buffer `0x0201d2b0` using GBA BIOS SWI `0x11` (`LZ77UnCompWram`).
4. **Verified Modding Point**:
   By redirecting the 4-byte operand in the animation script (`0x08687e18`), we can make Boss use his alternate face graphic without needing to import new art (demonstrated in `patches/boss-portrait-demo`).

---

## 6. How We Author Dialogue Today

We have built an authored C workflow in `patches/include/dialogue.h` and `tools/hamtools/dialogue.py`. Modders can write natural English text with standard macros:

```c
#include "gba.h"
#include "dialogue.h"

// Define a named text block
const u8 Mod_BossSunflowerDialogue[] = {
    DIALOGUE_CALL(0x08), // Trigger Boss idle animation & portrait
    DIALOGUE_TEXT("There is a new sunflower\n"
                  "by the water."),
    DIALOGUE_END(),      // Wait for A, then close
};
```

When building, `hamtools` automatically converts the text into native game byte values and generates ready-to-compile ARM C in `build/`.
