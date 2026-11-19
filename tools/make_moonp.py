#!/usr/bin/env python3
"""Moon Presence -> moonp1.bin / moonp2.bin ("BBH2", the same layout as amyg.bin) for the Vita.

  python3 make_moonp.py --form 1 --dir "Moon Presence"                        --out moonp1.bin
  python3 make_moonp.py --form 2 --dir "Moon Presence (Second Form)"           --out moonp2.bin   (second form: c5410.obj, still needs c5400_Body_a / c5400_Tail_a pngs next to it)

The PS4 model is one static T-pose with no animation, so this script
  1. shrinks it (vertex clustering, about 7k triangles for the first form, 10k for the second) and the textures to 256 px,
  2. gives it a made-up skeleton: a body, two arms (shoulder + elbow), and a chain of 2-5 bones down every long tail / tendril
     (each tail has its own phase, so they ripple instead of moving together),
  3. makes the animations the Amygdala's boss code (BDA table) already knows by name, so the fight needs no new boss code.
Game space: +X forward, +Y right, Z up, metres.  The model hangs from its torso; its lowest tail tips sit SINK m under the floor (the lake bed hides them).
"""
import argparse, collections, math, os, struct
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('--form', type=int, default=1); ap.add_argument('--dir', required=True); ap.add_argument('--out', default='moonp.bin')
ap.add_argument('--scale', type=float, default=0.5); ap.add_argument('--sink', type=float, default=1.0)
ap.add_argument('--tex', type=int, default=256); ap.add_argument('--preview', default=None)
ap.add_argument('--budget', type=float, default=0.5); ap.add_argument('--pitch', type=float, default=90.0); ap.add_argument('--hover', type=float, default=0.03); ap.add_argument('--legsign', type=float, default=1.0)
a = ap.parse_args()
FORM = a.form; S = a.scale; FPS = 30.0
C = np.array([[0, -1, 0], [-1, 0, 0], [0, 0, 1]], float)      # model (x right-ish, y back, z up) -> game (x forward, y right, z up); a reflection, so the winding is flipped below
D = math.radians; tau = 2 * math.pi; sw = math.sin

# ------------------------------------------------------------------ read, shrink
objf = os.path.join(a.dir, 'c5400.obj' if FORM == 1 else 'c5410.obj')
V = []; VT = []; objs = collections.OrderedDict(); cur = None; mtl_of = {}
for l in open(objf):
    if l.startswith('v '): V.append(l.split()[1:4])
    elif l.startswith('vt '): VT.append(l.split()[1:3])
    elif l.startswith('o '): cur = l.split()[1]; objs[cur] = []
    elif l.startswith('usemtl '): mtl_of[cur] = l.split(None, 1)[1].strip()
    elif l.startswith('f '): objs[cur].append(l.split()[1:])
V = np.array(V, float); VT = np.array(VT, float)
def face_arr(fs):
    out = []
    for f in fs:
        c = [tuple(int(x) if x else 0 for x in t.split('/')[:2]) for t in f]
        for k in range(1, len(c) - 1): out.append((c[0], c[k], c[k + 1]))
    return np.array(out)
def decimate(fa, cell, uvw=10.0):
    p = V[fa[:, :, 0] - 1].reshape(-1, 3); t = VT[fa[:, :, 1] - 1].reshape(-1, 2)
    q = np.floor(np.concatenate([p / cell, t * uvw], 1)).astype(np.int64)
    _, inv, cnt = np.unique(q, axis=0, return_inverse=True, return_counts=True); inv = inv.ravel()
    P = np.zeros((len(cnt), 3)); T = np.zeros((len(cnt), 2)); np.add.at(P, inv, p); np.add.at(T, inv, t); P /= cnt[:, None]; T /= cnt[:, None]
    F = inv.reshape(-1, 3); ok = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2]); F = F[ok]
    _, ui = np.unique(np.sort(F, 1), axis=0, return_index=True); F = F[np.sort(ui)]
    used = np.unique(F); rm = -np.ones(len(P), int); rm[used] = np.arange(len(used)); return P[used], T[used], rm[F]
# which texture each piece wears, and how many triangles it gets
def texname(m):
    if 'Tail' in m: return 'tail'
    if 'Material_#12' in m: return 'body2'
    return 'body'
TEXFILE = {'body': 'c5400_Body_a.png', 'tail': 'c5400_Tail_a.png', 'body2': 'c5410_Body_a.png'}
def budget(name, nfaces):
    if FORM == 1: return {'mesh0': 4000, 'mesh1': 1500, 'mesh2': 1200}.get(name, 400)
    return {'5': 3500, '7': 1200, '6': 1200, '4': 1200, '8': 1200}.get(name[5] if name.startswith('mesh[') else name, 400)
pieces = []      # (name, texkey, P(model), T, F)
for name, fs in objs.items():
    fa = face_arr(fs); tg = int(budget(name, len(fa)) * a.budget); lo, hi = 0.003, 2.0
    for _ in range(20):
        m = (lo * hi) ** .5; P, T, F = decimate(fa, m)
        if len(F) > tg: lo = m
        else: hi = m
    P, T, F = decimate(fa, hi); pieces.append((name, texname(mtl_of.get(name, '')), P, T, F)); print(name, len(fa), '->', len(F), 'triangles')

# ------------------------------------------------------------------ to game space, one vertex array
G = []; UV = []; TRI = []; TX = []; PIECE = []; off = 0
for pi, (name, tk, P, T, F) in enumerate(pieces):
    G.append(P); UV.append(T); TRI.append(F + off); TX += [tk] * len(F); PIECE += [pi] * len(P); off += len(P)
G = np.concatenate(G); UV = np.concatenate(UV); TRI = np.concatenate(TRI); TX = np.array(TX); PIECE = np.array(PIECE)
G = (C @ G.T).T * S
# centre on the torso: the body piece's middle in x/y; the lowest vertex SINK under the floor
body_i = max(range(len(pieces)), key=lambda i: len(pieces[i][4]) if pieces[i][1] == 'body' else 0)
bm = PIECE == body_i; cen = G[bm].mean(axis=0)
G[:, 0] -= cen[0]; G[:, 1] -= cen[1]; G[:, 2] -= G[:, 2].min() - (-a.sink)
bc = np.array([0.0, 0.0, G[bm][:, 2].mean()])      # the torso's centre: the root bone turns about it
print('height %.1f m (floor at z 0, tail tips %.1f m under it), width %.1f m, depth %.1f m, torso centre z %.2f' % (G[:, 2].max(), a.sink, np.ptp(G[:, 1]), np.ptp(G[:, 0]), bc[2]))

# ------------------------------------------------------------------ skeleton: root, 2 arms x 2 bones, chains
names = ['body', 'armL', 'armL2', 'armR', 'armR2']; parent = [-1, 0, 1, 0, 3]; pivot = [bc.copy(), None, None, None, None]
nV = len(G); vb1 = np.zeros(nV, int); vb2 = np.zeros(nV, int); wt = np.full(nV, 255, int)
# arms: the vertices well out to the side at about shoulder height, in the pieces that are not tails/tendrils
zsh = bc[2]
lim = 0.18 * np.ptp(G[:, 1])
armv = (np.abs(G[:, 1]) > 0.9 * S / 0.5) & (G[:, 2] > bc[2] - 1.2) & (G[:, 2] < bc[2] + 1.8)
for pi, (name, tk, P, T, F) in enumerate(pieces):
    if tk == 'tail' or (FORM == 2 and name in ('mesh[4]_mesh[4]_mesh', 'mesh[8]_mesh[8]_mesh')): armv &= PIECE != pi
