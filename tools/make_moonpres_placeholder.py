#!/usr/bin/env python3
"""make_moonpres_placeholder.py - a stand-in for the Moon Presence flip-book that hangs over the blood moon after Gehrman and the Amygdala are dead.
It draws its own simple figure (a tall dark silhouette with spread arms, trailing hair and tendrils, swaying); no game data is used, so the file is safe to build
and share. The real picture can replace it later: same file name, same layout.

  python3 make_moonpres_placeholder.py --out moonpres.bin [--preview moonpres_placeholder.gif]

Copy moonpres.bin to ux0:data/bbpsx/.   Layout: 4 x u32 (frame w, frame h, columns, frames) then an RGBA4444 atlas (frames in rows of `columns`).
Tuning in game: ux0:data/bbpsx/moon_pres.txt = "scale dy fps".
"""
import argparse, math, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
ap = argparse.ArgumentParser(); ap.add_argument('--out', default='moonpres.bin'); ap.add_argument('--preview', default=None); a = ap.parse_args()
FW, FH, COLS, N = 224, 168, 8, 32; SS = 3; W, H = FW * SS, FH * SS
def curve(p0, p1, p2, p3, n=28):
    t = np.linspace(0, 1, n)[:, None]; return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3
def strand(dr, pts, w0, w1, col):
    n = len(pts)
    for i in range(n - 1):
        w = w0 + (w1 - w0) * i / (n - 1); dr.line([tuple(pts[i]), tuple(pts[i + 1])], fill=col, width=max(1, int(w)))
        dr.ellipse([pts[i][0] - w / 2, pts[i][1] - w / 2, pts[i][0] + w / 2, pts[i][1] + w / 2], fill=col)
def frame(k):
    w = 2 * math.pi * k / N; im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(im); C = (10, 2, 14, 255)
    cx, cy = W * 0.5, H * 0.42; S = H / 168.0
    sw = math.sin(w)
    # tendrils and trailing hair first (behind): long strands that ripple, each with its own phase
    for i in range(11):
        ph = i * 0.9; bx = cx + (i - 5) * 4 * S; by = cy - 18 * S
        d = (i - 5) / 5.0
        p0 = np.array([bx, by]); p3 = np.array([cx + d * 70 * S + 16 * S * math.sin(2 * w + ph), cy + 78 * S + 10 * S * math.cos(w + ph)])
        p1 = p0 + np.array([d * 30 * S + 10 * S * math.sin(w + ph), 26 * S]); p2 = p3 - np.array([d * 12 * S + 12 * S * math.sin(2 * w + ph + 1), 34 * S])
        strand(dr, curve(p0, p1, p2, p3), 7 * S, 1.5 * S, C)
    # arms: spread wide, drooping, a slow sway; fine fingers as short strands
    for sd in (-1, 1):
        sh = np.array([cx + sd * 10 * S, cy - 6 * S]); el = sh + np.array([sd * 38 * S, 10 * S + 4 * S * sw]); wr = el + np.array([sd * 34 * S, 22 * S + 8 * S * math.sin(w + 0.8)])
        strand(dr, curve(sh, sh + np.array([sd * 16 * S, 0]), el - np.array([sd * 10 * S, 0]), el), 9 * S, 6 * S, C); strand(dr, curve(el, el + np.array([sd * 12 * S, 4 * S]), wr - np.array([sd * 6 * S, 10 * S]), wr), 6 * S, 4 * S, C)
        for f in range(4):
            fp = wr + np.array([sd * (6 + f * 2) * S, (2 + f * 5) * S + 2 * S * math.sin(w + f)]); strand(dr, curve(wr, wr + np.array([sd * 4 * S, 4 * S]), fp - np.array([0, 3 * S]), fp), 3 * S, 1 * S, C)
    # body: a long tapering robe, shoulders, a small head
    body = [(cx - 15 * S, cy - 12 * S), (cx + 15 * S, cy - 12 * S), (cx + 11 * S + 3 * S * sw, cy + 40 * S), (cx + 5 * S, cy + 92 * S), (cx - 5 * S, cy + 92 * S), (cx - 11 * S + 3 * S * sw, cy + 40 * S)]
    dr.polygon(body, fill=C); dr.ellipse([cx - 11 * S, cy - 36 * S, cx + 11 * S, cy - 8 * S], fill=C)
    im = im.filter(ImageFilter.GaussianBlur(0.9)).resize((FW, FH), Image.LANCZOS); return im
atlas = np.zeros((N // COLS * FH, COLS * FW), dtype=np.uint16); frames = []
for k in range(N):
    im = frame(k); frames.append(im); p = np.array(im).astype(np.uint16)
    px = ((p[..., 0] >> 4) << 12) | ((p[..., 1] >> 4) << 8) | ((p[..., 2] >> 4) << 4) | (p[..., 3] >> 4); r, c = divmod(k, COLS); atlas[r * FH:(r + 1) * FH, c * FW:(c + 1) * FW] = px
open(a.out, 'wb').write(struct.pack('<4I', FW, FH, COLS, N) + atlas.astype('<u2').tobytes()); print('wrote', a.out, FW * COLS * FH * (N // COLS) * 2 // 1024, 'KB of atlas,', N, 'frames')
if a.preview:
    y, x = np.mgrid[0:FH * 2, 0:FW * 2]; dm = np.hypot(x - FW, y - FH * 0.9); bg = np.where((dm < 120)[..., None], np.array([205, 95, 45]), np.array([30, 8, 24])).astype('uint8'); out = []
    for f in frames:
        b = Image.fromarray(bg).convert('RGBA'); b.alpha_composite(f.resize((FW * 2, FH * 2), Image.LANCZOS)); out.append(b.convert('P'))
    out[0].save(a.preview, save_all=True, append_images=out[1:], duration=66, loop=0, disposal=2); print('preview', a.preview)
