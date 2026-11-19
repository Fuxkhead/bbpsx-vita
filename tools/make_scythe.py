#!/usr/bin/env python3
"""make_scythe.py: builds Gehrman's Burial Blade as files the existing converter already understands (a skinned .psk with a 'transformer' bone, .psa transform animations and a texture),
laid out exactly like the Blood Spear's, so make_gehr.sh can use it with SCYTHE=1.

  python3 assets/tools/make_scythe.py --out assets/BP/PlayerWeapons/BurialBlade [--open 100] [--length 120] [--curve 42] [--haft 160]

The weapon is built in the weapon file's own space (cm): the long axis runs along -Z (butt at +Z, grip at the origin), the blade bows toward -X (--bend), the flat of the blade faces +-Y.
  closed = the curved sword (the blade carries straight on from the haft); open = the scythe (the blade is turned sideways at the top of the haft by --open degrees about Y).
Tune: --open (turn of the blade), --length / --curve (blade), --haft (haft length). If it sits wrong in his hand: WARGS="--weaponrotx 0" / "--weaponroty 90" / "--weaponoff x,y,z" in make_gehr.sh."""
import argparse, math, os, struct
import numpy as np
from PIL import Image, ImageDraw

def chunk(cid, size, items):
    body = b''.join(items) if items else b''
    return cid.encode().ljust(20, b'\0') + struct.pack('<iii', 1999801, size, len(items)) + body

def qconj(q): return (-q[0], -q[1], -q[2], q[3])
def qaxis(ax, ang):
    ax = np.array(ax, float); ax /= np.linalg.norm(ax); s = math.sin(ang / 2); return (ax[0] * s, ax[1] * s, ax[2] * s, math.cos(ang / 2))

def build(a):
    pts, uvs, faces, bone = [], [], [], []      # pts: list of xyz; each wedge has its own uv (one wedge per point here)
    def P(x, y, z, u, v, b):
        pts.append((x, y, z)); uvs.append((u, v)); bone.append(b); return len(pts) - 1
    def tri(i, j, k, both=True):
        faces.append((i, j, k)); 
        if both: faces.append((i, k, j))
    def quad(i, j, k, l, both=True): tri(i, j, k, both); tri(i, k, l, both)
    def tube(z0, z1, r0, r1, sides, b, u0, u1, v0=0.0, v1=1.0, cap=True):
        ring0, ring1 = [], []
        for s in range(sides + 1):
            t = s / sides * 2 * math.pi; c, sn = math.cos(t), math.sin(t)
            ring0.append(P(r0 * c, r0 * sn, z0, u0 + (u1 - u0) * s / sides, v0, b)); ring1.append(P(r1 * c, r1 * sn, z1, u0 + (u1 - u0) * s / sides, v1, b))
        for s in range(sides): quad(ring0[s], ring0[s + 1], ring1[s + 1], ring1[s], both=False)
        if cap:
            for z, r, ring in ((z0, r0, ring0), (z1, r1, ring1)):
                cc = P(0, 0, z, (u0 + u1) / 2, (v0 + v1) / 2, b)
                for s in range(sides): tri(cc, ring[s], ring[s + 1], both=False) if z == z1 else tri(cc, ring[s + 1], ring[s], both=False)
    H = a.haft; top = -H + 25.0          # hinge height: the top of the haft (z, negative = forward)
    # ---- haft (root bone 0): wood, left half of the texture
    tube(+25.0, top, 1.9, 1.7, 8, 0, 0.02, 0.45, 0.0, 1.0)
    for z in (+18.0, +8.0, -2.0, -12.0):              # leather wraps on the grip
        tube(z, z - 5.0, 2.35, 2.35, 8, 0, 0.02, 0.45, 0.80, 0.95)
    tube(+25.0, +29.0, 2.6, 2.0, 8, 0, 0.02, 0.45, 0.9, 1.0)        # pommel
    tube(top + 0.0, top - 9.0, 3.4, 3.4, 6, 0, 0.02, 0.45, 0.70, 0.78)    # the collar where the blade hinges
    # ---- blade (transformer bone 1): steel, right half of the texture
    hz = top - 9.0 + a.slide                           # the blade's hinge point while closed: the collar's end, slid down the haft by --slide
    sg = -1.0 if a.bend < 0 else 1.0
    L = a.length; n = 16; turn = math.radians(a.curve); W0 = 11.0
    cx, cz = 3.0, hz                                   # (the blade starts 3 cm beside the haft so it lies alongside it)
    st = []
    for i in range(n + 1):
        s = i / n; phi = turn * s * s                  # the curve gets tighter toward the tip
        if i > 0:
            ph_m = turn * ((i - 0.5) / n) ** 2; cx += sg * math.sin(ph_m) * L / n; cz -= math.cos(ph_m) * L / n
        w = W0 * (1.0 - s) ** 0.75 + 0.6
        sp = np.array([cx, 0.0, cz]); nrm = np.array([sg * math.cos(phi), 0.0, math.sin(phi)])
        st.append((sp, nrm, w, s))
    rows = []
    for sp, nrm, w, s in st:
        ed = sp + nrm * w
        u_sp, u_ed = 0.55, 0.98; v = s
        t_ = P(*(sp + np.array([0, 0.7 * (1 - 0.6 * s), 0])), u_sp, v, 1); b_ = P(*(sp - np.array([0, 0.7 * (1 - 0.6 * s), 0])), u_sp, v, 1); e_ = P(*ed, u_ed, v, 1)
        rows.append((t_, b_, e_))
    for i in range(n):
        (t0, b0, e0), (t1, b1, e1) = rows[i], rows[i + 1]
        quad(t0, e0, e1, t1, both=True); quad(b0, b1, e1, e0, both=True); quad(t0, t1, b1, b0, both=True)
    # a short square stub that joins the collar to the blade, and a pair of lugs
    tube(hz + 3.0, hz - 9.0, 3.5, 3.5, 6, 1, 0.55, 0.98, 0.0, 0.1)      # the band that rides on the haft
    tip = st[-1][0] + np.array([0, 0, 0.0])
    return pts, uvs, faces, bone, hz, tip

