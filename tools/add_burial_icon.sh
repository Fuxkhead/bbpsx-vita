#!/bin/bash
# puts the Burial Blade's menu icon into itemicons.bin (the shop, the inventory and the equip screens use it) and copies the pack to the card
#   cp ~/Downloads/add_burial_icon.sh ~/bbpsx-vita/assets/tools/; bash ~/bbpsx-vita/assets/tools/add_burial_icon.sh
cd ~/bbpsx-vita || exit 1
D=assets/UI/ItemIcons; mkdir -p $D
SRC=$(find assets -name 'T_IconBurialBlade.png' | head -1)
[ -n "$SRC" ] || { echo "T_IconBurialBlade.png not found under assets/"; exit 1; }
[ -f $D/T_IconBurialBlade.png ] || cp -v "$SRC" $D/T_IconBurialBlade.png
python3 - <<'PY'
import os, struct
from PIL import Image
d = os.path.expanduser('~/bbpsx-vita/assets/UI/ItemIcons')
out = []
for f in sorted(os.listdir(d)):
    if not f.lower().endswith('.png'): continue
    n = os.path.splitext(f)[0]
    if len(n) > 31: print('skip (name too long):', n); continue
    im = Image.open(os.path.join(d, f)).convert('RGBA'); w, h = im.size
    out.append(bytes([len(n)]) + n.encode() + struct.pack('<HH', w, h) + im.tobytes())
open('itemicons.bin', 'wb').write(b'BBUI' + struct.pack('<I', len(out)) + b''.join(out))
print('packed', len(out), 'icons')
PY
cp -v itemicons.bin /run/media/deck/USD00/Data/bbpsx/itemicons.bin
