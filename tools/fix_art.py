#!/usr/bin/env python3
"""checks the LiveArea art in ~/bbpsx-vita/sce_sys and rewrites it the way the Vita installer wants it:
exact sizes, 8-bit palette PNG (a 24/32-bit PNG makes the VPK install fail with error 0x8010113D).
the originals are kept next to it as <name>.orig.png.  usage: python3 fix_art.py [sce_sys folder]"""
import sys, os, shutil
from PIL import Image
S = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else '~/bbpsx-vita/sce_sys')
WANT = {'icon0.png': (128, 128), 'pic0.png': (960, 544), 'livearea/contents/bg0.png': (840, 500), 'livearea/contents/startup.png': (280, 158)}
for rel, (w, h) in WANT.items():
    p = os.path.join(S, rel)
    if not os.path.isfile(p): print('  missing', rel, '(skipped)'); continue
    im = Image.open(p); print('  %-32s %dx%d %s' % (rel, im.width, im.height, im.mode), end='')
    if im.mode == 'P' and im.size == (w, h): print('  ok'); continue
    shutil.copy(p, p[:-4] + '.orig.png')
    im = im.convert('RGBA')
    if im.size != (w, h): im = im.resize((w, h), Image.LANCZOS); print('  resized to %dx%d' % (w, h), end='')
    bg = Image.new('RGB', im.size, (0, 0, 0)); bg.paste(im, mask=im.split()[3])      # the Vita draws LiveArea art without alpha
    bg.quantize(colors=256, method=Image.MEDIANCUT).save(p, optimize=True); print('  -> 8-bit palette')
tx = os.path.join(S, 'livearea/contents/template.xml'); print('  template.xml', 'ok' if os.path.isfile(tx) else 'MISSING')
