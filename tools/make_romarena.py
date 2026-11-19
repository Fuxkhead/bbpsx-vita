#!/usr/bin/env python3
"""make_romarena.py - builds a Rom-style lake arena (Byrgenwerth's misty lake) as a game map, with no source assets needed.

writes  level_romarena.bin  interact_romarena.bin  floor_romarena.bin   into --outdir  (copy all three to ux0:data/bbpsx/)

The arena (metres, +Z up, Rom's spot is the centre 0,0):
  - a round, shallow lake (the floor is the scrolling water texture, so you wade; wading footsteps) about 60 m across
  - a few muddy islands, a ring of broken standing stones round the middle, fallen pillars, boulders, dead trees, reeds
  - a muddy bank all the way round, then a steep cliff wall (solid) and mist
  - you arrive on the bank on the west side, next to a lantern
usage: python3 make_romarena.py --outdir ~/bbpsx-vita [--seed 7]
"""
import argparse, math, os, random, struct
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("--outdir", default=".")
ap.add_argument("--seed", type=int, default=7)
ap.add_argument("--assets", default=None, help="your exported assets folder (e.g. ~/bbpsx-vita/assets): the arena then uses the game's own textures (T_Stone, T_Dirt, t_grass1, T_WaterTransp, t_stackedstone, t_gravestone) where it finds them")
ap.add_argument("--waterlight", type=float, default=0.9, help="brightness of the water ripple streaks")
ap.add_argument("--dark", type=float, default=0.8, help="brightness of the game textures (the game's materials are tinted darker)")
ap.add_argument("--preview", default=None, help="also write a top-down preview png")
args = ap.parse_args()
R = random.Random(args.seed)
NP = np.random.RandomState(args.seed)

# ---------------------------------------------------------------- textures (procedural, PSX-ish: small, posterised)
def noise(n, scale, seed):
    r = np.random.RandomState(seed); g = r.rand(scale + 1, scale + 1)
    ys, xs = np.mgrid[0:n, 0:n] / n * scale; x0 = xs.astype(int); y0 = ys.astype(int); fx = xs - x0; fy = ys - y0
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    x1 = (x0 + 1) % scale; y1 = (y0 + 1) % scale; x0 = x0 % scale; y0 = y0 % scale
    return (g[y0, x0] * (1 - fx) + g[y0, x1] * fx) * (1 - fy) + (g[y1, x0] * (1 - fx) + g[y1, x1] * fx) * fy

def tex_img(n, base, amp, scales, seed, post=24, extra=None):
    v = sum(noise(n, s, seed + i) * w for i, (s, w) in enumerate(scales)) / sum(w for _, w in scales)
    img = np.zeros((n, n, 4), np.float32); img[..., 3] = 255
    for k in range(3): img[..., k] = base[k] + (v - 0.5) * 2 * amp[k]
    if extra: extra(img, n)
    img[..., :3] = np.clip(np.round(img[..., :3] / post) * post, 0, 255)
    return Image.fromarray(img.astype(np.uint8), "RGBA")

def ex_water(img, n):
    for k in range(40):      # light ripple streaks
        x = R.randrange(n); y = R.randrange(n); l = R.randrange(6, 20)
        for i in range(l): img[y, (x + i) % n, :3] += 26