def write_psk(path, a):
    pts, uvs, faces, bone, hz, tip = build(a)
    out = bytearray()
    out += chunk('ACTRHEAD', 0, [])
    out += chunk('PNTS0000', 12, [struct.pack('<3f', *p) for p in pts])
    out += chunk('VTXW0000', 16, [struct.pack('<IffBBH', i, u, v, 0, 0, 0) for i, (u, v) in enumerate(uvs)])
    out += chunk('FACE0000', 12, [struct.pack('<3HBBI', f[0], f[1], f[2], 0, 0, 1) for f in faces])
    out += chunk('MATT0000', 88, [b'MI_BurialBlade'.ljust(64, b'\0') + struct.pack('<6i', 0, 0, 0, 0, 0, 0)])
    def bonerec(name, parent, nch, q, p):
        return name.encode().ljust(64, b'\0') + struct.pack('<Iii', 0, nch, parent) + struct.pack('<7f', *q, *p) + struct.pack('<4f', 1, 1, 1, 1)
    bones = [('root', -1, 1, (0, 0, 0, 1), (0, 0, 0)), ('transformer', 0, 1, (0, 0, 0, 1), (0, 0, hz)), ('transformer_end', 1, 0, (0, 0, 0, 1), tuple(np.array(tip) - np.array([0, 0, hz])))]
    out += chunk('REFSKELT', 120, [bonerec(*b) for b in bones])
    out += chunk('RAWWEIGHTS', 12, [struct.pack('<fii', 1.0, i, b) for i, b in enumerate(bone)])
    open(path, 'wb').write(out)
    return bones, hz

def write_psa(path, bones, names_anim, slide=0.0):
    """names_anim: list of (name, fps, [(angle about Y in radians, how far up the haft it has slid 0..1) per frame])"""
    out = bytearray(); out += chunk('ANIMHEAD', 0, [])
    out += chunk('BONENAMES', 120, [b[0].encode().ljust(64, b'\0') + struct.pack('<Iii', 0, b[2], b[1]) + struct.pack('<7f', *b[3], *b[4]) + struct.pack('<4f', 1, 1, 1, 1) for b in bones])
    # build ANIMINFO records with the exact layout the loader reads: name[64] group[64] totalbones rootinclude keystyle keyquotum keyreduction tracktime animrate startbone firstrawframe numrawframes
    infos = []; first = 0
    for name, fps, angs in names_anim:
        infos.append(name.encode().ljust(64, b'\0') + b'None'.ljust(64, b'\0') + struct.pack('<4i', len(bones), 0, 0, len(angs) * len(bones)) + struct.pack('<3f', 0.0, len(angs) / fps, fps) + struct.pack('<3i', 0, first, len(angs)))
        first += len(angs)
    out += chunk('ANIMINFO', 168, infos)
    kb = []
    for name, fps, angs in names_anim:
        for ang in angs:
            for bi, b in enumerate(bones):
                q = (0, 0, 0, 1); p = b[4]
                if b[0] == 'transformer': ang, sl = ang; q = qconj(qaxis((0, 1, 0), ang)); p = (p[0], p[1], p[2] - slide * sl)
                kb.append(struct.pack('<3f4ff', *p, *q, 1.0))
    out += chunk('ANIMKEYS', 32, kb)
    open(path, 'wb').write(out)

