#!/usr/bin/env python3
"""Build dlgfont.bin, the font used for subtitles and menu text ("DFN1").  UNTESTED against the game: written from the loader in main.c (fb_load).
The original build used the game's own bold serif (Times Bold look). Give it any bold serif TTF:
  python3 make_dlgfont.py FONT.ttf dlgfont.bin [SIZE]       (SIZE = pixel size, default 48)
Layout: "DFN1", u16 cellW, cellH, cols, baseline, capHeight, then 95 u8 advances (ASCII 32..126), then an 8-bit alpha atlas
(cols cells per row, 95 cells, each cellW x cellH). Glyphs are drawn 4 px in from the cell's left edge (the game shifts them back by 4)."""
import math, struct, sys
from PIL import Image, ImageDraw, ImageFont
if len(sys.argv) < 3: sys.exit(__doc__)
S = int(sys.argv[3]) if len(sys.argv) > 3 else 48
f = ImageFont.truetype(sys.argv[1], S)
asc, desc = f.getmetrics()
cw = int(math.ceil(S * 1.15)) + 8; ch = asc + desc + 4; cols = 16; base = asc + 2
cap = f.getbbox('H', anchor='ls')[3] - f.getbbox('H', anchor='ls')[1]
rows = (95 + cols - 1) // cols
im = Image.new('L', (cw * cols, ch * rows), 0); d = ImageDraw.Draw(im); adv = bytearray()
for i in range(95):
    c = chr(32 + i); x = (i % cols) * cw + 4; y = (i // cols) * ch + base
    if c != ' ': d.text((x, y), c, font=f, fill=255, anchor='ls')
    adv.append(min(255, int(round(f.getlength(c)))))
with open(sys.argv[2], 'wb') as o:
    o.write(b'DFN1' + struct.pack('<5H', cw, ch, cols, base, cap) + bytes(adv) + im.tobytes())
print('wrote', sys.argv[2], 'cell', cw, 'x', ch, 'cap', cap, 'base', base)