def ex_stone(img, n):
    for y in range(0, n, 16):
        img[y, :, :3] -= 38
        for x in range((y // 16 % 2) * 16, n, 32): img[y:y + 16, x, :3] -= 38
    m = noise(n, 4, 91) > 0.62; img[m, 0] -= 6; img[m, 1] += 10; img[m, 2] -= 8      # a little moss
def ex_cliff(img, n):
    for y in range(n):
        d = 14 * math.sin(y * 0.5) + 10 * math.sin(y * 1.3 + 2); img[y, :, :3] += d
def ex_bark(img, n):
    for x in range(0, n, 3): img[:, x, :3] -= 16
def ex_grass(img, n):
    for k in range(260):
        x = R.randrange(n); y = R.randrange(n); l = R.randrange(2, 6)
        for i in range(l): img[(y - i) % n, x, :3] += (14, 18, -6)

TEX = [
    ("watertransp_romlake.png", tex_img(128, (30, 48, 56), (14, 16, 16), [(4, 2), (8, 1)], 11, 8, ex_water)),      # 'watertransp' = scrolls, 'water' = wading steps
    ("mud_rom.png", tex_img(64, (66, 56, 44), (20, 16, 14), [(4, 2), (8, 2), (16, 1)], 21)),
    ("deadgrass_rom.png", tex_img(64, (84, 82, 54), (22, 22, 14), [(4, 2), (8, 1)], 31, 16, ex_grass)),
    ("stone_rom.png", tex_img(64, (104, 108, 112), (16, 16, 18), [(4, 1), (8, 2), (16, 1)], 41, 16, ex_stone)),
    ("cliff_rom.png", tex_img(64, (68, 66, 74), (16, 14, 18), [(2, 2), (8, 1)], 51, 16, ex_cliff)),
    ("bark_rom.png", tex_img(32, (50, 40, 34), (16, 14, 12), [(4, 1), (8, 1)], 61, 12, ex_bark)),
]
def reed_tex():      # cut-out reeds: blades with alpha 0 between them
    n = 32; img = np.zeros((n, n, 4), np.uint8)
    for k in range(9):
        x = R.randrange(2, n - 2); h = R.randrange(18, n - 1); lean = R.choice((-1, 0, 0, 1)); g = R.choice(((92, 98, 58), (110, 104, 62), (74, 86, 50)))
        for y in range(h):
            xx = x + (lean * y) // 8
            if 0 <= xx < n: img[n - 1 - y, xx] = (g[0], g[1], g[2], 255)
            if y < h // 2 and 0 <= xx + 1 < n: img[n - 1 - y, xx + 1] = (g[0] - 12, g[1] - 12, g[2] - 8, 255)
    return Image.fromarray(img, "RGBA")
TEX.append(("reeds_rom.png", reed_tex()))
TEX.append(("gravestone_rom.png", TEX[3][1]))
TEX.append(("lakebed_rom.png", TEX[0][1]))      # the lake bed (solid, dark wet ground); the water is a see-through ripple sheet laid just over it, like the sewers
def ripple_tex():      # fallback water surface: pale ripple streaks on clear, scrolls (name has 'watertransp')
    n = 128; img = np.zeros((n, n, 4), np.uint8)
    for k in range(70):
        x = R.randrange(n); y = R.randrange(n); l = R.randrange(8, 30)
        for i in range(l):
            yy = (y + int(1.5 * math.sin(i * 0.4))) % n; img[yy, (x + i) % n] = (150, 176, 188, 255); img[(yy + 1) % n, (x + i) % n] = (110, 138, 150, 255)
    return Image.fromarray(img, "RGBA")
TEX[0] = ("watertransp_rom.png", ripple_tex())
T_WATER, T_MUD, T_GRASS, T_STONE, T_CLIFF, T_BARK, T_REED, T_GRAVE, T_BED, T_TREE0, T_TREE1, T_TREE2 = range(12)
for _k in range(3): TEX.append(("tree_card_%d.png" % _k, TEX[5][1]))      # placeholders: replaced by the game's T_Tree*Dead cards when found
CARDS = {}      # role -> width / height of the card image
GAME_ROLES = set()

def game_textures():
    """swap the procedural textures for the game's own where the files exist (ground roles must be opaque)"""
    if not args.assets: return
    root = os.path.expanduser(args.assets); idx = {}
    for dp, _, fs in os.walk(root):
        for fn in fs:
            if fn.lower().endswith(".png"): idx.setdefault(fn.lower(), os.path.join(dp, fn))
    want = {T_WATER: ["t_watertransp.png"], T_BED: ["t_water.png"], T_TREE0: ["t_tree2dead.png"], T_TREE1: ["t_tree3dead.png"], T_TREE2: ["t_tree1dead.png"], T_REED: ["t_grass1.png"], T_MUD: ["t_dirt.png"], T_GRASS: ["t_flowerstile.png"], T_STONE: ["t_stone.png"], T_CLIFF: ["t_stackedstone.png", "t_stone.png"], T_GRAVE: ["t_gravestone.png", "t_gravestone2.png", "t_stone.png"]}
    for role, names in want.items():
        for nm in names:
            if nm not in idx: continue
            try:
                im = Image.open(idx[nm]).convert("RGBA"); a = np.asarray(im)
                tr = a[..., 3] < 128
                if role in (T_WATER, T_REED, T_TREE0, T_TREE1, T_TREE2):      # see-through textures stay see-through (the water is a ripple sheet over the lake bed, the reeds are cut-out cards)
                    if tr.mean() > 0.995: print(f"  {nm}: fully transparent, kept the generated one"); continue
                    card = role in (T_TREE0, T_TREE1, T_TREE2); aspect = im.width / im.height
                    w = 1
                    while w * 2 <= min(im.width, 256 if card else 128): w *= 2
                    h = 1
                    while h * 2 <= min(im.height, 256 if card else 128): h *= 2
                    im = im.convert("RGBa").resize((w, h), Image.BOX).convert("RGBA"); a = np.asarray(im).astype(np.float32); a[..., :3] *= (args.waterlight if role == T_WATER else args.dark)      # (resized with the colour weighted by the alpha, so no dark / white fringes)
                    if role != T_WATER: a[..., 3] = np.clip(a[..., 3] * 2.2, 0, 255)      # thin twigs and blades keep above the game's cut-out threshold after shrinking
                    if card: CARDS[role] = aspect
                    GAME_ROLES.add(role)
                    TEX[role] = ("watertransp_game.png" if role == T_WATER else ("reeds_game.png" if role == T_REED else "tree_card_%d_game.png" % (role - T_TREE0)), Image.fromarray(a.astype(np.uint8), "RGBA")); print(f"  {'water' if role == T_WATER else ('reeds' if role == T_REED else 'tree card')}: using the game's {os.path.basename(idx[nm])} ({w}x{h}, {tr.mean() * 100:.0f}% clear, kept see-through)"); break
                if tr.mean() > 0.97: print(f"  {nm}: fully transparent, kept the generated one"); continue
                if tr.mean() > 0.0:      # cut-out / see-through texture: the clear parts take the average colour of the solid parts, so it works as a ground
                    a = a.copy(); a[tr, :3] = a[~tr, :3].mean(0).astype(np.uint8); a[..., 3] = 255; im = Image.fromarray(a, "RGBA"); print(f"  {nm}: {tr.mean() * 100:.0f}% clear, filled")
                w = 1
                while w * 2 <= min(im.width, 128): w *= 2
                h = 1
                while h * 2 <= min(im.height, 128): h *= 2
                im = im.resize((w, h), Image.BOX); a = np.asarray(im).astype(np.float32); a[..., :3] *= args.dark; a[..., 3] = 255
                keep = TEX[role][0] if role == T_WATER else os.path.basename(idx[nm]).lower()
                if role == T_WATER: keep = "watertransp_game.png"      # the name must contain 'watertransp' (it scrolls) 
                GAME_ROLES.add(role); TEX[role] = (keep, Image.fromarray(a.astype(np.uint8), "RGBA")); print(f"  {role}: using the game's {os.path.basename(idx[nm])} ({w}x{h})"); break
            except Exception as e: print(f"  {nm}: could not read ({e})")
game_textures()

def grass_from_blades():
    """the game's t_grass1 is a card of blades: scatter it over an olive base to get a proper grass ground"""
    if T_REED not in GAME_ROLES or T_GRASS in GAME_ROLES: return      # (the Hunter's Dream flower grass, t_flowerstile, is used when it is found)
    card = np.asarray(TEX[T_REED][1]).copy(); m = card[..., 3] > 100
    if m.sum() < 20: return
    mean = card[m, :3].astype(np.float32).mean(0)
    base = np.clip(mean * np.array([0.52, 0.60, 0.40]) + np.array([4, 8, 0]), 0, 255)      # a dull dead-grass green-olive under the blades
    N = 128; can = np.zeros((N, N, 4), np.float32); can[..., :3] = base; can[..., 3] = 255
    n2 = noise(N, 8, 77); can[..., :3] *= (0.85 + 0.3 * n2)[..., None]
    cw, ch = card.shape[1], card.shape[0]; rr = random.Random(5)
    for k in range(150):
        c = card[:, ::-1] if rr.random() < 0.5 else card; x0 = rr.randrange(N); y0 = rr.randrange(N)
        for yy in range(ch):
            for xx in range(cw):
                px = c[yy, xx]
                if px[3] > 100:
                    X = (x0 + xx) % N; Y = (y0 + yy) % N; can[Y, X, :3] = px[:3] * rr.uniform(0.7, 1.0)
    TEX[T_GRASS] = ("grass_game.png", Image.fromarray(np.clip(can, 0, 255).astype(np.uint8), "RGBA")); print("  grass: built from the game's t_grass1 blades")
grass_from_blades()


# ---------------------------------------------------------------- geometry containers
tris = []        # (tex, (x,y,z,u,v)*3, collide)
def add_tri(tex, a, b, c, col=True): tris.append((tex, a, b, c, col))

def tri_uv(p0, p1, p2, s=0.25):
    """triplanar-ish UVs by dominant normal axis -> 3 (x,y,z,u,v)"""
    ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]; vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
    nx, ny, nz = abs(uy * vz - uz * vy), abs(uz * vx - ux * vz), abs(ux * vy - uy * vx)
    out = []
    for p in (p0, p1, p2):
        if nz >= nx and nz >= ny: uv = (p[0] * s, p[1] * s)
        elif nx >= ny: uv = (p[1] * s, p[2] * s)
        else: uv = (p[0] * s, p[2] * s)
        out.append((p[0], p[1], p[2], uv[0], uv[1]))
    return out

def add_plain(tex, p0, p1, p2, s=0.25, col=True):
    a, b, c = tri_uv(p0, p1, p2, s); add_tri(tex, a, b, c, col)

def add_quad(tex, p0, p1, p2, p3, s=0.25, col=True):
    add_plain(tex, p0, p1, p2, s, col); add_plain(tex, p0, p2, p3, s, col)

# ---------------------------------------------------------------- terrain
SEG = 64
RINGS = [0.0] + [3.0 * i for i in range(1, 13)] + [38.0, 40.0, 42.0, 44.0, 46.0, 48.0, 50.0, 54.0, 58.0]
def sstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)
def vnoise(x, y, sc, seed):
    r = np.random.RandomState(seed); return 0
