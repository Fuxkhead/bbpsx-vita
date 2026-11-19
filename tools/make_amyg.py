#!/usr/bin/env python3
"""Amygdala -> amyg.bin ("BBH2", the same layout as clericbeast.bin / hunter.bin) for the Vita.

The game's Amygdala meshes (SM_Amyg2.usda = the resting pose) are one static mesh made of 28 separate pieces
(body, abdomen, two raised arms, two front legs, the whip, and many small claws).  There is no skeleton, so this
script makes one: every big piece becomes a rigid bone that swings about the point where it meets the body, every
small piece follows the big piece it is nearest to, and the animations are made up here (idle, walk, the swipes and
slams the Cleric Beast fight uses, flinches, death).  The animation names are the Cleric Beast's, so the existing
boss fight code drives it (see amyg_test.txt in the game).

  python3 tools/make_amyg.py --usda SM_Amyg2.usda --tex ~/bbpsx-vita/assets --out amyg.bin [--scale 0.5]

--scale: the model is about 11.7 m wide at scale 1; the Cleric Beast arena fits it at 0.5 (about 4 m tall).
--tex: a folder searched (recursively) for t_amyg.png / .tga; without it the model is grey.
Game space: +X forward, +Y right, Z up, metres (the file faces -Y and is mirrored, as with the hunter).
"""
import argparse, glob, math, os, re, struct, sys
import numpy as np
SOLE_N = np.array([0.0875, 0.0145, 0.9960])      # the foot's own sole plane in rest pose (tilted ~5 deg: lowest points of block and toes)

C = np.array([[0, -1, 0], [-1, 0, 0], [0, 0, 1]], float)
SCALE = 0.01
FPS = 60.0

def load_usda(path):
    t = open(path).read()
    pts = re.search(r'point3f\[\] points = \[(.*?)\]', t, re.S).group(1)
    P = np.array(re.findall(r'\(([-\d.e+]+), ([-\d.e+]+), ([-\d.e+]+)\)', pts), float)
    fi = np.array([int(x) for x in re.search(r'int\[\] faceVertexIndices = \[(.*?)\]', t, re.S).group(1).split(',')]).reshape(-1, 3)
    m = re.search(r'texCoord2f\[\] primvars:st = \[(.*?)\]', t, re.S)
    st = np.array(re.findall(r'\(([-\d.e+]+), ([-\d.e+]+)\)', m.group(1)), float) if m else np.zeros((len(P), 2))
    return P, fi, st

def components(P, T):
    key = {}; idx = []
    for p in P: idx.append(key.setdefault(tuple(np.round(p, 2)), len(key)))
    par = list(range(len(key)))
    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for t in T:
        a, b, c = [idx[v] for v in t]; par[find(a)] = find(b); par[find(b)] = find(c)
    comp_of_tri = [find(idx[t[0]]) for t in T]
    roots = sorted(set(comp_of_tri), key=lambda r: -comp_of_tri.count(r))
    cid = {r: i for i, r in enumerate(roots)}
    vcomp = np.zeros(len(P), int) - 1
    for ti, t in enumerate(T):
        for v in t: vcomp[v] = cid[comp_of_tri[ti]]
    return vcomp, len(roots), [comp_of_tri.count(r) for r in roots]

def subdivide(P, T, st):
    """smooth_model: every triangle becomes four (a new point in the middle of each edge), so the long flat limbs have enough points along them to bend in a curve instead of folding at a few creases"""
    P = [np.array(p, float) for p in P]; st = [np.array(u, float) for u in st]; mid = {}; T2 = []
    def m_(a, b):
        k = (min(a, b), max(a, b))
        if k not in mid: mid[k] = len(P); P.append(0.5 * (P[a] + P[b])); st.append(0.5 * (st[a] + st[b]))
        return mid[k]
    for a, b, c in [[int(x) for x in t] for t in T]:
        ab = m_(a, b); bc_ = m_(b, c); ca = m_(c, a); T2 += [[a, ab, ca], [ab, b, bc_], [ca, bc_, c], [ab, bc_, ca]]
    return np.array(P), np.array(T2, int), np.array(st)

def smooth_mesh(P, T, its=2, lam=0.5, mu=-0.52):
    """smooth_model: rounds the hard corners off (each point moves toward the middle of its neighbours, then back out again so nothing shrinks). Points that share a place move together; the open edge of a sheet only slides along that edge"""
    key = {}; wid = np.array([key.setdefault(tuple(np.round(p, 2)), len(key)) for p in P]); n = len(key)
    W = np.zeros((n, 3)); cnt = np.zeros(n)
    for i, p in enumerate(P): W[wid[i]] += p; cnt[wid[i]] += 1
    W /= cnt[:, None]; ec = {}
    for t in T:
        a, b, c = [int(wid[v]) for v in t]
        for u, v in ((a, b), (b, c), (c, a)):
            if u != v: k = (min(u, v), max(u, v)); ec[k] = ec.get(k, 0) + 1
    nb = [[] for _ in range(n)]; bnb = [[] for _ in range(n)]
    for (u, v), c in ec.items():
        nb[u].append(v); nb[v].append(u)
        if c == 1: bnb[u].append(v); bnb[v].append(u)
    for it in range(its * 2):
        f = lam if it % 2 == 0 else mu; N = W.copy()
        for i in range(n):
            q = bnb[i] if bnb[i] else nb[i]
            if len(q) >= 2: N[i] = W[i] + f * (W[q].mean(axis=0) - W[i])
        W = N
    return W[wid]

# ---------------------------------------------------------------- rotations
def rot_axis(axis, ang):
    a = np.array(axis, float); a = a / (np.linalg.norm(a) + 1e-9); c, s = math.cos(ang), math.sin(ang)
    x, y, z = a
    return np.array([[c + x*x*(1-c), x*y*(1-c) - z*s, x*z*(1-c) + y*s],
                     [y*x*(1-c) + z*s, c + y*y*(1-c), y*z*(1-c) - x*s],
                     [z*x*(1-c) - y*s, z*y*(1-c) + x*s, c + z*z*(1-c)]])

def about(R, pivot, t=(0, 0, 0)):
    """3x4 matrix: rotate by R about pivot, then translate by t"""
    M = np.zeros((3, 4)); M[:, :3] = R; M[:, 3] = pivot - R @ pivot + np.array(t, float); return M

def mul(A, B):
    """A after B, both 3x4"""
    M = np.zeros((3, 4)); M[:, :3] = A[:, :3] @ B[:, :3]; M[:, 3] = A[:, :3] @ B[:, 3] + A[:, 3]; return M