def texture(path):
    """one 128x128 atlas: left 58 px = the haft (dark oiled wood with leather wraps), right = the blade (dark Yharnam steel: bluish, a pale ground edge, a fuller down the spine, a stained tip)"""
    W = H = 128; im = Image.new('RGBA', (W, H)); px = im.load(); rng = np.random.default_rng(7)
    for y in range(H):
        for x in range(W):
            if x < 58:
                g = 0.5 + 0.5 * math.sin(x * 0.9 + math.sin(y * 0.15) * 2.0); base = np.array([74, 50, 34]) * (0.75 + 0.35 * g)
                if 0.8 * H < y < 0.95 * H: base = np.array([38, 28, 22]) * (0.8 + 0.3 * g)      # leather wraps
                if 0.70 * H < y < 0.78 * H: base = np.array([150, 120, 70]) * (0.85 + 0.2 * g)    # brass collar
                px[x, y] = tuple(int(c) for c in base) + (255,)
            else:
                u = (x - 58) / (W - 58)
                base = np.array([92, 100, 112]) * (0.60 + 0.40 * u)          # dark, slightly blue steel, brighter toward the edge
                if u > 0.88: base = np.array([205, 212, 222]) * (0.9 + 0.1 * (u - 0.88) / 0.12)      # the ground, polished edge
                if 0.10 < u < 0.22: base *= 0.55                               # the fuller
                if y > 0.80 * H: base = base * (1.0 - 0.5 * (y / H - 0.80) / 0.20) + np.array([60, 6, 6]) * 0.25      # blood on the tip
                base += rng.integers(-6, 7)
                px[x, y] = tuple(int(max(0, min(255, c))) for c in base) + (255,)
    # the game's own textures as the grain, when they are on disk (run from ~/bbpsx-vita): T_Wood under the haft, the grimy t_paintedmetal under the blade
    try:
        def grain(rel, w, h):
            g = Image.open(rel).convert('L').resize((w, h), Image.LANCZOS); a_ = np.asarray(g, dtype=np.float32); return (a_ - a_.mean()) / (a_.std() + 1e-3)
        A = np.asarray(im.convert('RGB'), dtype=np.float32)
        gw = grain('assets/General/Mat/Tex/T_Wood.png', 58, H); A[:, :58] *= (1.0 + 0.30 * gw[:, :, None])
        gm = grain('assets/NMKART/Content/Char/NPCs/Lilith/Renders/SunsOut/t_paintedmetal.png', W - 58, H); A[:, 58:] *= (1.0 + 0.22 * gm[:, :, None])
        A[:, 58:, 0] += 18 * np.clip(-gm, 0, 2)                                           # rust and old blood in the pits of the grime
        im = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)).convert('RGBA'); print('texture: grain from T_Wood + t_paintedmetal')
    except Exception as e_:
        print('texture: procedural only (', e_, ')')
    im.save(path)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='BurialBlade'); ap.add_argument('--open', type=float, default=100.0, help='degrees the blade turns when it opens (sign flips the side)')
    ap.add_argument('--length', type=float, default=110.0); ap.add_argument('--curve', type=float, default=42.0); ap.add_argument('--haft', type=float, default=150.0); ap.add_argument('--slide', type=float, default=55.0, help='cm the blade rides down the haft while it is a sword (0 = it stays at the top)'); ap.add_argument('--bend', type=float, default=-1.0, help='-1: the blade bows toward -X (open: toward the wielder, like a real scythe); +1 the other way')
    a = ap.parse_args()
    for d in ('Mesh', 'Anim', 'Mat'): os.makedirs(os.path.join(a.out, d), exist_ok=True)
    bones, hz = write_psk(os.path.join(a.out, 'Mesh', 'SkM_BurialBlade.psk'), a)
    n = 24; op = math.radians(a.open)
    sm = lambda t: t * t * (3 - 2 * t)
    # it first rides up the haft (0..55 % of the time), then turns into the scythe (35..100 %)
    fr = []
    for i in range(n):
        t = i / (n - 1); fr.append((op * sm(min(1.0, max(0.0, (t - 0.35) / 0.65))), sm(min(1.0, t / 0.55))))
    write_psa(os.path.join(a.out, 'Anim', 'BurialBlade_open.psa'), bones, [('BurialBlade_open', 30.0, fr)], a.slide)
    write_psa(os.path.join(a.out, 'Anim', 'BurialBlade_closedidle.psa'), bones, [('BurialBlade_closedidle', 30.0, [(0.0, 0.0), (0.0, 0.0)])], a.slide)
    texture(os.path.join(a.out, 'Mat', 't_burialblade.png'))
    print('wrote', a.out, ' hinge at z', hz)

if __name__ == '__main__': main()