_gn = noise(256, 16, 5)
def gnoise(x, y, scale=0.08):       # smooth world noise 0..1
    u = (x * scale) % 16.0; v = (y * scale) % 16.0; return float(_gn[int(v / 16.0 * 255) % 256, int(u / 16.0 * 255) % 256])
ISLANDS = [(-9.0, 10.0, 5.5, 0.9), (11.0, 7.0, 6.5, 1.1), (7.0, -12.0, 5.0, 0.8), (-12.0, -9.0, 6.0, 1.0), (21.0, -4.0, 4.5, 0.7), (-23.0, 3.0, 5.0, 0.8), (0.0, -22.0, 4.5, 0.7), (1.0, 20.0, 4.0, 0.6)]
def rim_r(th): return 36.0 + 3.2 * math.sin(th * 3 + 1.0) + 1.8 * math.sin(th * 5 + 0.3) + 1.2 * math.sin(th * 9)      # where the bank starts rising
def height(x, y):
    r = math.hypot(x, y); th = math.atan2(y, x); rr = rim_r(th)
    h = 0.0
    for cx, cy, rad, hh in ISLANDS:
        d = math.hypot(x - cx, y - cy)
        if d < rad: h = max(h, hh * (0.5 + 0.5 * math.cos(math.pi * d / rad)) ** 0.8)
    h += 0.10 * gnoise(x, y, 0.5)
    b = sstep(rr - 5.0, rr + 1.5, r) * 2.5                                    # the bank rises out of the lake
    h = max(h * (1 - sstep(rr - 6, rr - 2, r)), 0.0) + b
    if r > rr + 3.0: h += (r - rr - 3.0) * 4.6                                # then the cliff wall
    if r > rr + 8.5: h = (rr + 5.5 - rr) * 0 + h
    if r > rr + 12.0: h = min(h, 2.5 + 9.0 * 4.6 + 6.0)
    return h
