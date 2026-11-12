#!/bin/bash
# Packs every PNG in assets/UI/ItemIcons into itemicons.bin and copies it to the Vita data folder.
cd ~/bbpsx-vita || exit 1
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
mkdir -p ~/bbpsx-vita/data_out 2>/dev/null
echo "Copy itemicons.bin to the Vita: ux0:data/bbpsx/itemicons.bin  (file is in ~/bbpsx-vita/)"
ls -l itemicons.bin