armv &= PIECE == body_i
ELB, WRI, SHB, BH_ = 0.40, 0.74, 0.10, 0.07      # arm: elbow and wrist as a fraction of its length; the shoulder root; the half-width of the blend at each joint (small: the limb bends AT the joint, not along its length)
WRIST_PIV = {}; WRIST_IDX = {}
for bi_, nm_ in ((1, 'armL3'), (3, 'armR3')): names.append(nm_); parent.append(bi_ + 1); pivot.append(None); WRIST_IDX[bi_] = len(names) - 1
for side, bi in ((-1, 1), (1, 3)):
    m = armv & (np.sign(G[:, 1]) == side)
    if not m.any(): continue
    ys = np.abs(G[m, 1]); sh = ys.min(); tip = ys.max(); L_ = max(tip - sh, 1e-6); el = sh + ELB * L_; wr = sh + WRI * L_
    def _jp(yv):      # a joint sits in the middle of the limb's cross-section at that distance, not on one of its edge vertices
        sel = np.where(m & (np.abs(np.abs(G[:, 1]) - yv) < 0.05 * L_))[0]
        if not len(sel): sel = np.where(m)[0][[np.argmin(np.abs(ys - yv))]]
        c = G[sel].mean(axis=0); return np.array([c[0], side * yv, c[2]])
    pivot[bi] = _jp(sh); pivot[bi + 1] = _jp(el); WRIST_PIV[bi] = _jp(wr)
    for v in np.where(m)[0]:
        y = abs(G[v, 1]); u = (y - sh) / L_
        if u < SHB: vb1[v] = bi; vb2[v] = 0; wt[v] = int(255 * (0.55 + 0.45 * u / SHB))      # only the very root of the arm follows the body
        else:
            seg = 0 if u < ELB else (1 if u < WRI else 2); k1 = seg; w1 = 1.0
            up_b = ELB if seg == 0 else (WRI if seg == 1 else None); dn_b = ELB if seg == 1 else (WRI if seg == 2 else None)
            if up_b is not None and up_b - u < BH_: k1 = seg + 1; w1 = 1.0 - 0.5 * (1.0 - (up_b - u) / BH_)      # 1 deep inside the segment, 0.5 right at the joint
            elif dn_b is not None and u - dn_b < BH_: k1 = seg - 1; w1 = 1.0 - 0.5 * (1.0 - (u - dn_b) / BH_)
            bones_ = (bi, bi + 1, WRIST_IDX[bi]); vb1[v] = bones_[seg]; vb2[v] = bones_[k1]; wt[v] = int(round(255 * w1))
for bi in (1, 3):
    if pivot[bi] is None: pivot[bi] = bc.copy(); pivot[bi + 1] = bc.copy()
    pivot[WRIST_IDX[bi]] = WRIST_PIV.get(bi, pivot[bi + 1].copy())
armtip = {1: None, 3: None}
for side, bi in ((-1, 1), (1, 3)):
    m = armv & (np.sign(G[:, 1]) == side)
    armtip[bi] = G[m][np.argmax(np.abs(G[m, 1]))] if m.any() else bc + np.array([0, side * 2.0, 0])
# legs: the two small folded hind legs under the torso (components of the body piece whose feet reach well forward, low down): hip, knee, foot
def _comps(F, n):
    par = list(range(n))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for t in F: par[f(t[0])] = f(t[1]); par[f(t[1])] = f(t[2])
    return np.array([f(i) for i in range(n)])
legbones = {}      # side (-1 left / +1 right) -> [hip, knee, foot] bone indices
_ids = np.where(PIECE == body_i)[0]; _P = pieces[body_i][2]; _F = pieces[body_i][4]; _cl = _comps(_F, len(_ids))
legv = np.zeros(nV, bool)
for r in set(_cl):
    m = _cl == r
    if m.sum() < 50 or _P[m, 1].min() > 0.9 or _P[m, 2].max() > 1.25: continue
    vs = _ids[m]; sd = -1 if G[vs, 1].mean() < 0 else 1
    legv[vs] = True; legbones.setdefault(sd, [])
    hip = vs[np.argmax(-G[vs, 0])]; u0 = G[hip, 0]; u1 = G[vs, 0].max(); L = max(u1 - u0, 1e-6)      # along the leg by how far forward it reaches: hip -> foot
    KN, AN, LBH = 0.40, 0.76, 0.06      # knee and ankle as a fraction of the leg's reach; the blend at a joint is only +-LBH of it (the leg bends AT the joint)
    for j, uj in enumerate((0.0, KN, AN)):
        if j: sel = vs[np.abs((G[vs, 0] - u0) / L - uj) < 0.05]; c = G[sel].mean(axis=0) if len(sel) else G[vs][np.argmin(np.abs((G[vs, 0] - u0) / L - uj))]
        else: c = G[hip].copy()
        names.append('leg%s%d' % ('L' if sd < 0 else 'R', j)); parent.append(len(names) - 2 if j else 0); pivot.append(c); legbones[sd].append(len(names) - 1)
    for v in vs:
        u = min(max((G[v, 0] - u0) / L, 0.0), 1.0); k0 = 0 if u < KN else (1 if u < AN else 2); k1 = k0; blw = 0.0
        if k0 < 2 and (KN if k0 == 0 else AN) - u < LBH: k1 = k0 + 1; blw = 0.5 * (1.0 - ((KN if k0 == 0 else AN) - u) / LBH)
        elif k0 > 0 and u - (KN if k0 == 1 else AN) < LBH: k1 = k0 - 1; blw = 0.5 * (1.0 - (u - (KN if k0 == 1 else AN)) / LBH)
        b0 = legbones[sd][k0]; b1 = legbones[sd][k1]; vb1[v] = b0; vb2[v] = b1; wt[v] = int(round(255 * (1.0 - blw)))
print('legs found:', {('left' if k < 0 else 'right'): len(v) for k, v in legbones.items()}, 'vertices', int(legv.sum()))
# chains: every long component of a tail / tendril piece
chains = []      # (list of bone indices)
def components(F, n):
    par = list(range(n))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for t in F: par[f(t[0])] = f(t[1]); par[f(t[1])] = f(t[2])
    return np.array([f(i) for i in range(n)])