def terrain():
    V = [[None] * (SEG + 1) for _ in RINGS]
    for i, r in enumerate(RINGS):
        for j in range(SEG + 1):
            th = (j % SEG) / SEG * 2 * math.pi
            if r < 40: jit = 0.0
            else: jit = 0.0
            x, y = r * math.cos(th), r * math.sin(th)
            V[i][j] = (x, y, height(x, y))
    cnt = 0
    for i in range(len(RINGS) - 1):
        for j in range(SEG):
            a, b, c, d = V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]
            for t in ((a, b, c), (a, c, d)):
                if i == 0 and t == (a, c, d) and False: continue
                zc = sum(p[2] for p in t) / 3.0; cx = sum(p[0] for p in t) / 3.0; cy = sum(p[1] for p in t) / 3.0
                ux, uy, uz = [t[1][k] - t[0][k] for k in range(3)]; vx, vy, vz = [t[2][k] - t[0][k] for k in range(3)]
                nxx, nyy, nzz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx; nl = math.sqrt(nxx * nxx + nyy * nyy + nzz * nzz) or 1.0
                if nl < 1e-6: continue
                steep = abs(nzz) / nl < 0.62
                if steep or zc > 4.0: tex = T_CLIFF
                elif math.hypot(cx, cy) > rim_r(math.atan2(cy, cx)) - 6.5: tex = T_GRASS if gnoise(cx, cy, 0.35) < 0.8 else T_MUD      # the bank, and its foot: grass (some mud)
                elif zc < 0.10 and max(p[2] for p in t) < 0.16: tex = T_WATER
                else: tex = T_GRASS if gnoise(cx, cy, 0.35) > 0.35 else T_MUD
                if tex == T_WATER:
                    uv = [(p[0] * 0.09, p[1] * 0.09) for p in t]
                    add_tri(T_BED, *[(p[0], p[1], p[2], uv[k][0] * 0.7, uv[k][1] * 0.7) for k, p in enumerate(t)])      # solid lake bed
                    uv2 = [(p[0] * 0.14, p[1] * 0.14) for p in t]
                    add_tri(T_WATER, *[(p[0], p[1], p[2] + 0.07, uv2[k][0], uv2[k][1]) for k, p in enumerate(t)], col=False)      # the scrolling ripple sheet, a hand's width above it
                    add_tri(T_WATER, *[(p[0], p[1], p[2] + 0.10, p[1] * 0.19 + 3.0, p[0] * 0.19) for k, p in enumerate(t)], col=False)      # a second sheet turned a quarter, a different size: the game scrolls both along their own v, so the ripples cross (it reads as moving water)
                else: add_plain(tex, *t, s=0.2 if tex != T_CLIFF else 0.14)
    return V

# ---------------------------------------------------------------- props
placed = []      # (x, y, radius) of solid props, to keep trees / stones from overlapping
def free_spot(x, y, rad):
    return all(math.hypot(x - px, y - py) > rad + pr + 0.3 for px, py, pr in placed)

