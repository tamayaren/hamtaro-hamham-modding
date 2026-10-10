# Consistent Boss repeat hint

Once Boss's mapped greeting reaches its random repeat route, it always picks
the third hint. The script originally asks for a number from 0 up to, but
not including, 3. This mod changes the lower bound to 2: the only possible
result is 2. The nonempty range preserves the random-range routine's contract.

This demonstrates a gameplay parameter inside an event script. It changes
neither the game's global random generator nor Boss's dialogue text.

```powershell
$env:UV_CACHE_DIR = '.cache/uv'
$env:UV_NO_SYNC = '1'
uv run hamtools patch build gameplay-boss-hint
```

The original two-byte operand is checked before editing. Outputs are
`build/hamtaro-mod.gba` and `build/hamtaro-mod.bps`. Build by name to exclude
the other enabled demonstrations.

Verified against the original ROM on 2026-10-11 with a controlled repeat-route
copy of `dialogue-state.ss0`. The helper received lower/upper bounds 2/3,
the byte-result writer stored 2, and show-text command `0x08050104` ran.
The original with the same zero RNG chose result 0's command `0x080500c0`.
Both conversations closed and returned to normal input. Cold boot and
3,600 frames across supplied room/menu states showed no observed freeze or
graphics corruption. Other story gates and natural progression need playtesting.

Separate outputs are `build/gameplay-boss-hint/hamtaro-mod.gba` and
`build/gameplay-boss-hint/hamtaro-mod.bps`. Applying the BPS to the verified
original reproduced the built ROM exactly. The CLI command above writes the
default `build/` filenames; the recipe remains disabled for unnamed builds.

Playtest: apply the BPS to a copy of the verified USA ROM or open its built ROM,
using a test save copy. Load local `gameplay-boss-random-ready.ss0`; A talks to
Boss, A chooses Hamha, then advance all pages with A until control returns.
Repeat three times: the random repeat route should always choose its third
hint. The same state on the original chooses the first hint. This lab state
sets flag 0x0010, clears 0x007e/0x0191, sets hint counter 3 and zeros RNG.
Use an ordinary save afterward to check earlier hints, menus, room transitions
and a save/Continue cycle. An early Boss state can take a different story route.
See [gameplay.md](../../kb/gameplay.md) for the full checklist and limitations.
