# Mods

Each mod is a folder with a `mod.toml` (format documented at the top of
`tools/hamtools/patch.py` and in the `patch-build` skill). Build every enabled mod:

```
uv run hamtools patch build            # -> build/hamtaro-mod.gba + build/hamtaro-mod.bps
uv run hamtools patch build some-mod   # only the named mod(s)
uv run hamtools patch list
```

Only sources live here — never ROM bytes beyond the short `expect` checks.
