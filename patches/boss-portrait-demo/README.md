# Existing Boss room-head frame swap

Build explicitly with `uv run hamtools patch build boss-portrait-demo`.
This redirects the idle Entity animation to a different existing compressed
**room-head** frame. The earlier dialogue-portrait description was too broad:
the face beside the text is a separate BG image. The checked byte edit remains
unchanged. Use [boss-recolor](../boss-recolor/README.md) to change the actual
dialogue portrait, and see [portraits.md](../../kb/portraits.md) for the correction.
