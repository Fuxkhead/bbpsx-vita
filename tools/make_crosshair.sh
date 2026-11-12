#!/bin/bash
# make_crosshair.sh - turns T_crosshair.png (found under ~/bbpsx-vita/assets or ~/Downloads) into ~/bbpsx-vita/crosshair.bin for the free-aim mode.
# Copy crosshair.bin to the Vita: ux0:data/bbpsx/crosshair.bin   (without it the game draws a simple built-in crosshair)
src=$(find ~/bbpsx-vita/assets ~/Downloads -iname 'T_crosshair.png' 2>/dev/null | head -1)
[ -z "$src" ] && { echo "T_crosshair.png not found - put it in ~/Downloads and run again"; exit 1; }
echo "using $src"
python3 - "$src" <<'PY'
import sys, struct, os
from PIL import Image
im = Image.open(sys.argv[1]).convert('RGBA')
im.thumbnail((128, 128), Image.LANCZOS)
w, h = im.size
open(os.path.expanduser('~/bbpsx-vita/crosshair.bin'), 'wb').write(struct.pack('<HH', w, h) + im.tobytes())
print(f"wrote ~/bbpsx-vita/crosshair.bin ({w}x{h})")
PY
