#!/bin/bash
# make_logo.sh - turns T_BloodbornePSXLogoShadow.png (found anywhere under ~/bbpsx-vita/assets or ~/Downloads) into the boot splash file
# the game reads: ux0:data/bbpsx/logo.bin. Writes it to ~/bbpsx-vita/logo.bin; copy it to the Vita's ux0:data/bbpsx/ folder.
src=$(find ~/bbpsx-vita/assets ~/Downloads -iname 'T_BloodbornePSXLogoShadow.png' 2>/dev/null | head -1)
[ -z "$src" ] && { echo "T_BloodbornePSXLogoShadow.png not found - put it in ~/Downloads and run again"; exit 1; }
echo "using $src"
python3 - "$src" <<'PY'
import sys, struct
from PIL import Image
im = Image.open(sys.argv[1]).convert('RGBA')
im.thumbnail((512, 512), Image.LANCZOS)
bg = Image.new('RGBA', im.size, (0, 0, 0, 255)); bg.alpha_composite(im)      # onto black, the splash background is black
w, h = bg.size
open(__import__('os').path.expanduser('~/bbpsx-vita/logo.bin'), 'wb').write(struct.pack('<HH', w, h) + bg.tobytes())
print(f"wrote ~/bbpsx-vita/logo.bin ({w}x{h})")
PY
