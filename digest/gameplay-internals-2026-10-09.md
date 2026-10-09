# Gameplay & RAM Internals (2026-10-09)

A plain-language guide to player physics, movement tables, controller input handling, and the core RAM layout in *Hamtaro: Ham-Ham Heartbreak*.

---

## 1. Player Physics & Movement

### 1.1 Coordinates & Fixed-Point Math
Hamtaro's position is tracked in 3D space ($X$, $Z$ height, $Y$) using **32-bit signed 16.16 fixed-point numbers**:
- The high 16 bits represent whole screen pixels.
- The low 16 bits represent fractional sub-pixel movement.
- A value of `0x00010000` equals exactly 1.0 pixel.

When moving, velocity is added to the coordinate, and the fractional accumulator ensures smooth movement across frames.

### 1.2 Speed & Velocity Table
Movement velocities are read directly from a table in ROM, `kPlayerMoveVelocityTable` at `0x08467af0`:

```
Table Layout: [Mode: Walk or Run] x [Direction: Up, Down, Left, Right] x (vx, vy)
```

| Mode | Direction | Original Velocity | Pixels per Frame |
|---|---|---|---|
| **Walk** | Up | `0xFFFF0000` | -1.0 px/frame |
| | Down | `0x00010000` | +1.0 px/frame |
| | Left | `0xFFFF0000` | -1.0 px/frame |
| | Right | `0x00010000` | +1.0 px/frame |
| **Run** *(B held)* | Up | `0xFFFE0000` | -2.0 px/frame |
| | Down | `0x00020000` | +2.0 px/frame |
| | Left | `0xFFFE0000` | -2.0 px/frame |
| | Right | `0x00020000` | +2.0 px/frame |

- **Strict Priority**: The game checks directions in order: **Up > Down > Left > Right**. If multiple D-pad buttons are held, only the highest priority direction applies (no diagonal movement).
- **Collision Preserved**: Poking higher speeds (such as in `faster-walk`) revealed that the game's tile and boundary collision routines continue to halt Hamtaro cleanly against walls and furniture.

---

## 2. Character Entities & The Entity Array

All actors on screen (Hamtaro, companions, and NPCs) are stored in an array of `Entity` structs (size `0x68` bytes each):

- **Array Base**: Pointer `gEntityArray` at `0x03002d88`.
- **Hamtaro Slot**: `gPlayerEntityIndex` at `0x03002bfc` (Index `10` in the clubhouse bedroom).
- **Formula**:
  $$\text{Entity Address} = \text{*}gEntityArray + (\text{Index} \times 0x68)$$

### Key Entity Fields

| Offset | Type | Name | Purpose |
|---|---|---|---|
| `+0x04` | Pointer | `animationScript` | Current ROM animation script. |
| `+0x18` | s32 (16.16) | `x` | Horizontal position. |
| `+0x1c` | s32 (16.16) | `z` | Height / vertical elevation. |
| `+0x20` | s32 (16.16) | `y` | Vertical position (down is positive). |
| `+0x24` | s32 (16.16) | `vx` | Horizontal velocity (zeroed after update). |
| `+0x2c` | s32 (16.16) | `vy` | Vertical velocity. |
| `+0x4c` | u16 | `animationOffset` | Byte offset into the active animation script. |

> [!TIP]
> Do not hard-code absolute RAM addresses like `0x02022c34` in mods: always dereference `gEntityArray` and multiply by `gPlayerEntityIndex`, as the entity buffer can move across scenes.

---

## 3. Controller Input & Auto-Repeat Subsystem

The game polls controller input once per frame in `Input_Update` (`0x08009614`, Thumb). It reads the hardware register `REG_KEYINPUT` (`0x04000130`), inverts it from active-low to active-high, and writes a structured `InputState` block starting at `0x03000820`:

### Button Bitmask Layout (Bits 0–9)

| Button | Hex Mask | Button | Hex Mask |
|---|---|---|---|
| **A** | `0x0001` | **B** | `0x0002` |
| **Select** | `0x0004` | **Start** | `0x0008` |
| **Right** | `0x0010` | **Left** | `0x0020` |
| **Up** | `0x0040` | **Down** | `0x0080` |
| **R** | `0x0100` | **L** | `0x0200` |

### Input Variables in IWRAM

| Address | Variable | Purpose |
|---|---|---|
| `0x03000820` | `gKeysHeld` | Buttons held down right now. |
| `0x03000822` | `gKeysPressed` | Buttons newly pressed this frame (does not repeat). |
| `0x03000824` | `gKeysPressedRepeat` | Newly pressed buttons **plus** auto-repeat pulses while held. |
| `0x03000826` | `gKeysReleased` | Buttons let go this frame. |
| `0x0300082c` | `gInputRepeatInitialDelay` | Frames to wait before first auto-repeat (e.g. 90 frames on title screen). |
| `0x0300082e` | `gInputRepeatInterval` | Frames between subsequent auto-repeat pulses (e.g. 4 frames). |
| `0x03000830` | `gInputRepeatCountdown` | Live countdown timer for repeat pulses. |
| `0x03000838` | `gKeysPrevious` | Buttons held on the previous frame. |

---

## 4. Master RAM Map Cheat Sheet

A concise reference for the most important global memory addresses confirmed in the game:

### Fast IWRAM (`0x03000000`–`0x03007FFF`)
- `0x03000010`: Current event opcode (`gEventOpcode`).
- `0x030005f0`: Text state owned by active dialogue event (`gEventTextState`).
- `0x03000608`: Head of active text-window objects list (`gTextStateList`).
- `0x03000610`: Text list sentinel / empty list indicator (`gTextStateSentinel`).
- `0x03000820`: Controller input state base (`InputState`).
- `0x03001f58`: Current subscene ID (`gSubsceneId`).
- `0x03001fac`: Shared selector / menu result (`gEventSelector`).
- `0x03001fb0`: Scene callback function table (`gSceneCallbacks`).
- `0x03002170`: **Progression bitflags array** (`gEventFlags`). Accessed via byte `id >> 3` and bit `id & 7`.
- `0x030021e0`: Active room interaction record pointer slots (`gInteractionRecords`).
- `0x03002bfc`: Player entity slot index (`gPlayerEntityIndex`).
- `0x03002c48`: Current scene ID (`gSceneId`).
- `0x03002c50`: Live event script operand pointer (`gEventCursor`).
- `0x03002d88`: Pointer to the Entity array (`gEntityArray`).

### General EWRAM (`0x02000000`–`0x0203FFFF`)
- `0x02003990`: Event byte variables array (`gEventByteVars`).
- `0x020039cb`: Boss repeat-hint counter (`gBossHintCounter`, byte var `0x003b`).
- `0x0201d0b0`: Event word variables array (`gEventWordVars`).
- `0x0201d2b0`: Boss decompress portrait destination buffer (Slot 2).
- `0x0202280c`: Entity array buffer in clubhouse bedroom scene.
- `0x0202447c`: Active dialogue `TextState` struct in clubhouse scene.
