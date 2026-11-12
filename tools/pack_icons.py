#!/usr/bin/env python3
"""Pack PNGs into the game's icon file format ("BBUI": u32 count, then {u8 nameLen, name, u16 w, u16 h, RGBA}).
Used for itemicons.bin, papericons.bin and menuart.bin.
  python3 pack_icons.py OUT.bin NAME=path.png[:SIZE] ...      (SIZE resizes to SIZE x SIZE; names must be <= 31 chars)
  python3 pack_icons.py --dir DIR OUT.bin                     (every PNG in DIR, name = file name)
The files the game expects:
  papericons.bin : T_IconFirePaper=<png>:128  T_IconBoltPaper=<png>:128
  menuart.bin    : M_Slot=<png>:96  M_TabItems=<png>:72  M_TabStatus=<png>:72  M_TabSystem=<png>:72
  itemicons.bin  : --dir assets/UI/ItemIcons   (make_itemicons.sh does this one)
Find the source PNGs under assets/UI (the FModel export): search by name, e.g.  find assets -iname 'T_IconFirePaper*'"""
import os, struct, sys
from PIL import Image
a = sys.argv[1:]
if not a: sys.exit(__doc__)
items = []
if a[0] == '--dir':
    d, out = a[1], a[2]
    for f in sorted(os.listdir(d)):
        if f.lower().endswith('.png'): items.append((os.path.splitext(f)[0], os.path.join(d, f), 0))
else:
    out = a[0]
    for s in a[1:]:
        n, p = s.split('=', 1); sz = 0
        if ':' in p and p.rsplit(':', 1)[1].isdigit(): p, sz = p.rsplit(':', 1); sz = int(sz)
        items.append((n, p, sz))
buf = []
for n, p, sz in items:
    if len(n) > 31: print('skip (name too long):', n); continue
    im = Image.open(p).convert('RGBA')
    if sz: im = im.resize((sz, sz), Image.LANCZOS)
    w, h = im.size
    buf.append(bytes([len(n)]) + n.encode() + struct.pack('<HH', w, h) + im.tobytes())
open(out, 'wb').write(b'BBUI' + struct.pack('<I', len(buf)) + b''.join(buf))
print('packed', len(buf), 'icons ->', out)
