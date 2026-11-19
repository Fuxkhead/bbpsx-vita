#!/usr/bin/env python3
"""make_rom.py. Builds Rom, the Vacuous Spider, out of the Child of Rom rip (c1400.obj + its two textures):
the child's body and face scaled up, its big arching legs removed, its small low legs kept and spread along both sides (5 a side),
and a great pale lichen-like mound grown over her back, as in the PS4 game. Personal use only: the result stays on your card.
  python3 make_rom.py --dir "Child of Rom" --out rom.bin [--preview rom_preview.png]
  python3 make_rom.py --dir "Child of Rom" --child 1 --out romchild.bin      (her spiders: the rip as it is, small, with the big legs kept)
Both files go to ux0:data/bbpsx/. The game loads them only in Rom's lake.
"""
import argparse, math, os, struct
import numpy as np
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser(); ap.add_argument('--dir', default=None); ap.add_argument('--placeholder', type=int, default=0, help='1 = build a stand-in out of simple generated shapes (no rip needed: nothing of the game is used)'); ap.add_argument('--preview', default=None); ap.add_argument('--size', type=float, default=3.4, help='how many times bigger than the child')
ap.add_argument('--tint', type=float, default=0.12, help='how much of the child\'s colour is drained from her skin (0 = the rip as it is: the cream face with its eyes)'); ap.add_argument('--facecell', type=float, default=0.008, help='finer vertex grid for the face so its eyes and mouth keep their shape'); ap.add_argument('--tilt', type=float, default=50.0, help='how far her head tilts down, degrees'); ap.add_argument('--tuck', type=float, default=0.0, help='how far the head is pushed back into her body (rip units)'); ap.add_argument('--mound', type=float, default=1.3, help='how much longer her white back is than before (1 = as it was); it grows toward the tail'); ap.add_argument('--moundfront', type=float, default=0.9, help='where the front of her white back ends, as a fraction of her length from the tail (0.78 = as it was; higher = further up into her head)'); ap.add_argument('--curlgap', type=float, default=0.30, help='how far apart the two loops of each curled leg stand, rip units'); ap.add_argument('--curlr', type=float, default=0.055, help='radius of the four curled front legs of the Children, rip units'); ap.add_argument('--curlwide', type=float, default=2.0, help='how much wider the four curled front legs of the Children are made'); ap.add_argument('--curlround', type=float, default=1.0, help='their thickness as a fraction of their (new) width: 1 = a square-ish limb, small = a flat panel'); ap.add_argument('--legthick', type=float, default=0.16, help='thickness of every leg, rip units (the rip\'s legs are flat blades: 0 = as they were)'); ap.add_argument('--torsofloor', type=float, default=0.12); ap.add_argument('--moundw', type=float, default=1.0); ap.add_argument('--torsox', type=float, default=1.0); ap.add_argument('--torsoy', type=float, default=1.7); ap.add_argument('--torso', type=float, default=1.6); ap.add_argument('--torsolen', type=float, default=0.9); ap.add_argument('--torsofwd', type=float, default=0.22); ap.add_argument('--alllegs', type=int, default=1); ap.add_argument('--backr', type=float, default=0.05); ap.add_argument('--tnb', type=int, default=28); ap.add_argument('--tns', type=int, default=10); ap.add_argument('--cbody', type=float, default=2.7); ap.add_argument('--cleg', type=float, default=2.0); ap.add_argument('--bridge', type=float, default=0.0); ap.add_argument('--brx', type=float, default=0.0); ap.add_argument('--bry', type=float, default=0.27); ap.add_argument('--brz', type=float, default=0.62); ap.add_argument('--brw', type=float, default=0.44); ap.add_argument('--brh', type=float, default=0.25); ap.add_argument('--brl', type=float, default=0.17); ap.add_argument('--bowl', type=float, default=0.0); ap.add_argument('--bowlz', type=float, default=0.95); ap.add_argument('--bowlc', type=float, default=0.82); ap.add_argument('--bowlr', type=float, default=0.2); ap.add_argument('--bowldy', type=float, default=0.0); ap.add_argument('--lobe', type=float, default=0.0); ap.add_argument('--capz', type=float, default=0.80); ap.add_argument('--capbulge', type=float, default=1.0); ap.add_argument('--flowers', type=int, default=230); ap.add_argument('--girth', type=float, default=1.2, help='how much wider than the child her body is'); ap.add_argument('--leg', type=float, default=1.2, help='leg length against the child'); ap.add_argument('--face', type=float, default=1.75, help='how much the head end is enlarged'); ap.add_argument('--cell', type=float, default=0.042); ap.add_argument('--out', default='rom.bin'); ap.add_argument('--child', type=int, default=0, help='1 = build the Child of Rom (her spiders) instead: romchild.bin'); ap.add_argument('--tex', type=int, default=256); a = ap.parse_args()
PH = bool(a.placeholder) or not a.dir or not os.path.exists(os.path.join(a.dir, 'c1400.obj'))
if PH: print('placeholder mode: Rom is built from simple generated shapes (no Child of Rom rip used)')
rng = np.random.default_rng(7)
# ---- read the rip (skipped in placeholder mode)
if PH:
    V = VT = np.zeros((0, 3)); F = FT = np.zeros((0, 3), int); FM = np.zeros(0, int); froot = np.zeros(0, int); left = []
    def _skin(sz, base, seed, fine=14.0):
        r = np.random.default_rng(seed); n = r.normal(0, 1, (sz[1], sz[0])); n = (n + np.roll(n, 1, 0) + np.roll(n, 1, 1)) / 3.0; im = np.zeros((sz[1], sz[0], 3)); im[:] = base; im += n[..., None] * fine; return im
    t1 = _skin((128, 64), (146, 158, 172), 3); t1[:, 64:] = _skin((64, 64), (226, 206, 172), 4, 6.0)      # left half the skin, right half the face
    yy_, xx_ = np.mgrid[0:64, 0:64]
    for ex_ in (20, 44): t1[:, 64:][((xx_ - ex_) ** 2 / 30.0 + (yy_ - 26) ** 2 / 16.0) < 1.0] = (24, 18, 22)      # eyes
    t1[:, 64:][(np.abs(yy_ - 46 - 3.0 * np.sin((xx_ - 32) / 10.0)) < 1.5) & (np.abs(xx_ - 32) < 14)] = (80, 40, 44)      # mouth
    TEX = {1: Image.fromarray(t1.clip(0, 255).astype('uint8'), 'RGB'), 2: Image.fromarray(_skin((32, 32), (96, 108, 124), 5).clip(0, 255).astype('uint8'), 'RGB')}
