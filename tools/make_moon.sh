#!/bin/bash
# Turns Moon.png into the moon file the game draws in every sky.   usage: bash assets/tools/make_moon.sh
SRC=~/bbpsx-vita/assets/Env/HuntersDream/Mat/Tex/Moon.png
CARD=/run/media/deck/USD00/Data/bbpsx
python3 - "$SRC" "$CARD/moon.bin" <<'PY' || exit 1
import sys, struct
from PIL import Image
im = Image.open(sys.argv[1]).convert('RGBA')
if max(im.size) > 256: im.thumbnail((256, 256), Image.LANCZOS)
px = im.load(); w, h = im.size
opaque = True      # always rebuild alpha from brightness (a 'transparent' png can still hold a dark box)
if opaque:      # no cut-out in the picture: black becomes see-through
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]; k = max(0, max(r, g, b) - 28); px[x, y] = (r, g, b, min(255, int(k * 1.5)))
open(sys.argv[2], 'wb').write(struct.pack('<II', w, h) + im.tobytes())
print('moon.bin', w, 'x', h, 'opaque source -> alpha from brightness' if opaque else 'has its own alpha')
PY
ls -l $CARD/moon.bin
echo "optional: $CARD/moon.txt with three numbers 'azimuth elevation size' (degrees; default 215 32 5.5) moves or resizes it"
