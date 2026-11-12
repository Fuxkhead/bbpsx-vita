#!/usr/bin/env python3
"""Pack one image into the game's plain image format: u16 width, u16 height, RGBA bytes.
Used for title.bin (title screen picture, 588x330 in the original build) and logo.bin (splash, fits in 512x512; make_logo.sh does that one).
  python3 pack_rgba.py IN.png OUT.bin [MAXW MAXH]      (optionally shrink to fit MAXW x MAXH, keeping the aspect ratio)
The title picture is a screenshot / key art of your choice: any PNG works."""
import struct, sys
from PIL import Image
if len(sys.argv) < 3: sys.exit(__doc__)
im = Image.open(sys.argv[1]).convert('RGBA')
if len(sys.argv) >= 5: im.thumbnail((int(sys.argv[3]), int(sys.argv[4])), Image.LANCZOS)
w, h = im.size
open(sys.argv[2], 'wb').write(struct.pack('<HH', w, h) + im.tobytes())
print(sys.argv[2], w, 'x', h)