else:
    V = []; VT = []; F = []; FT = []; FM = []; cur = 0
    for l in open(os.path.join(a.dir, 'c1400.obj')):
        if l.startswith('v '): V.append([float(x) for x in l.split()[1:4]])
        elif l.startswith('vt '): VT.append([float(x) for x in l.split()[1:3]])
        elif l.startswith('o '): cur += 1
        elif l.startswith('f '):
            t = [x.split('/') for x in l.split()[1:]]
            for k in range(1, len(t) - 1): F.append([int(t[0][0]) - 1, int(t[k][0]) - 1, int(t[k + 1][0]) - 1]); FT.append([int(t[0][1]) - 1, int(t[k][1]) - 1, int(t[k + 1][1]) - 1]); FM.append(cur)
    V = np.array(V); VT = np.array(VT); F = np.array(F); FT = np.array(FT); FM = np.array(FM)
    def cool(im, k=0.75):      # her skin is a cold blue-grey, not the child's brown: mostly drained of colour, then tinted
        p = np.array(im.convert('RGB')).astype(float); g = p.mean(2, keepdims=True); p = g + (p - g) * (1 - k); p *= 1.0 + (np.array([0.78, 0.92, 1.08]) - 1.0) * (k / 0.75); return Image.fromarray(p.clip(0, 255).astype('uint8'), 'RGB')
    def warm(im):      # her face is cream, not white: the pale parts of the rip are warmed (the game's Rom has a tan face)
        p = np.array(im.convert('RGB')).astype(float) * np.array([1.0, 0.90, 0.74]); return Image.fromarray(p.clip(0, 255).astype('uint8'), 'RGB')
    TEX = {1: (lambda im_: im_ if a.child else warm(im_))(cool(Image.open(os.path.join(a.dir, 'c1400_c5100_body_a.png')), a.tint if not a.child else 0.25)), 2: cool(Image.open(os.path.join(a.dir, 'c1400_c5100_leg_a.png')), 0.6 if not a.child else 0.2)}
    # ---- the legs: split mesh 2 into its separate legs; keep only the small low ones (the big arching legs and the tall arms go)
    key = {}; w = np.array([key.setdefault(tuple(np.round(p, 4)), len(key)) for p in V]); par = list(range(len(key)))
    def fnd(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for t in F[FM == 2]: par[fnd(w[t[0]])] = fnd(w[t[1]]); par[fnd(w[t[1]])] = fnd(w[t[2]])
    froot = np.array([fnd(w[t[0]]) if m == 2 else -1 for t, m in zip(F, FM)])
    legs = []
    for r in sorted(set(froot[froot >= 0])):
        fs = np.where(froot == r)[0]; P = V[np.unique(F[fs])]
        if P[:, 1].max() < 0.5 and np.ptp(P[:, 0]) > 0.4: legs.append(fs)
    left = [fs for fs in legs if V[np.unique(F[fs])][:, 0].mean() < 0]
    left.sort(key=lambda fs: V[np.unique(F[fs])][:, 2].mean())
    print('small legs kept as patterns (left side):', len(left), 'of', len(legs))
# ---- pieces: (name, verts xyz, uv per corner, tris, texture id)
def soup(fs):      # triangle soup with per-corner uv -> unique (v, vt) pairs
    m = {}; P = []; U = []; T = []
    for f, ft in zip(F[fs], FT[fs]):
        tri = []
        for vi, ti in zip(f, ft):
            k = (int(vi), int(ti))
            if k not in m: m[k] = len(P); P.append(V[vi]); U.append(VT[ti])
            tri.append(m[k])
        T.append(tri)
    return np.array(P), np.array(U), np.array(T)
def shrink(P, U, T, cell):      # vertex clustering: every point snaps to a grid cell; a cell keeps one point (the mean) and the uv of its first corner
    q = np.floor(P / cell).astype(int); m = {}; idx = np.zeros(len(P), int); acc = []; cnt = []; uv = []
    for i, k in enumerate(map(tuple, q)):
        if k not in m: m[k] = len(acc); acc.append(P[i].copy()); cnt.append(1); uv.append(U[i])
        else: j = m[k]; acc[j] += P[i]; cnt[j] += 1
        idx[i] = m[k]
    P2 = np.array(acc) / np.array(cnt)[:, None]; T2 = idx[T]; ok = (T2[:, 0] != T2[:, 1]) & (T2[:, 1] != T2[:, 2]) & (T2[:, 0] != T2[:, 2])
    return P2, np.array(uv), T2[ok]
def fatten(P, k, r):      # a ribbon gets wider: every point moves away from the middle line of the ribbon (the average of the points near it)
    D_ = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2); W_ = (D_ < r).astype(float); C_ = (W_ @ P) / W_.sum(1, keepdims=True)
    return C_ + (P - C_) * k
def tube(P, U, T, R, nb=28, ns=10):      # a ribbon becomes a round limb: its middle line is found along the ribbon (distance along the mesh from one end to the other), and a tube of radius R is grown round it
    D_ = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2); W_ = (D_ < 0.16).astype(float); C0 = (W_ @ P) / W_.sum(1, keepdims=True)
    C0 = np.unique(np.round(C0 / 0.01).astype(int), axis=0) * 0.01; n = len(C0)      # the middle line of the ribbon, as a cloud of points
    Dm = np.linalg.norm(C0[:, None, :] - C0[None, :, :], axis=2); inT = np.zeros(n, bool); inT[0] = True; par = np.full(n, -1); best = Dm[0].copy(); bp = np.zeros(n, int); tadj = [[] for _ in range(n)]
    for _ in range(n - 1):      # a minimum spanning tree of the cloud, then its longest path = the limb's middle line from end to end
        j = int(np.argmin(np.where(inT, 1e9, best))); inT[j] = True; tadj[j].append(int(bp[j])); tadj[int(bp[j])].append(j)
        upd = (Dm[j] < best) & ~inT; best[upd] = Dm[j][upd]; bp[upd] = j
    def far(s0):
        d = np.full(n, -1.0); d[s0] = 0.0; pr = np.full(n, -1); q = [s0]
        for u in q:
            for v in tadj[u]:
                if d[v] < 0: d[v] = d[u] + Dm[u, v]; pr[v] = u; q.append(v)
        return int(np.argmax(d)), pr
    A, _ = far(0); B, pr = far(A); path = [B]
    while path[-1] != A: path.append(int(pr[path[-1]]))
    Cp = C0[path]; far_end = 0 if np.linalg.norm(Cp[0][[0, 2]]) > np.linalg.norm(Cp[-1][[0, 2]]) else -1
    if far_end == 0: Cp = Cp[::-1]      # (the end farther out from the body is the tip, last)
    L_ = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(Cp, axis=0), axis=1))]; ts = np.linspace(0.0, L_[-1], nb)
    C = np.stack([np.interp(ts, L_, Cp[:, c]) for c in range(3)], 1)
    CU = np.stack([np.interp(ts, L_, np.interp(L_, L_, np.zeros(len(L_)))) for _ in range(2)], 1)
    kd = np.argmin(np.linalg.norm(C[:, None, :] - P[None, :, :], axis=2), axis=1); CU = U[kd]      # (each ring takes the texture point of the ribbon vertex nearest it)
    for _ in range(2): C[1:-1] = 0.25 * C[:-2] + 0.5 * C[1:-1] + 0.25 * C[2:]
    m_ = len(C); Tg = np.gradient(C, axis=0); Tg /= np.linalg.norm(Tg, axis=1)[:, None] + 1e-9
    nrm = np.cross(Tg[0], [0.0, 1.0, 0.0]);
    if np.linalg.norm(nrm) < 1e-3: nrm = np.cross(Tg[0], [1.0, 0.0, 0.0])
    nrm /= np.linalg.norm(nrm); VP = []; VU = []
    for k in range(m_):
        nrm = nrm - Tg[k] * float(nrm @ Tg[k]); nrm /= np.linalg.norm(nrm) + 1e-9; bn = np.cross(Tg[k], nrm)
        u_ = k / (m_ - 1.0); rk = R * (1.0 - 0.55 * max(0.0, (u_ - 0.75) / 0.25) ** 1.5)      # (round, and fining toward the tip)
        for j in range(ns): th = 2 * math.pi * j / ns; VP.append(C[k] + rk * (math.cos(th) * nrm + math.sin(th) * bn)); VU.append(CU[k])
    TT = []
    for k in range(m_ - 1):
        for j in range(ns):
            a_ = k * ns + j; b_ = k * ns + (j + 1) % ns; c_ = (k + 1) * ns + j; d_ = (k + 1) * ns + (j + 1) % ns; TT += [(a_, b_, c_), (b_, d_, c_)]
    return np.array(VP), np.array(VU), np.array(TT)
def slab(P, U, T, t):      # a flat blade becomes a solid slab: a second copy a little way off, joined all round the edge
    if t <= 0 or len(T) < 2: return P, U, T
    c = P.mean(0); w, vv = np.linalg.eigh(np.cov((P - c).T)); n = vv[:, 0]      # the thinnest direction of the blade
    n = n * (1.0 if n[1] <= 0 else -1.0) if False else n
    n_ = len(P); Pf = P - n * (t / 2); Pb = P + n * (t / 2)
    ed = {}
    for tr in T:
        for i in range(3):
            a_, b_ = int(tr[i]), int(tr[(i + 1) % 3]); k = (min(a_, b_), max(a_, b_)); ed.setdefault(k, []).append((a_, b_))
    side = []
    for k, v in ed.items():
        if len(v) == 1:
            a_, b_ = v[0]; side += [(a_, b_, b_ + n_), (a_, b_ + n_, a_ + n_)]
    T2 = np.concatenate([T, T[:, ::-1] + n_] + ([np.array(side)] if side else []))
    return np.concatenate([Pf, Pb]), np.concatenate([U, U]), T2
