#!/usr/bin/env python3
"""make_moonarena.py - the Moon Presence's arena: a calm, endless sheet of shallow water under a twilight sky (no source assets needed).

writes  level_moonarena.bin  interact_moonarena.bin  floor_moonarena.bin   into --outdir  (copy all three to ux0:data/bbpsx/)

  - a flat lake bed 150 m across with the scrolling ripple sheets laid over it (you wade; wading footsteps), nothing to hide behind
  - an invisible wall 42 m from the middle keeps you in (it is collision only, so the water seems to go on for ever)
  - one small stone islet with the lantern, west of the middle; you arrive beside it
usage: python3 make_moonarena.py --outdir ~/bbpsx-vita
"""
import argparse, math, os, random, struct
import numpy as np
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument("--outdir", default="."); ap.add_argument("--seed", type=int, default=11); args = ap.parse_args()
R = random.Random(args.seed)
def noise(n, scale, seed):
    r = np.random.RandomState(seed); g = r.rand(scale + 1, scale + 1); ys, xs = np.mgrid[0:n, 0:n] / n * scale; x0 = xs.astype(int); y0 = ys.astype(int); fx = xs - x0; fy = ys - y0
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy); x1 = (x0 + 1) % scale; y1 = (y0 + 1) % scale; x0 = x0 % scale; y0 = y0 % scale
    return (g[y0, x0] * (1 - fx) + g[y0, x1] * fx) * (1 - fy) + (g[y1, x0] * (1 - fx) + g[y1, x1] * fx) * fy
def tex_img(n, base, amp, scales, seed, post=16):
    v = sum(noise(n, s, seed + i) * w for i, (s, w) in enumerate(scales)) / sum(w for _, w in scales); img = np.zeros((n, n, 4), np.float32); img[..., 3] = 255
    for k in range(3): img[..., k] = base[k] + (v - 0.5) * 2 * amp[k]
    img[..., :3] = np.clip(np.round(img[..., :3] / post) * post, 0, 255); return Image.fromarray(img.astype(np.uint8), "RGBA")
def ripple_tex():      # pale, moonlit ripple streaks on clear, tiles
    n = 128; img = np.zeros((n, n, 4), np.uint8)
    for k in range(80):
        x = R.randrange(n); y = R.randrange(n); l = R.randrange(8, 34)
        for i in range(l):
            yy = (y + int(1.5 * math.sin(i * 0.4))) % n; img[yy, (x + i) % n] = (176, 186, 230, 255); img[(yy + 1) % n, (x + i) % n] = (120, 126, 176, 255)
    return Image.fromarray(img, "RGBA")
