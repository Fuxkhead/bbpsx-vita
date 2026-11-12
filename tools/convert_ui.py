#!/usr/bin/env python3
"""Pack the HUD PNGs into ui.bin ("BBUI"): u32 count; then {u8 nameLen, name, u16 w, u16 h, RGBA}.
usage: python3 tools/convert_ui.py --tex DIR [DIR ...] --out ui.bin   (PNGs are searched recursively by name)"""
import argparse, os, struct, sys
from PIL import Image
NAMES = "healthFg healthBg staminaFg healthglow T_crosshair T_Frame T_FrameTransp T_FrameTranspLess T_FrameHighlightYellow T_IconBloodVial T_QuicksilverBullet huntersymbol T_insighticon Gradient BarHighlight healthBgTransp T_lockon T_D-padDown T_D-padUp T_D-padLeft T_D-padRight T_FaceButtonTriangle T_FaceButtonCircle T_FaceButtonCross T_FaceButtonBox T_ButtonR1 T_ButtonL1 T_ButtonL2 T_ButtonR2 T_ButtonStart T_ButtonSelect T_Icon_SEPoison T_Icon_SERPoison T_Icon_SEFrenzy".split()
ap = argparse.ArgumentParser()
ap.add_argument('--tex', nargs='+', required=True)
ap.add_argument('--out', default='ui.bin')
ap.add_argument('--names', nargs='*', default=NAMES)
a = ap.parse_args()
found = {}
for d in a.tex:
    for root, _, files in os.walk(d):
        for f in files:
            if f.lower().endswith('.png'): found.setdefault(os.path.splitext(f)[0].lower(), os.path.join(root, f))
out = []
for n in a.names:
    p = found.get(n.lower())
    if not p: print('WARNING: no', n + '.png'); continue
    im = Image.open(p).convert('RGBA'); w, h = im.size
    out.append(bytes([len(n)]) + n.encode() + struct.pack('<HH', w, h) + im.tobytes())
    print('%-24s %3dx%-3d %s' % (n, w, h, p))
open(a.out, 'wb').write(b'BBUI' + struct.pack('<I', len(out)) + b''.join(out))
print('wrote', a.out, len(out), 'textures')