def box(cx, cy, z0, hx, hy, h, yaw, lean=(0.0, 0.0), taper=0.85, tex=T_STONE, col=True, broken=0.0):
    c, s = math.cos(yaw), math.sin(yaw)
    def P(lx, ly, z, k):
        lx *= (1 - (1 - taper) * k); ly *= (1 - (1 - taper) * k)
        return (cx + lx * c - ly * s + lean[0] * k, cy + lx * s + ly * c + lean[1] * k, z0 + z)
    top = h
    B = [P(-hx, -hy, 0, 0), P(hx, -hy, 0, 0), P(hx, hy, 0, 0), P(-hx, hy, 0, 0)]
    T = [P(-hx, -hy, top, 1), P(hx, -hy, top - broken * 0.6, 1), P(hx, hy, top, 1), P(-hx, hy, top - broken, 1)]
    for k in range(4):
        a, b = k, (k + 1) % 4; add_quad(tex, B[a], B[b], T[b], T[a], 0.45, col)
    add_quad(tex, T[0], T[1], T[2], T[3], 0.45, col)

def ground_z(x, y): return height(x, y)

def pillar(x, y, h, w=0.55, yaw=None, broken=0.5):
    yaw = R.uniform(0, math.pi) if yaw is None else yaw
    z = ground_z(x, y) - 0.4
    lean = (R.uniform(-0.25, 0.25), R.uniform(-0.25, 0.25))
    box(x, y, z, w, w * R.uniform(0.8, 1.2), h + 0.4, yaw, lean, 0.8, T_STONE, True, broken)
    placed.append((x, y, w + 0.3))

def fallen(x, y, length, w, yaw):
    z = ground_z(x, y) - 0.1; c, s = math.cos(yaw), math.sin(yaw)
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1): pts.append((x + sx * length / 2 * c - sy * w * s, y + sx * length / 2 * s + sy * w * c))
    zs = [z, z + w * 1.6]
    # an elongated block: sides + top
    A = [(p[0], p[1], zs[0]) for p in pts]; Bt = [(p[0], p[1], zs[1]) for p in pts]
    # pts order: (-1,-1) (-1,1) (1,-1) (1,1)
    q = [0, 1, 3, 2]
    for k in range(4):
        a, b = q[k], q[(k + 1) % 4]; add_quad(T_STONE, A[a], A[b], Bt[b], Bt[a], 0.45)
    add_quad(T_STONE, Bt[0], Bt[1], Bt[3], Bt[2], 0.45)
    placed.append((x, y, length / 2 * 0.6))

def boulder(x, y, rad, buried=0.35, seed=0):
    rr = random.Random(seed); z0 = ground_z(x, y)
    sx, sy, sz = rad * rr.uniform(0.8, 1.2), rad * rr.uniform(0.8, 1.2), rad * rr.uniform(0.55, 0.85)
    # octahedron-subdivided blob (rings x segments)
    NR, NS = 4, 7; yaw = rr.uniform(0, 6.28)
    rows = []
    for i in range(NR + 1):
        phi = math.pi * i / NR; row = []
        for j in range(NS):
            th = 2 * math.pi * j / NS + yaw; k = 1.0 + rr.uniform(-0.16, 0.16)
            if i in (0, NR): k = 1.0
            row.append((x + sx * k * math.sin(phi) * math.cos(th), y + sy * k * math.sin(phi) * math.sin(th), z0 + sz * (1 - buried) + sz * k * math.cos(phi) * 0.9))
        rows.append(row)
    for i in range(NR):
        for j in range(NS):
            a, b, c, d = rows[i][j], rows[i][(j + 1) % NS], rows[i + 1][(j + 1) % NS], rows[i + 1][j]
            if i == 0: add_plain(T_STONE, a, c, d, 0.4)
            elif i == NR - 1: add_plain(T_STONE, a, b, c, 0.4)
            else: add_quad(T_STONE, a, b, c, d, 0.4)
    placed.append((x, y, rad * 0.9))

def prism(p0, p1, r0, r1, tex, col, n=5, rot=0.0):
    """tapered n-sided prism from p0 to p1"""
    dx, dy, dz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]; L = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    ax = (dx / L, dy / L, dz / L); ref = (0, 0, 1) if abs(ax[2]) < 0.9 else (1, 0, 0)
    u = (ax[1] * ref[2] - ax[2] * ref[1], ax[2] * ref[0] - ax[0] * ref[2], ax[0] * ref[1] - ax[1] * ref[0]); ul = math.sqrt(sum(k * k for k in u)) or 1.0; u = tuple(k / ul for k in u)
    v = (ax[1] * u[2] - ax[2] * u[1], ax[2] * u[0] - ax[0] * u[2], ax[0] * u[1] - ax[1] * u[0])
    def ring(p, r): return [tuple(p[k] + r * (math.cos(2 * math.pi * i / n + rot) * u[k] + math.sin(2 * math.pi * i / n + rot) * v[k]) for k in range(3)) for i in range(n)]
    A, B = ring(p0, r0), ring(p1, r1)
    for i in range(n):
        j = (i + 1) % n; add_quad(tex, A[i], A[j], B[j], B[i], 0.5, col)
    if r1 > 0.02:
        for i in range(n): add_plain(tex, B[i], B[(i + 1) % n], p1, 0.5, col)