# ---------------------------------------------------------------- the animations
D_ = math.radians
def smooth(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def pulse(t, a, b, c):
    """0 before a, rises to 1 at b, falls back to 0 at c"""
    if t <= a or t >= c: return 0.0
    return smooth((t - a) / (b - a)) if t < b else 1.0 - smooth((t - b) / (c - b))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--usda', required=True); ap.add_argument('--tex', default=None); ap.add_argument('--out', default='amyg.bin')
    ap.add_argument('--scale', type=float, default=0.5); ap.add_argument('--maxtex', type=int, default=256)
    ap.add_argument('--flipv', type=int, default=1); ap.add_argument('--smooth', type=int, default=1); ap.add_argument('--upscale', type=int, default=0); ap.add_argument('--torn', type=int, default=0)      # --torn 1: the model after he has torn his upper arms off: they are carried in his front hands as clubs (amyg2.bin)
    a = ap.parse_args(); TORN = bool(a.torn)
    P, T, st = load_usda(a.usda)
    if a.smooth:
        n0_ = len(P); P, T, st = subdivide(P, T, st); vc_, nc_, nt_ = components(P, T); Ps_ = smooth_mesh(P, T); mk_ = vc_ == 0; P = np.where(mk_[:, None], Ps_, P)      # only the torso and head (the biggest piece) are rounded off: the same smoothing squeezes the thin limbs and claws flat, so those are only given more points
        print('smooth_model: %d -> %d points, %d triangles' % (n0_, len(P), len(T)))
    vcomp, nc, ntris = components(P, T)
    if a.smooth: ntris = [n_ // 4 for n_ in ntris]      # (the pieces are told apart by their original triangle counts)
    G = (C @ P.T).T * SCALE * a.scale                      # game space, metres
    G[:, 2] -= G[:, 2].min()                               # feet on the floor
    big = [c for c in range(nc) if ntris[c] >= 26]         # body, abdomen, 4 limbs, whip
    cen = {c: G[vcomp == c].mean(axis=0) for c in range(nc)}
    body = 0
    bc = cen[body]
    # pivot of a big piece: its vertex nearest the body centre
    piv = {}
    for c in big:
        vs = G[vcomp == c]; piv[c] = vs[np.argmin(np.linalg.norm(vs - bc, axis=1))] if c != body else bc.copy()
    # bone order: 0 body, 1 abdomen, then limbs / whip
    abds = [c for c in big if c != body and ntris[c] == 60]
    abd = abds[0] if abds else [c for c in big if c != body][0]
    rest = [c for c in big if c not in (body, abd)]
    whip = min(rest, key=lambda c: ntris[c])
    limbs = [c for c in rest if c != whip]
    # arms = the two highest limbs, fronts = the two reaching furthest forward
    limbs.sort(key=lambda c: -G[vcomp == c][:, 2].max())
    arms = limbs[:2]; fronts = limbs[2:]
    def side(c): return -1 if cen[c][1] < bc[1] else 1       # -1 = left (-y)
    arms.sort(key=side); fronts.sort(key=side)
    limbc = {'armL': arms[0], 'armR': arms[1], 'frontL': fronts[0], 'frontR': fronts[1]}
    NSEG = {'armL': 5, 'armR': 5, 'frontL': 4, 'frontR': 4, 'backL': 4, 'backR': 4}      # joints per limb: the arms get shoulder, upper arm, elbow, forearm, wrist/hand; the legs hip, knee, ankle, foot
    names = ['body'] + [n if k == 0 else n + str(k + 1) for n in ('armL', 'armR', 'frontL', 'frontR', 'backL', 'backR') for k in range(NSEG[n])] + ['whip', 'tail', 'tail2', 'tail3']
    NB = len(names); bi_ = {n: i for i, n in enumerate(names)}
    # which big piece does every piece belong to
    owner = {body: 'body', abd: 'backL', whip: 'whip'}      # the 60-triangle piece is the pair of folded hind legs: split left / right below
    for n, c in limbc.items(): owner[c] = n
    bigs = list(owner)                                       # the big pieces only: a small piece (a claw, a finger) must never follow another small piece
    # small pieces (claws, fingers, the little chest arms and THEIR hands) join whatever they are attached to, nearest first: a little arm joins the body it grows from, and then its hand joins that little arm.
    # (hands_fix: every small piece used to go to the nearest BIG piece, so the hands of the little chest arms were given to the big front limbs hanging next to them, and flew off their own wrists whenever those limbs moved)
    _small = [c for c in range(nc) if c not in owner]; _done = list(bigs); _dc = {}
    def _gap(c1, c2):
        k_ = (c1, c2)
        if k_ not in _dc: _dc[k_] = float(np.min(np.linalg.norm(G[vcomp == c1][:, None, :] - G[vcomp == c2][None, :, :], axis=2)))
        return _dc[k_]
    _whand = None
    while _small:
        best = None
        for c in _small:
            cside = -1 if cen[c][1] < bc[1] else 1
            for o_ in _done:
                nm_ = owner[o_]
                if nm_ == 'whip' and o_ in bigs: continue         # (never the head / whip)
                if o_ != abd and nm_ not in ('body', 'whip') and (-1 if nm_.endswith('L') else 1) != cside: continue      # a limb (or anything already on a limb) only takes pieces on its own side: the two front hands touch each other at rest and must not swap sides
                d = _gap(c, o_)
                if best is None or d < best[0]: best = (d, c, o_)
        d, c, o_ = best
        if owner[o_][:3] in ('arm', 'fro') and _gap(c, body) <= d + 0.05: o_ = body      # thin_arms: a piece that reaches the torso as well as a big limb grows from the torso (the two thin arms whose shoulders sit beside the front limbs' used to be glued to those limbs, so they and their hands swung away with them)
        owner[c] = owner[o_]
        if o_ == abd: owner[c] = 'backL' if cen[c][1] < bc[1] else 'backR'
        _done.append(c); _small.remove(c)
    vown = np.array([owner[c] for c in vcomp])
    # whip_hand: the "whip" piece is really the left thin arm's HAND with the thin whip wire growing out of it. Only the wire is the whip now: the hand itself goes with its arm (like the right hand, its mirror image, which has no wire), and the wire swings about the point where it leaves the hand.
    _wv = np.where(vcomp == whip)[0]; _sm = [c for c in range(nc) if c not in bigs]
    if len(_wv) and _sm:
        _arm = min(_sm, key=lambda c: _gap(whip, c)); _mc = cen[whip].copy(); _mc[1] = 2 * bc[1] - _mc[1]
        _mir = min((c for c in _sm if c != _arm), key=lambda c: float(np.linalg.norm(cen[c] - _mc)))
        _mp = G[vcomp == _mir].copy(); _mp[:, 1] = 2 * bc[1] - _mp[:, 1]
        _dm = np.min(np.linalg.norm(G[_wv][:, None, :] - _mp[None, :, :], axis=2), axis=1); _hand = _wv[_dm < 0.08]
        if len(_hand) < 10:      # (no mirror image found: the hand is whatever lies within 0.7 m of the wrist)
            _av = G[vcomp == _arm]; _dw = np.min(np.linalg.norm(G[_wv][:, None, :] - _av[None, :, :], axis=2), axis=1); _hand = _wv[_dw < 0.7]
        _wire = np.array([v for v in _wv if v not in set(_hand.tolist())], int)
        if len(_hand) and len(_wire):
            vown[_hand] = owner[_arm]; _whand = (_hand, _arm)
            _dd = np.linalg.norm(G[_wire][:, None, :] - G[_hand][None, :, :], axis=2); piv[whip] = G[_wire[np.unravel_index(np.argmin(_dd), _dd.shape)[0]]].copy()
            print('whip hand: %d hand vertices go with the %s, %d wire vertices stay the whip (mirror piece %d vertices)' % (len(_hand), owner[_arm], len(_wire), len(_mp)))
    for v in np.where(vcomp == abd)[0]: vown[v] = 'backL' if G[v][1] < bc[1] else 'backR'
    # the tail: the few body vertices that stick out at the back, on the centre line (between the hind legs)
    bm_ = vown == 'body'; xmin_ = G[bm_][:, 0].min(); tx_ = bc[0] - 0.65 * (bc[0] - xmin_)
    tail_m = bm_ & (G[:, 0] < tx_) & (np.abs(G[:, 1] - bc[1]) < 0.35)
    for v in np.where(tail_m)[0]: vown[v] = 'tail'
    # thin_sway: the thin chest arms (small pieces that grow from the torso) each get a short chain of their own bones, so they sway and bend along their length instead of being frozen to the body
    thin = []; _bs = [c for c in range(nc) if c not in bigs and owner[c] == 'body']; _gp = {c: c for c in _bs}
    def _gf(x):
        while _gp[x] != x: _gp[x] = _gp[_gp[x]]; x = _gp[x]
        return x
    for i_, c1 in enumerate(_bs):
        for c2 in _bs[i_ + 1:]:
            if _gap(c1, c2) < 0.06: _gp[_gf(c1)] = _gf(c2)
    _grp = {}
    for c in _bs: _grp.setdefault(_gf(c), []).append(c)
    _bv = G[vcomp == body]
    for cs_ in _grp.values():
        vi_ = np.where(np.isin(vcomp, cs_) & (vown == 'body'))[0]
        hv_ = _whand[0] if (_whand is not None and _whand[1] in cs_) else np.array([], int)
        if len(vi_) < 6: continue
        dbody = np.min(np.linalg.norm(G[vi_][:, None, :] - _bv[None, :, :], axis=2), axis=1); root = G[vi_[np.argmin(dbody)]].copy()
        allv = np.concatenate([vi_, hv_]).astype(int); dr_ = np.linalg.norm(G[allv] - root, axis=1)
        if dr_.max() < 0.7: continue
        nm_ = 'thin%d' % (len(thin) + 1); main_ = max(cs_, key=lambda c: int((vcomp == c).sum()))
        thin.append({'name': nm_, 'pieces': cs_, 'main': main_, 'verts': vi_, 'hand': hv_, 'root': root, 'tip': G[allv[np.argmax(dr_)]].copy()})
        vown[allv] = nm_
    TN = [t_['name'] for t_ in thin]
    names += ['whip2', 'whip3', 'whip4'] + [n_ + sfx for n_ in TN for sfx in ('', '_2', '_3')]
    NB = len(names); bi_ = {n: i for i, n in enumerate(names)}
    print('pieces', nc, 'bones', names, 'tail verts', int(tail_m.sum()), 'thin arms', [(t_['name'], len(t_['verts']) + len(t_['hand'])) for t_ in thin])
    # pivots: the shoulder of each limb (its vertex nearest the body centre), and the knee half way to the tip
    pivots = [None] * NB; tips = {}
    pivots[0] = bc.copy(); pivots[bi_['whip']] = piv[whip]
    t_of = np.zeros(len(G)); vbone = np.zeros(len(G), int); vbone2 = np.zeros(len(G), int); wt = np.full(len(G), 255, int)
    for n in ('body', 'whip'):
        m = vown == n; vbone[m] = vbone2[m] = bi_[n]
    BLO = 0.3
    def hind_u(pts, zh, zl):      # position along the hind leg by HEIGHT: the folded leg zig-zags (hip at the top, a thigh plate, the shin running down, then the foot and toes), so the knee sits where the top plates end (about 30 % down), the ankle about 62 % down, the toes at 85 %
        t = np.clip((zh - pts[:, 2]) / max(zh - zl, 1e-6), 0.0, 1.0)
        return np.interp(t, [0.0, 0.30, 0.62, 0.85, 1.0], [0.0, 0.25, 0.50, 0.75, 1.0])
    SHB = 0.3; SHW = 0.25                                         # shoulder blend: first 35 % of the upper segment, up to 65 % body
    for n, c in list(limbc.items()) + [('backL', None), ('backR', None)]:
        if c is None:
            vs = G[(vcomp == abd) & ((G[:, 1] < bc[1]) if n == 'backL' else (G[:, 1] >= bc[1]))]; sh = vs[np.argmin(np.linalg.norm(vs - bc, axis=1))]
        else: sh = piv[c]; vs = G[vcomp == c]
        tip = vs[np.argmax(np.linalg.norm(vs - sh, axis=1))]
        ax = tip - sh; L2 = float(ax @ ax); ns = NSEG[n]
        tips[n] = tip
        m = np.where(vown == n)[0]; zh_ = G[m][:, 2].max(); zl_ = G[m][:, 2].min()
        for k in range(ns):
            q = sh + (k / ns) * ax
            if k > 0:                                         # the knee turns about the middle of the limb's own cross-section there, not a point on the straight line
                uu = ((G[m] - sh) @ ax) / L2
                if n.startswith('back'): uu = hind_u(G[m], G[m][:, 2].max(), G[m][:, 2].min())      # hind legs: the joints follow the leg's real zig-zag (thigh plate, shin, foot), not the straight line from hip to toe tip
                cs = G[m][np.abs(uu - k / ns) < (0.1 if n.startswith('back') else 0.07)]
                if len(cs) >= 3: q = cs.mean(axis=0)
            pivots[bi_[n if k == 0 else n + str(k + 1)]] = q
        hind_c = {}
        if n.startswith('back'):      # the hind leg is a set of separate plates and blocks: every piece moves as one rigid part on the bone for its height (no tearing, no gap opening inside a plate)
            ms_ = set(int(x) for x in m); par_ = {x: x for x in ms_}
            def fnd_(x):
                while par_[x] != x: par_[x] = par_[par_[x]]; x = par_[x]
                return x
            for tr_ in T:
                a_, b_, c_ = int(tr_[0]), int(tr_[1]), int(tr_[2])
                if a_ in ms_ and b_ in ms_ and c_ in ms_: par_[fnd_(a_)] = fnd_(b_); par_[fnd_(b_)] = fnd_(c_)
            grp_ = {}
            for x in ms_: grp_.setdefault(fnd_(x), []).append(x)
            for g_ in grp_.values():
                uc_ = float(hind_u(G[g_].mean(axis=0)[None, :], zh_, zl_)[0])
                for x in g_: hind_c[x] = uc_
        for v in m:
            if n.startswith('back'):
                k0 = int(min(hind_c[int(v)], 0.9999) * ns); vbone[v] = vbone2[v] = bi_[n if k0 == 0 else n + str(k0 + 1)]; wt[v] = 255; continue
            u = min(max(float((G[v] - sh) @ ax) / L2, 0.0), 0.9999) * ns
            if n.startswith('back'): u = min(float(hind_u(G[v][None, :], zh_, zl_)[0]), 0.9999) * ns
            k0 = int(u); fr = u - k0; k1 = k0; bl = 0.0
            if fr > BLO and k0 < ns - 1: k1 = k0 + 1; bl = (fr - BLO) / (1.0 - BLO) * 0.5      # wide, continuous blend across each joint: no tearing
            elif fr < 1.0 - BLO and k0 > 0: k1 = k0 - 1; bl = (1.0 - BLO - fr) / (1.0 - BLO) * 0.5
            nm_ = lambda k: n if k == 0 else n + str(k + 1)
            vbone[v] = bi_[nm_(k0)]; vbone2[v] = bi_[nm_(k1)]; wt[v] = int(round(255 * (1.0 - bl)))
            if k0 == 0 and fr < SHB:                              # the root of the limb follows the body part of the way, so the joint can't tear open
                bs = SHW * (1.0 - fr / SHB); vbone2[v] = 0; wt[v] = int(round(255 * (1.0 - bs)))
    # hands / claws: a small piece (a claw, a finger) used to take its bones from where it projects on the limb's shoulder-to-tip line, so one that sits off to the side of the hand could end up on the elbow's bone and swing away from the wrist in a swipe.
    # Now the whole piece is one rigid part that takes the bones and weights of the point on its own limb's big piece that it touches (the nearest vertex), so it moves exactly with the part of the arm it is attached to.
    nre_ = 0
    for c in range(nc):
        n = owner.get(c)
        if c in bigs or n not in limbc: continue
        pv_ = np.where(vcomp == c)[0]; lv_ = np.where(vcomp == limbc[n])[0]
        if len(pv_) == 0 or len(lv_) == 0: continue
        dd_ = np.linalg.norm(G[pv_][:, None, :] - G[lv_][None, :, :], axis=2); j_ = np.unravel_index(np.argmin(dd_), dd_.shape)[1]; at_ = lv_[j_]
        for v in pv_: vbone[v] = vbone[at_]; vbone2[v] = vbone2[at_]; wt[v] = wt[at_]
        nre_ += 1
    print('hands: rebound', nre_, 'small limb pieces to the bone of the limb point they touch')
    if tail_m.any():
        tv = G[tail_m]; troot = tv[np.argmax(tv[:, 0])]; ttip = tv[np.argmin(tv[:, 0])]; tax = ttip - troot; tL2 = float(tax @ tax)
        tn = ['tail', 'tail2', 'tail3']
        for k in range(3): pivots[bi_[tn[k]]] = troot + (k / 3.0) * tax
        for v in np.where(tail_m)[0]:
            u = min(max(float((G[v] - troot) @ tax) / tL2, 0.0), 0.9999) * 3; k0 = int(u); fr = u - k0; k1 = k0; bl = 0.0
            if fr > 0.3 and k0 < 2: k1 = k0 + 1; bl = (fr - 0.3) / 0.7 * 0.5
            elif fr < 0.7 and k0 > 0: k1 = k0 - 1; bl = (0.7 - fr) / 0.7 * 0.5
            vbone[v] = bi_[tn[k0]]; vbone2[v] = bi_[tn[k1]]; wt[v] = int(round(255 * (1.0 - bl)))
    def chain_w(vi, root, ax, bn, body_blend):      # points along a chain: each takes the bone of its stretch and blends into the next one across the joint
        L2_ = float(ax @ ax); ns_ = len(bn)
        for v in vi:
            u = min(max(float((G[v] - root) @ ax) / L2_, 0.0), 0.9999) * ns_; k0 = int(u); fr = u - k0; k1 = k0; bl = 0.0
            if fr > 0.3 and k0 < ns_ - 1: k1 = k0 + 1; bl = (fr - 0.3) / 0.7 * 0.5
            elif fr < 0.7 and k0 > 0: k1 = k0 - 1; bl = (0.7 - fr) / 0.7 * 0.5
            vbone[v] = bi_[bn[k0]]; vbone2[v] = bi_[bn[k1]]; wt[v] = int(round(255 * (1.0 - bl)))
            if body_blend and k0 == 0 and fr < 0.45: vbone2[v] = 0; wt[v] = int(round(255 * (1.0 - 0.5 * (1.0 - fr / 0.45))))
    whip_par = 0
    for th in thin:
        bn = [th['name'], th['name'] + '_2', th['name'] + '_3']; ax = th['tip'] - th['root']
        for k in range(3): pivots[bi_[bn[k]]] = th['root'] + (k / 3.0) * ax
        d0 = ax.copy(); d0[2] = 0; a1 = np.cross([0, 0, 1.0], d0); th['ax1'] = a1 / np.linalg.norm(a1) if np.linalg.norm(a1) > 1e-6 else np.array([0, 1.0, 0]); th['p0'] = 1.9 * len(th['name']) + 2.3 * thin.index(th)
        mv = np.where((vcomp == th['main']) & (vown == th['name']))[0]; chain_w(mv, th['root'], ax, bn, True); bound = list(mv)
        rest_ = [np.where((vcomp == c) & (vown == th['name']))[0] for c in th['pieces'] if c != th['main']] + ([th['hand']] if len(th['hand']) else [])
        rest_ = [r_ for r_ in rest_ if len(r_)]
        while rest_:      # hands, fingers and claws: each small piece is one rigid part on the bone of the point it touches, nearest first (so a hand follows its wrist exactly)
            dd = [np.linalg.norm(G[r_][:, None, :] - G[bound][None, :, :], axis=2) for r_ in rest_]; i_ = int(np.argmin([d.min() for d in dd])); at_ = bound[np.unravel_index(np.argmin(dd[i_]), dd[i_].shape)[1]]
            for v in rest_[i_]: vbone[v] = vbone[at_]; vbone2[v] = vbone2[at_]; wt[v] = wt[at_]
            bound += list(rest_[i_]); rest_.pop(i_)
        if len(th['hand']): whip_par = int(vbone[th['hand'][np.argmin(np.linalg.norm(G[th['hand']] - piv[whip], axis=1))]])      # the whip wire grows out of this arm's hand: it rides on the hand's bone
    wv_ = np.where(vown == 'whip')[0]; WN = ['whip', 'whip2', 'whip3', 'whip4']
    if len(wv_):
        wtip = G[wv_[np.argmax(np.linalg.norm(G[wv_] - piv[whip], axis=1))]]; wax = wtip - piv[whip]
        for k in range(4): pivots[bi_[WN[k]]] = piv[whip] + (k / 4.0) * wax
        chain_w(wv_, piv[whip], wax, WN, False)
    else:
        for k in range(1, 4): pivots[bi_[WN[k]]] = piv[whip]
    print('whip rides on bone', names[whip_par])
    tips['whip'] = None
    dirs = {}
    LIMBS = list(limbc) + ['backL', 'backR']
    for n in LIMBS: dirs[n] = tips[n] - pivots[bi_[n]]
    z = np.array([0, 0, 1.0])
    def lift_axis(n):
        d = dirs[n].copy(); d[2] = 0
        nn = np.linalg.norm(d); d = d / nn if nn > 1e-6 else np.array([1.0, 0, 0])
        ax = np.cross(z, d)
        return ax if np.linalg.norm(ax) > 1e-6 else np.array([0, 1.0, 0])
    LIFT = {n: lift_axis(n) for n in LIMBS}
    GRIP = {}      # torn arms: each upper arm, turned to point along the front hand of its own side and moved so the hand holds it just below the shoulder end
    for n_, f_ in (('armL', 'frontL'), ('armR', 'frontR')):
        hb_ = f_ + str(NSEG[f_]); da_ = dirs[n_] / np.linalg.norm(dirs[n_]); dh_ = tips[f_] - pivots[bi_[hb_]]; dh_ = dh_ / max(np.linalg.norm(dh_), 1e-6)
        dh_ = 0.6 * dh_ + np.array([1.0, 0.0, 0.35]); dh_ = dh_ / np.linalg.norm(dh_)      # (held pointing forward and a little up from the hand, not straight on from it: hanging straight down they went through the floor)
        ax_ = np.cross(da_, dh_); R_ = rot_axis(ax_ / np.linalg.norm(ax_), math.acos(max(-1.0, min(1.0, float(da_ @ dh_))))) if np.linalg.norm(ax_) > 1e-6 else np.eye(3)
        g_ = pivots[bi_[n_]] + 0.10 * dirs[n_]; GRIP[n_] = (hb_, about(R_, g_, tips[f_] - g_))
    AIM = {'armL': np.array([0.8, -0.5, 0.6]), 'armR': np.array([0.8, 0.5, 0.6]), 'frontL': np.array([1.0, -0.4, 0.1]), 'frontR': np.array([1.0, 0.4, 0.1]), 'backL': np.array([-1.0, -0.25, -0.2]), 'backR': np.array([-1.0, 0.25, -0.2])}      # where each limb points at the top of the jump: the arms and front legs ahead, the hind legs kicked out behind
    SWX = {}                                                   # the walking sweep axis of each limb: turning about it moves the foot straight along his direction of travel (x)
    for n in LIMBS:
        r_ = dirs[n]; a_ = np.cross(r_, [1.0, 0, 0])
        a_ = a_ / np.linalg.norm(a_) if np.linalg.norm(a_) > 1e-3 else z.copy()
        if np.cross(a_, r_)[0] < 0: a_ = -a_
        SWX[n] = a_
    LIFT['whip'] = np.array([0, 1.0, 0])
    SG = {}                                                   # which way the hind legs' knee and ankle turn to stretch the leg out
    for n in ('backL', 'backR'):
        sh = pivots[bi_[n]]; best = (-1.0, 1, 1)
        for s2 in (1, -1):
            for s3 in (1, -1):
                M2 = about(rot_axis(LIFT[n], s2 * D_(55)), pivots[bi_[n + '2']]); M3 = about(rot_axis(LIFT[n], s3 * D_(45)), pivots[bi_[n + '3']])
                q = M3[:, :3] @ tips[n] + M3[:, 3]; q = M2[:, :3] @ q + M2[:, 3]; dd = float(np.linalg.norm(q - sh))
                if dd > best[0]: best = (dd, s2, s3)
        SG[n] = (best[1], best[2])
    feet_ = []                                                 # where he stands: the lowest point of each limb that walks. A spin (yaw) turns him about the middle of these, so he pivots on his feet
    for n_ in ('backL', 'backR', 'armL', 'armR'):
        vs_ = G[vown == n_]; feet_.append(vs_[np.argmin(vs_[:, 2])])
    FC = np.mean(feet_, axis=0); FC[2] = 0.0; print('feet centre', FC.round(2))
    S = a.scale * 2.0                                          # lengths in the animations scale with the model (0.5 -> 1.0)

    # pose: body offset / pitch / roll / yaw, per bone (name_l = lift, name_s = sweep) in radians; limbs: 'frontL' is the shoulder, 'frontL2' the knee (relative)
    def build(pose):
        bz = pose.get('bz', 0.0); bx = pose.get('bx', 0.0); by = pose.get('by', 0.0); pitch = pose.get('pitch', 0.0); roll = pose.get('roll', 0.0); yaw = pose.get('yaw', 0.0)
        Rb = rot_axis([0, 1, 0], pitch) @ rot_axis([1, 0, 0], roll)
        mats = [None] * NB; mats[0] = mul(about(rot_axis([0, 0, 1], yaw), FC), about(Rb, bc, (bx, by, bz)))      # pitch / roll about the body, yaw about his feet
        ph_ = pose.get('sw_ph', 0.0); sk_ = pose.get('sw_k', 1.0)      # sway: the thin arms, the whip and the tail keep moving on their own in every animation, a wave running from root to tip
        for th in thin:
            cur = mats[0]
            for j_, sfx in enumerate(('', '_2', '_3')):
                cur = mul(cur, about(rot_axis(th['ax1'], sk_ * D_(4.0 + 1.5 * j_) * math.sin(ph_ + th['p0'] - 0.8 * j_)) @ rot_axis([0, 0, 1], sk_ * D_(3.5) * math.sin(2 * ph_ + 1.7 * th['p0'] - 0.8 * j_)), pivots[bi_[th['name'] + sfx]])); mats[bi_[th['name'] + sfx]] = cur
        wl_ = pose.get('whip_l', 0.0); ws_ = pose.get('whip_s', 0.0)
        cur = mul(mats[whip_par], about(rot_axis([0, 1, 0], wl_) @ rot_axis([0, 0, 1], ws_), pivots[bi_['whip']])); mats[bi_['whip']] = cur
        for j_ in range(1, 4):      # the whip wire bends along its length: each stretch curls a little further and lags the one before it
            cur = mul(cur, about(rot_axis([0, 1, 0], 0.3 * wl_ + sk_ * D_(8) * math.sin(2 * ph_ + 1.0 - 0.9 * j_)) @ rot_axis([0, 0, 1], 0.3 * ws_ + sk_ * D_(11) * math.sin(2 * ph_ - 0.9 * j_)), pivots[bi_['whip%d' % (j_ + 1)]])); mats[bi_['whip%d' % (j_ + 1)]] = cur
        ts = pose.get('tail_s', 0.6 * pose.get('whip_s', 0.0)); tl = pose.get('tail_l', 0.3 * pose.get('whip_l', 0.0)); cur = mats[0]      # the tail follows the whip's motion unless it has its own keys
        for j_, nm_ in enumerate(('tail', 'tail2', 'tail3')):
            cur = mul(cur, about(rot_axis([0, 1, 0], tl * (1.0 + 0.25 * j_)) @ rot_axis([0, 0, 1], ts * (1.0 + 0.25 * j_) + sk_ * D_(5) * math.sin(ph_ + 0.7 - 1.0 * j_)), pivots[bi_[nm_]])); mats[bi_[nm_]] = cur
        for n in (sorted(LIMBS, key=lambda q_: q_.startswith('arm')) if TORN else LIMBS):      # (torn: the front hands first, the arms they carry after them)
            Raim = np.eye(3); f_ = pose.get(n + '_aim', 0.0)          # aim: turn the whole limb towards a target direction (the frog kick: the back legs stretch out behind)
            if f_ != 0.0:
                d0 = dirs[n] / np.linalg.norm(dirs[n]); tg = AIM[n] / np.linalg.norm(AIM[n]); ax_ = np.cross(d0, tg)
                if np.linalg.norm(ax_) > 1e-6: Raim = rot_axis(ax_, f_ * math.acos(max(-1.0, min(1.0, float(d0 @ tg)))))
            up = mul(mats[0], about(Raim @ rot_axis(LIFT[n], pose.get(n + '_l', 0.0)) @ rot_axis([0, 0, 1], pose.get(n + '_s', 0.0)) @ rot_axis(SWX[n], pose.get(n + '_f', 0.0)), pivots[bi_[n]]))
            if TORN and n in GRIP: up = mul(mats[bi_[GRIP[n][0]]], mul(GRIP[n][1], about(rot_axis(LIFT[n], 0.25 * pose.get(n + '_l', 0.0)), pivots[bi_[n]])))      # the torn arm rides in the hand; its own keys only make it waggle a little
            k2 = pose.get(n + '2_l', 0.0); k3 = 0.0
            if n.startswith('arm'): k3 = pose.get(n + '3_l', 0.65 * k2 + 0.2 * pose.get(n + '_l', 0.0)); k2 = 0.65 * k2      # arms: the bend is shared by the elbow and the wrist
            if TORN and n in GRIP: k2 *= 0.35; k3 *= 0.35
            if n.startswith('back'): ex = pose.get(n + '_ext', 0.0); k2 += SG[n][0] * ex * D_(40); k3 = pose.get(n + '3_l', 0.0) + SG[n][1] * ex * D_(30)      # hind legs: _ext stretches the folded leg out
            ns = NSEG[n]
            if ns == 5: ang = [0.5 * k2, 0.5 * k2, 0.5 * k3, 0.5 * k3]                    # arm: shoulder-elbow, elbow, forearm, wrist
            elif n.startswith('front'): ang = [0.4 * k2, 0.35 * k2, 0.25 * k2]            # front leg: knee, ankle, foot
            else: ang = [0.9 * k2, 0.6 * k2 + 0.6 * k3, 0.9 * k3]                         # hind leg: knee, ankle, foot (bends a good half more than the raw angles, so the knees really fold)
            for j_ in range(len(ang)): ang[j_] += pose.get(n + '_j' + str(j_ + 2), 0.0)     # per-joint extras (follow-through ripple)
            cur = up; mats[bi_[n]] = up
            for j_ in range(1, ns):
                cur = mul(cur, about(rot_axis(LIFT[n], ang[j_ - 1]), pivots[bi_[n + str(j_ + 1)]]))
                lv_ = pose.get(n + '_level', 0.0)
                if lv_ and (j_ == ns - 1 or (n.startswith('back') and j_ == ns - 2)):      # (hind legs: the foot block turns back about the ankle too, then the toes about theirs) level: the foot keeps its sole flat on the ground however the leg and the body tilt (turned back about the ankle by the pitch it has picked up)
                    pp_ = cur[:, :3] @ pivots[bi_[n + str(j_ + 1)]] + cur[:, 3]
                    if n.startswith('back'):      # flat foot: turn the foot back so its sole faces straight down again, both fore-aft (pitch) and sideways (roll): the heel and the toes stay flat on the floor
                        v_ = cur[:, :3] @ SOLE_N; ax_ = np.cross(v_, [0.0, 0.0, 1.0]); sn_ = float(np.linalg.norm(ax_))
                        if sn_ > 1e-6: cur = mul(about(rot_axis(ax_ / sn_, math.atan2(sn_, float(v_[2])) * lv_), pp_), cur)
                        mats[bi_[n + str(j_ + 1)]] = cur; continue
                    for _it in range(4):      # (a few passes: the limb's own axes are not exactly the pitch axis)
                        R_ = cur[:, :3]; a_ = math.atan2(R_[0, 2], R_[2, 2])
                        cur = mul(about(rot_axis([0, 1, 0], -a_ * lv_), pp_), cur)
                mats[bi_[n + str(j_ + 1)]] = cur
        return mats
    bv_ = G[vown == 'body']                                    # the head point (where the beam comes out): the middle of his face on the centre line, not the front-most vertex (that one sits a head's width to his right)
    head_pt = np.array([bc[0] + 0.88 * (bv_[:, 0].max() - bc[0]) * 1.0 + 0.0, bc[1], bv_[:, 2].min() + 0.42 * (bv_[:, 2].max() - bv_[:, 2].min())])
    att_pts = [('frontR4', tips['frontR']), ('frontL4', tips['frontL']), ('body', head_pt), ('body', bc)]      # hand_r, hand_l, head, spine_2
    if TORN: att_pts[0] = ('armR' + str(NSEG['armR']), tips['armR']); att_pts[1] = ('armL' + str(NSEG['armL']), tips['armL'])      # the blows land with the ends of the clubs
    gz = G.copy()
    hidx = {n: np.where(vown == n)[0] for n in ('backL', 'backR')}
    oidx = np.where((vown != 'backL') & (vown != 'backR'))[0]
    bidx_ = np.where(vown == 'body')[0]
    aidx = {n: np.where(vown == n)[0] for n in ('frontL', 'frontR', 'armL', 'armR')}
    def low_of(mats, idx):
        M = np.array(mats); b0 = vbone[idx]; b1 = vbone2[idx]; w = (wt[idx] / 255.0)[:, None]
        p0 = np.einsum('vij,vj->vi', M[b0][:, :, :3], G[idx]) + M[b0][:, :, 3]; p1 = np.einsum('vij,vj->vi', M[b1][:, :, :3], G[idx]) + M[b1][:, :, 3]
        return float((w * p0 + (1 - w) * p1)[:, 2].min())
    def plant_abs(pose):
        """rearing up: each hind leg takes the stretch at which its foot reaches lowest (the foot is the unimodal minimum of the leg's reach); the body then rises or drops by whatever is missing so the foot stands exactly on the floor"""
        pose = dict(pose); best = {}
        for n in hidx:
            lo_e, hi_e = -1.0, 2.0
            for _ in range(16):
                m1 = lo_e + (hi_e - lo_e) / 3.0; m2 = hi_e - (hi_e - lo_e) / 3.0
                q = dict(pose); q[n + '_ext'] = m1; l1 = low_of(build(q), hidx[n]); q[n + '_ext'] = m2; l2 = low_of(build(q), hidx[n])
                if l1 < l2: hi_e = m2
                else: lo_e = m1
            e = 0.5 * (lo_e + hi_e); pose[n + '_ext'] = e; best[n] = low_of(build(pose), hidx[n])
        miss = max(best.values()); pose['bz'] = pose.get('bz', 0.0) - miss
        return pose, 0.0
    def plant_hind(pose, absfloor=False, floor=None):
        """the floor is where the rest of him stands (his lowest point other than the hind legs); each hind leg is then stretched or folded until its foot touches that floor, so it neither floats nor sinks"""
        if absfloor: return plant_abs(pose)
        pose = dict(pose); mats = build(pose); fl = low_of(mats, oidx) if floor is None else floor
        for n in hidx:
            e0 = pose.get(n + '_ext', 0.0); lo_e, hi_e = e0 - 1.6, e0 + 1.6
            pose[n + '_ext'] = hi_e
            if low_of(build(pose), hidx[n]) > fl + 0.003: continue      # even fully stretched it cannot reach: best effort
            pose[n + '_ext'] = lo_e
            if low_of(build(pose), hidx[n]) < fl - 0.003: continue      # even fully folded it is still below the floor
            for _ in range(14):
                mid = 0.5 * (lo_e + hi_e); pose[n + '_ext'] = mid
                if low_of(build(pose), hidx[n]) > fl + 0.003: lo_e = mid
                else: hi_e = mid
            pose[n + '_ext'] = hi_e
        return pose, fl
    def clamp_arms(pose):
        pose = dict(pose)
        for n in aidx:      # arms never swing into the floor: a stroke that would go deeper than 5 cm is scaled back until the fist just meets the ground (so the body is not hoisted up to make room, and the hind feet stay down)
            ks = [n + '_l', n + '2_l', n + '3_l']
            if low_of(build(pose), aidx[n]) < -0.05 and any(pose.get(k, 0.0) > 0 for k in ks):
                lo_k, hi_k = 0.0, 1.0
                for _ in range(9):
                    mid = 0.5 * (lo_k + hi_k); q = dict(pose)
                    for k in ks:
                        if q.get(k, 0.0) > 0: q[k] *= mid
                    if low_of(build(q), aidx[n]) < -0.05: hi_k = mid
                    else: lo_k = mid
                for k in ks:
                    if pose.get(k, 0.0) > 0: pose[k] *= lo_k
        return pose
    def frame(pose, ground=False, plant=False):
        feet_ = plant == 'feet'
        if plant == 'feet':      # both hind feet stand on the floor (z = 0) wherever the body is; plant_w (0..1) lets a pose lift them (airborne frames)
            pose = dict(pose); w_ = pose.pop('plant_w', 1.0)
            bl_ = low_of(build(pose), bidx_)      # his belly and head do not dig into the floor either: the body rises by whatever it would sink beyond 5 cm
            if bl_ < -0.05: pose['bz'] = pose.get('bz', 0.0) - 0.05 - bl_
            pose = clamp_arms(pose)
            for n_ in hidx: pose[n_ + '_level'] = max(pose.get(n_ + '_level', 0.0), w_)      # flat feet: the sole stays level on the floor however the leg and the body tilt
            orig_ = dict(pose)
            for pass_ in range(2 if w_ >= 0.5 else 1):
              if w_ > 0.001:      # each hind leg swings at the hip (more than its stretch can) until its lowest point just meets the floor
                  for n in hidx:      # the knee does the reaching; the hip swings only as far as it must (a wide hip swing pulls the leg out of its socket in the body)
                      b0 = pose.get(n + '_l', 0.0); k0 = pose.get(n + '2_l', 0.0); e0 = pose.get(n + '_ext', 0.0); grid = [D_(g) for g in range(-30, 91, 15)]; best = None; sol = None
                      for dh in (0.0, D_(5), D_(10)):
                          for de in (0.0, 0.8, 1.6):
                              q = dict(pose); q[n + '_ext'] = e0 + de; q[n + '_l'] = b0 + dh; lows = []
                              for d in grid: q[n + '2_l'] = k0 + d; lows.append(low_of(build(q), hidx[n]))
                              k = next((k for k, v in enumerate(lows) if v <= 0.003), None)
                              if k is None:
                                  m = min(range(len(lows)), key=lambda k: lows[k])
                                  if best is None or lows[m] < best[0]: best = (lows[m], de, dh, grid[m])
                                  continue
                              lo_d, hi_d = (grid[k - 1], grid[k]) if k > 0 else (grid[0], grid[0])
                              for _ in range(12 if k > 0 else 0):
                                  mid = 0.5 * (lo_d + hi_d); q[n + '2_l'] = k0 + mid
                                  if low_of(build(q), hidx[n]) > 0.003: lo_d = mid
                                  else: hi_d = mid
                              sol = (de, dh, hi_d); break
                          if sol is not None: break
                      if sol is None: sol = best[1:]
                      pose[n + '_ext'] = e0 + w_ * sol[0]; pose[n + '_l'] = b0 + w_ * sol[1]; pose[n + '2_l'] = k0 + w_ * sol[2]
              if pass_ == 0 and w_ >= 0.5:      # rearing: if the feet still cannot reach, the body comes down by what is missing and they are solved again (the feet stay planted, the rest rises around them)
                  miss_ = max(low_of(build(pose), hidx[n]) for n in hidx)
                  if miss_ > 0.02 and not pose.get('no_drop'): pose = dict(orig_); pose['bz'] = pose.get('bz', 0.0) - miss_
                  else: break
            plant = False
        if plant: pose = clamp_arms(pose)
        if plant:
            pose, fl_ = plant_hind(pose, plant == 'abs'); mats = build(pose); mats = [m.copy() for m in mats]
            for m in mats: m[2, 3] -= fl_      # the hind feet are the floor
            sk = None
        else: mats = build(pose)
        M_ = np.array(mats); w_s = (wt / 255.0)[:, None]
        sk = w_s * (np.einsum('vij,vj->vi', M_[vbone][:, :, :3], G) + M_[vbone][:, :, 3]) + (1 - w_s) * (np.einsum('vij,vj->vi', M_[vbone2][:, :, :3], G) + M_[vbone2][:, :, 3])
        lo = sk[:, 2].min()                                    # nothing sinks through the floor (ground=True: the lowest foot also never floats)
        if feet_ and lo < -0.45:      # hind feet stand on the floor: other tips (the tail, mostly) may press a little into the ground, but nothing sinks further than that
            mats = [m.copy() for m in mats]
            for m in mats: m[2, 3] -= lo + 0.45
        elif not feet_ and not plant and (lo < 0.0 or (ground and lo > 0.0)):
            mats = [m.copy() for m in mats]
            for m in mats: m[2, 3] -= lo
        out = list(mats)
        for nm, p in att_pts:
            M = mats[bi_[nm]].copy(); M[:, 3] = mats[bi_[nm]][:, :3] @ p + mats[bi_[nm]][:, 3]; out.append(M)
        return np.concatenate([m.reshape(12) for m in out]).astype('<f4')

    def anim(name, dur, fn, loop=False, travel=(0.0, 0.0), ground=False, plant=False):
        if plant is False and name not in ('Walk', 'WalkFast'): plant = 'feet'      # every move keeps the hind feet on the floor (the walk cycles already step them)
        n = max(2, int(round(dur * FPS)))
        if not ground and not loop and name not in ('Scream1', 'Death', 'ArcaneBeam', 'ArmTear'): fn = ambient(fn, dur)      # limbs the move does not use keep drifting like in the idle
        if os.environ.get('AMYG_ONLY') and name not in os.environ['AMYG_ONLY'].split(','): n = 2      # (debug: only build the named animations in full)
        ncy_ = max(1, int(round(dur / 2.4))); fn0_ = fn
        def fn(t, f_=fn0_):      # sway: its phase runs a whole number of times through every animation, so loops close
            o_ = dict(f_(t)); o_.setdefault('sw_ph', 2 * math.pi * ncy_ * t)
            if name == 'Death': o_.setdefault('sw_k', max(0.0, 1.0 - 1.5 * t))
            return o_
        frs = [frame(fn(i / (n - 1) if not loop else i / n), ground, plant) for i in range(n)]
        return (name, FPS, np.array(frs, '<f4'), travel)
    anims = []
    D = math.radians
    sw = math.sin; tau = 2 * math.pi
    LEGS = ['frontL', 'frontR', 'armL', 'armR']
    def ambient(fn, dur):
        """the limbs a move leaves alone keep flowing a little (a slow, soft sway with the joints lagging behind), faded in and out at both ends so the move still starts and ends from the idle"""
        def w(t):
            o = dict(fn(t)); e = smooth(min(1.0, t / 0.12, (1.0 - t) / 0.12)) if True else 1.0
            e = max(0.0, e)
            ph = tau * t * max(1, round(dur / 2.4))
            for k, n in enumerate(('frontL', 'frontR', 'armL', 'armR')):
                if any(key.startswith(n) for key in o): continue
                a = 1.0 if n.startswith('arm') else 0.8
                o[n + '_l'] = e * a * D(8) * sw(ph + k * 1.6); o[n + '_s'] = e * a * D(7) * sw(ph + k * 1.3 + 1); o[n + '2_l'] = e * a * D(11) * sw(ph + k * 1.6 + 1.2)
                if n.startswith('front'): o[n + '3_l'] = e * a * D(9) * sw(ph + k * 1.6 + 2.0)
            if not any(key.startswith('tail') for key in o): o['tail_s'] = e * D(7) * sw(ph + 2.2); o['tail_l'] = e * D(5) * sw(ph + 0.4)
            if not any(key.startswith('whip') for key in o): o['whip_l'] = e * D(18) * sw(ph * 2); o['whip_s'] = e * D(30) * sw(ph * 2 + 1)
            return o
        return w
    def idle(t):
        ph = t * tau
        o = {'bz': 0.09 * S * sw(ph), 'bx': 0.05 * S * sw(ph + 1), 'roll': D(2.5) * sw(ph + 0.5), 'pitch': D(2) * sw(ph), 'whip_l': D(18) * sw(ph * 2), 'whip_s': D(30) * sw(ph * 2 + 1), 'tail_s': D(7) * sw(ph * 2 + 2.2), 'tail_l': D(4) * sw(ph * 2 + 0.4)}
        for k, n in enumerate(LEGS):
            o[n + '_l'] = D(13) * sw(ph + k * 1.6) + D(4) * sw(2 * ph + k * 0.9); o[n + '_s'] = D(12) * sw(ph + k * 1.3 + 1) + D(3) * sw(2 * ph + k); o[n + '2_l'] = D(19) * sw(ph + k * 1.6 + 1.2) + D(5) * sw(2 * ph + k * 1.7)
            if n.startswith('front'): o[n + '3_l'] = D(15) * sw(ph + k * 1.6 + 2.1)      # (each joint lags the one before it, so the limbs ripple)
        for k, n in enumerate(('backL', 'backR')): o[n + '_l'] = D(5) * sw(ph + k * 2.2); o[n + '2_l'] = D(8) * sw(ph + k * 2.2 + 1)
        return o
    anims.append(anim('Idle', 2.4, idle, loop=True))
    def gait(ph):
        """one leg, 60 % stance / 40 % swing. Stance: the foot sweeps back at a steady pace (it grips the floor). Swing: a Hermite curve that leaves and arrives at exactly the stance pace, so the speed never jumps at the stride boundaries (no mechanical hitch)"""
        ph %= 1.0
        if ph < 0.6: return 1.0 - 2.0 * ph / 0.6, 0.0, 0.0
        u = (ph - 0.6) / 0.4; m = -2.0 / 0.6 * 0.4                                  # the stance slope, per unit of swing time
        sweep = (2 * u**3 - 3 * u**2 + 1) * -1.0 + (u**3 - 2 * u**2 + u) * m + (-2 * u**3 + 3 * u**2) * 1.0 + (u**3 - u**2) * m
        lift = math.sin(math.pi * u) ** 1.3
        return sweep, lift, math.sin(math.pi * min(1.0, u * 1.2)) ** 1.1
    def sweep_amp(n, stride):
        """how far a foot has to swing back during stance so it does not slide: the body moves 0.6 * stride while the foot is planted, the foot's reach along x per radian is |r| * sin(angle to x)"""
        r = dirs[n]; Ln = float(np.linalg.norm(r)); sp = max(0.35, float(np.linalg.norm(np.cross(r / Ln, [1.0, 0, 0]))))
        return min(max(0.3 * stride / (Ln * sp), D(10)), D(50))
    def ripple(o, n, t, p0, amp):
        """each joint lags the one before it: the lift travels down the limb like a wave (follow-through), so nothing moves as one stiff piece"""
        l0 = gait(t + p0)[1]
        for j in range(2, NSEG[n] + 1): o[n + '_j' + str(j)] = D(amp) * (gait(t + p0 - 0.045 * (j - 1))[1] - l0) * (1.0 if j < NSEG[n] else -1.4)
    def walk_fn(lean, bob, stride):
        def walk(t):
            ph = t * tau
            o = {'bz': bob * S * (0.5 * math.cos(ph * 2.0 + 0.3) + 0.15 * math.cos(ph * 4.0 + 0.6)), 'by': 0.06 * S * sw(ph), 'roll': D(4.0) * sw(ph + 0.3), 'pitch': D(lean) + D(2.2) * sw(ph * 2 + 0.9), 'yaw': D(5) * sw(ph - 0.4), 'bx': 0.04 * S * sw(ph * 2 + 0.5),
                 'whip_l': D(28) * sw(ph * 2 - 0.8), 'whip_s': D(45) * sw(ph - 0.5), 'tail_s': D(9) * sw(ph - 1.6), 'tail_l': D(5) * sw(ph * 2 + 0.3)}
            for n, p0 in (('armL', 0.0), ('backR', 0.0), ('armR', 0.5), ('backL', 0.5)):       # the four rear limbs walk, as a trot: opposite corners step together
                sweep, lift, fold = gait(t + p0)
                ripple(o, n, t, p0, 14)
                if n.startswith('back'):                         # the hind legs: long stride, high lift, knee and ankle folding
                    o[n + '_f'] = sweep_amp(n, stride) * sweep; o[n + '_l'] = D(34) * lift - D(5); o[n + '2_l'] = D(-40) * fold + D(5) * (1 - lift); o[n + '3_l'] = D(-30) * fold + D(6) * (1 - lift)
                else:                                            # the other walking pair, the longest stride
                    o[n + '_f'] = sweep_amp(n, stride) * sweep; o[n + '_l'] = D(30) * lift - D(5); o[n + '2_l'] = D(-48) * fold + D(6) * (1 - lift)
            for p0_ in (0.0, 0.5):      # walk_v2: weight. Each time a pair of limbs lands the body sinks onto it and nods a little, then is carried up and over; he also leans further across onto the side that is planted
                imp_ = pulse((t + p0_) % 1.0, 0.0, 0.06, 0.24); o['bz'] -= 0.055 * S * imp_ * (bob / 0.14); o['pitch'] += D(1.4) * imp_; o['tail_l'] += D(3) * imp_
            o['by'] = 0.10 * S * sw(ph); o['roll'] = D(5.5) * sw(ph + 0.3)
            for n, sg in (('frontL', 1.0), ('frontR', -1.0)):    # the big front limbs are his ARMS: they hang bent and swing against the stride, the claws trail, they never step
                a_ = ph + (0.0 if sg > 0 else math.pi)
                ripple2 = [D(10) * sw(a_ - 0.7 * j) for j in range(1, 4)]
                o[n + '_f'] = 0.5 * sweep_amp(n, stride) * sw(a_ + math.pi); o[n + '_s'] = sg * D(-6); o[n + '_l'] = D(-8) + D(9) * sw(a_ + 1.0)
                o[n + '2_l'] = D(-36) + D(14) * sw(a_ + 0.4)
                for j_, v in enumerate(ripple2): o[n + '_j' + str(j_ + 2)] = v
            return o
        return walk
    walk = walk_fn(3.0, 0.14, 2.6 * S); runw = walk_fn(8.0, 0.2, 3.6 * S)
    anims.append(anim('Walk', 1.0, walk, loop=True, travel=(2.6 * S, 0)))
    anims.append(anim('WalkFast', 0.7, runw, loop=True, travel=(3.6 * S, 0)))
    def swipe(n, sgn, a1=0.38):
        def f(t):
            w = pulse(t, 0.0, 0.24, a1); st_ = pulse(t, a1 - 0.05, a1 + 0.1, 0.85)
            o = {n + '_s': sgn * (D(-70) * w + D(90) * st_), n + '_l': D(45) * w - D(14) * st_, n + '2_l': D(-40) * w + D(25) * st_, 'yaw': sgn * (D(-16) * w + D(20) * st_), 'bx': 0.45 * S * st_ - 0.15 * S * w, 'roll': sgn * D(-6) * w + sgn * D(5) * st_, 'whip_s': D(35) * (st_ - w)}
            return o
        return f
    anims.append(anim('SwipeL', 1.5, swipe('frontL', 1.0)))
    def merge(*fs):
        def f(t):
            o = {}
            for g in fs:
                for k, v in g(t).items(): o[k] = o.get(k, 0.0) + v
            return o
        return f
    def seg(fn, lo, hi): return lambda t: fn(min(max((t - lo) / (hi - lo), 0.0), 1.0)) if lo <= t <= hi else (fn(0.0) if t < lo else fn(1.0))
    anims.append(anim('2HitComboL-R1', 2.6, merge(seg(swipe('frontL', 1.0), 0.0, 0.5), seg(swipe('frontR', -1.0), 0.45, 1.0))))
    anims.append(anim('2HitComboR-L1', 2.6, merge(seg(swipe('frontR', -1.0), 0.0, 0.5), seg(swipe('frontL', 1.0), 0.45, 1.0))))
    def punch(n, amp=1.0):
        def f(t):
            up = pulse(t, 0.0, 0.35, 0.5); down = pulse(t, 0.4, 0.55, 0.85)
            return {n + '_l': amp * (D(-75) * up + D(50) * down), n + '2_l': amp * (D(-35) * up + D(45) * down), 'pitch': D(-10) * up + D(11) * down, 'bx': 0.55 * S * down, 'bz': 0.28 * S * up - 0.18 * S * down}
        return f
    anims.append(anim('GroundPunchR', 2.0, merge(punch('frontR'), punch('armR', 0.7))))
    anims.append(anim('GroundSlapL', 1.8, merge(punch('frontL'), punch('armL', 0.7))))
    def slap_back(t):
        g = merge(punch('frontL'), punch('armL', 0.7))(t); g['bx'] = g.get('bx', 0) - 0.9 * S * pulse(t, 0.4, 0.7, 1.0); return g
    anims.append(anim('GroundSlapLStepBack', 2.0, slap_back, travel=(-1.2 * S, 0)))
    JT = 4.4 * S
    def jump(t):      # coil, spring, arc through the air with the front legs raised, then crash down on the target and rise again
        crouch = smooth(t / 0.15) * (1.0 - smooth((t - 0.15) / 0.06))               # sinks over 0.15, springs up by 0.21
        u = min(max((t - 0.2) / 0.42, 0.0), 1.0); arc = 4.0 * u * (1.0 - u)         # a true parabola from take-off (0.2) to landing (0.62)
        push = pulse(t, 0.14, 0.22, 0.34)                                           # hind legs shove off the ground
        reach = pulse(t, 0.2, 0.33, 0.5); apex = pulse(t, 0.3, 0.42, 0.55); fall = pulse(t, 0.46, 0.6, 0.72)
        hit = pulse(t, 0.6, 0.66, 0.8); rec = pulse(t, 0.62, 0.7, 0.95)
        o = {'bz': 2.4 * S * arc - 0.42 * S * crouch - 0.2 * S * hit, 'bx': JT * 0.7 * (smooth(u) - t) - 0.2 * S * crouch,       # the game already carries him JT metres along the jump (travel): only the DIFFERENCE from that even pace is baked in, so the model ends where the game left him (no jolt back)
             
             'pitch': D(9) * crouch - D(24) * reach + D(26) * fall - D(5) * rec, 'roll': D(3) * sw(t * tau * 2) * arc,
             'whip_l': D(45) * reach - D(60) * fall, 'whip_s': D(30) * sw(t * tau * 3) * arc}
        for n in ('frontL', 'frontR'):
            o[n + '_aim'] = 0.5 * reach * (1.0 - fall)
            o[n + '_l'] = D(18) * crouch - D(32) * apex + D(34) * fall + D(10) * hit
            o[n + '2_l'] = D(-30) * crouch - D(45) * apex + D(80) * fall
        for n in ('armL', 'armR'):
            o[n + '_aim'] = 0.3 * reach * (1.0 - fall)
            o[n + '_l'] = D(14) * crouch - D(22) * apex + D(26) * fall
            o[n + '2_l'] = D(-25) * crouch - D(25) * apex + D(65) * fall
        lc = pulse(t, 0.6, 0.67, 0.82)                                              # absorbing the landing
        for n in ('backL', 'backR'):                                                # the hind legs do the jumping: coil deep, drive straight (a real push-off), tuck in the air, bend to take the landing
            o[n + '_ext'] = 0.65 * push - 0.35 * crouch - 0.2 * arc
            o[n + '_l'] = D(10) * crouch - D(8) * push + D(9) * arc * (1 - hit) + D(10) * lc      # (small hip angles: the leg bends at the knee, the hip stays in its socket)
            o[n + '2_l'] = D(-45) * crouch + D(30) * push - D(28) * arc * (1 - hit) - D(38) * lc
            o[n + '3_l'] = D(-30) * crouch + D(20) * push - D(18) * arc - D(25) * lc
        o['plant_w'] = (1.0 - smooth((t - 0.18) / 0.05)) if t < 0.4 else smooth((t - 0.5) / 0.12); o['no_drop'] = 1.0
        return o
    anims.append(anim('JumpSlam', 2.4, jump, travel=(4.4 * S, 0)))
    def scream(t):
        r = pulse(t, 0.0, 0.25, 0.9)
        o = {'pitch': D(-30) * r, 'bz': 0.8 * S * r, 'bx': -0.3 * S * r, 'tail_l': D(18) * r, 'whip_s': D(40) * sw(t * tau * 6) * r, 'roll': D(4) * sw(t * tau * 8) * r}
        for n in ('backL', 'backR'): o[n + '_level'] = r
        for k, n in enumerate(LEGS): o[n + '_l'] = D(-70) * r + D(8) * sw(t * tau * 7 + k) * r; o[n + '2_l'] = D(-45) * r + D(10) * sw(t * tau * 6 + k) * r; o[n + '_s'] = D(12) * sw(t * tau * 5 + k) * r
        return o
    anims.append(anim('Scream1', 3.0, scream, plant='abs'))
    def armtear(t):      # ArmTear (at 30% health): he rears up, the front hands reach up to the upper arms, he strains and shudders, then wrenches them down and off with a scream; the game then swaps to the model that carries them (amyg2.bin)
        rear = smooth(t / 0.2) * (1.0 - smooth((t - 0.82) / 0.18)); grab = smooth((t - 0.1) / 0.2) * (1.0 - smooth((t - 0.6) / 0.08))
        strain = pulse(t, 0.28, 0.48, 0.62); rip = smooth((t - 0.6) / 0.06); settle = smooth((t - 0.74) / 0.26); shake = strain + rip * (1.0 - settle)
        o = {'pitch': D(-26) * rear * (1.0 - 0.6 * rip) + D(12) * rip * (1.0 - settle), 'bz': 0.7 * S * rear, 'bx': -0.3 * S * rear + 0.25 * S * rip * (1.0 - settle),
             'roll': D(5) * sw(t * tau * 9) * strain + D(3) * sw(t * tau * 15) * rip * (1.0 - settle), 'whip_s': D(38) * sw(t * tau * 6) * shake, 'tail_l': D(16) * rear}
        for n in ('backL', 'backR'): o[n + '_level'] = rear
        hold = smooth((t - 0.1) / 0.2)      # the upper arms are swung up and forward to meet the raised front hands, and stay in their grip from then on (the next model carries them there)
        for k, n in enumerate(('frontL', 'frontR')): o[n + '_l'] = D(-58) * grab + D(26) * rip * (1.0 - settle) + D(4) * sw(t * tau * 11 + k) * strain; o[n + '2_l'] = D(-40) * grab + D(12) * rip * (1.0 - settle)
        for k, n in enumerate(('armL', 'armR')): o[n + '_aim'] = hold * (1.0 - 0.25 * settle); o[n + '_l'] = -D(10) * strain * (1.0 + 0.5 * sw(t * tau * 10 + k)) + D(28) * rip * (1.0 - 0.5 * settle); o[n + '2_l'] = D(-24) * strain + D(30) * rip * (1.0 - settle)
        return o
    if not TORN: anims.append(anim('ArmTear', 3.4, armtear, plant='abs'))
    def hurt(n):
        def f(t):
            p = pulse(t, 0.0, 0.2, 0.8)
            return {'bx': -0.35 * S * p, 'pitch': D(-3) * p, n + '_l': D(-35) * p, n + '2_l': D(25) * p, 'roll': D(6) * p, 'whip_s': D(40) * p}
        return f
    for nm, lb in (('ArmLDmg1', 'armL'), ('ArmRDmg1', 'armR'), ('HeadDmg1', 'armL'), ('LegDmgL', 'frontL'), ('LegDmgR', 'frontR')):
        anims.append(anim(nm, 0.8, hurt(lb), ground=True, plant='feet'))
    def stagger(t):      # he sags onto bent legs and rocks back without sliding: ground=True keeps the lowest foot on the floor
        p = smooth(t / 0.25) if t < 0.7 else 1.0 - smooth((t - 0.7) / 0.3)
        o = {'pitch': D(-4) * p, 'roll': D(5) * sw(t * tau * 2) * p, 'whip_s': D(30) * sw(t * tau * 3) * p}
        for n in LEGS: o[n + '_l'] = D(8) * p; o[n + '2_l'] = D(-10) * p      # (a small sag only: bending the limbs hard lifted his rear a metre off the ground)
        return o
    anims.append(anim('CounteredStart', 1.6, stagger, ground=True, plant='feet'))
    anims.append(anim('Visceral', 2.4, stagger, ground=True, plant='feet'))
    def death(t):      # he rears up as if to fire the beam, head thrown back, and screams, shuddering harder and harder; the game holds this last pose and lets him crumble into smoke
        up = smooth(t / 0.3); sc = smooth((t - 0.25) / 0.45)                       # rise (0 - 0.3), then the scream builds
        sh = sc * (0.6 + 0.4 * sw(t * tau * 3))
        o = {'pitch': D(-34) * up - D(8) * sc, 'bz': 0.85 * S * up, 'bx': -0.2 * S * up, 'roll': D(4) * sw(t * tau * 13) * sh, 'yaw': D(3.5) * sw(t * tau * 9) * sh,
             'whip_l': D(-42) * sc, 'whip_s': D(18) * sw(t * tau * 11) * sh, 'tail_l': D(20) * up, 'tail_s': D(12) * sw(t * tau * 4) * sc}
        for n in ('frontL', 'frontR'):
            sg = 1 if n.endswith('L') else -1
            o[n + '_l'] = D(-60) * up - D(8) * sw(t * tau * 10) * sh; o[n + '_s'] = sg * D(40) * up; o[n + '2_l'] = D(-28) * up - D(12) * sw(t * tau * 8) * sh
        for n in ('armL', 'armR'):
            sg = 1 if n.endswith('L') else -1
            o[n + '_l'] = D(-48) * up - D(6) * sw(t * tau * 9) * sh; o[n + '_s'] = sg * D(32) * up; o[n + '2_l'] = D(-18) * up
        for n in ('backL', 'backR'): o[n + '_ext'] = 0.5 * up; o[n + '_level'] = up
        return o
    anims.append(anim('Death', 3.0, death, ground=True, plant='abs'))

    # ---- his own moves (the game's Amygdala table lists them: ClawFlurry, WhipLash, SpinSweep, RearUpSlam, LegStomp, BackHop)
    def jab(n, t0, sgn):                                     # one fast stab of a front leg at the target
        def f(t):
            w = pulse(t, t0, t0 + 0.05, t0 + 0.13)
            return {n + '_aim': 0.9 * w, n + '2_l': D(-30) * w, 'bx': 0.45 * S * w, 'yaw': sgn * D(7) * w, 'roll': sgn * D(-4) * w}
        return f
    anims.append(anim('ClawFlurry', 2.2, merge(jab('frontL', 0.10, 1), jab('frontR', 0.27, -1), jab('frontL', 0.44, 1), jab('frontR', 0.61, -1), lambda t: {'bz': -0.12 * S * pulse(t, 0.05, 0.4, 0.85)})))
    def whiplash(t):                                         # rears back, lashes the whip over its head and thrusts a front leg with it
        w = pulse(t, 0.0, 0.3, 0.45); st_ = pulse(t, 0.38, 0.5, 0.75)
        return {'pitch': D(-16) * w + D(8) * st_, 'bz': 0.25 * S * w, 'whip_l': D(-70) * w + D(60) * st_, 'whip_s': D(60) * sw(t * tau * 4) * st_, 'frontR_aim': 0.9 * st_, 'frontR2_l': D(-25) * st_, 'bx': 0.6 * S * st_, 'yaw': D(-10) * w + D(10) * st_}
    anims.append(anim('WhipLash', 2.0, whiplash))
    def spin(t):                                             # a full turn with the front legs flung out
        w = pulse(t, 0.05, 0.25, 0.8)
        o = {'yaw': tau * smooth((t - 0.2) / 0.55), 'bz': 0.12 * S * w, 'whip_s': D(70) * sw(t * tau * 3) * w, 'roll': D(5) * w}
        o['frontL_s'] = D(-70) * w; o['frontR_s'] = D(70) * w; o['frontL_l'] = D(30) * w; o['frontR_l'] = D(30) * w
        o['armL_s'] = D(-35) * w; o['armR_s'] = D(35) * w
        return o
    anims.append(anim('SpinSweep', 2.6, spin))
    def rearup(t):                                           # rises on the hind legs, front legs high, then crashes down on the target
        up = pulse(t, 0.0, 0.4, 0.55); down = pulse(t, 0.5, 0.62, 0.9)
        o = {'pitch': D(-38) * up + D(14) * down, 'bz': 0.9 * S * up - 0.15 * S * down, 'bx': -0.2 * S * up + 0.9 * S * down, 'whip_l': D(30) * up}
        for n in ('frontL', 'frontR'): o[n + '_l'] = D(-85) * up + D(60) * down; o[n + '2_l'] = D(-35) * up + D(50) * down
        for n in ('armL', 'armR'): o[n + '_l'] = D(-60) * up + D(40) * down
        for n in ('backL', 'backR'): o[n + '_ext'] = 0.5 * up; o[n + '_level'] = up
        return o
    anims.append(anim('RearUpSlam', 2.8, rearup))
    def stomp(n, t0, amp=1.0):
        def f(t):
            up = pulse(t, t0, t0 + 0.09, t0 + 0.18); down = pulse(t, t0 + 0.14, t0 + 0.2, t0 + 0.3)
            return {n + '_l': amp * (D(-55) * up + D(30) * down), n + '2_l': amp * (D(-40) * up + D(35) * down), 'bz': -0.12 * S * down, 'pitch': D(3) * down}
        return f
    anims.append(anim('LegStomp', 2.6, merge(stomp('frontL', 0.08), stomp('armR', 0.26, 0.8), stomp('frontR', 0.44), stomp('armL', 0.62, 0.8), lambda t: {'roll': D(3) * sw(t * tau * 2)})))
    def hop(t):                                              # BackHop: coil on the hind legs, shove off (they straighten hard), fly back with the legs trailing, reach down and take the landing
        crouch = pulse(t, 0.0, 0.14, 0.27); push = pulse(t, 0.14, 0.23, 0.36); air = pulse(t, 0.22, 0.47, 0.72); lc = pulse(t, 0.66, 0.75, 0.92)
        P = smooth((t - 0.22) / 0.5)                         # where he is: still while coiling and after landing, travelling while airborne (only the deviation from the game's even travel is baked in)
        o = {'bz': 1.05 * S * air - 0.32 * S * crouch - 0.16 * S * lc, 'bx': -3.4 * S * (P - t) + 0.25 * S * crouch,
             'pitch': D(7) * crouch - D(16) * push - D(6) * air + D(9) * lc, 'whip_l': D(25) * air}
        for n in LEGS: o[n + '_l'] = D(-34) * air + D(14) * crouch + D(10) * lc; o[n + '2_l'] = D(-38) * air - D(14) * crouch
        for n in ('backL', 'backR'):
            o[n + '_ext'] = 0.95 * push + 0.55 * air - 0.45 * crouch
            o[n + '_l'] = D(10) * crouch - D(8) * push + D(6) * air * (1 - lc) + D(9) * lc
            o[n + '2_l'] = D(-42) * crouch + D(30) * push - D(20) * air * (1 - lc) - D(32) * lc
            o[n + '3_l'] = D(-28) * crouch + D(22) * push - D(14) * air - D(22) * lc
        o['plant_w'] = (1.0 - smooth((t - 0.15) / 0.09)) if t < 0.45 else smooth((t - 0.62) / 0.08)      # feet on the floor while coiling and landing, free in between
        return o
    anims.append(anim('BackHop', 1.4, hop, travel=(-3.4 * S, 0)))

    # ---- the rest of his real moveset (palm thrust + slam, wide sweeps, rear stomp, acid vomit and the under-body scoop)
    def palmslam(t):      # PalmSlam: right palm, left palm thrust out in front, then both crash down on the ground and he stays hunched with his head low (the counter-attack window)
        th1 = pulse(t, 0.08, 0.18, 0.30); th2 = pulse(t, 0.26, 0.36, 0.48); rise = pulse(t, 0.42, 0.52, 0.60); slam = pulse(t, 0.55, 0.62, 0.74); low = smooth((t - 0.58) / 0.1) * (1.0 - smooth((t - 0.9) / 0.1))
        o = {'pitch': D(-6) * (th1 + th2) - D(12) * rise + D(15) * slam + D(8) * low, 'bz': 0.1 * S * rise - 0.2 * S * low, 'bx': 0.15 * S * (th1 + th2) + 0.7 * S * slam, 'whip_l': D(20) * rise}
        for n, th in (('frontR', th1), ('frontL', th2)):
            o[n + '_aim'] = 0.8 * th; o[n + '_l'] = D(-10) * th; o[n + '2_l'] = D(-6) * th
        for n in ('frontL', 'frontR'):
            o[n + '_l'] = o.get(n + '_l', 0.0) - D(52) * rise + D(62) * slam + D(14) * low; o[n + '2_l'] = o.get(n + '2_l', 0.0) - D(20) * rise + D(48) * slam
        for n in ('armL', 'armR'): o[n + '_l'] = D(-28) * rise + D(22) * slam; o[n + '2_l'] = D(-14) * rise + D(26) * slam
        return o
    anims.append(anim('PalmSlam', 3.2, palmslam))
    def widesweep(t):      # WideSweep: both big arms swing across the front of him in broad horizontal arcs, right to left, then back
        a = pulse(t, 0.12, 0.3, 0.46); b = pulse(t, 0.42, 0.62, 0.8)
        o = {'yaw': D(-24) * a + D(30) * b, 'roll': D(4) * (a - b), 'pitch': D(-5) * (a + b), 'bz': 0.06 * S * (a + b), 'whip_s': D(40) * (b - a)}
        for n, sg in (('frontL', 1.0), ('frontR', -1.0)):
            o[n + '_l'] = D(-52) * (a + b); o[n + '2_l'] = D(-20) * (a + b)
            o[n + '_s'] = sg * (D(70) * a - D(85) * b)
        for n in ('armL', 'armR'): o[n + '_l'] = D(-14) * (a + b)
        return o
    anims.append(anim('WideSweep', 2.4, widesweep))
    def hindstomp(t):      # HindStomp: for anyone behind him: the rear legs lift one after the other and stomp the ground, he leans forward over the front ones
        def st(t0):
            up = pulse(t, t0, t0 + 0.1, t0 + 0.2); down = pulse(t, t0 + 0.16, t0 + 0.22, t0 + 0.34); return up, down
        u1, d1 = st(0.12); u2, d2 = st(0.4)
        o = {'pitch': D(5) * (u1 + u2) - D(3) * (d1 + d2), 'bz': -0.1 * S * (d1 + d2), 'roll': D(5) * (u2 - u1), 'tail_l': D(-14) * (d1 + d2)}
        for n, up, down in (('armL', u1, d1), ('armR', u2, d2)):
            o[n + '_l'] = D(-30) * up + D(22) * down; o[n + '2_l'] = D(-26) * up + D(26) * down
        return o
    anims.append(anim('HindStomp', 2.2, hindstomp))
    def acid(t):      # AcidVomit: for anyone standing under his body: he rears his arms wide, dips his head and spews dark fluid straight down
        dip = pulse(t, 0.12, 0.3, 0.9); spew = pulse(t, 0.3, 0.45, 0.8)
        o = {'pitch': D(16) * dip, 'bz': -0.3 * S * dip, 'roll': D(3) * sw(t * tau * 9) * spew, 'whip_l': D(30) * dip, 'whip_s': D(25) * sw(t * tau * 8) * spew}
        for n, sg in (('frontL', 1.0), ('frontR', -1.0)):
            o[n + '_s'] = sg * D(35) * dip; o[n + '_l'] = D(-30) * dip; o[n + '2_l'] = D(-24) * dip
        return o
    anims.append(anim('AcidVomit', 3.0, acid))
    def scoop(t):      # UnderGrab: the lower hands dip down under his chest and scoop whoever stands there back in towards him
        reach = pulse(t, 0.1, 0.3, 0.5); pull = pulse(t, 0.42, 0.58, 0.8)
        o = {'pitch': D(10) * reach - D(6) * pull, 'bz': -0.25 * S * reach + 0.08 * S * pull, 'bx': 0.2 * S * reach - 0.3 * S * pull}
        for n in ('frontL', 'frontR'):
            o[n + '_l'] = D(64) * reach - D(20) * pull; o[n + '2_l'] = D(40) * reach - D(34) * pull; o[n + '_s'] = (D(18) if n == 'frontL' else D(-18)) * pull
        for n in ('armL', 'armR'): o[n + '_l'] = D(20) * reach - D(14) * pull
        return o
    anims.append(anim('UnderGrab', 2.6, scoop))

    def beam(t):      # ArcaneBeam: he rears up and spreads his arms, the head draws back and shudders as the light gathers (0.2 - 0.4), then snaps forward as the beam fires and he holds until the blasts have run out
        up = smooth(t / 0.22) * (1.0 - smooth((t - 0.74) / 0.22))
        chg = pulse(t, 0.18, 0.36, 0.48); fire = pulse(t, 0.38, 0.46, 0.72); sh = pulse(t, 0.28, 0.4, 0.52)
        o = {'pitch': D(-30) * up - D(8) * chg + D(16) * fire, 'bz': 0.8 * S * up, 'bx': -0.2 * S * up,
             'whip_l': D(-38) * chg + D(25) * fire, 'whip_s': D(14) * sw(t * tau * 9) * sh, 'roll': D(3) * sw(t * tau * 11) * sh, 'yaw': D(2) * sw(t * tau * 7) * sh,
             'tail_l': D(18) * up, 'tail_s': D(10) * sw(t * tau * 3) * up}
        for n in ('frontL', 'frontR'):
            sg = 1 if n.endswith('L') else -1
            o[n + '_l'] = D(-55) * up; o[n + '_s'] = sg * D(35) * up; o[n + '2_l'] = D(-25) * up - D(10) * sw(t * tau * 8) * sh
        for n in ('armL', 'armR'):
            sg = 1 if n.endswith('L') else -1
            o[n + '_l'] = D(-45) * up; o[n + '_s'] = sg * D(30) * up; o[n + '2_l'] = D(-15) * up
        for n in ('backL', 'backR'): o[n + '_ext'] = 0.5 * up; o[n + '_level'] = up
        return o
    anims.append(anim('ArcaneBeam', 3.6, beam, plant='abs'))

    # ---------------------------------------------------------------- texture and the file
    tex = None
    if a.tex:
        from PIL import Image
        hits = []
        for ext in ('png', 'tga', 'PNG', 'TGA'): hits += glob.glob(os.path.join(os.path.expanduser(a.tex), '**', 't_amyg.' + ext), recursive=True)
        hits += [h for h in glob.glob(os.path.join(os.path.expanduser(a.tex), '**', '*'), recursive=True) if os.path.basename(h).lower().startswith('t_amyg.') and h not in hits]
        if hits:
            im = Image.open(hits[0]).convert('RGBA')
            src_ = im.size
            while max(im.size) > a.maxtex: im = im.resize((max(1, im.size[0] // 2), max(1, im.size[1] // 2)))
            if a.upscale and max(im.size) < a.maxtex:      # tex_upscale: a texture smaller than --maxtex is enlarged to it (smooth resampling, then sharpened so the detail stays crisp instead of going blurry)
                from PIL import ImageFilter
                k_ = a.maxtex / float(max(im.size)); rgb = im.convert('RGB').resize((int(round(im.size[0] * k_)), int(round(im.size[1] * k_))), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.5, percent=90, threshold=2))
                al_ = im.getchannel('A').resize(rgb.size, Image.LANCZOS); im = Image.merge('RGBA', (*rgb.split(), al_))
            print('texture size: source %dx%d -> stored %dx%d' % (src_[0], src_[1], im.size[0], im.size[1]))
            tex = ('T_Amyg', im); print('texture', hits[0], im.size)
        else: print('texture t_amyg not found: the model will be grey')
    nB, nAt = NB, 4
    verts = np.zeros(len(G), dtype=[('p', '<3f4'), ('uv', '<2f4'), ('b', 'u1', 4)])
    for i in range(len(G)):
        verts['p'][i] = G[i]; verts['uv'][i] = (st[i][0], 1.0 - st[i][1] if a.flipv else st[i][1]); verts['b'][i] = (vbone[i], vbone2[i], wt[i], 0)
    idx = []
    ncut = 0
    for t in T:
        ow = {str(vown[int(v)]) for v in t} - {'body', 'whip'} - set(TN)
        if len(ow) > 1: ncut += 1; continue                    # a triangle bridging two limbs (the web between the hind legs) tears when they move apart: leave it out
        idx += [int(t[0]), int(t[2]), int(t[1])]               # reflection flips the winding
    print('left out', ncut, 'triangles that joined two limbs')
    out = bytearray(b'BBH2')
    out += struct.pack('<7I', len(G), len(idx), nB, len(anims), nAt, 1, 1)
    if tex is None: out += struct.pack('<BHH', 0, 1, 1) + bytes([150, 140, 130, 255])
    else:
        nm = tex[0].encode(); out += struct.pack('<B', len(nm)) + nm + struct.pack('<HH', *tex[1].size) + tex[1].tobytes()
    out += struct.pack('<IIHH', 0, len(idx), 0, 0)
    out += verts.tobytes(); out += np.array(idx, '<u2').tobytes()
    for n in ('hand_r', 'hand_l', 'head', 'spine_2'): out += n.encode().ljust(16, b'\0')
    for nm, fps, fr, tv in anims:
        out += nm.encode()[:32].ljust(32, b'\0') + struct.pack('<fIff', fps, len(fr), tv[0], tv[1]) + fr.tobytes()
    # limb_map: which limb every bone belongs to (0 body, 1 right arm, 2 left arm, 3 legs, 4 the tail) and how far along that limb it sits; the game uses it for limb breaking and for the arm's hit box. Older builds of the game ignore this block
    lcode = [0] * NB; lfrac = [0] * NB
    for n_ in ('armL', 'armR', 'frontL', 'frontR', 'backL', 'backR'):
        cd_ = (1 if n_.endswith('R') else 2) if (n_.startswith('front') or (TORN and n_.startswith('arm'))) else 3      # the big front limbs are his arms (torn: the clubs they carry too); the upper pair he walks on and the hind legs are his legs
        for k_ in range(NSEG[n_]): b_ = bi_[n_ if k_ == 0 else n_ + str(k_ + 1)]; lcode[b_] = cd_; lfrac[b_] = 255 if (TORN and n_.startswith('arm')) else int(255 * (k_ + 1) / NSEG[n_])
    for k_, n_ in enumerate(('tail', 'tail2', 'tail3')): lcode[bi_[n_]] = 4; lfrac[bi_[n_]] = int(255 * (k_ + 1) / 3)
    out += b'LMB1' + struct.pack('<I', NB) + bytes(lcode) + bytes(lfrac)
    open(a.out, 'wb').write(out)
    print('wrote %s: %d KB (%d verts, %d tris, %d bones, %d anims; %.1f x %.1f x %.1f m)' % (a.out, len(out) // 1024, len(G), len(T), nB, len(anims), np.ptp(G[:, 0]), np.ptp(G[:, 1]), np.ptp(G[:, 2])))

if __name__ == '__main__':
    main()