def ico(n):
    t = (1 + 5 ** 0.5) / 2; P = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    T = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    P = [np.array(p, float) / np.linalg.norm(p) for p in P]
    for _ in range(n):
        m = {}; T2 = []
        def mid(i, j):
            k = (min(i, j), max(i, j))
            if k not in m: q = P[i] + P[j]; m[k] = len(P); P.append(q / np.linalg.norm(q))
            return m[k]
        for x, y, z in T: ab = mid(x, y); bc = mid(y, z); ca = mid(z, x); T2 += [(x, ab, ca), (y, bc, ab), (z, ca, bc), (ab, bc, ca)]
        T = T2
    return np.array(P), np.array(T)
def ph_ell(c, r, face=False, nu=24, nv=14):      # placeholder: an ellipsoid (z along); the body gets the skin half of the texture, the head the face half
    c = np.asarray(c, float); r = np.asarray(r, float); P = []; U = []
    for j in range(nv + 1):
        th = math.pi * j / nv
        for i in range(nu + 1):
            ph = 2 * math.pi * i / nu; d = np.array([math.sin(th) * math.cos(ph), math.cos(th), math.sin(th) * math.sin(ph)]); P.append(c + d * r)
            if face: U.append((0.75 + 0.22 * d[0] * (1.0 if d[2] >= 0 else -1.0), 0.5 + 0.4 * d[1]))
            else: U.append((0.05 + 0.4 * i / nu, 0.1 + 0.8 * j / nv))
    T = []
    for j in range(nv):
        for i in range(nu): a0 = j * (nu + 1) + i; T += [(a0, a0 + 1, a0 + nu + 1), (a0 + 1, a0 + nu + 2, a0 + nu + 1)]
    return np.array(P), np.array(U), np.array(T)
def ph_tube(path, R, ns=10):      # placeholder: a round limb along a list of points, fining to the tip
    path = np.asarray(path, float); m = len(path); Tg = np.gradient(path, axis=0); Tg /= np.linalg.norm(Tg, axis=1)[:, None] + 1e-9
    nrm = np.cross(Tg[0], [0.0, 1.0, 0.0]); nrm = nrm if np.linalg.norm(nrm) > 1e-3 else np.cross(Tg[0], [1.0, 0.0, 0.0]); nrm /= np.linalg.norm(nrm); VP = []; VU = []
    for k in range(m):
        nrm = nrm - Tg[k] * float(nrm @ Tg[k]); nrm /= np.linalg.norm(nrm) + 1e-9; bn = np.cross(Tg[k], nrm); rk = R * (1.0 - 0.7 * (k / (m - 1.0)) ** 1.6)
        for j in range(ns): th = 2 * math.pi * j / ns; VP.append(path[k] + rk * (math.cos(th) * nrm + math.sin(th) * bn)); VU.append((k / (m - 1.0) * 0.9 + 0.05, j / ns))
    TT = []
    for k in range(m - 1):
        for j in range(ns): a_ = k * ns + j; b_ = k * ns + (j + 1) % ns; c_ = (k + 1) * ns + j; d_ = (k + 1) * ns + (j + 1) % ns; TT += [(a_, b_, c_), (b_, d_, c_)]
    return np.array(VP), np.array(VU), np.array(TT)
def ph_leg(sd, zc, tall):      # placeholder leg: hip on the flank, a knee up and out, the foot on the ground
    if tall: pts = [(sd * 0.28, 0.42, zc), (sd * 0.62, 0.86, zc + 0.02), (sd * 0.95, 0.80, zc + 0.04), (sd * 1.25, 0.08, zc + 0.05)]
    else: pts = [(sd * 0.28, 0.42, zc), (sd * 0.85, 0.80, zc + 0.03), (sd * 1.25, 0.58, zc + 0.06), (sd * 1.62, 0.08, zc + 0.08)]
    return ph_tube(np.array([curve_pt for curve_pt in pts]), 0.065 if not tall else 0.05)
def ph_body():      # placeholder body + head: two ellipsoids; returns points, uv, triangles and the head weight per point (0 body .. 1 head) like the rip version
    bP, bU, bT = ph_ell((0, 0.42, -0.15), (0.50, 0.36, 0.95)); hP, hU, hT = ph_ell((0, 0.46, 0.98), (0.36, 0.36, 0.34), True)
    P = np.concatenate([bP, hP]); U = np.concatenate([bU, hU]); T = np.concatenate([bT, hT + len(bP)])
    zn = P[:, 2].max() - 0.42; kf = np.clip((P[:, 2] - zn) / 0.18, 0.0, 1.0); kf = kf * kf * (3 - 2 * kf); return P, U, T, kf