for pi, (name, tk, P, T, F) in enumerate(pieces):
    if not (tk == 'tail' or (FORM == 2 and name in ('mesh[4]_mesh[4]_mesh', 'mesh[8]_mesh[8]_mesh'))): continue
    ids = np.where(PIECE == pi)[0]; comp = components(F, len(ids))
    for root in sorted(set(comp), key=lambda r: -(comp == r).sum()):
        vs = ids[comp == root]
        if len(vs) < 14: continue
        z = G[vs, 2]; zhi, zlo = z.max(), z.min(); ext = zhi - zlo
        if ext < 0.55: continue
        ns = int(min(5, max(2, round(ext / 0.8)))); bl = []
        for k in range(ns):
            zk = zhi - ext * k / ns; sel = vs[np.abs(G[vs, 2] - zk) < ext / ns * 0.8 + 0.05]
            cxy = G[sel, :2].mean(axis=0) if len(sel) else G[vs, :2].mean(axis=0)
            names.append('ch%d_%d' % (len(chains), k)); parent.append(bl[-1] if bl else 0); pivot.append(np.array([cxy[0], cxy[1], zk])); bl.append(len(names) - 1)
        chains.append(bl)
        for v in vs:
            u = min(max((zhi - G[v, 2]) / ext, 0.0), 0.9999) * ns; k0 = int(u); fr = u - k0; k1 = k0; blw = 0.0; BLO = 0.3
            if fr > 1 - BLO and k0 < ns - 1: k1 = k0 + 1; blw = (fr - (1 - BLO)) / BLO * 0.5
            elif fr < BLO and k0 > 0: k1 = k0 - 1; blw = (BLO - fr) / BLO * 0.5
            vb1[v] = bl[k0]; vb2[v] = bl[k1]; wt[v] = int(round(255 * (1.0 - blw)))
spike_ci = set()      # the head spikes / crown: pieces that reach back behind the head (they used to be rigid): a chain of 2-4 bones along each, so they sway like the video
_taken = np.zeros(nV, bool)
for pi, (name, tk, P, T, F) in enumerate(pieces):
    if pi == body_i or tk == 'tail' or (FORM == 2 and name in ('mesh[4]_mesh[4]_mesh', 'mesh[8]_mesh[8]_mesh')): continue
    ids = np.where(PIECE == pi)[0]; comp = components(F, len(ids))
    for root in sorted(set(comp), key=lambda r: -(comp == r).sum()):
        vs = ids[comp == root]
        if len(vs) < 20 or legv[vs].any(): continue
        xs = G[vs, 0]
        if xs.min() > -0.8 or np.ptp(xs) < 0.7 or G[vs, 2].max() < bc[2] + 0.3: continue
        xr = xs.max(); ext = xr - xs.min(); ns = int(min(4, max(2, round(ext / 0.6)))); bl = []
        for k in range(ns):
            xk = xr - ext * k / ns; sel = vs[np.abs(G[vs, 0] - xk) < ext / ns * 0.8 + 0.05]
            c = G[sel].mean(axis=0) if len(sel) else G[vs].mean(axis=0)
            names.append('ch%d_%d' % (len(chains), k)); parent.append(bl[-1] if bl else 0); pivot.append(np.array([xk, c[1], c[2]])); bl.append(len(names) - 1)
        spike_ci.add(len(chains)); chains.append(bl)
        for v in vs:
            u = min(max((xr - G[v, 0]) / ext, 0.0), 0.9999)
            if u < 0.15: vb1[v] = 0; vb2[v] = bl[0]; wt[v] = int(round(255 * (1.0 - 0.6 * u / 0.15))); continue      # the root stays on the head
            uu = u * ns; k0 = int(uu); fr = uu - k0; k1 = k0; blw = 0.0; BLO = 0.3
            if fr > 1 - BLO and k0 < ns - 1: k1 = k0 + 1; blw = (fr - (1 - BLO)) / BLO * 0.5
            elif fr < BLO and k0 > 0: k1 = k0 - 1; blw = (BLO - fr) / BLO * 0.5
            vb1[v] = bl[k0]; vb2[v] = bl[k1]; wt[v] = int(round(255 * (1.0 - blw)))
print('spike chains', len(spike_ci))
NB = len(names); print('bones', NB, 'chains', len(chains), [len(c) for c in chains])
assert NB < 120
head_pt = G[PIECE == body_i][np.argmax(G[PIECE == body_i][:, 2])] if True else bc
att_pts = [(WRIST_IDX[3], armtip[3]), (WRIST_IDX[1], armtip[1]), (0, head_pt), (0, bc)]      # hand_r, hand_l, head, spine_2
# the model hangs from its torso with its tails straight down; he is turned forward by --pitch degrees (90: head forward, tails trailing behind him) and floats HOVER m over the water
_th = math.radians(a.pitch); Rt = np.array([[math.cos(_th), 0, math.sin(_th)], [0, 1, 0], [-math.sin(_th), 0, math.cos(_th)]])
_bc0 = bc.copy()
def _tr(p): return Rt @ (np.array(p) - _bc0) + _bc0
G = (G - _bc0) @ Rt.T + _bc0
pivot = [_tr(p) for p in pivot]; att_pts = [(b, _tr(p)) for b, p in att_pts]; head_pt = _tr(head_pt); armtip = {k: _tr(v) for k, v in armtip.items()}
_dz = a.hover - G[legv, 2].min(); G[:, 2] += _dz      # the feet are on the floor
pivot = [p + np.array([0, 0, _dz]) for p in pivot]; att_pts = [(b, p + np.array([0, 0, _dz])) for b, p in att_pts]; bc = _bc0 + np.array([0, 0, _dz])
AX1 = Rt @ np.array([1.0, 0, 0]); AX2 = Rt @ np.array([0, 1.0, 0])      # the chains bend about these (what used to be sideways and fore-aft when they hung)
print('turned %.0f degrees: length %.1f m, height %.1f m; feet at %.2f m, lowest part of anything else %.2f m' % (a.pitch, np.ptp(G[:, 0]), np.ptp(G[:, 2]), G[legv, 2].min(), G[~legv, 2].min()))

# ------------------------------------------------------------------ poses
def rot_axis(axis, ang):
    ax = np.array(axis, float); ax /= np.linalg.norm(ax) + 1e-9; c, s = math.cos(ang), math.sin(ang); x, y, z = ax
    return np.array([[c + x*x*(1-c), x*y*(1-c) - z*s, x*z*(1-c) + y*s], [y*x*(1-c) + z*s, c + y*y*(1-c), y*z*(1-c) - x*s], [z*x*(1-c) - y*s, z*y*(1-c) + x*s, c + z*z*(1-c)]])
def about(R, p, t=(0, 0, 0)):
    M = np.zeros((3, 4)); M[:, :3] = R; M[:, 3] = np.array(p) - R @ np.array(p) + np.array(t); return M
def mul(A, B):
    M = np.zeros((3, 4)); M[:, :3] = A[:, :3] @ B[:, :3]; M[:, 3] = A[:, :3] @ B[:, 3] + A[:, 3]; return M
