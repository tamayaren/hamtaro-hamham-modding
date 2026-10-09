# Modding & Authoring Guide (2026-10-09)

A practical, hands-on guide for creating mods for *Hamtaro: Ham-Ham Heartbreak* using our tooling and patch system.

---

## 1. Setup & Environment

Before building mods, ensure your environment is set up:

```powershell
# 1. Install dependencies
uv sync

# 2. Verify your USA ROM dump (SHA1 must match 2525cc23524068dfb3a2b4e0ce7b736f95023e82)
uv run hamtools rom verify

# 3. Check ROM info
uv run hamtools rom info
```

For compiling C/asm mods (such as custom dialogue), make sure the GNU ARM toolchain (`arm-none-eabi-gcc`) is in your PATH or set `$env:ARM_TOOLCHAIN_BIN`.

---

## 2. Modding Walking & Running Speed

Movement speed is controlled by `kPlayerMoveVelocityTable` at `0x08467af0`. You can change Hamtaro's speed without compiling any code by adding byte edits in a `mod.toml`.

### Example: Double Walk Speed
In `patches/faster-walk/mod.toml`:

```toml
name = "faster-walk"
description = "Hamtaro walks at 2 px/frame (was 1) and runs at 3 px/frame (was 2)"
enabled = true

# Walk Up vy: -1.0 (0xFFFF) -> -2.0 (0xFFFE)
[[edit]]
address = 0x08467af4
expect = "00 00 ff ff"
hex = "00 00 fe ff"
comment = "walk Up vy -1 -> -2"

# Walk Down vy: +1.0 (0x0001) -> +2.0 (0x0002)
[[edit]]
address = 0x08467afc
expect = "00 00 01 00"
hex = "00 00 02 00"
comment = "walk Down vy +1 -> +2"

# Walk Left vx: -1.0 (0xFFFF) -> -2.0 (0xFFFE)
[[edit]]
address = 0x08467b00
expect = "00 00 ff ff"
hex = "00 00 fe ff"
comment = "walk Left vx -1 -> -2"

# Walk Right vx: +1.0 (0x0001) -> +2.0 (0x0002)
[[edit]]
address = 0x08467b08
expect = "00 00 01 00"
hex = "00 00 02 00"
comment = "walk Right vx +1 -> +2"
```

The `expect` field ensures safety: if the ROM bytes at that address do not match the original game, the build immediately aborts.

---

## 3. Authoring Custom Dialogue

You can write new dialogue in plain C using the macros in `patches/include/dialogue.h`.

### 3.1 Writing the Text Source
Open `patches/sunflower-dialogue/dialogue.c`:

```c
#include "gba.h"
#include "dialogue.h"

// Define your dialogue stream
const u8 Mod_BossSunflowerDialogue[] = {
    // 1. Play Boss's talking animation & portrait
    DIALOGUE_CALL(0x08),

    // 2. Display text on two lines
    DIALOGUE_TEXT("There is a new sunflower\n"
                  "by the water."),

    // 3. Wait for the player to press A, then close the box
    DIALOGUE_END(),
};
```

### 3.2 Useful Dialogue Macros

| Macro | Description |
|---|---|
| `DIALOGUE_TEXT("...")` | Encodes plain English text into the game's native one-byte font. Supports letters, digits, accents, commas, periods, quotes, `!`, `?`, etc. |
| `\n` | Soft newline within the same dialogue box. |
| `DIALOGUE_WAIT_LINE()` | Waits for the player to press **A**, then clears or scrolls to the next line (control `0xe3`). |
| `DIALOGUE_CALL(id)` | Invokes a scene callback (control `0xf4 [id]`). Callback `0x08` sets Boss's talking animation in the clubhouse. |
| `DIALOGUE_END()` | Waits for **A**, then closes the dialogue window and returns control (control `0xe0`). |
| `DIALOGUE_GLYPH(NAME)` | Inserts special symbols: `HEART`, `STAR`, `MUSIC_NOTE`, `DEGREE`, `BOXED_E`. |

### 3.3 Redirecting the Game to Your Dialogue
In `patches/sunflower-dialogue/mod.toml`, bind the event pointer to your compiled C array:

```toml
name = "sunflower-dialogue"
description = "Replaces Boss's clubhouse Hamha response with an authored C sentence"
enabled = true

c_sources = ["dialogue.c"]

# Redirect Boss's unaligned response pointer
[[pointer]]
address = 0x0804ffb6
expect = 0x0846cc6b
symbol = "Mod_BossSunflowerDialogue"
comment = "Redirect Boss Hamha response pointer to our authored text in free space"
```

`hamtools` compiles your text into ROM free space (`0x086d0000`) and updates the pointer at `0x0804ffb6`.

---

## 4. Swapping Character Portraits

To change a character's face, you can redirect the 4-byte unaligned asset pointer inside their animation script:

In `patches/boss-portrait-demo/mod.toml`:

```toml
name = "boss-portrait-demo"
description = "Redirects Boss's idle portrait to his alternate face graphic"
enabled = true

[[edit]]
address = 0x08687e18
expect = "74 fc 1b 08"      # Original: 0x081bfc74 (Normal face)
hex    = "60 fa 1b 08"      # New:      0x081bfa60 (Alternate face)
comment = "Redirect portrait asset operand to existing alternate face"
```

---

## 5. Building, Patching & Playtesting

### 5.1 Build the Patched ROM & BPS Patch

```powershell
$env:UV_CACHE_DIR = '.cache/uv'
uv run hamtools patch build
```

This will:
1. Verify the original ROM SHA1.
2. Compile enabled C mods into free space (`0x086d0000`).
3. Apply all pointer redirects and byte edits.
4. Verify all `expect` byte checks.
5. Generate `build/hamtaro-mod.gba`.
6. Generate a standalone `build/hamtaro-mod.bps` patch file.
7. Verify that patching the original ROM with the BPS reproduces `build/hamtaro-mod.gba` byte-for-byte.

### 5.2 Test in Emulator
Launch mGBA with our automated Lua bridge:

```powershell
uv run hamtools emu launch
```

### 5.3 Automated Verification
Run the complete regression test suite:

```powershell
uv run pytest -q
```
All 61+ tests (including ARM compilation, BPS verification, and ROM integrity) should pass.