def dead_tree(x, y, h, seed):
    rr = random.Random(seed); z0 = ground_z(x, y) - 0.3
    lean = (rr.uniform(-0.1, 0.1) * h, rr.uniform(-0.1, 0.1) * h); r0 = rr.uniform(0.34, 0.5)
    top = (x + lean[0], y + lean[1], z0 + h)
    # trunk in two sections (a kink), solid
    mid = (x + lean[0] * 0.4 + rr.uniform(-0.2, 0.2), y + lean[1] * 0.4 + rr.uniform(-0.2, 0.2), z0 + h * 0.5)
    prism((x, y, z0), mid, r0, r0 * 0.62, T_BARK, True, 6)
    prism(mid, top, r0 * 0.62, 0.09, T_BARK, False, 5)
    for k in range(rr.randrange(4, 7)):
        t = rr.uniform(0.38, 0.95); bx = [mid[i] + (top[i] - mid[i]) * (t - 0.5) / 0.5 for i in range(3)] if t > 0.5 else [(x + (mid[0] - x) * t / 0.5), (y + (mid[1] - y) * t / 0.5), z0 + h * t]
        a = rr.uniform(0, 6.28); el = rr.uniform(0.25, 0.9); L = rr.uniform(1.4, 3.2) * (1.2 - t * 0.6)
        e = (bx[0] + math.cos(a) * L * math.cos(el), bx[1] + math.sin(a) * L * math.cos(el), bx[2] + L * math.sin(el))
        prism(tuple(bx), e, 0.11, 0.03, T_BARK, False, 4)
        if rr.random() < 0.6:      # a fork
            f = tuple(bx[i] + (e[i] - bx[i]) * 0.6 for i in range(3)); a2 = a + rr.uniform(-1.0, 1.0)
            prism(f, (f[0] + math.cos(a2) * 1.1, f[1] + math.sin(a2) * 1.1, f[2] + rr.uniform(0.2, 0.9)), 0.06, 0.02, T_BARK, False, 3)
    placed.append((x, y, r0 + 0.1))

def card_tree(x, y, h, seed):
    """a dead tree from the game's own tree picture: two crossed cut-out cards, with a hidden solid trunk"""
    rr = random.Random(seed); z0 = ground_z(x, y) - 0.4; role = rr.choice(sorted(CARDS)); wd = h * CARDS[role] * rr.uniform(0.9, 1.1); a0 = rr.uniform(0, math.pi)
    for k in range(2):
        a = a0 + k * math.pi / 2; dx, dy = math.cos(a) * wd / 2, math.sin(a) * wd / 2
        p = [(x - dx, y - dy, z0), (x + dx, y + dy, z0), (x + dx, y + dy, z0 + h), (x - dx, y - dy, z0 + h)]; uv = [(0, 1), (1, 1), (1, 0), (0, 0)]
        q = [(p[i][0], p[i][1], p[i][2], uv[i][0], uv[i][1]) for i in range(4)]
        add_tri(role, q[0], q[1], q[2], False); add_tri(role, q[0], q[2], q[3], False)
    prism((x, y, z0), (x, y, z0 + 3.2), 0.38, 0.3, -1, True, 6)      # the trunk you bump into (not drawn: the card has one)
    placed.append((x, y, 0.5))

def reed_clump(x, y, seed):
    rr = random.Random(seed); z = ground_z(x, y); s = rr.uniform(0.9, 1.5)
    for k in range(2):
        a = rr.uniform(0, math.pi) + k * math.pi / 2; dx, dy = math.cos(a) * 0.7 * s, math.sin(a) * 0.7 * s
        p = [(x - dx, y - dy, z - 0.05), (x + dx, y + dy, z - 0.05), (x + dx, y + dy, z + 1.5 * s), (x - dx, y - dy, z + 1.5 * s)]
        uv = [(0, 1), (1, 1), (1, 0), (0, 0)]
        q = [(p[i][0], p[i][1], p[i][2], uv[i][0], uv[i][1]) for i in range(4)]
        add_tri(T_REED, q[0], q[1], q[2], False); add_tri(T_REED, q[0], q[2], q[3], False)

# ---------------------------------------------------------------- build
V = terrain()
# spawn + lantern on the west bank, in front of the arch, facing the lake
sa = math.pi; sr = rim_r(sa) + 1.5
LANT = (sr * math.cos(sa) + 1.0, sr * math.sin(sa) + 2.4, 0.0); LANT = (LANT[0], LANT[1], ground_z(LANT[0], LANT[1]))
SPAWN = (sr * math.cos(sa) + 1.2, sr * math.sin(sa) - 1.2, ground_z(sr * math.cos(sa) + 1.2, sr * math.sin(sa) - 1.2) + 1.0)