pieces = []
kfB = None
if not a.child:
    if PH:
        bP, bU, bT, kf = ph_body(); pieces.append(('body', bP, bU, bT, 1))
        for k, zc in enumerate(np.linspace(-0.42, 0.34, 5)):
            P, U, T = ph_leg(-1, zc, False); pieces.append(('legL%d' % k, P, U, T, 2)); Pm = P.copy(); Pm[:, 0] = -Pm[:, 0]; pieces.append(('legR%d' % k, Pm, U, T[:, ::-1], 2))
    else:
        _fb = np.where(FM == 1)[0]; _zmax = V[np.unique(F[_fb])][:, 2].max(); _zc = V[F[_fb]][:, :, 2].mean(1); _hd = _fb[_zc > _zmax - 0.46]; _bd = _fb[_zc <= _zmax - 0.46]
        bP, bU, bT = soup(_bd); bP, bU, bT = shrink(bP, bU, bT, a.cell)
        hP, hU, hT = soup(_hd); hP, hU, hT = shrink(hP, hU, hT, a.facecell)      # the face keeps its detail: a finer grid, so the eyes and the mouth are not smeared
        _nB = len(bP)
        bT = np.concatenate([bT, hT + len(bP)]); bP = np.concatenate([bP, hP]); bU = np.concatenate([bU, hU])
        # her face is far bigger for her body than the child's: the head end swells (smoothly, from the neck forward) about the neck's centre
        zn = bP[:, 2].max() - 0.42; nk = bP[np.abs(bP[:, 2] - zn) < 0.05].mean(0); kf = np.clip((bP[:, 2] - zn) / 0.18, 0.0, 1.0); kf = kf * kf * (3 - 2 * kf)
        if a.torso > 1.0:      # the original torso is sized up toward the head so it meets the head with no gap
            _tb = np.arange(len(bP)) < _nB; _rp = np.clip((bP[:, 2] - (zn - a.torsolen)) / a.torsolen, 0.0, 1.0); _rp = _rp * _rp * (3 - 2 * _rp) * _tb
            _scx = 1.0 + (a.torsox - 1.0) * _rp; _scy = 1.0 + (a.torsoy - 1.0) * _rp; bP[:, 0] = nk[0] + (bP[:, 0] - nk[0]) * _scx; _top = 0.70; bP[:, 1] = np.where(_tb, _top - (_top - bP[:, 1]) * _scy, bP[:, 1]); bP[:, 2] += a.torsofwd * _rp
            _lw = np.where(_tb & (bP[:, 1] < a.torsofloor), a.torsofloor + (bP[:, 1] - a.torsofloor) * 0.12, bP[:, 1]); bP[:, 1] = _lw      # (the underside is flattened: it stays above her feet and never drags on the floor)
        bP = nk + (bP - nk) * (1.0 + (a.face - 1.0) * kf)[:, None]; bP[:, 1] -= 0.10 * kf
        _th = np.radians(a.tilt) * kf; _d = bP - nk; _y = _d[:, 1] * np.cos(_th) - _d[:, 2] * np.sin(_th); _z = _d[:, 1] * np.sin(_th) + _d[:, 2] * np.cos(_th); bP = nk + np.stack([_d[:, 0], _y, _z - a.tuck * kf], 1)      # the head tilts down about the neck (smoothly, so the join stays closed): her face hangs toward you      # (and hangs a little lower, toward the water)
        bP[:, 0] *= 1.0 + (a.girth - 1.0) * (1.0 - kf)      # her body is broad and hangs out over her legs (the face keeps its own size)
        # the head mask is hollow at the back; the tilt turns that hollow up into a scoop beside the white mound: a rounded cap of her own skin closes it
        _ed = {}
        for _t in hT + _nB:
            for _i in range(3):
                _p, _q = int(_t[_i]), int(_t[(_i + 1) % 3]); _ed.setdefault((min(_p, _q), max(_p, _q)), []).append(1)
        _bd = np.array(sorted({v for k, c in _ed.items() if len(c) == 1 for v in k})); _rim = _bd[(bP[_bd, 2] < a.capz) & (bP[_bd, 1] > 0.30)]
        if len(_rim) > 8:
            _R = bP[_rim]; _c = _R.mean(0); _ang = np.arctan2(_R[:, 1] - _c[1], _R[:, 0] - _c[0]); _o = _rim[np.argsort(_ang)]; _R = bP[_o]; _n = len(_o)
            _rings = [_o]; _P0 = len(bP); _newP = []; _newU = []; _newT = []
            for _lv, (_sc, _sh) in enumerate(((0.62, 0.07), (0.25, 0.12), (0.0, 0.14))):
                _q = _c + (_R - _c) * _sc; _q[:, 2] = _R[:, 2] - _sh * a.capbulge
                if _sc == 0.0: _q = _q[:1]
                _base = _P0 + sum(len(x) for x in _newP); _newP.append(_q); _newU.append(bU[_o][:len(_q)])
                _rings.append(np.arange(_base, _base + len(_q)))
            _bP2 = np.concatenate([bP] + _newP); _bU2 = np.concatenate([bU] + _newU); _tri = []
            for _l in range(len(_rings) - 1):
                A_, B_ = _rings[_l], _rings[_l + 1]
                for _k in range(_n):
                    _k2 = (_k + 1) % _n
                    if len(B_) == 1: _tri.append((A_[_k], A_[_k2], B_[0]))
                    else: _tri += [(A_[_k], A_[_k2], B_[_k]), (A_[_k2], B_[_k2], B_[_k])]
            _tri = np.array(_tri); bT = np.concatenate([bT, _tri, _tri[:, ::-1]]); bP = _bP2; bU = _bU2; kf = np.concatenate([kf, np.full(len(bP) - len(kf), 1.0)])
        if a.bowl > 0:      # the head mask is an open shell at the back: a solid lump of her own skin fills the whole bowl
            _hs = bP[_nB:_nB + len(hP)]; _sel = np.where((_hs[:, 2] < a.bowlz) & (_hs[:, 1] > 0.15))[0]
            if len(_sel) > 8:
                _bc = np.array([_hs[_sel, 0].mean(), _hs[_sel, 1].mean() + a.bowldy, a.bowlc]); _br = np.array([0.5 * np.ptp(_hs[_sel, 0]) * 0.95, 0.5 * np.ptp(_hs[_sel, 1]) * 0.9, a.bowlr]) * a.bowl
                S2, ST2 = ico(3); _kd = None
                _vP = _bc + S2 * _br; _src = _nB + _sel[np.argmin(np.abs(_hs[_sel, 2] - 0.80))]; _vU = bU[_nB + _sel][np.argmin(((_vP[:, None, :] - _hs[_sel][None]) ** 2).sum(2), 1)]
                bT = np.concatenate([bT, ST2 + len(bP)]); bP = np.concatenate([bP, _vP]); bU = np.concatenate([bU, _vU]); kf = np.concatenate([kf, np.full(len(S2), 1.0)])
                print('bowl centre', _bc, 'radii', _br)
        if a.bridge > 0:      # a solid neck of her own skin joins the head to the body, closing the see-through gap under her white back
            S3, ST3 = ico(3); _bc2 = np.array([a.brx, a.bry, a.brz]); _vP = _bc2 + S3 * np.array([a.brw, a.brh, a.brl]) * a.bridge
            _hs = bP[:_nB]; _vU = bU[np.argmin(((_vP[:, None, :] - bP[None]) ** 2).sum(2), 1)]
            bT = np.concatenate([bT, ST3 + len(bP)]); bP = np.concatenate([bP, _vP]); bU = np.concatenate([bU, _vU]); kf = np.concatenate([kf, np.full(len(S3), 1.0)])
        pieces.append(('body', bP, bU, bT, 1))
        zs = np.linspace(-0.42, 0.34, 5)      # five legs a side, evenly along her flanks
        for k, zc in enumerate(zs):
            fs = left[k % len(left)]; P, U, T = soup(fs); P, U, T = shrink(P, U, T, a.cell * 0.8)
            P = P.copy(); P[:, 2] += zc - P[:, 2].mean(); P[:, 0] *= a.leg; P[:, 1] *= 1.0      # (a little longer: hers splay wide)
            P, U, T = slab(P, U, T, a.legthick)      # (solid: a slab, not a flat blade)
            pieces.append(('legL%d' % k, P, U, T, 2))
            Pm = P.copy(); Pm[:, 0] = -Pm[:, 0]; pieces.append(('legR%d' % k, Pm, U, T[:, ::-1], 2))
    # ---- the mound on her back: a lumpy pale dome from behind the head to the tail, with tufts standing out of it
    bl = bP[:, 2]; z0, z1 = bl.min(), bl.max(); L = z1 - z0
    _rear = 0.78 - 0.84 * a.mound; _rz = (a.moundfront - _rear) / 2.0; mc = np.array([0.0, 0.66, z0 + (a.moundfront - _rz) * L]); mr = np.array([0.725 * a.girth * a.moundw, 0.70, _rz * L])      # (the back end stays where --mound put it; the front end comes up toward her head)      # (the front edge stays where it was behind the head: the extra length grows toward the tail)      # (wide enough to overhang the legs)      # centre and radii (x across, y up, z along her)
    S, ST = ico(3); ph = rng.uniform(0, 6.28, (10, 3)); fq = np.concatenate([rng.uniform(2.0, 4.0, (4, 3)), rng.uniform(6.0, 11.0, (6, 3))])
    bump = sum(np.sin(S @ fq[i] + ph[i].sum()) * (1.0 if i < 4 else 0.55) for i in range(10)) / 5.0
    mP = mc + S * mr * (1.0 + 0.2 * bump)[:, None]; keep = mP[:, 1] > 0.22      # (the underside is inside her body: dropped)
    mU = np.stack([0.5 + 1.4 * S[:, 0] + 0.3 * bump, 0.5 + 1.4 * S[:, 2] + 0.9 * S[:, 1]], 1)      # (the small texture repeats a few times over the dome)
    mT = ST[keep[ST].all(1)]
    if a.lobe > 0:      # a lobe of the same white growth fills the scoop at the back of her head (in front of the dome's rounded front)
        _lc = np.array([0.0, 0.58, 0.80]); _lr = np.array([0.50, 0.44, 0.24]) * a.lobe; _lP = _lc + S * _lr * (1.0 + 0.15 * bump)[:, None]; _lk = _lP[:, 1] > 0.22
        _lU = np.stack([0.5 + 1.4 * S[:, 0] + 0.3 * bump, 0.5 + 1.4 * S[:, 2] + 0.9 * S[:, 1]], 1); _lT = ST[_lk[ST].all(1)] + len(mP)
        mT = np.concatenate([mT, _lT]); mP = np.concatenate([mP, _lP]); mU = np.concatenate([mU, _lU])
    pieces.append(('mound', mP, mU, mT, 3))
    tP = []; tU = []; tT = []      # flowers: soft white blooms all over the dome. Each is five broad petals round a pale yellow heart, slightly cupped, tilted this way and that, on the surface or a little above it
    for _ in range(a.flowers):
        d = rng.normal(size=3); d[1] = abs(d[1]) + 0.15; d /= np.linalg.norm(d); n = d / mr; n /= np.linalg.norm(n)
        n = n + rng.normal(size=3) * 0.35; n /= np.linalg.norm(n)      # each bloom faces its own way
        c0 = mc + d * mr * (1.0 + 0.2 * 0.5) + n * rng.uniform(0.0, 0.07)
        u = np.cross(n, [0.3, 0.1, 1.0]); u /= np.linalg.norm(u) + 1e-9; v = np.cross(n, u); r = rng.uniform(0.07, 0.15); cup = rng.uniform(0.15, 0.5); a0 = rng.uniform(0, 6.28); i0 = len(tP)
        tP.append(c0); tU.append((0.5, 0.5))
        for k in range(5):
            for sgn in (-1, 1):
                ang = a0 + k * 1.2566 + sgn * 0.5; tP.append(c0 + r * (math.cos(ang) * u + math.sin(ang) * v) + n * r * cup); tU.append((0.5 + 0.48 * math.cos(k * 1.2566 + sgn * 0.5), 0.5 + 0.48 * math.sin(k * 1.2566 + sgn * 0.5)))
            tT.append((i0, i0 + 1 + 2 * k, i0 + 2 + 2 * k)); tT.append((i0, i0 + 2 + 2 * k, i0 + 1 + 2 * k))      # (seen from both sides)
    pieces.append(('flowers', np.array(tP), np.array(tU), np.array(tT), 4))
    kfB = kf
    # her mound's own texture: pale, speckled, with dark pits
    tx = rng.normal(0, 1, (64, 64)); 
    for _ in range(3): tx = (tx + np.roll(tx, 1, 0) + np.roll(tx, 1, 1) + np.roll(tx, -1, 0) + np.roll(tx, -1, 1)) / 5.0
    tx = (tx - tx.min()) / (tx.max() - tx.min()); g = 205 + 50 * tx; g[tx < 0.3] = 120 + 280 * tx[tx < 0.3]      # (pale and soft under the flowers, only faintly shadowed)
    yy, xx = np.mgrid[0:32, 0:32]; rr = np.hypot(xx - 15.5, yy - 15.5) / 15.5; fl = np.stack([255 - 10 * rr, 252 - 6 * rr, 235 + 14 * np.clip(rr * 3, 0, 1)], 2); fl[rr < 0.22] = (238, 226, 150)      # the flower: white petals, a soft yellow heart
    TEX[4] = Image.fromarray(fl.clip(0, 255).astype('uint8'), 'RGB')
    TEX[3] = Image.fromarray(np.stack([g * 0.96, g, g * 1.02], 2).clip(0, 255).astype('uint8'), 'RGB').resize((128, 128), Image.BILINEAR)

