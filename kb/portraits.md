# Dialogue portraits

Addresses refer to the verified USA AH3E ROM, SHA1
`2525cc23524068dfb3a2b4e0ce7b736f95023e82`. No extracted graphics are tracked.

## Boss portrait assets

| Address | Meaning | Confidence |
|---|---|---|
| `0x081bfc74` | Boss's clubhouse idle portrait tiles, LZ77-compressed; expands to `0x480` bytes | confirmed |
| `0x081bfa60` | Another Boss portrait tile block, LZ77-compressed; same expanded size | confirmed |
| `0x08687e17` | Boss idle animation script; starts with portrait-load command `0xcb` | confirmed |
| `0x08687e18` | Unaligned four-byte portrait asset operand in that script | confirmed |
| `0x08687dde` | Alternate Boss animation script; starts with the other portrait asset | confirmed by animation replay |
| `0x08687ddf` | Its four-byte portrait operand | confirmed |
| `0x0201d2b0` | Loaded portrait tile buffer for Boss in this scene, slot 2 | confirmed |

Both assets have compression header `10 80 04 00`. Local decompression consumed
`0x222` bytes for the idle asset and `0x213` bytes for the alternate, including
the header. The expanded `0x480` bytes fit 36 4bpp tiles, consistent with a
48x48 portrait (**likely** geometry). Exact tile arrangement, palette choice,
and blink/mouth overlay composition have not been mapped.

Changing Boss's live animation pointer and resetting its script offset loaded
the alternate graphic. Restoring the saved normal scene restored a buffer that
matched the normal asset exactly. Searching the whole EWRAM region found the
alternate bytes at `0x0201d2b0`; the normal and alternate buffers were each
compared against independent local decompression of their ROM assets.

The optional `patches/boss-portrait-demo` then changed **only the four-byte
asset pointer** at `0x08687e18`, leaving the animation and text controls intact.
The built game displayed the alternate portrait, loaded the expected alternate
buffer, and passed message close/repeat checks. This directly confirms the
portrait operand rather than inferring its purpose only from a whole animation.

## How dialogue reaches the portrait

Text control `0xf4` plus one byte invokes a **scene callback**. It is not a
universal portrait-selection opcode. `Text_CtrlInvokeCallback` at `0x08005558`
consumes that byte, then calls `Scene_InvokeCallback` at `0x08001440`.
The latter indexes the function-pointer table at `0x03001fb0`.

In the provided clubhouse scene:

| Callback byte | Function, Thumb | Observed/static action |
|---|---|---|
| `0x08` | `0x0804193c` | Set Boss idle animation to `0x08687e17`; normal portrait path confirmed |
| `0x09` | `0x080418b8` | Set animation to `0x08679610` and request an event wait; likely from code |
| `0x16` | `0x080418dc` | Set animation to `0x08687dde`; likely from code |

The live table's callback `0x08` entry is `0x03001fd0`. Its read was observed
at reported PC `0x0800144e`, exact Thumb instruction `0x0800144a`, with
LR `0x08005569`. The table is scene-installed, so another scene may give the
same byte a different meaning. Do not rename these bytes as global face IDs.

Callback `0x08` calls `Entity_SetAnimation` at `0x0800af54`. Boss's entity index
is read from `0x03002bf4`; it was 16 in this scene. The entity array was
`0x0202280c`, so Boss was at `0x02022e8c` (stride `0x68`). Its `+0x04` animation
pointer is `0x02022e90`, and its `+0x4c` script byte offset is `0x02022ed8`.
The setter also resets animation counters. These entity addresses are scene
observations, not addresses to hard-code for other NPCs.

## Animation command and decompression

`Anim_CtrlLoadPortraitTiles` at `0x0800d014` handles `0xcb` followed by a
little-endian four-byte asset pointer. It reads the four bytes separately,
so the operand need not be aligned. Read-watchpoints reported PCs
`0x0800d034`, `0x0800d036`, `0x0800d03c`, `0x0800d042`, corresponding to
instructions `0x0800d030`, `0x0800d032`, `0x0800d038`, `0x0800d03e`.
Both the normal and pointer-patched paths executed this reader.

The handler obtains the entity index, computes `(index - 10) / 3`, and takes
the first word of a record at `0x08469cdc + slot * 0x11c`. This is division,
not a remainder: Boss index 16 selects slot 2. That calculation agrees with
the observed `r0 = 2` and the matched destination buffer.

| Slot | Record's first word address | Destination | Confidence |
|---|---|---|---|
| 0 | `0x08469cdc` | `0x02002590` | likely; static pointer |
| 1 | `0x08469df8` | `0x0201fcd0` | likely; static pointer |
| 2 | `0x08469f14` | `0x0201d2b0` | confirmed buffer match |

It calls the BIOS LZ77-to-WRAM wrapper at `0x080e5614` (`swi 0x11`), then
advances both the temporary script pointer and Entity `+0x4c` offset by five
bytes. General record size/other fields and the later graphics upload are
still **likely** or unmapped. The expanded block was not found as a single
contiguous block in the sampled VRAM; do not claim a VRAM destination yet.

The portrait changes through a character animation, so swapping its operand
affects other uses of that animation too. A callback can change the room
sprite as well as the dialogue portrait. A future portrait-specific API needs
the remaining composition/upload path mapped first.

The active TextState's `+0x30` was `0x08464e5c`, matching window template 1
in a static table at `0x08464e30` with stride `0x2c` (**likely** format).
The scene's window-template indices at `0x03000600` had slot 0 set to 1.
The window records were reached through `0x03002df8` (value `0x020237a4`),
with an animation pointer at record `+0x14` (`0x020237b8`, value `0x0866fc3d`).
Those window/frame observations are distinct from the verified Boss portrait
asset operand. Reserved text sprite slots 3 through 7 were empty in this scene.

## Local evidence and verification

All local extracted material is under `extracted/dialogue-hunt-20261009/`.
It includes `portrait-image-command.txt`, `portrait-buffer-and-callback.txt`,
the independently decompressed portrait binaries, runtime traces, and
`portrait-pointer-mod-test.json`. Screenshots are
`screenshots/dialogue-helper-normal.png` and
`screenshots/portrait-demo-alternate.png`; savestates are in `states/`.

The initial fast portrait test pressed A before text reached its final control.
The corrected test explicitly waited for cursor `0x086d0028`, then verified A
closed the text list to `0x03000610`; a second conversation loaded the same
alternate buffer and reached the same final wait. No original ROM file was
changed. Wider animation reuse, room changes, and longer sessions remain for
human playtesting.