# standing stones: a broken ring round the middle
for k in range(11):
    if k in (3, 8): continue
    a = k / 11 * 2 * math.pi + 0.2; r = 15.5 + R.uniform(-1.0, 1.0)
    pillar(r * math.cos(a), r * math.sin(a), R.choice((1.4, 2.2, 3.0, 3.8, 4.4)), R.uniform(0.5, 0.75))
for k in range(5):      # an inner ruined arc
    a = 0.9 + k * 0.5; r = 8.0
    pillar(r * math.cos(a), r * math.sin(a), R.choice((0.9, 1.5, 2.1)), 0.45)
for (x, y, L, yaw) in [(-4.0, 13.0, 3.4, 0.4), (12.5, -12.0, 2.8, 1.9), (-17.0, -6.0, 3.0, 2.7), (5.0, 17.5, 2.6, 0.9), (-3.5, -14.5, 3.2, 1.4)]:
    fallen(x, y, L, 0.5, yaw)
# the ruined arch where you arrive (west bank), two tall pillars and a lintel resting on one
ax, ay = -36.0, 0.0
arch_th = math.atan2(ay, ax); rr_ = rim_r(arch_th)
ar = sr - 4.5; ax, ay = ar * math.cos(arch_th), ar * math.sin(arch_th)      # a few steps in front of where you arrive, so you walk down through it
tx, ty = -math.sin(arch_th), math.cos(arch_th)      # along the bank
for s in (-1, 1):
    pillar(ax + tx * 2.6 * s, ay + ty * 2.6 * s, 5.2 if s < 0 else 3.4, 0.7, arch_th, 0.9 if s > 0 else 0.2)
zl = ground_z(ax - tx * 2.6, ay - ty * 2.6) + 5.0
box(ax - tx * 1.6, ay - ty * 1.6, zl, 0.45, 2.1, 0.6, arch_th + math.pi / 2 + 0.05, (0, 0), 1.0, T_STONE, True, 0.0)      # lintel, solid
# low wall stubs along the bank
for k in range(7):
    a = R.uniform(0, 2 * math.pi)
    if abs(math.atan2(math.sin(a - math.pi), math.cos(a - math.pi))) < 0.45: continue
    r = rim_r(a) + R.uniform(-1.0, 0.5); x, y = r * math.cos(a), r * math.sin(a)
    if free_spot(x, y, 1.6): box(x, y, ground_z(x, y) - 0.2, 1.6, 0.35, R.uniform(0.9, 1.6), a + math.pi / 2 + R.uniform(-0.4, 0.4), (0, 0), 0.9, T_STONE, True, 0.5); placed.append((x, y, 1.6))
# boulders
for k in range(16):
    a = R.uniform(0, 2 * math.pi); r = R.choice((R.uniform(18, 30), rim_r(a) + R.uniform(-3, 1.5), R.uniform(4, 28)))
    x, y = r * math.cos(a), r * math.sin(a)
    if math.hypot(x - SPAWN[0], y - SPAWN[1]) < 7 or math.hypot(x, y) < 3.5: continue
    rad = R.uniform(0.9, 2.2)
    if free_spot(x, y, rad): boulder(x, y, rad, 0.35, k * 17 + 3)
# dead trees: mostly on the banks, a few standing in the lake
n_t = 0; tries = 0
while n_t < (60 if CARDS else 44) and tries < 1200:
    tries += 1; a = R.uniform(0, 2 * math.pi)
    r = (rim_r(a) + R.uniform(-4.0, 1.5)) if R.random() < 0.7 else R.uniform(6, 30)
    x, y = r * math.cos(a), r * math.sin(a)
    if math.hypot(x - SPAWN[0], y - SPAWN[1]) < 6.0 or math.hypot(x, y) < 5.0 or not free_spot(x, y, 0.6): continue
    (card_tree(x, y, R.uniform(6.5, 10.5), 1000 + n_t) if CARDS else dead_tree(x, y, R.uniform(4.5, 8.5), 1000 + n_t)); n_t += 1
# gravestones leaning on the banks and islands, a graveyard feel
for k in range(0):      # (the leaning gravestones are removed; raise this number to bring them back)
    a = R.uniform(0, 2 * math.pi)
    if abs(math.atan2(math.sin(a - math.pi), math.cos(a - math.pi))) < 0.5: continue
    if R.random() < 0.7: r = rim_r(a) + R.uniform(-2.5, 1.5); x, y = r * math.cos(a), r * math.sin(a)
    else: cx_, cy_, rad_, hh_ = R.choice(ISLANDS); x, y = cx_ + R.uniform(-1, 1) * rad_ * 0.6, cy_ + R.uniform(-1, 1) * rad_ * 0.6
    if not free_spot(x, y, 0.6): continue
    h = R.uniform(0.8, 1.7); lean = (R.uniform(-0.25, 0.25), R.uniform(-0.25, 0.25))
    box(x, y, ground_z(x, y) - 0.25, 0.42, 0.11, h, math.atan2(y, x) + R.uniform(-0.5, 0.5), lean, 0.9, T_GRAVE, True, R.choice((0.0, 0.0, 0.3)))
    placed.append((x, y, 0.5))