else:
    if PH:
        bP, bU, bT, kf = ph_body(); kfB = kf; pieces.append(('body', bP, bU, bT, 1)); nl = 0
        for sd in (-1, 1):
            for zc in np.linspace(-0.55, 0.55, 4):
                P, U, T = ph_leg(sd, zc, abs(zc) > 0.4)
                if sd > 0: T = T[:, ::-1]
                pieces.append(('leg%s%d' % ('R' if sd > 0 else 'L', nl), P, U, T, 2)); nl += 1
    else:
        # ---- her spiders: the rip as it is (body, head, every leg), small
        bP, bU, bT = soup(np.where(FM == 1)[0]); bP, bU, bT = shrink(bP, bU, bT, a.cell * a.cbody)
        zn = bP[:, 2].max() - 0.42; kf = np.clip((bP[:, 2] - zn) / 0.18, 0.0, 1.0); kf = kf * kf * (3 - 2 * kf); kfB = kf
        pieces.append(('body', bP, bU, bT, 1)); nl = 0
        _zb = 0.5 * (bP[:, 2].min() + bP[:, 2].max())
        for r in sorted(set(froot[froot >= 0])):
            fs = np.where(froot == r)[0]; P, U, T = soup(fs); P, U, T = shrink(P, U, T, a.cell * a.cleg)
            if len(T) < 4: continue
            tall_ = np.ptp(P[:, 1]) > 1.35      # (the four curled front legs are the ones 1.4 tall: two on each of bones 18 and 19; the 1.3 ones are the tall arms)
            if tall_:      # the four curled front legs become round limbs: a tube of radius --curlr all along, fining toward the tip
                c_ = P.mean(0); w_, vv_ = np.linalg.eigh(np.cov((P - c_).T)); n_ = vv_[:, 0]      # the two loops each curled leg showed (its front and back sheet) are kept as two round limbs
                Pa, Ua, Ta = tube(P - n_ * a.curlgap / 2, U, T, a.curlr, a.tnb, a.tns); Pb, Ub, Tb = tube(P + n_ * a.curlgap / 2, U, T, a.curlr, a.tnb, a.tns)
                P = np.concatenate([Pa, Pb]); U = np.concatenate([Ua, Ub]); T = np.concatenate([Ta, Tb + len(Pa)]); print('curled leg: two round limbs, radius %.3f' % a.curlr)
            else:
                _back = P[:, 2].mean() < _zb      # the back legs: behind the middle of the body
                if _back or a.alllegs:
                    _t = tube(P, U, T, a.backr, a.tnb, a.tns)
                    if np.isfinite(_t[0]).all() and len(_t[2]) > 3: P, U, T = _t
                    else: print('  (a leg could not be rounded: kept as it was)'); P, U, T = slab(P, U, T, a.legthick * 2.0)      # (the back legs become round limbs, like the curled front ones)
                else: P, U, T = slab(P, U, T, a.legthick * 2.0)
                pass; print('leg z %.2f %s' % (P[:, 2].mean(), 'BACK' if _back else 'front'))
            pieces.append(('leg%s%d' % ('R' if P[:, 0].mean() > 0 else 'L', nl), P, U, T, 2)); nl += 1
CH = bool(a.child); SZ = a.size if not CH else (a.size if a.size != 3.4 else 0.75)
def G_(P): return np.stack([P[:, 2], P[:, 0], P[:, 1]], 1) * SZ      # the rip (x across, y up, z along) -> game (x forward, y right, z up), metres
# ---- bones and skin weights
names = ['body', 'head'] + ([] if CH else ['mound']); pivot = [None, None] + ([] if CH else [None]); legbones = []      # (side, [bone indices], tip)
VP = []; VU = []; VB = []; secs = []; idx = []; base = 0; tex_ids = sorted(set(p[4] for p in pieces))
bodyG = G_(pieces[0][1]); bc = bodyG.mean(0); xmin_, xmax_ = bodyG[:, 0].min(), bodyG[:, 0].max(); Lb = xmax_ - xmin_
neck = np.array([xmax_ - 0.42 * SZ * (a.face if not CH else 1.0) * 0.6, 0.0, bc[2]]); head_pt = np.array([xmax_ - 0.05 * Lb, 0.0, bodyG[bodyG[:, 0] > xmax_ - 0.2 * Lb][:, 2].mean()])
pivot[0] = bc.copy(); pivot[1] = neck
for ti in tex_ids:
    st = len(idx)
    for nm, P, U, T, t2 in pieces:
        if t2 != ti: continue
        Gp = G_(P); n = len(Gp); b0 = np.zeros(n, int); b1 = np.zeros(n, int); w0 = np.full(n, 255, int)
        if nm == 'body': b1[:] = 1; w0 = np.round(255 * (1.0 - 0.9 * kfB)).astype(int)
        elif nm in ('mound', 'flowers'):
            b0[:] = 2; b1[:] = 0; zrel = np.clip((P[:, 1] - 0.3) / 0.3, 0.0, 1.0); w0 = np.round(255 * zrel).astype(int)
            if pivot[2] is None: pivot[2] = np.array([Gp[:, 0].mean(), 0.0, Gp[:, 2].min()])
        else:      # a leg
            sg = 1.0 if Gp[:, 1].mean() > 0 else -1.0; ay = np.abs(Gp[:, 1]); y0, y1 = ay.min(), ay.max(); u = (ay - y0) / max(y1 - y0, 1e-6)
            hip = Gp[u < 0.1].mean(0); tip = Gp[np.argmax(ay)]
            if CH:
                names.append(nm); pivot.append(hip); bi = len(names) - 1; b0[:] = bi; b1[:] = bi; legbones.append((sg, [bi], tip, hip, float(Gp[:, 2].max()), float(y1 - y0)))
            else:
                km = (u > 0.4) & (u < 0.6); knee = Gp[km].mean(0) if km.any() else 0.5 * (hip + tip)
                names += [nm, nm + '_2']; pivot += [hip, knee]; bh = len(names) - 2; bk = bh + 1
                b0[:] = bh; b1[:] = bk; w0 = np.round(255 * (1.0 - np.clip((u - 0.4) / 0.2, 0.0, 1.0))).astype(int); legbones.append((sg, [bh, bk], tip, hip, float(Gp[:, 2].max()), float(y1 - y0)))
        for t in T: idx += [base + int(t[0]), base + int(t[1]), base + int(t[2])]
        VP.append(Gp); VU.append(U); VB.append(np.stack([b0, b1, w0], 1)); base += n
    secs.append((st, len(idx) - st, tex_ids.index(ti), 0))