def stone_tex():
    t = tex_img(64, (96, 98, 112), (14, 14, 18), [(4, 1), (8, 2), (16, 1)], 41, 16); a = np.asarray(t).copy()
    for y in range(0, 64, 16):
        a[y, :, :3] = (a[y, :, :3] * 0.6).astype(np.uint8)
        for x in range((y // 16 % 2) * 16, 64, 32): a[y:y + 16, x, :3] = (a[y:y + 16, x, :3] * 0.6).astype(np.uint8)
    return Image.fromarray(a, "RGBA")
TEX = [("watertransp_moon.png", ripple_tex()), ("lakebed_moon.png", tex_img(64, (34, 36, 58), (10, 10, 16), [(4, 2), (8, 1), (16, 1)], 21, 8)), ("stone_moon.png", stone_tex())]
T_WATER, T_BED, T_STONE = 0, 1, 2
tris = []
def add_tri(tex, a, b, c, col=True): tris.append((tex, a, b, c, col))
def tri_uv(p0, p1, p2, s):
    ux, uy, uz = [p1[k] - p0[k] for k in range(3)]; vx, vy, vz = [p2[k] - p0[k] for k in range(3)]; nx, ny, nz = abs(uy * vz - uz * vy), abs(uz * vx - ux * vz), abs(ux * vy - uy * vx); out = []
    for p in (p0, p1, p2):
        uv = (p[0] * s, p[1] * s) if (nz >= nx and nz >= ny) else ((p[1] * s, p[2] * s) if nx >= ny else (p[0] * s, p[2] * s)); out.append((p[0], p[1], p[2], uv[0], uv[1]))
    return out
def add_plain(tex, p0, p1, p2, s=0.3, col=True): a, b, c = tri_uv(p0, p1, p2, s); add_tri(tex, a, b, c, col)
def add_quad(tex, p0, p1, p2, p3, s=0.3, col=True): add_plain(tex, p0, p1, p2, s, col); add_plain(tex, p0, p2, p3, s, col)

SEG = 48; BORDER = 42.0; EXTENT = 75.0; ISL = (-21.0, 0.0, 3.0)      # islet: centre x, y, radius
RINGS = [0.0, 6.0, 12.0, 18.0, 24.0, 30.0, 36.0, 42.0, 50.0, 60.0, EXTENT]
def bed(x, y): return 0.0
SPAWN = (ISL[0] + 3.6, ISL[1] - 1.2, 1.0); LANT = (ISL[0] - 0.6, ISL[1] + 0.4, 0.40)
# the lake: bed (solid) + two ripple sheets just over it (no collision, they scroll)
for i in range(len(RINGS) - 1):
    for j in range(SEG):
        P = lambda r, k: (r * math.cos(k / SEG * 2 * math.pi), r * math.sin(k / SEG * 2 * math.pi), bed(0, 0))
        a, b, c, d = P(RINGS[i], j), P(RINGS[i], j + 1), P(RINGS[i + 1], j + 1), P(RINGS[i + 1], j)
        for t in ((a, b, c), (a, c, d)):
            if math.hypot(*[sum(p[k] for p in t) / 3.0 for k in (0, 1)]) < 1e-6: continue
            ux, uy = t[1][0] - t[0][0], t[1][1] - t[0][1]; vx, vy = t[2][0] - t[0][0], t[2][1] - t[0][1]
            if abs(ux * vy - uy * vx) < 1e-6: continue
            add_tri(T_BED, *[(p[0], p[1], p[2], p[0] * 0.06, p[1] * 0.06) for p in t])
            add_tri(T_WATER, *[(p[0], p[1], p[2] + 0.07, p[0] * 0.14, p[1] * 0.14) for p in t], col=False)
            add_tri(T_WATER, *[(p[0], p[1], p[2] + 0.10, p[1] * 0.19 + 3.0, p[0] * 0.19) for p in t], col=False)
# the islet: a low round stone dais, three steps' worth of rim
def disc(cx, cy, rad, z0, z1, n=20):
    for k in range(n):
        a0, a1 = k / n * 2 * math.pi, (k + 1) / n * 2 * math.pi; p0 = (cx + rad * math.cos(a0), cy + rad * math.sin(a0)); p1 = (cx + rad * math.cos(a1), cy + rad * math.sin(a1))
        add_quad(T_STONE, (p0[0], p0[1], z0), (p1[0], p1[1], z0), (p1[0], p1[1], z1), (p0[0], p0[1], z1), 0.45)
        add_plain(T_STONE, (cx, cy, z1), (p0[0], p0[1], z1), (p1[0], p1[1], z1), 0.45)
disc(ISL[0], ISL[1], ISL[2] + 0.5, 0.0, 0.18); disc(ISL[0], ISL[1], ISL[2], 0.0, 0.36)
# the invisible wall (collision only: texture -1 is not drawn): a ring at BORDER, tall
N = 64
for k in range(N):
    a0, a1 = k / N * 2 * math.pi, (k + 1) / N * 2 * math.pi; p0 = (BORDER * math.cos(a0), BORDER * math.sin(a0)); p1 = (BORDER * math.cos(a1), BORDER * math.sin(a1))
    q = [(p0[0], p0[1], -1.0), (p1[0], p1[1], -1.0), (p1[0], p1[1], 14.0), (p0[0], p0[1], 14.0)]
    add_tri(-1, (*q[0], 0, 0), (*q[1], 0, 0), (*q[2], 0, 0)); add_tri(-1, (*q[0], 0, 0), (*q[2], 0, 0), (*q[3], 0, 0))
    add_tri(-1, (*q[0], 0, 0), (*q[2], 0, 0), (*q[1], 0, 0)); add_tri(-1, (*q[0], 0, 0), (*q[3], 0, 0), (*q[2], 0, 0))      # both faces
def write():
    os.makedirs(args.outdir, exist_ok=True); col = [t for t in tris if t[4]]; groups = {}
    for t in tris:
        if t[0] < 0: continue
        cx = sum(p[0] for p in t[1:4]) / 3; cy = sum(p[1] for p in t[1:4]) / 3
        groups.setdefault((t[0], int(math.floor(cx / 24.0)), int(math.floor(cy / 24.0))), []).append(t)
    geoms = []; draws = []
    for key in sorted(groups):
        pos = []; ind = []; cache = {}
        for t in groups[key]:
            for p in t[1:4]:
                if p not in cache: cache[p] = len(pos); pos.append(p)
                ind.append(cache[p])
        geoms.append((pos, ind)); draws.append(key[0])
    with open(os.path.join(args.outdir, "level_moonarena.bin"), "wb") as f:
        f.write(b"BBL2"); f.write(struct.pack("<IIIII", len(TEX), len(geoms), len(geoms), len(geoms), len(col))); f.write(struct.pack("<3f", *SPAWN))
        for t in col: f.write(struct.pack("<9f", *[t[i][k] for i in (1, 2, 3) for k in range(3)]))
        for name, im in TEX: nb = name.encode(); f.write(struct.pack("<B", len(nb)) + nb + struct.pack("<HH", im.width, im.height) + im.tobytes())
        for pos, ind in geoms:
            f.write(struct.pack("<II", len(pos), len(ind)))
            for p in pos: f.write(struct.pack("<5f", *p))
            f.write(struct.pack("<%dH" % len(ind), *ind))
        for gi, tx in enumerate(draws): f.write(struct.pack("<H", 1)); f.write(struct.pack("<IH", gi, tx))
        for gi in range(len(geoms)): f.write(struct.pack("<I12f", gi, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0))
    flo = [t for t in tris if t[0] == T_BED]
    with open(os.path.join(args.outdir, "floor_moonarena.bin"), "wb") as f:
        f.write(b"FLR1"); f.write(struct.pack("<I", len(flo)))
        for t in flo: f.write(struct.pack("<I9f", 2, *[t[i][k] for i in (1, 2, 3) for k in range(3)]))
    with open(os.path.join(args.outdir, "interact_moonarena.bin"), "wb") as f:
        f.write(b"BBI1"); f.write(struct.pack("<I", 0)); f.write(struct.pack("<I", 0))
        for tag in (b"ITM1", b"SPN1", b"LDR1", b"BLD1", b"ELV1", b"DST1", b"ITM2", b"FIR1", b"WCH1", b"LSL1", b"PTC1"): f.write(tag); f.write(struct.pack("<I", 0))
        f.write(b"LMP1"); f.write(struct.pack("<I", 1)); f.write(struct.pack("<3f", *LANT)); f.write(struct.pack("<I", 0))
    print(f"level_moonarena.bin: {len(tris)} triangles ({len(col)} solid), {len(geoms)} blocks; spawn {SPAWN}; lantern {LANT}")
write()