# reeds: round the islands and the shoreline
for k in range(110):
    if R.random() < 0.55: cx, cy, rad, hh = R.choice(ISLANDS); a = R.uniform(0, 6.28); d = rad * R.uniform(0.8, 1.1); x, y = cx + d * math.cos(a), cy + d * math.sin(a)
    else: a = R.uniform(0, 6.28); r = rim_r(a) - R.uniform(0, 3.0); x, y = r * math.cos(a), r * math.sin(a)
    reed_clump(x, y, k)

# ---------------------------------------------------------------- write
def write():
    os.makedirs(args.outdir, exist_ok=True)
    col = [t for t in tris if t[4]]
    # geometry blocks: one per (texture, 24 m cell) so the game can cull
    groups = {}
    for t in tris:
        if t[0] < 0: continue      # collision-only pieces are not drawn
        cx = sum(p[0] for p in t[1:4]) / 3; cy = sum(p[1] for p in t[1:4]) / 3
        groups.setdefault((t[0], int(math.floor(cx / 24.0)), int(math.floor(cy / 24.0))), []).append(t)
    geoms = []; draws = []
    for key in sorted(groups):
        pos = []; ind = []; cache = {}
        for t in groups[key]:
            for p in t[1:4]:
                if p not in cache:
                    if len(pos) >= 65530: break
                    cache[p] = len(pos); pos.append(p)
                ind.append(cache[p])
        geoms.append((pos, ind)); draws.append((key[0]))
    with open(os.path.join(args.outdir, "level_romarena.bin"), "wb") as f:
        f.write(b"BBL2"); f.write(struct.pack("<IIIII", len(TEX), len(geoms), len(geoms), len(geoms), len(col)))
        f.write(struct.pack("<3f", *SPAWN))
        for t in col:
            f.write(struct.pack("<9f", *[t[i][k] for i in (1, 2, 3) for k in range(3)]))
        for name, im in TEX:
            nb = name.encode(); f.write(struct.pack("<B", len(nb)) + nb + struct.pack("<HH", im.width, im.height) + im.tobytes())
        for pos, ind in geoms:
            f.write(struct.pack("<II", len(pos), len(ind)))
            for p in pos: f.write(struct.pack("<5f", *p))
            f.write(struct.pack("<%dH" % len(ind), *ind))
        for gi, tx in enumerate(draws):
            f.write(struct.pack("<H", 1)); f.write(struct.pack("<IH", gi, tx))
        for gi in range(len(geoms)):
            f.write(struct.pack("<I12f", gi, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0))
    flo = [t for t in tris if t[0] == T_BED]
    with open(os.path.join(args.outdir, "floor_romarena.bin"), "wb") as f:
        f.write(b"FLR1"); f.write(struct.pack("<I", len(flo)))
        for t in flo: f.write(struct.pack("<I9f", 2, *[t[i][k] for i in (1, 2, 3) for k in range(3)]))
    with open(os.path.join(args.outdir, "interact_romarena.bin"), "wb") as f:
        f.write(b"BBI1"); f.write(struct.pack("<I", 0)); f.write(struct.pack("<I", 0))      # doors, ladders
        for tag in (b"ITM1", b"SPN1", b"LDR1", b"BLD1", b"ELV1", b"DST1", b"ITM2", b"FIR1", b"WCH1", b"LSL1", b"PTC1"): f.write(tag); f.write(struct.pack("<I", 0))
        f.write(b"LMP1"); f.write(struct.pack("<I", 1)); f.write(struct.pack("<3f", *LANT)); f.write(struct.pack("<I", 0))
    print(f"level_romarena.bin: {len(tris)} triangles ({len(col)} solid), {len(geoms)} blocks, {len(TEX)} textures; spawn {SPAWN[0]:.1f} {SPAWN[1]:.1f} {SPAWN[2]:.1f}; lantern {LANT[0]:.1f} {LANT[1]:.1f} {LANT[2]:.1f}; {len(placed)} solid props")
write()

if args.preview:      # quick top-down look: terrain height shaded + props
    from PIL import ImageDraw
    N = 700; sc = N / 130.0; im = Image.new("RGB", (N, N), (20, 24, 30)); dr = ImageDraw.Draw(im)
    avg = {i: tuple(int(np.asarray(t[1]).reshape(-1, 4)[:, k].mean()) for k in range(3)) for i, t in enumerate(TEX)}
    for t in sorted([t for t in tris if t[0] >= 0], key=lambda t: sum(p[2] for p in t[1:4])):
        pts = [(N / 2 + p[0] * sc, N / 2 - p[1] * sc) for p in t[1:4]]; z = sum(p[2] for p in t[1:4]) / 3
        c = avg[t[0]]; k = min(1.25, 0.7 + z / 16.0)
        dr.polygon(pts, fill=tuple(min(255, int(v * k)) for v in c))
    im.save(args.preview)