VP = np.concatenate(VP); VU = np.concatenate(VU); VB = np.concatenate(VB); NB = len(names); nV = len(VP)
zfl = VP[:, 2].min(); VP[:, 2] -= zfl; pivot = [p - [0, 0, zfl] for p in pivot]; bc = bc - [0, 0, zfl]; head_pt = head_pt - [0, 0, zfl]; legbones = [(sg, bl, tip - [0, 0, zfl], hip - [0, 0, zfl], zt - zfl, ln) for sg, bl, tip, hip, zt, ln in legbones]
legbones.sort(key=lambda q: (q[3][0], q[0]))      # back to front, left then right
print('%s: %d points, %d triangles, %d bones; %.1f m long, %.1f m wide, %.1f m tall' % ('Child of Rom' if CH else 'Rom', nV, len(idx) // 3, NB, np.ptp(VP[:, 0]), np.ptp(VP[:, 1]), np.ptp(VP[:, 2])))
# ---- poses
def Rx(t): c, s = math.cos(t), math.sin(t); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def Ry(t): c, s = math.cos(t), math.sin(t); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def Rz(t): c, s = math.cos(t), math.sin(t); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
def about(R, p, t=(0, 0, 0)): M = np.zeros((3, 4)); M[:, :3] = R; M[:, 3] = np.asarray(p) - R @ np.asarray(p) + np.asarray(t); return M
def mul(A, B): M = np.zeros((3, 4)); M[:, :3] = A[:, :3] @ B[:, :3]; M[:, 3] = A[:, :3] @ B[:, 3] + A[:, 3]; return M
D = math.radians; tau = 2 * math.pi; sn = math.sin
def sm(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def pulse(t, a_, b_, c_, d_): return sm((t - a_) / max(b_ - a_, 1e-6)) * (1.0 - sm((t - c_) / max(d_ - c_, 1e-6)))
rear = np.array([xmin_ + 0.22 * Lb, 0.0, 0.25 * SZ])      # she rears about her hind end, which stays on the ground
NL = len(legbones)
def build(o):
    M0 = mul(about(Rz(o.get('yaw', 0.0)) @ Rx(o.get('roll', 0.0)), bc, (o.get('bx', 0.0), o.get('by', 0.0), o.get('bz', 0.0))), about(Ry(-o.get('pitch', 0.0)), rear))      # pitch > 0 = front up
    mats = [None] * NB; mats[0] = M0; mats[1] = mul(M0, about(Ry(-o.get('hp', 0.0)) @ Rz(o.get('hy', 0.0)), pivot[1]))
    if not CH: mats[2] = mul(M0, about(Rx(o.get('mr', 0.0)) @ Ry(o.get('mp', 0.0)), pivot[2]))
    lf = o.get('lift', None); sw_ = o.get('sweep', None); kn = o.get('knee', None)
    for i, (sg, bl, tip, hip, zt, ln) in enumerate(legbones):
        l = lf[i] if lf is not None else 0.0; s = sw_[i] if sw_ is not None else 0.0; k = kn[i] if kn is not None else 0.0
        H = mul(M0, about(Rz(-sg * s) @ Rx(sg * l), pivot[bl[0]])); mats[bl[0]] = H
        if len(bl) > 1: mats[bl[1]] = mul(H, about(Rx(sg * k), pivot[bl[1]]))
    return mats
fr_tip = sorted(legbones, key=lambda q: -q[3][0])[:2]      # the two front legs: their tips are the "hands"
if CH: fr_tip = sorted(legbones, key=lambda q: -q[4])[:2]      # (the child: its two tall arms)
hr = next(q for q in fr_tip if q[0] > 0) if any(q[0] > 0 for q in fr_tip) else fr_tip[0]; hl = next(q for q in fr_tip if q[0] < 0) if any(q[0] < 0 for q in fr_tip) else fr_tip[-1]
att_pts = [(hr[1][-1], hr[2]), (hl[1][-1], hl[2]), (1, head_pt), (0, bc)]      # hand_r, hand_l, head, spine_2
B0 = VB[:, 0]; B1 = VB[:, 1]; W0 = (VB[:, 2] / 255.0)[:, None]
def skin(mats):
    M = np.array(mats); return W0 * (np.einsum('vij,vj->vi', M[B0][:, :, :3], VP) + M[B0][:, :, 3]) + (1 - W0) * (np.einsum('vij,vj->vi', M[B1][:, :, :3], VP) + M[B1][:, :, 3])
FPS = 30.0
def frame(o):
    mats = build(o); lo = skin(mats)[:, 2].min()
    if lo < -0.02 or o.get('ground'): mats = [m.copy() for m in mats]; [m.__setitem__((2, 3), m[2, 3] - lo) for m in mats]      # nothing sinks through the floor
    out = list(mats)
    for b, p in att_pts: M = mats[b].copy(); M[:, 3] = mats[b][:, :3] @ p + mats[b][:, 3]; out.append(M)
    return np.concatenate([m.reshape(12) for m in out]).astype('<f4')
anims = []
def anim(name, dur, fn, loop=False, travel=(0.0, 0.0)):
    n = max(2, int(round(dur * FPS))); anims.append((name, FPS, np.array([frame(fn(i / n if loop else i / (n - 1))) for i in range(n)], '<f4'), travel))
def legs(ph, la, sa, ka=0.0, lag=1.25, base_l=0.0, twitch=0.0):      # a spider's gait: the legs move in two alternating sets (every other leg, the two sides opposed), each a little off the beat and a little different in reach, so no two legs move alike
    L_ = []; S_ = []; K_ = []
    for i, (sg, bl, tip, hip, zt, ln) in enumerate(legbones):
        grp = (i // 2) % 2; p = ph + (math.pi if ((sg > 0) != (grp == 1)) else 0.0) + 0.4 * sn(i * 2.1); amp = 1.0 + 0.3 * sn(i * 1.7 + 1.0)
        tw = twitch * max(0.0, sn(ph * (1 + i % 3) + i * 1.9)) ** 3      # (idle: now and then one leg feels about, on its own beat)
        L_.append(base_l + D(la) * amp * max(0.0, math.cos(p)) + D(14) * tw); S_.append(D(sa) * amp * sn(p) + D(10) * tw * sn(ph * 2 + i)); K_.append(D(ka) * amp * max(0.0, math.cos(p - 0.5)) + D(18) * tw)
    return L_, S_, K_
def front(w):      # how much each leg counts as a front leg (0 at the back, 1 at the front)
    xs = [q[3][0] for q in legbones]; lo, hi = min(xs), max(xs); return [((x - lo) / max(hi - lo, 1e-6)) ** 1.5 * w for x in xs]
if not CH:
    def idle(t):
        ph = t * tau; L_, S_, K_ = legs(ph, 8, 6, 8, twitch=1.0)
        return {'bz': 0.07 * sn(ph), 'pitch': D(1.5) * sn(ph + 1), 'roll': D(1.2) * sn(ph * 2), 'hp': D(4) * sn(ph + 0.6), 'hy': D(5) * sn(ph * 0.5 + 0.3) if False else D(5) * sn(ph), 'mr': D(1.5) * sn(ph * 2 + 1), 'mp': D(1.2) * sn(ph + 2), 'lift': L_, 'sweep': S_, 'knee': K_}
    anim('Idle', 3.0, idle, loop=True)
    def walk(t):
        ph = t * tau; L_, S_, K_ = legs(ph, 34, 30, 26)
        return {'bz': 0.06 * sn(ph * 2), 'roll': D(2.5) * sn(ph), 'yaw': D(2) * sn(ph + 0.5), 'pitch': D(1.5) * sn(ph * 2 + 1), 'hp': D(3) * sn(ph * 2), 'mr': D(2.5) * sn(ph + 1.2), 'lift': L_, 'sweep': S_, 'knee': K_}
    anim('WalkFast', 1.6, walk, loop=True, travel=(1.3, 0.0))
    def meteor(t):      # MeteorSlam: she rears back, her front legs reaching up at the sky, holds, then drops; the crystals fall as her body hits the ground (0.56)
        up = pulse(t, 0.04, 0.3, 0.47, 0.56); hit = pulse(t, 0.53, 0.58, 0.64, 0.8); fw = front(1.0); shake = pulse(t, 0.25, 0.32, 0.45, 0.5)
        return {'pitch': D(34) * up - D(4) * hit, 'bz': -0.12 * hit, 'bx': -0.3 * up, 'hp': D(18) * up, 'mr': D(2) * sn(t * 60) * shake, 'roll': D(1.5) * sn(t * 70) * shake,
                'lift': [D(55) * f * up + D(4) * sn(t * 40 + i) * shake for i, f in enumerate(fw)], 'sweep': [D(20) * f * up for f in fw], 'knee': [D(-30) * f * up for f in fw]}
    anim('MeteorSlam', 3.2, meteor)
    def iceroll(t):      # IceRoll: she heaves over onto her back, legs working in the air, while the crystals burst up under you (from 0.35), then rights herself
        r = pulse(t, 0.06, 0.3, 0.7, 0.94); ph = t * tau * 7
        return {'roll': D(172) * r, 'by': 1.6 * SZ / 3.4 * sn(math.pi * min(1.0, t / 0.3)) * (1 if t < 0.3 else 0) - 1.6 * SZ / 3.4 * sn(math.pi * min(1.0, max(0.0, (t - 0.7) / 0.24))) * (1 if t > 0.7 else 0), 'hp': D(10) * r,
                'lift': [D(25) * r + D(18) * sn(ph + i * 0.9) * r for i in range(NL)], 'sweep': [D(14) * sn(ph * 0.8 + i * 1.3) * r for i in range(NL)], 'knee': [D(20) * sn(ph + i) * r for i in range(NL)], 'ground': 1}
    anim('IceRoll', 3.4, iceroll)
    def blast(t):      # BlastSlam: up on her hind end, higher than for the meteors, a short hold, then down hard: the burst goes off as she lands (0.56)
        up = pulse(t, 0.06, 0.34, 0.48, 0.56); hit = pulse(t, 0.53, 0.58, 0.66, 0.85); fw = front(1.0)
        return {'pitch': D(52) * up - D(6) * hit, 'bz': 0.25 * up - 0.18 * hit, 'bx': -0.5 * up + 0.3 * hit, 'hp': D(-12) * up + D(10) * hit, 'mr': D(3) * sn(t * 55) * hit,
                'lift': [D(40) * f * up - D(8) * hit for f in fw], 'sweep': [D(-15) * f * up for f in fw], 'knee': [D(25) * f * up for f in fw]}
    anim('BlastSlam', 2.6, blast)
    def flail(t):      # FlailCombo: she throws her bulk from side to side, twice, and comes down
        e = pulse(t, 0.05, 0.2, 0.75, 0.95); ph = (t - 0.15) / 0.6 * tau * 2
        return {'yaw': D(24) * sn(ph) * e, 'roll': D(13) * sn(ph + 0.6) * e, 'by': 0.7 * sn(ph) * e, 'bz': 0.15 * abs(sn(ph)) * e, 'hy': D(14) * sn(ph - 0.5) * e, 'mr': D(5) * sn(ph - 1.0) * e,
                'lift': [D(22) * abs(sn(ph + i * 0.7)) * e for i in range(NL)], 'sweep': [D(18) * sn(ph + i * 0.9) * e for i in range(NL)], 'knee': [0.0] * NL}
    anim('FlailCombo', 2.2, flail)
    anim('HeadDmg1', 0.6, lambda t: {'pitch': D(5) * pulse(t, 0, 0.25, 0.4, 1), 'hp': D(-14) * pulse(t, 0, 0.2, 0.4, 1), 'bx': -0.15 * pulse(t, 0, 0.25, 0.4, 1)})
    anim('LegDmgL', 0.6, lambda t: {'roll': D(7) * pulse(t, 0, 0.25, 0.4, 1), 'by': 0.15 * pulse(t, 0, 0.25, 0.4, 1), 'mr': D(-4) * pulse(t, 0, 0.3, 0.5, 1)})
    anim('LegDmgR', 0.6, lambda t: {'roll': D(-7) * pulse(t, 0, 0.25, 0.4, 1), 'by': -0.15 * pulse(t, 0, 0.25, 0.4, 1), 'mr': D(4) * pulse(t, 0, 0.3, 0.5, 1)})
    def stag(t):      # CounteredStart: she slumps, legs splayed and slack, head down, and stays so
        d = sm(t / 0.18); q = sn(t * 30) * (1 - sm(t / 0.4)) * 0.5
        return {'bz': -0.3 * d, 'roll': D(9) * d + D(2) * q, 'hp': D(-22) * d, 'pitch': D(-3) * d, 'mr': D(5) * d, 'lift': [D(-10) * d] * NL, 'sweep': [D(6) * (1 if i % 4 < 2 else -1) * d for i in range(NL)], 'knee': [D(-14) * d] * NL, 'ground': 1}
    anim('CounteredStart', 3.0, stag)
    def visc(t):
        j = pulse(t, 0.0, 0.08, 0.2, 0.5); rec = sm((t - 0.6) / 0.4)
        return {'pitch': D(16) * j, 'bx': -0.5 * j, 'bz': -0.25 * (1 - rec) * sm(t / 0.2), 'roll': D(8) * (1 - rec) + D(3) * sn(t * 45) * j, 'hp': D(-25) * j, 'lift': [D(20) * j] * NL, 'knee': [D(-20) * (1 - rec)] * NL, 'sweep': [0.0] * NL, 'ground': 1}
    anim('Visceral', 2.5, visc)
    def death(t):      # Death: a last heave, then her legs curl in under her and she settles on her side
        h = pulse(t, 0.0, 0.12, 0.2, 0.4); d = sm((t - 0.25) / 0.45)
        return {'pitch': D(18) * h, 'roll': D(62) * d, 'bz': 0.2 * h, 'hp': D(-30) * d, 'mr': D(8) * d, 'lift': [D(-25) * d + D(25) * h] * NL, 'knee': [D(-70) * d] * NL, 'sweep': [0.0] * NL, 'ground': 1}
    anim('Death', 3.5, death)
else:
    def cidle(t):
        ph = t * tau; L_, S_, K_ = legs(ph, 8, 6, twitch=1.0)
        return {'bz': 0.03 * sn(ph), 'hp': D(5) * sn(ph + 1), 'hy': D(8) * sn(ph * 0.5), 'lift': L_, 'sweep': S_}
    anim('Idle1', 2.0, cidle, loop=True)
    def cwalk(a_l, a_s, bob):
        def f(t):
            ph = t * tau; L_, S_, K_ = legs(ph, a_l, a_s, lag=1.9)
            return {'bz': bob * sn(ph * 2), 'roll': D(3) * sn(ph), 'yaw': D(3) * sn(ph + 1), 'lift': L_, 'sweep': S_}
        return f
    anim('Walk', 0.8, cwalk(30, 34, 0.02), loop=True, travel=(1.1, 0.0))
    anim('Run', 0.5, cwalk(38, 40, 0.04), loop=True, travel=(1.7, 0.0))
    fw = front(1.0)
    def combo(t):      # 2HitCombo: two quick jabs with the tall front arms, lunging in
        a1 = pulse(t, 0.08, 0.2, 0.26, 0.4); a2 = pulse(t, 0.45, 0.57, 0.63, 0.8)
        return {'bx': 0.35 * (a1 + a2), 'pitch': D(-10) * (a1 + a2), 'hp': D(-10) * (a1 + a2), 'lift': [D(6) * f * (a1 + a2) + D(34) * f * (pulse(t, 0, 0.08, 0.1, 0.2) + pulse(t, 0.36, 0.45, 0.47, 0.57)) for f in fw], 'sweep': [D(30) * f * (a1 + a2) for f in fw]}
    anim('2HitCombo', 1.2, combo)
    anim('Bite1', 0.9, lambda t: {'bx': 0.5 * pulse(t, 0.25, 0.4, 0.5, 0.8) - 0.15 * pulse(t, 0, 0.15, 0.22, 0.35), 'pitch': D(-14) * pulse(t, 0.25, 0.4, 0.5, 0.8) + D(8) * pulse(t, 0, 0.15, 0.22, 0.35), 'hp': D(-20) * pulse(t, 0.25, 0.4, 0.5, 0.8)})
    def cjump(t):
        c = pulse(t, 0.0, 0.15, 0.2, 0.28); u = min(max((t - 0.25) / 0.4, 0.0), 1.0); arc = 4 * u * (1 - u); land = pulse(t, 0.62, 0.68, 0.75, 0.95)
        return {'bz': 0.55 * arc - 0.1 * c - 0.08 * land, 'bx': 0.9 * sm(u) * (1 - sm((t - 0.75) / 0.25)), 'pitch': D(12) * c - D(18) * arc + D(8) * land, 'lift': [D(25) * arc + D(-12) * land] * NL, 'sweep': [D(15) * arc * (1 if i % 2 else -1) for i in range(NL)]}
    anim('JumpAttack', 1.3, cjump)
    anim('HitReactF', 0.5, lambda t: {'bx': -0.2 * pulse(t, 0, 0.25, 0.4, 1), 'pitch': D(10) * pulse(t, 0, 0.25, 0.4, 1), 'hp': D(15) * pulse(t, 0, 0.2, 0.4, 1)})
    anim('HitReactB', 0.5, lambda t: {'bx': 0.2 * pulse(t, 0, 0.25, 0.4, 1), 'pitch': D(-8) * pulse(t, 0, 0.25, 0.4, 1), 'roll': D(8) * pulse(t, 0, 0.25, 0.4, 1)})
    anim('Death', 1.6, lambda t: {'roll': D(175) * sm((t - 0.1) / 0.45), 'bz': 0.25 * pulse(t, 0.05, 0.2, 0.3, 0.5), 'lift': [D(-40) * sm((t - 0.3) / 0.4)] * NL, 'hp': D(-20) * sm(t / 0.3), 'ground': 1})
# ---- the file (BBH2), with the limb map (LMB1) at the end
def tex_pack(ti):
    im = TEX[ti].convert('RGBA'); cap = a.tex if ti == 1 else (a.tex // 2 if ti == 2 else 128)
    while max(im.size) > cap: im = im.resize((max(1, im.size[0] // 2), max(1, im.size[1] // 2)), Image.LANCZOS)
    return im
verts = np.zeros(nV, dtype=[('p', '<3f4'), ('uv', '<2f4'), ('b', 'u1', 4)])
verts['p'] = VP; verts['uv'] = np.stack([VU[:, 0], 1.0 - VU[:, 1]], 1); verts['b'][:, :3] = VB
out = bytearray(b'BBH2'); out += struct.pack('<7I', nV, len(idx), NB, len(anims), 4, len(secs), len(tex_ids))
for k, ti in enumerate(tex_ids):
    im = tex_pack(ti); nb = ('T_Rom%d' % ti).encode(); out += struct.pack('<B', len(nb)) + nb + struct.pack('<HH', *im.size) + im.tobytes()
for s_ in secs: out += struct.pack('<IIHH', *s_)
out += verts.tobytes(); out += np.array(idx, '<u2').tobytes()
for n_ in ('hand_r', 'hand_l', 'head', 'spine_2'): out += n_.encode().ljust(16, b'\0')
for nm, fps, fr, tv in anims: out += nm.encode()[:32].ljust(32, b'\0') + struct.pack('<fIff', fps, len(fr), tv[0], tv[1]) + fr.tobytes()
lcode = [0] * NB; lfrac = [0] * NB
for sg, bl, tip, hip, zt, ln in legbones:
    for k, b in enumerate(bl): lcode[b] = 3; lfrac[b] = int(255 * (k + 1) / len(bl))
out += b'LMB1' + struct.pack('<I', NB) + bytes(lcode) + bytes(lfrac)
open(a.out, 'wb').write(out); print('wrote %s: %d KB, %d animations' % (a.out, len(out) // 1024, len(anims)))
if a.preview:
    shots = [('Idle', 0.0), ('MeteorSlam', 0.42), ('IceRoll', 0.5), ('BlastSlam', 0.45), ('FlailCombo', 0.4), ('Death', 1.0)] if not CH else [('Idle1', 0.0), ('Run', 0.3), ('2HitCombo', 0.22), ('JumpAttack', 0.45), ('Death', 1.0)]
    Sz = 420; sheet = Image.new('RGB', (Sz * len(shots), Sz * 2), (150, 156, 166)); span = 13.0 if not CH else 4.5; pxs = {ti: np.array(TEX[ti].convert('RGB')) for ti in tex_ids}; vt = np.zeros(nV, int); 
    tri = np.array(idx).reshape(-1, 3); ttex = np.zeros(len(tri), int)
    for (st, cnt, tk, fl) in secs: ttex[st // 3:(st + cnt) // 3] = tex_ids[tk]
    for k, (nm, f) in enumerate(shots):
        A = next(x for x in anims if x[0] == nm)[2]; fr = A[int(f * (len(A) - 1))].reshape(-1, 3, 4); Q0 = skin(list(fr[:NB]))
        for r, yaw in enumerate((35, 100)):
            im = Image.new('RGB', (Sz, Sz), (150, 156, 166)); d = ImageDraw.Draw(im); c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw)); Q = Q0 @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]).T; sc = Sz / span; lst = []
            for t, tk in zip(tri, ttex):
                q = Q[t]; n = np.cross(q[1] - q[0], q[2] - q[0]); ln = np.linalg.norm(n)
                if ln < 1e-12: continue
                px = pxs[tk]; uv = VU[t].mean(0); col = px[int((1 - uv[1] % 1.0) * (px.shape[0] - 1)), int((uv[0] % 1.0) * (px.shape[1] - 1))].astype(float); sh = 0.45 + 0.55 * abs(n[0]) / ln + 0.15 * max(0.0, n[2] / ln)
                lst.append((q[:, 0].mean(), [(Sz / 2 + p[1] * sc, Sz * 0.8 - p[2] * sc) for p in q], tuple(int(min(255, x * sh)) for x in col)))
            for _, pts, col in sorted(lst, key=lambda t: t[0]): d.polygon(pts, fill=col)
            d.line([(0, Sz * 0.8), (Sz, Sz * 0.8)], fill=(110, 116, 126)); d.text((6, 6), '%s @ %.2f' % (nm, f), fill=(0, 0, 0)); sheet.paste(im, (Sz * k, Sz * r))
    sheet.save(a.preview); print('preview', a.preview)

if a.preview and not CH:      # a close-up of the face from the front, every pixel textured (so the eyes and the mouth can be checked)
    A = next(x for x in anims if x[0] == 'Idle')[2]; fr = A[0].reshape(-1, 3, 4); Q = skin(list(fr[:NB]))
    hp = Q[np.argmax(Q[:, 0])]; c0 = np.array([0.0, hp[1], hp[2]]); S = 760; img = np.full((S, S, 3), 150, np.uint8); zb = np.full((S, S), -1e9); sc = S / 5.2
    for t, tk in zip(tri, ttex):
        q = Q[t]; n = np.cross(q[1] - q[0], q[2] - q[0])
        if n[0] <= 0: continue
        X = (q[:, 1] - c0[1]) * sc + S / 2; Y = S / 2 - (q[:, 2] - c0[2]) * sc
        x0, x1 = int(max(0, X.min())), int(min(S - 1, X.max() + 1)); y0, y1 = int(max(0, Y.min())), int(min(S - 1, Y.max() + 1))
        if x1 <= x0 or y1 <= y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1)); d = (Y[1] - Y[2]) * (X[0] - X[2]) + (X[2] - X[1]) * (Y[0] - Y[2])
        if abs(d) < 1e-9: continue
        l0 = ((Y[1] - Y[2]) * (gx - X[2]) + (X[2] - X[1]) * (gy - Y[2])) / d; l1 = ((Y[2] - Y[0]) * (gx - X[2]) + (X[0] - X[2]) * (gy - Y[2])) / d; l2 = 1 - l0 - l1
        m = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        if not m.any(): continue
        u = l0 * VU[t[0], 0] + l1 * VU[t[1], 0] + l2 * VU[t[2], 0]; v = l0 * VU[t[0], 1] + l1 * VU[t[1], 1] + l2 * VU[t[2], 1]; px = pxs[tk]
        col = px[((1 - v) % 1.0 * (px.shape[0] - 1)).astype(int), (u % 1.0 * (px.shape[1] - 1)).astype(int)]
        zz = l0 * q[0, 0] + l1 * q[1, 0] + l2 * q[2, 0]; sel = m & (zz > zb[gy, gx]); zb[gy[sel], gx[sel]] = zz[sel]; img[gy[sel], gx[sel]] = col[sel]
    Image.fromarray(img).save(a.preview.replace('.png', '_face.png')); print('face close-up written')