def smooth(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def pulse(t, a0, b0, c0):
    if t <= a0 or t >= c0: return 0.0
    return smooth((t - a0) / (b0 - a0)) if t < b0 else 1.0 - smooth((t - b0) / (c0 - b0))
def build(pose):
    bx, by, bz = pose.get('bx', 0.0), pose.get('by', 0.0), pose.get('bz', 0.0)
    Rb = rot_axis([0, 1, 0], pose.get('pitch', 0.0)) @ rot_axis([1, 0, 0], pose.get('roll', 0.0))
    mats = [None] * NB
    mats[0] = mul(about(rot_axis([0, 0, 1], pose.get('yaw', 0.0)), (0, 0, 0)), about(Rb, bc, (bx, by, bz)))
    for sg, bi, nm in ((-1, 1, 'armL'), (1, 3, 'armR')):
        lift = pose.get(nm + '_l', 0.0); fwd = pose.get(nm + '_s', 0.0)
        R = rot_axis([0, 0, 1], -sg * fwd) @ rot_axis([1, 0, 0], sg * lift)
        mats[bi] = mul(mats[0], about(R, pivot[bi]))
        R2 = rot_axis([0, 0, 1], -sg * pose.get(nm + '2_s', 0.4 * fwd)) @ rot_axis([1, 0, 0], sg * pose.get(nm + '2_l', 0.4 * lift))
        mats[bi + 1] = mul(mats[bi], about(R2, pivot[bi + 1]))
        e_s = pose.get(nm + '2_s', 0.4 * fwd); e_l = pose.get(nm + '2_l', 0.4 * lift)      # the wrist: the hand trails the forearm (curls the same way, about half as far), so the claw flicks at the end of a swing
        R3 = rot_axis([0, 0, 1], -sg * pose.get(nm + '3_s', 0.55 * e_s)) @ rot_axis([1, 0, 0], sg * pose.get(nm + '3_l', 0.55 * e_l))
        mats[WRIST_IDX[bi]] = mul(mats[bi + 1], about(R3, pivot[WRIST_IDX[bi]]))
    for sd, bl in legbones.items():
        nm = 'legL' if sd < 0 else 'legR'; cur = mats[0]
        for j, b in enumerate(bl):
            cur = mul(cur, about(rot_axis([0, 1, 0], pose.get(nm + str(j), 0.0)), pivot[b])); mats[b] = cur
    fa = pose.get('fa', 1.0); ph = pose.get('ph', 0.0); lash = pose.get('lash', 0.0); fl = pose.get('flare', 0.0)
    for ci, bl in enumerate(chains):
        cp = ci * 1.7; cur = mats[0]
        for k, b in enumerate(bl):
            amp = fa * (0.07 + 0.045 * k) * (2.4 if ci in spike_ci else 1.0); lag = ph - 0.8 * k + cp
            ax = amp * sw(lag) + lash * D(14) * sw(lag * 1.5 - 1.0) * (k + 1) / len(bl) + fl * D(9) * (1 if (ci % 2) else -1) * (k + 1) / len(bl)
            ay = pose.get('tail_up', D(9)) + amp * 0.8 * sw(lag + 1.3) + lash * D(22) * (k + 1) / len(bl) * pose.get('lash_dir', 1.0)
            R = rot_axis(AX1, ax) @ rot_axis(AX2, ay)
            cur = mul(cur, about(R, pivot[b])); mats[b] = cur
    return mats
def frame(pose):
    mats = build(pose); out = list(mats)
    for bi, p in att_pts:
        M = mats[bi].copy(); M[:, 3] = mats[bi][:, :3] @ p + mats[bi][:, 3]; out.append(M)
    return np.concatenate([m.reshape(12) for m in out]).astype('<f4')
def anim(name, dur, fn, loop=False, travel=(0.0, 0.0)):
    n = max(2, int(round(dur * FPS)))
    return (name, FPS, np.array([frame(fn(i / (n - 1) if not loop else i / n)) for i in range(n)], '<f4'), travel)
anims = []
def legs(o, ph, amp=0.0, knee=0.0, crouch=0.0):      # both hind legs: hip swing, knee bend, foot; the right leg is half a cycle behind the left
    for sd, nm, off in ((-1, 'legL', 0.0), (1, 'legR', 0.5)):
        q = tau * (ph + off); sg = a.legsign
        o[nm + '0'] = sg * (amp * sw(q) + D(10) * crouch); o[nm + '1'] = sg * (knee * max(0.0, sw(q + 1.2)) - D(18) * crouch); o[nm + '2'] = sg * (-0.5 * amp * sw(q) + D(8) * crouch)
    return o
def base(t, cyc=1, fa=1.0, bob=0.14):      # the always-on float: a slow bob, a little roll, and every tail rippling
    ph = tau * t * cyc
    return {'bz': bob * sw(ph), 'roll': D(2.0) * sw(ph + 0.6), 'pitch': D(1.5) * sw(ph), 'fa': fa, 'ph': ph * 2,
            'armL_l': D(8) * sw(ph + 0.3), 'armR_l': D(8) * sw(ph + 1.9), 'armL_s': D(4) * sw(ph), 'armR_s': D(4) * sw(ph + 1.0)}
# anim_v2: every move is built from the same three beats, like a hand-made one: a wind-up the other way (so you can read it coming), a fast strike that overshoots, a slow recovery.
# The hind legs work in every move (they crouch for the wind-up and push off for the strike), the body throws its weight in, and the tails and head spikes lash after it.
def strike(t, a0, b0, c0, d0):      # (wind-up 0..1 between a0 and b0, gone by c0;  hit 0..1 between b0 and c0 fast-out with a little overshoot, held, then eased away by d0)
    wind = smooth((t - a0) / (b0 - a0)) * (1.0 - smooth((t - b0) / (c0 - b0)))
    x = (t - b0) / (c0 - b0)
    if x <= 0.0: return wind, 0.0
    up = 1.0 - (1.0 - min(x, 1.0)) ** 3; over = 0.14 * math.sin(math.pi * min(max((t - b0) / ((c0 - b0) * 2.2), 0.0), 1.0))
    hold = c0 + 0.3 * (d0 - c0)
    return wind, (up + over) * (1.0 - smooth((t - hold) / (d0 - hold)))
def add(o, k, v): o[k] = o.get(k, 0.0) + v
def idle(t):
    ph = tau * t; o = base(t, 1, 1.0, 0.12)
    o['yaw'] = D(3.0) * sw(ph); o['by'] = 0.06 * sw(ph + 0.9); o['roll'] = D(2.5) * sw(ph + 0.6) + D(1.0) * sw(2 * ph)      # he shifts his weight from side to side and looks about
    o['armL_s'] = D(5) * sw(ph + 0.4); o['armR_s'] = D(5) * sw(ph + 2.6); o['armL2_s'] = D(6) * sw(2 * ph); o['armR2_s'] = D(6) * sw(2 * ph + 1.4)      # the claws flex
    o['tail_up'] = D(9) + D(4) * sw(ph + 2.0); o['flare'] = 0.5 * sw(2 * ph + 0.5); o['fa'] = 1.0 + 0.35 * sw(ph)
    return legs(o, t, D(2.5), D(3.0), 0.25 + 0.2 * sw(ph + 1.2))
anims.append(anim('Idle', 3.2, idle, loop=True))
def gait(ph):      # one limb, 60 % of the cycle planted and 40 % in the air. Planted: it sweeps back at a steady pace (it grips the ground). In the air: a curve that leaves and arrives at exactly that pace, so nothing jerks at the changeover.  -> (sweep +1 front .. -1 back, lift 0..1, fold 0..1)
    ph %= 1.0
    if ph < 0.6: return 1.0 - 2.0 * ph / 0.6, 0.0, 0.0
    u = (ph - 0.6) / 0.4; m = -2.0 / 0.6 * 0.4
    sweep = (2 * u**3 - 3 * u**2 + 1) * -1.0 + (u**3 - 2 * u**2 + u) * m + (-2 * u**3 + 3 * u**2) * 1.0 + (u**3 - u**2) * m
    return sweep, math.sin(math.pi * u) ** 1.3, math.sin(math.pi * min(1.0, u * 1.2)) ** 1.1
def _limb_x(pose, b): M = build(pose)[b]; return float((M[:, :3] @ pivot[b] + M[:, 3])[0])
HSG = {}      # which way each hip has to turn for the foot to go FORWARD (measured on the posed skeleton, so the feet can never walk backwards)
for sd_, bl_ in legbones.items():
    nm_ = 'legL' if sd_ < 0 else 'legR'; HSG[nm_] = 1.0 if _limb_x({nm_ + '0': 0.3}, bl_[2]) > _limb_x({}, bl_[2]) else -1.0
ASG = {}      # the same for the arms' forward swing
for nm_, b_ in (('armL', 2), ('armR', 4)): ASG[nm_] = 1.0 if _limb_x({nm_ + '_s': 0.3, nm_ + '2_s': 0.0}, b_) > _limb_x({nm_ + '_s': 0.0, nm_ + '2_s': 0.0}, b_) else -1.0
print('walk: forward signs, hips', HSG, 'arms', ASG)
def walk_fn(lean, bob, low, stride, armlift, sway, tails):
    def walk(t):      # he goes on all fours like a hunting animal: opposite corners step together (left arm with right leg), every limb plants, pulls back along the ground and is lifted forward; the body dips as each pair lands, the shoulders turn towards the reaching arm, the hips the other way, and the tails and head spikes trail the turn a moment late
        ph = tau * t; o = base(t, 2, 1.0 + tails, 0.0)
        o['bz'] = -low + bob * (-math.cos(2 * ph - 0.7)) + 0.03 * math.cos(4 * ph); o['pitch'] = D(lean) + D(2.5) * sw(2 * ph + 0.4)
        o['yaw'] = D(sway) * math.cos(ph - 0.8 * tau); o['roll'] = D(0.6 * sway) * sw(ph - 0.8 * tau); o['by'] = 0.07 * sw(ph + 0.3); o['bx'] = 0.05 * sw(2 * ph + 0.9)
        for nm, p0 in (('armL', 0.0), ('armR', 0.5)):
            sweep, lift, fold = gait(t + p0); sweep2, lift2, _ = gait(t + p0 - 0.06)      # (the forearm follows the upper arm a moment late)
            o[nm + '_s'] = D(20) + ASG[nm] * D(stride) * sweep; o[nm + '_l'] = D(-14) + D(armlift) * lift; o[nm + '2_l'] = D(0.7 * armlift) * lift2
            o[nm + '2_s'] = ASG[nm] * (D(0.12 * stride) * sweep2 + D(0.9 * stride) * fold + D(8) * (1.0 - lift)); o[nm + '3_s'] = -0.55 * o[nm + '2_s'] + ASG[nm] * D(0.25 * stride) * lift      # a hinge at the elbow: it folds as the claw is lifted and is straight when planted; the wrist bends back the other way so the claw lands flat
        for nm, p0 in (('legR', 0.0), ('legL', 0.5)):
            if nm not in HSG: continue
            sweep, lift, fold = gait(t + p0); sg = a.legsign
            o[nm + '0'] = HSG[nm] * D(0.9 * stride) * sweep + sg * D(4); o[nm + '1'] = sg * (D(1.7 * stride) * fold + D(6) * (1.0 - lift)); o[nm + '2'] = -0.55 * o[nm + '1'] - HSG[nm] * D(0.3 * stride) * sweep + sg * D(8) * lift
        o['lash'] = 0.55 * tails * sw(ph - 0.8 * tau - 1.1); o['lash_dir'] = 1.0; o['flare'] = 0.4 + 0.5 * tails * sw(2 * ph - 1.0); o['tail_up'] = D(9) + D(3) * sw(2 * ph - 1.6)
        return o
    return walk
anims.append(anim('WalkFast', 1.2, walk_fn(11.0, 0.13, 0.05, 30.0, 26.0, 7.0, 1.0), loop=True, travel=(4.2, 0.0)))      # a loping run: long reach, leaning into it
anims.append(anim('Walk', 1.6, walk_fn(6.0, 0.07, 0.16, 20.0, 34.0, 4.5, 0.5), loop=True, travel=(2.6, 0.0)))      # a slow stalk: low to the ground, each claw lifted high and placed
def hurt(kind):      # a snap away from the blow, then a slower sway back through the middle
    def f(t):
        h = smooth(t / 0.07) * (1.0 - smooth((t - 0.12) / 0.5)); rb = pulse(t, 0.4, 0.58, 0.9); o = base(t, 1, 1.0 + 2.5 * h, 0.1)
        add(o, 'pitch', D(-18) * h + D(5) * rb); o['bx'] = -0.35 * h + 0.08 * rb; add(o, 'roll', D(10) * h * kind[0] - D(3) * rb * kind[0]); o['yaw'] = D(9) * h * kind[0] - D(3) * rb * kind[0]
        o['armL_l'] = D(30) * h * (1 if kind[1] <= 0 else 0.3); o['armR_l'] = D(30) * h * (1 if kind[1] >= 0 else 0.3); o['armL2_l'] = D(18) * h; o['armR2_l'] = D(18) * h; o['flare'] = 2.5 * h - 0.8 * rb
        return legs(o, 0.0, 0.0, 0.0, 0.9 * h + 0.2 * rb)
    return f
for nm, kind in (('ArmLDmg1', (-1, -1)), ('ArmRDmg1', (1, 1)), ('HeadDmg1', (0, 0)), ('LegDmgL', (-1, 0)), ('LegDmgR', (1, 0))): anims.append(anim(nm, 0.9, hurt(kind)))
def stagger(t):      # his arms give way and his head drops to the ground, heaving
    h = smooth(t / 0.12) * (1 - smooth((t - 0.8) / 0.2)); drop = smooth(t / 0.12); o = base(t, 3, 1.0, 0.05)
    o['pitch'] = D(-10) * pulse(t, 0.0, 0.06, 0.16) + D(20) * h; o['bz'] = -0.45 * h + 0.05 * sw(tau * t * 3) * h; o['bx'] = 0.15 * h
    o['armL_l'] = D(-55) * h; o['armR_l'] = D(-55) * h; o['armL2_l'] = D(-35) * h; o['armR2_l'] = D(-35) * h; o['armL_s'] = D(18) * h; o['armR_s'] = D(18) * h
    o['fa'] = 0.4; o['flare'] = -1.5 * h; o['roll'] = D(4) * sw(tau * t * 2) * h * drop
    return legs(o, 0.0, 0.0, 0.0, 1.4 * h)
anims.append(anim('CounteredStart', 1.6, stagger))
def visc(t):      # wrenched upward by the hand in his chest, shuddering, then thrown back down
    h = smooth(t / 0.1) * (1 - smooth((t - 0.85) / 0.15)); rip = pulse(t, 0.5, 0.58, 0.8); o = base(t, 1, 1.0, 0.05)
    o['pitch'] = D(-24) * h + D(40) * rip; o['bz'] = 0.35 * h - 0.7 * rip; o['bx'] = -0.5 * rip; o['roll'] = D(5) * sw(tau * t * 13) * h * (1 - rip)
    o['armL_l'] = D(60) * h - D(90) * rip; o['armR_l'] = D(60) * h - D(90) * rip; o['armL_s'] = D(-30) * h; o['armR_s'] = D(-30) * h; o['fa'] = 0.3 + 3 * pulse(t, 0.2, 0.5, 0.7); o['flare'] = 3 * h
    return legs(o, 0.0, 0.0, 0.0, -0.5 * h + 1.6 * rip)
anims.append(anim('Visceral', 2.4, visc))
def death(t):      # he rears and thrashes, the thrashing weakens, then he folds forward and slides under the water
    thr = smooth(t / 0.06) * (1.0 - smooth((t - 0.3) / 0.25)); k = smooth((t - 0.35) / 0.3); o = base(t, 1, 1.0 + 3 * thr, 0.0)
    o['pitch'] = D(-22) * thr + D(34) * k; o['roll'] = D(9) * sw(tau * t * 7) * thr + D(14) * k; o['yaw'] = D(12) * sw(tau * t * 5 + 1.0) * thr
    o['armL_l'] = D(70) * thr * (0.6 + 0.4 * sw(tau * t * 6)) - D(70) * k; o['armR_l'] = D(70) * thr * (0.6 + 0.4 * sw(tau * t * 6 + 2.0)) - D(70) * k; o['armL_s'] = D(30) * sw(tau * t * 5) * thr; o['armR_s'] = D(30) * sw(tau * t * 5 + 2.2) * thr
    o['flare'] = 4 * thr; o['fa'] = 1.0 + 3 * thr + 1.5 * (1 - smooth(t)); o['lash'] = 1.5 * thr
    o['bz'] = 0.4 * thr - (bc[2] + 1.2) * smooth((t - 0.45) / 0.55)
    return legs(o, 0.0, 0.0, 0.0, 1.5 * k)
anims.append(anim('Death', 4.0, death))
def beam(t):      # he draws himself up, the light gathers while he shudders, the head snaps forward as it fires, and he sags afterwards
    up = smooth(t / 0.18) * (1.0 - smooth((t - 0.8) / 0.2)); chg = pulse(t, 0.16, 0.36, 0.42); fire = smooth((t - 0.38) / 0.04) * (1.0 - smooth((t - 0.7) / 0.12)); sag = pulse(t, 0.72, 0.84, 1.0); o = base(t, 1, 1.0, 0.1)
    o['pitch'] = D(-22) * up - D(10) * chg + D(20) * fire + D(8) * sag; o['bz'] = 0.5 * up - 0.2 * sag; o['bx'] = -0.25 * chg + 0.3 * fire
    for nm in ('armL', 'armR'): o[nm + '_l'] = D(60) * up + D(18) * chg - D(15) * sag; o[nm + '_s'] = D(35) * (up - 0.4 * chg) + D(22) * fire; o[nm + '2_l'] = D(-15) * up
    o['fa'] = 1.0 + 2.5 * chg + 1.0 * fire; o['flare'] = 2.5 * up + 1.5 * fire; o['roll'] = D(3) * sw(tau * t * 11) * (chg + 0.5 * fire)
    return legs(o, 0.0, 0.0, 0.0, 0.8 * chg - 0.5 * fire + 0.6 * sag)
anims.append(anim('ArcaneBeam', 3.4, beam))
def claw(t):      # four swipes, left and right in turn; each one is drawn back, thrown, and the body twists and steps in behind it
    o = base(t, 1, 1.5, 0.08); tw = 0.0; cr = 0.0; adv = 0.0
    for i in range(4):
        s0 = 0.06 + 0.2 * i; w, h = strike(t, s0, s0 + 0.075, s0 + 0.125, s0 + 0.3); sd = 1 if i % 2 == 0 else -1; nm = 'armR' if sd > 0 else 'armL'
        add(o, nm + '_l', D(78) * w - D(26) * h); add(o, nm + '_s', D(-28) * w + D(92) * h); add(o, nm + '2_s', D(-10) * w + D(34) * h); add(o, nm + '2_l', D(20) * w)
        tw += sd * (-D(12) * w + D(16) * h); cr += 0.7 * w - 0.3 * h; adv += h
    o['yaw'] = tw; add(o, 'roll', -0.5 * tw); add(o, 'pitch', D(8) + D(6) * min(adv, 1.0)); o['bx'] = 0.22 * min(adv, 1.2); o['flare'] = 1.0 + 1.2 * min(adv, 1.0)
    return legs(o, t * 2, D(6), D(10), cr)
anims.append(anim('ClawFlurry', 2.4, claw))
def whip(t):      # he coils away, then the whole body whips round and the tails crack across in front of him
    w, h = strike(t, 0.04, 0.3, 0.44, 0.9); o = base(t, 1, 1.0, 0.08)
    o['yaw'] = D(-55) * w + D(105) * h; o['roll'] = D(10) * w - D(14) * h; o['bz'] = -0.25 * w + 0.1 * h; o['bx'] = -0.2 * w + 0.35 * h
    o['armR_l'] = D(70) * w + D(20) * h; o['armR_s'] = D(-55) * w + D(120) * h; o['armR2_s'] = D(35) * h; o['armL_l'] = D(35) * w; o['armL_s'] = D(20) * w - D(15) * h
    o['lash'] = 0.8 * w + 3.4 * h; o['lash_dir'] = 1.0; o['fa'] = 1.0 + 2.2 * (w + h); o['flare'] = 2.0 * h
    return legs(o, 0.0, 0.0, 0.0, 1.0 * w - 0.4 * h)
anims.append(anim('WhipLash', 2.4, whip))
def spin(t):      # a short turn the wrong way, then a full spin low to the ground with everything flung out, and a skid to a stop
    w = pulse(t, 0.03, 0.17, 0.26); go = smooth((t - 0.2) / 0.42); env = smooth((t - 0.16) / 0.1) * (1 - smooth((t - 0.62) / 0.2)); skid = pulse(t, 0.6, 0.68, 0.92); o = base(t, 1, 1.0, 0.08)
    o['yaw'] = -D(28) * w + tau * go + D(14) * skid; o['roll'] = D(8) * w - D(13) * env + D(5) * skid; o['bz'] = -0.3 * env - 0.15 * w; o['pitch'] = D(6) * env
    o['armL_l'] = D(12) * env + D(25) * w; o['armR_l'] = D(12) * env + D(25) * w; o['armL_s'] = D(-20) * w + D(62) * env; o['armR_s'] = D(-20) * w + D(62) * env; o['armL2_s'] = D(20) * env; o['armR2_s'] = D(20) * env
    o['flare'] = 4.0 * env; o['fa'] = 1.0 + 2.2 * env; o['lash'] = 2.0 * env
    return legs(o, 0.0, 0.0, 0.0, 0.9 * w + 0.7 * env + 0.5 * skid)
anims.append(anim('SpinSweep', 3.0, spin))
def rear(t):      # up on the hind legs, both arms high and held a beat, then the whole of him comes down
    w, h = strike(t, 0.0, 0.4, 0.5, 0.95); o = base(t, 1, 1.0, 0.08)
    o['pitch'] = D(-30) * w + D(26) * h; o['bz'] = 0.9 * w - 0.4 * h; o['bx'] = -0.45 * w + 0.6 * h
    for nm in ('armL', 'armR'): o[nm + '_l'] = D(100) * w - D(30) * h; o[nm + '_s'] = D(-35) * w + D(100) * h; o[nm + '2_s'] = D(12) * w + D(32) * h; o[nm + '2_l'] = D(25) * w
    o['fa'] = 1.0 + 1.0 * w + 2.5 * h; o['flare'] = 1.5 * w + 2.5 * h; o['tail_up'] = D(9) - D(10) * w + D(6) * h; o['roll'] = D(2) * sw(tau * t * 9) * w
    return legs(o, 0.0, 0.0, 0.0, -0.9 * w + 1.3 * h)
anims.append(anim('RearUpSlam', 2.8, rear))
def palm(t):      # the right arm is hauled up and back over the shoulder, then driven into the ground with the shoulder behind it
    w, h = strike(t, 0.02, 0.4, 0.5, 0.92); o = base(t, 1, 1.0, 0.08)
    o['armR_l'] = D(115) * w - D(22) * h; o['armR_s'] = D(-30) * w + D(112) * h; o['armR2_s'] = D(34) * h; o['armR2_l'] = D(30) * w; o['armL_l'] = D(-10) * w - D(15) * h; o['armL_s'] = D(15) * w
    o['pitch'] = D(-10) * w + D(20) * h; o['roll'] = D(-9) * w + D(8) * h; o['yaw'] = D(-14) * w + D(16) * h; o['bx'] = -0.2 * w + 0.4 * h; o['bz'] = 0.2 * w - 0.25 * h; o['fa'] = 1.0 + 2 * h; o['flare'] = 1.8 * h
    return legs(o, 0.0, 0.0, 0.0, 0.5 * w + 0.9 * h)
anims.append(anim('PalmSlam', 2.4, palm))
def wide(t):      # both arms drawn far to one side, then raked across the whole front of him; the body follows through past the middle
    w, h = strike(t, 0.03, 0.3, 0.48, 0.92); o = base(t, 1, 1.0, 0.08)
    o['yaw'] = D(-62) * w + D(66) * h; o['roll'] = D(8) * w - D(10) * h; o['bz'] = -0.22 * (w + h); o['bx'] = -0.15 * w + 0.3 * h; o['pitch'] = D(7) * (w + h)
    o['armL_s'] = D(55) * w + D(78) * h; o['armR_s'] = D(55) * w + D(78) * h; o['armL_l'] = D(14) * (w + h); o['armR_l'] = D(14) * (w + h); o['armL2_s'] = D(26) * h; o['armR2_s'] = D(26) * h
    o['flare'] = 1.2 * w + 3.0 * h; o['fa'] = 1.0 + 1.8 * (w + h); o['lash'] = 1.2 * h; o['lash_dir'] = -1.0
    return legs(o, 0.0, 0.0, 0.0, 0.9 * w + 0.4 * h)
anims.append(anim('WideSweep', 2.8, wide))
def hop(t):      # crouch, kick off, sail back with the arms trailing, land in a crouch
    cr = pulse(t, 0.0, 0.14, 0.24); x = min(max((t - 0.18) / 0.5, 0.0), 1.0); air = 4 * x * (1 - x); land = pulse(t, 0.64, 0.72, 0.95); o = base(t, 1, 1.5, 0.05)
    o['bz'] = -0.3 * cr + 1.0 * air - 0.3 * land; o['pitch'] = D(8) * cr - D(16) * air + D(10) * land; o['armL_l'] = D(45) * air - D(15) * land; o['armR_l'] = D(45) * air - D(15) * land; o['armL_s'] = D(30) * air; o['armR_s'] = D(30) * air
    o['flare'] = 2.2 * air; o['tail_up'] = D(9) + D(10) * air
    return legs(o, 0.0, 0.0, 0.0, 1.3 * cr - 0.8 * air + 1.2 * land)
anims.append(anim('BackHop', 1.4, hop, travel=(-5.0, 0.0)))
def jump(t):      # the dive: a deep crouch, a high arc with both arms raised over his head, and he lands on them
    cr = pulse(t, 0.0, 0.16, 0.26); x = min(max((t - 0.2) / 0.36, 0.0), 1.0); air = 4 * x * (1 - x); w = smooth((t - 0.2) / 0.2) * (1 - smooth((t - 0.5) / 0.07)); sl = smooth((t - 0.5) / 0.07) * (1 - smooth((t - 0.72) / 0.26)); o = base(t, 1, 1.0, 0.05)
    o['bz'] = -0.35 * cr + 1.7 * air - 0.4 * sl; o['pitch'] = D(10) * cr - D(20) * w + D(30) * sl; o['bx'] = 0.3 * sl
    for nm in ('armL', 'armR'): o[nm + '_l'] = D(95) * w - D(28) * sl; o[nm + '_s'] = D(-20) * w + D(105) * sl; o[nm + '2_s'] = D(30) * sl
    o['fa'] = 1.0 + 2.5 * sl; o['flare'] = 2.2 * air + 2.0 * sl; o['tail_up'] = D(9) + D(12) * air - D(5) * sl
    return legs(o, 0.0, 0.0, 0.0, 1.4 * cr - 0.9 * air + 1.5 * sl)
anims.append(anim('JumpSlam', 2.4, jump, travel=(6.0, 0.0)))
def scream(t):      # he gathers himself low, then rears with arms and tails thrown wide and shakes with the roar
    gather = pulse(t, 0.0, 0.1, 0.2); env = smooth((t - 0.1) / 0.1) * (1 - smooth((t - 0.82) / 0.18)); o = base(t, 1, 1.0 + 2.5 * env, 0.08)
    o['pitch'] = D(10) * gather - D(22) * env; o['bz'] = -0.25 * gather + 0.55 * env; o['bx'] = -0.2 * env
    o['armL_s'] = D(-15) * gather + D(45) * env; o['armR_s'] = D(-15) * gather + D(45) * env; o['armL_l'] = D(75) * env; o['armR_l'] = D(75) * env; o['armL2_l'] = D(20) * env; o['armR2_l'] = D(20) * env
    o['flare'] = 4.5 * env; o['roll'] = D(3.5) * sw(tau * t * 12) * env; o['yaw'] = D(2.5) * sw(tau * t * 9 + 1.0) * env; o['tail_up'] = D(9) + D(12) * env
    return legs(o, 0.0, 0.0, 0.0, 1.0 * gather - 0.7 * env)
anims.append(anim('Scream1', 3.0, scream))

# ------------------------------------------------------------------ textures and the file
def load_tex(key):
    im = Image.open(os.path.join(a.dir, TEXFILE[key])).convert('RGBA')
    sz = (a.tex, a.tex // 2) if key == 'tail' else (a.tex, a.tex)
    return im.resize(sz, Image.LANCZOS)
tkeys = [k for k in ('body', 'tail', 'body2') if k in set(TX.tolist())]
texs = []
for k in tkeys:
    if not os.path.exists(os.path.join(a.dir, TEXFILE[k])): raise SystemExit('missing ' + TEXFILE[k] + ' in ' + a.dir + ' (copy it next to the obj)')
    texs.append(('MoonP_' + k, load_tex(k)))
# triangles grouped by texture -> one section each
idx = []; secs = []
for ti, k in enumerate(tkeys):
    sel = TRI[TX == k]; st = len(idx)
    for t in sel: idx += [int(t[0]), int(t[2]), int(t[1])]      # the reflection flips the winding
    secs.append((st, len(idx) - st, ti, 0))
verts = np.zeros(nV, dtype=[('p', '<3f4'), ('uv', '<2f4'), ('b', 'u1', 4)])
for i in range(nV): verts['p'][i] = G[i]; verts['uv'][i] = (UV[i][0], 1.0 - UV[i][1]); verts['b'][i] = (vb1[i], vb2[i], wt[i], 0)
out = bytearray(b'BBH2')
out += struct.pack('<7I', nV, len(idx), NB, len(anims), len(att_pts), len(secs), len(texs))
for nm, im in texs:
    nb = nm.encode(); out += struct.pack('<B', len(nb)) + nb + struct.pack('<HH', *im.size) + im.tobytes()
for s in secs: out += struct.pack('<IIHH', *s)
out += verts.tobytes(); out += np.array(idx, '<u2').tobytes()
for n in ('hand_r', 'hand_l', 'head', 'spine_2'): out += n.encode().ljust(16, b'\0')
for nm, fps, fr, tv in anims: out += nm.encode()[:32].ljust(32, b'\0') + struct.pack('<fIff', fps, len(fr), tv[0], tv[1]) + fr.tobytes()
# limb_map: which limb every bone belongs to (0 body, 1 right arm, 2 left arm, 3 legs, 4+ one number per tail) and how far along that limb it sits; the game uses it for limb breaking and for the arm's hit box. Older builds of the game ignore this block
lcode = [0] * NB; lfrac = [0] * NB
for k_, b_ in enumerate((3, 4, WRIST_IDX[3])): lcode[b_] = 1; lfrac[b_] = (128, 192, 255)[k_]
for k_, b_ in enumerate((1, 2, WRIST_IDX[1])): lcode[b_] = 2; lfrac[b_] = (128, 192, 255)[k_]
for bl_ in (legbones.values() if isinstance(legbones, dict) else legbones):
    for k_, b_ in enumerate(bl_): lcode[b_] = 3; lfrac[b_] = int(255 * (k_ + 1) / len(bl_))
tc_ = 0
for ci_, bl_ in enumerate(chains):
    if ci_ in spike_ci: continue
    for k_, b_ in enumerate(bl_): lcode[b_] = min(4 + tc_, 250); lfrac[b_] = int(255 * (k_ + 1) / len(bl_))
    tc_ += 1
out += b'LMB1' + struct.pack('<I', NB) + bytes(lcode) + bytes(lfrac); print('limb map: %d tails, %d leg bones' % (tc_, sum(1 for c_ in lcode if c_ == 3)))
open(a.out, 'wb').write(out)
print('wrote %s: %d KB (%d verts, %d tris, %d bones, %d anims)' % (a.out, len(out) // 1024, nV, len(idx) // 3, NB, len(anims)))

# ------------------------------------------------------------------ optional preview: a few poses, skinned on the CPU
if a.preview:
    TXI = {k: np.asarray(texs[i][1]).astype(float) for i, k in enumerate(tkeys)}
    def skin(fr):
        M = fr.reshape(-1, 12)[:NB].reshape(NB, 3, 4); h = np.concatenate([G, np.ones((nV, 1))], 1)
        p1 = np.einsum('vij,vj->vi', M[vb1], h); p2 = np.einsum('vij,vj->vi', M[vb2], h); w = (wt / 255.0)[:, None]
        return p1 * w + p2 * (1 - w)
    def render(P, yaw, S_=380, zoom=1.0):
        img = np.zeros((S_, S_, 3), np.uint8); img[:] = (16, 18, 34); zb = np.full((S_, S_), 1e9)
        cy_, sy_ = math.cos(yaw), math.sin(yaw); R = np.array([[cy_, -sy_, 0], [sy_, cy_, 0], [0, 0, 1]]); Q = P @ R.T
        zc = 2.6; sc = S_ * 0.9 / 9.0 * float(os.environ.get('MOON_ZOOM', '1')) * 1.5; ox_, oz_ = [float(x) for x in os.environ.get('MOON_OFF', '0 0').split()]
        for ti, t in enumerate(TRI):
            k = TX[ti]; tx = TXI[k]; th, tw = tx.shape[:2]; a_, b_, c_ = Q[t]
            X = (np.array([a_[0] * 0.0 + a_[1], b_[1], c_[1]]) - ox_) * sc + S_ / 2; Y = S_ - 110 - (np.array([a_[2], b_[2], c_[2]]) - oz_) * sc; Z = np.array([a_[0], b_[0], c_[0]])
            x0, x1 = int(max(0, X.min())), int(min(S_ - 1, X.max() + 1)); y0, y1 = int(max(0, Y.min())), int(min(S_ - 1, Y.max() + 1))
            if x1 < x0 or y1 < y0: continue
            xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5); den = (Y[1] - Y[2]) * (X[0] - X[2]) + (X[2] - X[1]) * (Y[0] - Y[2])
            if abs(den) < 1e-9: continue
            w0 = ((Y[1] - Y[2]) * (xs - X[2]) + (X[2] - X[1]) * (ys - Y[2])) / den; w1 = ((Y[2] - Y[0]) * (xs - X[2]) + (X[0] - X[2]) * (ys - Y[2])) / den; w2 = 1 - w0 - w1
            ins = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not ins.any(): continue
            z = w0 * Z[0] + w1 * Z[1] + w2 * Z[2]; u = w0 * UV[t[0], 0] + w1 * UV[t[1], 0] + w2 * UV[t[2], 0]; v = w0 * UV[t[0], 1] + w1 * UV[t[1], 1] + w2 * UV[t[2], 1]
            px = np.clip(tx[((1 - v) * th).astype(int) % th, (u * tw).astype(int) % tw][..., :3] * 2.4, 0, 255).astype(np.uint8)
            sub = zb[y0:y1 + 1, x0:x1 + 1]; mk = ins & (z < sub); sub[mk] = z[mk]; img[y0:y1 + 1, x0:x1 + 1][mk] = px[mk]
        return Image.fromarray(img)
    from PIL import ImageDraw
    show = ['Idle', 'WalkFast', 'WalkFast ', 'ArcaneBeam', 'RearUpSlam', 'Death']; fr_at = {'Idle': 0.0, 'WalkFast': 0.1, 'WalkFast ': 0.6, 'ArcaneBeam': 0.5, 'RearUpSlam': 0.55, 'Death': 0.6}
    if os.environ.get('MOON_SHOW'): show = [x + ' ' * i for i, x in enumerate(os.environ['MOON_SHOW'].split(','))]; fr_at = {k: float(k.strip().split('@')[1]) for k in show}; PYAW = float(os.environ.get('MOON_YAW', '35'))
    else: PYAW = 35.0
    sheet = Image.new('RGB', (380 * 3, 380 * 2))
    for i, nm in enumerate(show):
        A = [x for x in anims if x[0] == nm.strip().split('@')[0]][0]; f = A[2][int(fr_at[nm] * (len(A[2]) - 1))]
        im = render(skin(f), D(PYAW)); ImageDraw.Draw(im).text((6, 6), nm, fill=(255, 255, 255)); sheet.paste(im, ((i % 3) * 380, (i // 3) * 380))
    sheet.save(a.preview); print('preview', a.preview)
