# Structs

## InputState (minimum covered size 0x14)

Base: `0x03000820`. Updated by `Input_Update` at `0x08009614` (Thumb).
The covered region ends at `+0x14`; the exact allocation size is unknown.
All identified fields use u16 storage. `+0x0a` is an unclassified two-byte gap.
`gKeysPrevious` is separate storage at `0x03000838`, accessed through its own pointer.

| Offset | Address | Size | Name | Meaning | Confidence |
|---|---|---|---|---|---|
| `+0x00` | `0x03000820` | 2 | `gKeysHeld` | Current active-high button mask, low 10 bits | confirmed |
| `+0x02` | `0x03000822` | 2 | `gKeysPressed` | `held & ~previous`; pure new presses, no repeat | confirmed |
| `+0x04` | `0x03000824` | 2 | `gKeysPressedRepeat` | Initially pure new presses; replaced by held mask when repeat countdown reaches zero | confirmed |
| `+0x06` | `0x03000826` | 2 | `gKeysReleased` | `previous & ~held`, one-poll release pulse | confirmed |
| `+0x08` | `0x03000828` | 2 | `gInputDpadPacked` | Packed high/low bytes from indexed D-pad tables | likely |
| `+0x0a` | `0x0300082a` | 2 unmapped bytes | unknown | No interpretation or type assigned | — |
| `+0x0c` | `0x0300082c` | 2 | `gInputRepeatInitialDelay` | Initial countdown; title value 90 | confirmed |
| `+0x0e` | `0x0300082e` | 2 | `gInputRepeatInterval` | Countdown reload at repeat; title value 4 | confirmed |
| `+0x10` | `0x03000830` | 2 | `gInputRepeatCountdown` | u16 countdown, initial load followed by same-poll decrement | confirmed |
| `+0x12` | `0x03000832` | 2 | `gInputUnchangedMaskFrames` | Static unchanged-held-mask counter; boundary behavior untested | likely |

Repeat timing was tested with L for 40 and 101 sampled held frames and R for 110.
With initial delay 90, first repeat occurred 89 frames after the first held poll.
Three L repeat hits spanned eight frames; six R repeat hits spanned twenty frames,
matching interval 4. Both the initial load and countdown/interval writer sites
were captured. Initial-delay restart occurs in the static code when
`pressed != 0 && pressed == held`; its behavior during partial-mask additions was
not separately timed. Countdown continues to decrement without held buttons.

For `+0x08`, the static code uses `index = (held & 0x00f0) >> 4` and, when index
is nonzero, stores `(table[0x08469cb4][index] << 8) | table[0x08469ca4][index]`.
The literal at `0x080096a4` points to the high-byte table `0x08469cb4`; the
literal at `0x080096a8` points to the low-byte table `0x08469ca4`. There is no
write on this path when no D-pad button is held, so static code suggests the last
value persists. Table purpose, individual byte meanings, and persistence were
not separately tested; confidence remains likely.

For `+0x12`, the static condition is `held == previous && count != 0xffff`:
increment if true, otherwise set zero. At `0xffff`, the branch at `0x08009666`
reaches `0x0800967c` (`mov r0,#0`), then stores at `0x0800967e`. This resets
rather than saturates. A 65,536-frame boundary experiment was not performed;
the counter semantics and boundary remain likely.

Confidence comes from empirical button/watchpoint transitions and timer timing,
corroborated by the parent's disassembly. The one script poke had no successful
post-write observation and provides no confirming evidence. See
[findings.md](findings.md) for the tests and tool limitations.
