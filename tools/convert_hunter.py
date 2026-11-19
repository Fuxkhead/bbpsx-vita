#!/usr/bin/env python3
"""Convert the Hunter (ActorX .psk + .psa files from FModel) into hunter.bin ("BBH2") for the Vita.

  python3 tools/convert_hunter.py --psk SkM_AttireHunter.psk --psa assets/Char/Hunter/Anim \
        --tex assets/Char/Hunter/Mat/Tex --out hunter.bin

Output space ("game space"): +X is forward, +Y is the character's right... exactly like the map's UE
space with the character facing +X (the mesh in the file faces -Y and is Y-mirrored; this is fixed here).
Units are metres.  Z up.

hunter.bin layout (little endian)
  "BBH2"
  u32 nVerts, nIdx, nBones, nAnims, nAttach, nSections, nTex
  nTex x { u8 nameLen, name, u16 w, u16 h, RGBA }
  nSections x { u32 indexStart, u32 indexCount, u16 texIndex, u16 pad }
  nVerts x { f32 x,y,z,u,v ; u8 bone0, bone1, w0(0..255), pad }      (rest pose, 24 bytes)
  nIdx x u16
  nAttach x { char name[16] }
  nAnims x { char name[32], f32 fps, u32 nFrames,
             nFrames x ( nBones x 12 f32  skin matrices (3x4 row-major, game space),
                         nAttach x 12 f32 attachment world matrices (3x4 row-major) ) }
"""
import argparse, glob, os, struct, sys
import numpy as np
from PIL import Image

# ---------------------------------------------------------------- ActorX readers
def chunks(path):
    d = open(path, 'rb').read(); p = 0; out = {}
    while p + 32 <= len(d):
        cid = d[p:p+20].split(b'\0')[0].decode('latin1')
        flag, size, cnt = struct.unpack('<iii', d[p+20:p+32]); p += 32
        out[cid] = (size, cnt, d[p:p+size*cnt]); p += size*cnt
    return out

def cstr(b): return b.split(b'\0')[0].decode('latin1')

def read_bones(c):
    size, cnt, data = c; bones = []
    for i in range(cnt):
        b = data[i*size:(i+1)*size]
        name = cstr(b[:64]); flags, nch, parent = struct.unpack('<Iii', b[64:76])
        qx, qy, qz, qw, px, py, pz = struct.unpack('<7f', b[76:104])
        bones.append(dict(name=name, parent=parent, q=(qx, qy, qz, qw), p=(px, py, pz)))
    return bones

def load_usda_mesh(path):
    """a static mesh exported as .usda (no .psk / .pskx available): same dict as a .pskx"""
    import re
    t = open(path, encoding='utf-8', errors='replace').read()
    def arr(key):
        m = re.search(re.escape(key) + r'\s*=\s*\[(.*?)\]', t, re.S)
        return [float(x) for x in re.findall(r'-?[\d.]+(?:[eE][-+]?\d+)?', m.group(1))] if m else None
    pts = np.array(arr('point3f[] points'), np.float32).reshape(-1, 3)
    counts = [int(c) for c in arr('int[] faceVertexCounts')]; idx = [int(i) for i in arr('int[] faceVertexIndices')]
    st = arr('texCoord2f[] primvars:st'); st = np.array(st, np.float32).reshape(-1, 2) if st else None
    mst = re.search(r'primvars:st\s*=.*?interpolation\s*=\s*"(\w+)"', t, re.S); interp = mst.group(1) if mst else 'vertex'
    ind2 = re.search(r'primvars:st:indices\s*=\s*\[(.*?)\]', t, re.S)
    if st is not None and ind2: st = st[[int(i) for i in re.findall(r'-?\d+', ind2.group(1))]]
    mats = list(dict.fromkeys(re.findall(r'def Material "(\w+)"', t))) or ['MI_Default']
    fmat = [0] * len(counts)
    for m in re.finditer(r'GeomSubset\s+"\w+".*?int\[\]\s+indices\s*=\s*\[(.*?)\].*?material:binding\s*=\s*<([^>]*)>', t, re.S):
        nm = m.group(2).rstrip('/').split('/')[-1]
        if nm in mats:
            for fi in re.findall(r'\d+', m.group(1)):
                if int(fi) < len(fmat): fmat[int(fi)] = mats.index(nm)
    wd = np.dtype([('pt', '<u4'), ('u', '<f4'), ('v', '<f4'), ('mat', 'u1'), ('r', 'u1'), ('pad', '<u2')])
    fd = np.dtype([('w', '<3u2'), ('mat', 'u1'), ('aux', 'u1'), ('sg', '<u4')])
    wedges, faces, pos = [], [], 0
    for fi, c in enumerate(counts):
        for k in range(1, c - 1):
            w3 = []
            for corner in (pos, pos + k, pos + k + 1):
                if st is None: u = v = 0.0
                elif interp == 'faceVarying' and len(st) == len(idx): u, v = st[corner]
                else: u, v = st[idx[corner]] if idx[corner] < len(st) else (0.0, 0.0)
                wedges.append((idx[corner], u, 1.0 - v, fmat[fi], 0, 0)); w3.append(len(wedges) - 1)
            faces.append((tuple(w3), fmat[fi], 0, 0))
        pos += c
    return dict(pts=pts, wedge=np.array(wedges, wd), faces=np.array(faces, fd), mats=mats, weights=np.zeros(0, np.dtype([('w', '<f4'), ('pt', '<i4'), ('bone', '<i4')])), bones=[])

def load_psk(path):
    if path.lower().endswith('.usda'): return load_usda_mesh(path)
    k = chunks(path)
    pts = np.frombuffer(k['PNTS0000'][2], '<f4').reshape(-1, 3).copy()
    wedge = np.frombuffer(k['VTXW0000'][2], dtype=np.dtype([('pt', '<u4'), ('u', '<f4'), ('v', '<f4'), ('mat', 'u1'), ('r', 'u1'), ('pad', '<u2')]))
    if k['FACE0000'][0] != 12:
        sys.exit("this .psk uses 32-bit faces (FACE3200); send it to me and I'll add that")
    faces = np.frombuffer(k['FACE0000'][2], dtype=np.dtype([('w', '<3u2'), ('mat', 'u1'), ('aux', 'u1'), ('sg', '<u4')]))
    mats = [cstr(k['MATT0000'][2][i*88:i*88+64]) for i in range(k['MATT0000'][1])]
    wts = np.frombuffer(k['RAWWEIGHTS'][2], dtype=np.dtype([('w', '<f4'), ('pt', '<i4'), ('bone', '<i4')]))
    bones = read_bones(k['REFSKELT']) if 'REFSKELT' in k else []
    return dict(pts=pts, wedge=wedge, faces=faces, mats=mats, weights=wts, bones=bones)

def load_psa(path):
    k = chunks(path); bn = read_bones(k['BONENAMES'])
    sz, cnt, d = k['ANIMINFO']
    out = []
    for s in range(cnt):
        b = d[s*sz:(s+1)*sz]
        name = cstr(b[:64]); rate = struct.unpack('<f', b[152:156])[0]
        first, nf = struct.unpack('<2i', b[160:168])
        out.append((name, rate, first, nf))
    keys_all = np.frombuffer(k['ANIMKEYS'][2], dtype=np.dtype([('p', '<3f4'), ('q', '<4f4'), ('t', '<f4')]))
    seqs = []
    for name, rate, first, nf in out:                       # keys are frame-major: [frame][bone]
        ks = keys_all[first*len(bn):(first+nf)*len(bn)].reshape(nf, len(bn))
        seqs.append(dict(name=name, fps=rate, n=nf, keys=ks, bones=[b['name'] for b in bn], parents=[b['parent'] for b in bn]))
    return seqs

# ---------------------------------------------------------------- quaternion helpers
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return np.array([aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz])
def qconj(q): return np.array([-q[0], -q[1], -q[2], q[3]])
def qrot(q, v):
    r = qmul(qmul(q, np.array([v[0], v[1], v[2], 0.0])), qconj(q)); return r[:3]
def qmat(q):
    q = q / np.linalg.norm(q); x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])

# file space -> game space: (x,y,z) -> (-y,-x,z)   (un-mirrors Y, turns the mesh to face +X); cm -> m
C = np.array([[0, -1, 0], [-1, 0, 0], [0, 0, 1]], float)
SCALE = 0.01

def world_chain(names, parents, locals_qp):
    """ActorX: every bone except the first stores a conjugated quaternion."""
    W = []
    for i, (q, p) in enumerate(locals_qp):
        q = np.array(q, float); p = np.array(p, float)
        if i > 0: q = qconj(q)
        if parents[i] < 0: W.append((q, p))
        else:
            pq, pp = W[parents[i]]; W.append((qmul(pq, q), pp + qrot(pq, p)))
    return dict(zip(names, W))

def to34(R, t):
    return np.concatenate([R, t.reshape(3, 1)], axis=1).reshape(12).astype('<f4')

def convert_mat(R, t):
    """conjugate by the file->game axis map (and metres)"""
    return C @ R @ C.T, SCALE * (C @ t)

# ---------------------------------------------------------------- texture
def load_texture(path, maxtex):
    im = Image.open(path).convert('RGBA')
    def pot(n): return max(1, min(maxtex, 1 << max(0, (n - 1).bit_length())))
    w, h = pot(im.width), pot(im.height)
    if (w, h) != im.size: im = im.resize((w, h), Image.BOX)
    return im

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--psk', required=True, nargs='+', help='one or more .psk files; the first has the full skeleton (attire), the rest (face, hair...) are matched by bone name')
    ap.add_argument('--psa', required=True, nargs='+', help='a .psa file or a folder searched recursively for .psa')
    ap.add_argument('--tex', nargs='+', default=None, help='one or more folders with the PNG textures (T_HunterBody.png, t_sawcleaver.png, ...)')
    ap.add_argument('--texmap', default='MI_HunterFace=BbPSX_Head128v3,MI_HunterHair=t_hair,MI_HunterHeadPrev=T_HunterHead,MI_Cleaver=t_sawcleaver', help='MATERIAL=texturefile pairs (no .png) for materials whose texture is not named T_<material>')
    ap.add_argument('--hat', default=None, help='static mesh (.pskx) glued rigidly to the head bone')
    ap.add_argument('--mweaps', default=None, help='comma list of weapon meshes (.psk / .pskx) held by the messengers: section flags 5,6,7,8 (cleaver, cane in the first two hands... the game shows the right ones); even ones in hand_r, odd ones in hand_l'); ap.add_argument('--mwscale', type=float, default=0.6); ap.add_argument('--mwrot', default='0,0,0'); ap.add_argument('--mwoff', default='0,0,0')
    ap.add_argument('--mhats', default=None, help='comma list of static hat meshes (.pskx) glued to the head bone as switchable hats: section flags 10,11,12... (the game draws only the worn one)')
    ap.add_argument('--mhatoff', default='0,0,0', help='offset (cm, file space) added to every --mhats mesh after scaling'); ap.add_argument('--mhatscale', type=float, default=1.0, help='scale of every --mhats mesh, about its own origin')
    ap.add_argument('--hatoff', default='0,2,155.6', help='hat offset in file space cm (x,y,z) added to the hat mesh before attaching to the head')
    ap.add_argument('--tint', default='MI_HunterFace=225,184,158', help='MATERIAL=R,G,B (0-255; separate several with ;) recolours that material\'s texture to this average colour, keeping its light/dark detail; use --tint none to disable')
    ap.add_argument('--rootmotion', default='strip', choices=['strip', 'keep'], help='strip = remove horizontal root travel from animations (the game moves the player); keep = leave it')
    ap.add_argument('--weapon', default=None, help='weapon .psk glued rigidly to the hand_r bone (cleaver)')
    ap.add_argument('--weaponoff', default='0,0,0', help='weapon offset in hand_r bone space, cm (x,y,z)')
    ap.add_argument('--weaponroty', type=float, default=0.0, help='extra rotation of the weapon about the hand_r Y axis (the blade axis), degrees')
    ap.add_argument('--psaonly', default=None, help='comma-separated name fragments: only animations whose name contains one of them are packed (keeps enemy bins small)')
    ap.add_argument('--pistol', default=None, help='static pistol mesh (.pskx) glued rigidly to the left hand through its socket; the game only draws it while firing')
    ap.add_argument('--pistolframe', default='hand', choices=['hand', 'socket'], help='hand: barrel along the fingers, top toward the thumb; socket: the game\'s socket orientation (barrel forward)')
    ap.add_argument('--shift', action='append', default=None, help='NAME=x,y,z: slide every mesh file whose name contains NAME by x,y,z cm (psk axes, z up): lifts a wheelchair under a seated character')
    ap.add_argument('--pistoloff', default=None, help='pistol offset in the pistol file\'s own space, cm (x,y,z): slides it in the grip')
    ap.add_argument('--pistol2', default=None, help='a second static mesh on the same hand / frame / offset as --pistol (flag 3): drawn instead of it while the game sets show_alt (a messenger\'s open note)')
    ap.add_argument('--pistolrot', default='0,0,0', help='extra pistol rotation about its x,y,z axes, degrees')
    ap.add_argument('--pistolcenter', action='store_true', help='put the middle of the pistol mesh (its bounding box centre) at the hand bone; --pistoloff then slides it from there')
    ap.add_argument('--cbone', default=None, help='closed_note: bone for the --pistol mesh only (the --pistol2 mesh keeps --pistolbone / --pistolframe)'); ap.add_argument('--cframe', default=None, choices=['hand', 'socket']); ap.add_argument('--crot', default=None); ap.add_argument('--coff', default=None)
    ap.add_argument('--pistolbone', default='hand_l', help='bone the pistol is skinned to')
    ap.add_argument('--pistolsocket', default='hand_lSocket', help='socket bone whose frame the pistol file axes are matched to')
    ap.add_argument('--weaponanim', nargs='+', default=None, help='.psa files / folders animating the weapon\'s OWN skeleton (Cleaver_Open.psa ...): the blade part is split off and animated at runtime')
    ap.add_argument('--bladebones', default='transformer,transformer_end,DamageStart,DamageEnd,TransSpark', help='weapon bones that belong to the moving blade part')
    ap.add_argument('--transformbone', default='transformer', help='the weapon bone the transform animations move (case-insensitive; the axe calls it Transformer)')
    ap.add_argument('--damagebones', default='DamageStart,DamageEnd', help='weapon bones marking the damaging edge (start,end)')
    ap.add_argument('--weaponmap', default=None, help='override the file->hand axis mapping: three comma-separated terms giving the hand x,y,z axes as +-x/y/z of the weapon file, e.g. "-z,y,x" (the cleaver default)')
    ap.add_argument('--weaponrotx', type=float, default=180.0, help='extra rotation of the weapon about the hand_r X axis, degrees (default 180 = blade points forward; 0 = the other way round)')
    ap.add_argument('--bindpos', action='store_true', help='use this mesh\'s own bone lengths for the animations (animations borrowed from a skeleton with other proportions)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--maxtex', type=int, default=128)
    ap.add_argument('--flipv', type=int, default=0, help='1 = v -> 1-v; 0 = keep (ActorX/UE V is already top-down)')
    ap.add_argument('--attach', default='hand_r,hand_l,head,spine_2', help='bones whose animated world matrix is exported')
    ap.add_argument('--fps', type=float, default=0, help='resample animations to this fps (0 = keep original)')
    ap.add_argument('--slowfps', default='', help='NAME=FPS,...: animations whose name contains NAME are resampled to FPS instead (long cutscene animations: keeps the bin small)')
    a = ap.parse_args()

    meshes = [load_psk(p) for p in a.psk]
    # the first mesh's skeleton is the reference (full skeleton); other meshes are matched by bone name
    if a.hat:
        hm = load_psk(a.hat); hm['static'] = True
        hm['pts'] = hm['pts'] + np.array([float(x) for x in a.hatoff.split(',')], dtype=np.float32)
        meshes.append(hm); a.psk = list(a.psk) + [a.hat]
    for hi_, hp_ in enumerate([x for x in (a.mhats or '').split(',') if x]):
        hm = load_psk(hp_); hm['static'] = True; hm['mhat'] = hi_
        hm['pts'] = hm['pts'] * a.mhatscale + np.array([float(x) for x in a.mhatoff.split(',')], dtype=np.float32)
        meshes.append(hm); a.psk = list(a.psk) + [hp_]
    for wi_, wp_ in enumerate([x for x in (a.mweaps or '').split(',') if x]):
        wm = load_psk(wp_); wm['static'] = True; wm['mweap'] = wi_; wm['bone'] = 'hand_r' if wi_ % 2 == 0 else 'hand_l'
        meshes.append(wm); a.psk = list(a.psk) + [wp_]
    if a.weapon:
        wm = load_psk(a.weapon); wm['static'] = True; wm['bone'] = 'hand_r'; wm['weapon'] = True
        meshes.append(wm); a.psk = list(a.psk) + [a.weapon]
    if a.pistol:
        pm = load_psk(a.pistol); pm['static'] = True; pm['bone'] = a.cbone or a.pistolbone; pm['pistol'] = True
        meshes.append(pm); a.psk = list(a.psk) + [a.pistol]
        if a.pistol2:
            pm2 = load_psk(a.pistol2); pm2['static'] = True; pm2['bone'] = a.pistolbone; pm2['pistol'] = True; pm2['pistol2'] = True
            meshes.append(pm2); a.psk = list(a.psk) + [a.pistol2]
    m = meshes[0]
    bones = m['bones']; names = [b['name'] for b in bones]
    bind = world_chain(names, [b['parent'] for b in bones], [(b['q'], b['p']) for b in bones])
    used_names = []
    for mm in meshes:
        mn = [b['name'] for b in mm['bones']]
        if mm.get('static'):
            sb = mm.get('bone', 'head')
            if sb not in used_names: used_names.append(sb)
        for bi in ([] if mm.get('static') else sorted(set(int(b) for b in mm['weights']['bone']))):
            if mn[bi] not in used_names: used_names.append(mn[bi])
    skin_names = [n for n in names if n in used_names]
    missing = [n for n in used_names if n not in names]
    if missing: sys.exit(f"bones missing from the first mesh's skeleton: {missing}")
    skin_index = {n: i for i, n in enumerate(skin_names)}
    nB = len(skin_names)

    mat_names = []                                          # unique material names -> texture slots
    for mm in meshes:
        for mn_ in mm['mats']:
            if mn_ not in mat_names: mat_names.append(mn_)

    vert_chunks = []; idx = []; sections = []; vbase = 0
    for pth, mm in zip(a.psk, meshes):
        for _sh in (a.shift or []):
            _nm, _v = _sh.split('=', 1)
            if _nm.lower() in os.path.basename(pth).lower(): mm['pts'] = (mm['pts'].astype(float) + np.array([float(x) for x in _v.split(',')])[None, :]).astype(np.float32)
        mnames = [b['name'] for b in mm['bones']]
        if mm.get('weapon'):
            # weapon mesh space -> hand_r bone space: the cleaver's blade runs along the bone's Y axis and extends out
            # along +X (from SK_Hunter's CleaverTrailA/B sockets): hand = (-z, y, x), then offset / extra roll
            th = np.radians(a.weaponroty); cy_, sy_ = np.cos(th), np.sin(th)
            Ry = np.array([[cy_, 0, sy_], [0, 1, 0], [-sy_, 0, cy_]])
            tx = np.radians(a.weaponrotx); cx_, sx_ = np.cos(tx), np.sin(tx)
            Rx = np.array([[1, 0, 0], [0, cx_, -sx_], [0, sx_, cx_]])
            Mw = Rx @ Ry @ np.array([[0, 0, -1.0], [0, 1, 0], [1, 0, 0]])
            if a.weaponmap:
                Mw = np.zeros((3, 3))
                for i, t in enumerate(a.weaponmap.split(',')):
                    t = t.strip(); Mw[i, 'xyz'.index(t[-1])] = -1.0 if t.startswith('-') else 1.0
                Mw = Rx @ Ry @ Mw if False else Mw
            off = np.array([float(x) for x in a.weaponoff.split(',')])
            hq, hp = bind['hand_r']
            mm['Mw'] = Mw; mm['off'] = off; mm['hq'] = np.array(hq, float); mm['hp'] = np.array(hp, float)
            wnames_ = [b['name'] for b in mm['bones']]
            mm['bind_w'] = world_chain(wnames_, [b['parent'] for b in mm['bones']], [(b['q'], b['p']) for b in mm['bones']])
            mm['pts'] = (np.array(hp, float)[None, :] + (qmat(np.array(hq, float)) @ (Mw @ mm['pts'].astype(float).T + off[:, None])).T).astype(np.float32)
        if 'mweap' in mm:      # messenger weapons: the mesh origin sits in the hand (fingers along +x like the pistol's 'hand' frame), scaled to the messenger; the game can nudge it afterwards
            sq, sp = bind[mm['bone']]; Rs = qmat(np.array(sq, float)) @ np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]], float)
            rx, ry, rz = [np.radians(float(x)) for x in a.mwrot.split(',')]
            Rx_ = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]]); Ry_ = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]]); Rz_ = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
            off = np.array([float(x) for x in a.mwoff.split(',')])
            mm['pts'] = (np.array(sp, float)[None, :] + (Rs @ (Rz_ @ Ry_ @ Rx_ @ (mm['pts'].astype(float) * a.mwscale + off).T)).T).astype(np.float32)
        if mm.get('pistol'):
            # pistol file axes (barrel = -Y, top = +Z) coincide with the socket's axes; slide / roll it with --pistoloff / --pistolrot
            pf_ = a.pistolframe; pb_ = a.pistolbone; prot_ = a.pistolrot; poff_ = a.pistoloff      # closed_note: the closed note may sit in another hand than the open one
            if not mm.get('pistol2'):
                pf_ = a.cframe or pf_; pb_ = a.cbone or pb_; prot_ = a.crot or prot_; poff_ = a.coff or poff_
            if pf_ == 'hand':
                sq, sp = bind[pb_]; Rs = qmat(np.array(sq, float))
                Mh = np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]], float)      # pistol (x,y,z) -> hand: barrel (-y) = fingers (+x), top (+z) = thumb side (-y), x = +z
                Rs = Rs @ Mh
            else:
                sq, sp = bind[a.pistolsocket]; Rs = qmat(np.array(sq, float))
            rx, ry, rz = [np.radians(float(x)) for x in prot_.split(',')]
            Rx_ = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
            Ry_ = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
            Rz_ = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
            off = np.array([float(x) for x in (poff_ or ('1.6,-7,3' if pf_ == 'hand' else '1.6,-2,3')).split(',')])
            if a.pistolcenter:      # pistolcenter: the mesh's own middle sits on the bone, --pistoloff slides it from there
                _pp = mm['pts'].astype(float); off = (poff_ and np.array([float(x) for x in poff_.split(',')])) if poff_ else np.zeros(3)
                off = off - (_pp.min(0) + _pp.max(0)) / 2.0
            mm['pts'] = (np.array(sp, float)[None, :] + (Rs @ (Rz_ @ Ry_ @ Rx_ @ (mm['pts'].astype(float) + off).T)).T).astype(np.float32)
        print(f"{os.path.basename(pth)}: {len(mm['pts'])} points, {len(mm['wedge'])} verts, {len(mm['faces'])} tris, mats {mm['mats']}")
        inf = [[] for _ in range(len(mm['pts']))]
        if mm.get('static'): inf = [[(1.0, skin_index[mm.get('bone', 'head')])] for _ in range(len(mm['pts']))]
        for w in ([] if mm.get('static') else mm['weights']):
            inf[w['pt']].append((float(w['w']), skin_index[mnames[w['bone']]]))
        over = 0
        pt_b = np.zeros((len(mm['pts']), 3), np.uint8)
        for i, l in enumerate(inf):
            l.sort(reverse=True)
            if len(l) > 2: over += 1
            l = l[:2] if l else [(1.0, 0)]
            sm = sum(x[0] for x in l)
            b0 = l[0][1]; b1 = l[1][1] if len(l) > 1 else l[0][1]
            w0 = l[0][0] / sm if len(l) > 1 else 1.0
            pt_b[i] = (b0, b1, int(round(w0 * 255)))
        if over: print(f"  points with >2 influences (truncated to 2): {over}")
        nW = len(mm['wedge'])
        verts = np.zeros(nW, dtype=[('p', '<3f4'), ('uv', '<2f4'), ('b', 'u1', 4)])
        for i, w in enumerate(mm['wedge']):
            P = (C @ mm['pts'][w['pt']].astype(float)) * SCALE
            verts['p'][i] = P
            verts['uv'][i] = (w['u'], 1.0 - w['v'] if a.flipv else w['v'])
            verts['b'][i] = (pt_b[w['pt']][0], pt_b[w['pt']][1], pt_b[w['pt']][2], 0)
        vert_chunks.append(verts)
        order = np.argsort(mm['faces']['mat'], kind='stable')
        extra = []                                           # duplicated vertices for the moving blade part
        blade_pt = None
        if mm.get('weapon') and a.weaponanim:
            bb = set(x.strip() for x in a.bladebones.split(','))
            dom = np.zeros(len(mm['pts']), int) - 1; domw = np.zeros(len(mm['pts']))
            for w in mm['weights']:
                if w['w'] > domw[w['pt']]: domw[w['pt']] = w['w']; dom[w['pt']] = w['bone']
            blade_pt = np.array([d >= 0 and mnames[d] in bb for d in dom])
            print(f"  weapon split: {int(blade_pt.sum())} blade points of {len(blade_pt)}")
        for mi, mname in enumerate(mm['mats']):
            fs = [f for f in mm['faces'][order] if f['mat'] == mi]
            if not fs: continue
            groups = [fs] if blade_pt is None else [[f for f in fs if sum(bool(blade_pt[mm['wedge'][int(x)]['pt']]) for x in f['w']) < 2],
                                                     [f for f in fs if sum(bool(blade_pt[mm['wedge'][int(x)]['pt']]) for x in f['w']) >= 2]]
            for gi, grp in enumerate(groups):
                if not grp: continue
                start = len(idx)
                for f in grp:
                    if gi == 1:                              # blade face: private copies of its 3 vertices, flagged (pad byte = 1)
                        ids = []
                        for x in f['w']:
                            v = verts[int(x)].copy(); v['b'][3] = 1; extra.append(v); ids.append(nW + len(extra) - 1 + vbase)
                        i0, i1, i2 = ids
                    else:
                        if blade_pt is not None:
                            for x in f['w']: verts['b'][int(x)][3] = 2      # still part of the weapon (the haft): flag 2, so the game can slide / turn / raise it
                        i0, i1, i2 = (int(x) + vbase for x in f['w'])
                    idx += [i0, i2, i1]                      # reflection flips the winding
                sections.append((start, len(idx) - start, mat_names.index(mname), (3 if mm.get('pistol2') else (2 if mm.get('pistol') else (10 + mm['mhat'] if 'mhat' in mm else (5 + mm['mweap'] if 'mweap' in mm else 0))))))
        if extra:
            vert_chunks.append(np.array(extra, dtype=verts.dtype)); nW += len(extra)
        vbase += nW
    nW = vbase
    verts = np.concatenate(vert_chunks)
    if nW > 65535: sys.exit("too many vertices for 16-bit indices")
    print(f"total: {nW} verts, {len(idx)//3} tris, {nB} skinned bones")

    # ---- textures
    tex_list = []
    for mn in mat_names:
        base = 'T_' + mn[3:] if mn.startswith('MI_') else mn
        tmap = dict(kv.split('=', 1) for kv in a.texmap.split(',') if '=' in kv)
        base = tmap.get(mn, base)
        hit = []
        if a.tex:
            hit = [p for d_ in a.tex for p in glob.glob(os.path.join(d_, '**', '*.png'), recursive=True) if os.path.splitext(os.path.basename(p))[0].lower() == base.lower()]
        if not hit:
            print(f"WARNING: no texture {base}.png found under {a.tex}"); tex_list.append(None)
        else:
            im = load_texture(hit[0], a.maxtex)
            tints = {}
            if a.tint != 'none':
                for part in a.tint.split(';'):
                    if '=' in part: tints[part.split('=')[0]] = [float(x) for x in part.split('=')[1].split(',')]
            if mn in tints:
                arr = np.asarray(im).astype(np.float32)
                lum = (arr[..., 0] * 0.299 + arr[..., 1] * 0.587 + arr[..., 2] * 0.114)
                k = lum / max(1.0, lum.mean())
                col = np.array(tints[mn], np.float32)
                arr[..., :3] = np.clip(col[None, None, :] * k[..., None], 0, 255)
                im = Image.fromarray(arr.astype(np.uint8), 'RGBA')
                print(f"  tinted {mn} -> {tuple(int(x) for x in col)}")
            tex_list.append((base, im)); print(f"texture {base}: {im.size}")

    # ---- animations
    files = []
    for src in a.psa:
        files += [src] if os.path.isfile(src) else sorted(glob.glob(os.path.join(src, '**', '*.psa'), recursive=True))
    attach_names = a.attach.split(',')
    anims = []
    for f in files:
        for s in load_psa(f):
            if a.psaonly and not any(t.lower() in s['name'].lower() for t in a.psaonly.split(',')):
                continue
            if any(x[0] == s['name'] for x in anims):
                continue                              # same sequence found twice (single .psa and AM_ montage export)
            for n_ in skin_names:      # sock_bone: a socket (e.g. NoteSocket) is in the mesh skeleton but not in the animation: hang it off its parent at its bind pose
                if n_ not in s['bones']:
                    bi_ = names.index(n_); pn_ = names[bones[bi_]['parent']] if bones[bi_]['parent'] >= 0 else None
                    if pn_ in s['bones']:
                        s['bones'] = list(s['bones']) + [n_]; s['parents'] = list(s['parents']) + [list(s['bones']).index(pn_)]
                        k0_ = s['keys']; k1_ = np.empty((k0_.shape[0], k0_.shape[1] + 1), dtype=k0_.dtype); k1_[:, :-1] = k0_
                        k1_['p'][:, -1] = np.array(bones[bi_]['p'], np.float32); k1_['q'][:, -1] = np.array(bones[bi_]['q'], np.float32); k1_['t'][:, -1] = 0.0; s['keys'] = k1_
            if not all(n in s['bones'] for n in skin_names):
                print(f"skip {s['name']}: missing skin bones"); continue
            tvec = (0.0, 0.0)                         # game-space metres, relative to the facing direction (+X fwd, +Y right)
            # --- root motion: the game moves the player itself, so cancel horizontal travel baked into the root bone
            rn = 'root@@@' if 'root@@@' in s['bones'] else s['bones'][0]          # creatures: the first bone is the root
            if a.rootmotion == 'strip' and rn in s['bones']:
                ri = s['bones'].index(rn); pi = s['parents'][ri]
                s['keys'] = np.array(s['keys'])          # writable copy
                Ws = [world_chain(s['bones'], s['parents'], [(s['keys'][fr][i]['q'], s['keys'][fr][i]['p']) for i in range(len(s['bones']))]) for fr in range(s['n'])]
                p0 = np.array(Ws[0][rn][1], float)
                travel = max(np.linalg.norm((np.array(W_[rn][1], float) - p0)[:2]) for W_ in Ws)
                if travel > 30.0:
                    pname = s['bones'][pi] if pi >= 0 else None
                    for fr in range(s['n']):
                        d = np.array(Ws[fr][rn][1], float) - p0; d[2] = 0.0
                        pq = np.array(Ws[fr][pname][0], float) if pname else np.array([0, 0, 0, 1.0])
                        ld = qrot(qconj(pq), d)
                        lp = np.array(s['keys'][fr][ri]['p'], float) - ld
                        s['keys'][fr][ri]['p'] = lp
                    dend = np.array(Ws[-1][rn][1], float) - p0     # file space cm
                    tvec = (float(-dend[1] * SCALE), float(-dend[0] * SCALE))   # file -> game axes: x=-y, y=-x
                    print(f"  {s['name']}: stripped {travel:.0f} cm of root motion over {s['n']/s['fps']:.2f} s  ({travel/100/(s['n']/s['fps']):.1f} m/s)")
            if a.bindpos:                                        # animations made for another skeleton (other limb lengths): keep their rotations, use THIS mesh's bone lengths (no stretched limbs)
                s['keys'] = np.array(s['keys'])
                mpos = {b['name']: b['p'] for b in bones}
                par = s['parents']; depth = []
                for i_ in range(len(par)):
                    d_ = 0; j_ = i_
                    while par[j_] >= 0 and d_ < 64: j_ = par[j_]; d_ += 1
                    depth.append(d_)
                for i_, nm_ in enumerate(s['bones']):
                    if depth[i_] >= 3 and nm_ in mpos:
                        for fr_ in range(s['n']): s['keys'][fr_][i_]['p'] = mpos[nm_]
            frames = []
            for fr in range(s['n']):
                W = world_chain(s['bones'], s['parents'], [(s['keys'][fr][i]['q'], s['keys'][fr][i]['p']) for i in range(len(s['bones']))])
                mats = []
                for n in skin_names:
                    aq, ap_ = W[n]; bq, bp = bind[n]
                    Rb = qmat(qconj(bq)); Ra = qmat(aq)
                    R = Ra @ Rb                                      # = A * inv(B) rotation part
                    t = ap_ - R @ bp
                    Rg, tg = convert_mat(R, t); mats.append(to34(Rg, tg))
                att = []
                for n in attach_names:
                    aq, ap_ = W[n] if n in W else W[skin_names[0]]; Rg, tg = convert_mat(qmat(aq), ap_); att.append(to34(Rg, tg))     # a creature without that bone: use its first bone
                frames.append(np.concatenate(mats + att))
            frames = np.array(frames)
            fps = s['fps']
            tfps_ = a.fps
            for _sf in [x for x in a.slowfps.split(',') if '=' in x]:
                if _sf.split('=')[0].lower() in s['name'].lower(): tfps_ = float(_sf.split('=')[1])
            if tfps_ and abs(tfps_ - fps) > 1e-3:            # resample (linear matrix lerp)
                n_new = max(2, int(round(s['n'] * tfps_ / fps)))
                t = np.linspace(0, s['n'] - 1, n_new)
                lo = np.floor(t).astype(int); hi = np.minimum(lo + 1, s['n'] - 1); fr_ = (t - lo)[:, None]
                frames = frames[lo] * (1 - fr_) + frames[hi] * fr_; fps = tfps_
            anims.append((s['name'], fps, frames.astype('<f4'), tvec))
            print(f"anim {s['name']}: {len(frames)} frames @ {fps:.1f} fps")

    # ---- weapon animations (the weapon's own skeleton: Cleaver_Open / Cleaver_Close ...)
    wanims = []
    wm_ = next((mm for mm in meshes if mm.get('weapon')), None)
    if a.weaponanim and wm_ is not None:
        wf = []
        for src in a.weaponanim:
            wf += [src] if os.path.isfile(src) else sorted(glob.glob(os.path.join(src, '**', '*.psa'), recursive=True))
        # weapon file space -> game bind space:  P = Mg p + tg   (Mg includes the 0.01 scale)
        Rh = qmat(wm_['hq']); Mg = SCALE * (C @ Rh @ wm_['Mw']); tg = SCALE * (C @ (wm_['hp'] + Rh @ wm_['off']))
        Mgi = np.linalg.inv(Mg)
        d0, d1 = [x.strip() for x in a.damagebones.split(',')]
        bb = [x.strip() for x in a.bladebones.split(',')]
        for f in wf:
            for s_ in load_psa(f):
                if any(x[0] == s_['name'] for x in wanims): continue
                if a.transformbone not in s_['bones']:
                    print(f"skip weapon anim {s_['name']}: no '{a.transformbone}' bone"); continue
                frames = []
                for fr in range(s_['n']):
                    W = world_chain(s_['bones'], s_['parents'], [(s_['keys'][fr][i]['q'], s_['keys'][fr][i]['p']) for i in range(len(s_['bones']))])
                    bq, bp = wm_['bind_w'][a.transformbone]; aq, ap_ = W[a.transformbone]
                    Rw = qmat(aq) @ qmat(qconj(bq)); tw = ap_ - Rw @ bp
                    R = Mg @ Rw @ Mgi; t = tg - R @ tg + Mg @ tw
                    def bpos(nm):                         # animated position; bones the .psa doesn't carry follow the transformer bone
                        if nm in W: return np.array(W[nm][1], float)
                        return Rw @ np.array(wm_['bind_w'][nm][1], float) + tw
                    ds = Mg @ bpos(d0) + tg; de = Mg @ bpos(d1) + tg
                    frames.append(np.concatenate([to34(R, t), ds.astype('<f4'), de.astype('<f4')]))
                wanims.append((s_['name'], s_['fps'], np.array(frames, '<f4')))
                print(f"weapon anim {s_['name']}: {len(frames)} frames @ {s_['fps']:.1f} fps")

    # ---- write
    out = bytearray(b'BBH2')
    out += struct.pack('<7I', nW, len(idx), nB, len(anims), len(attach_names), len(sections), len(tex_list))
    for t in tex_list:
        if t is None:
            out += struct.pack('<BHH', 0, 1, 1) + bytes([128, 128, 128, 255])
        else:
            nm = t[0].encode(); out += struct.pack('<B', len(nm)) + nm + struct.pack('<HH', *t[1].size) + t[1].tobytes()
    for st, cnt, mi, fl in sections:
        out += struct.pack('<IIHH', st, cnt, mi, fl)
    out += verts.tobytes()
    out += np.array(idx, '<u2').tobytes()
    for n in attach_names: out += n.encode()[:16].ljust(16, b'\0')
    for nm, fps, fr, tv in anims:
        out += nm.encode()[:32].ljust(32, b'\0') + struct.pack('<fIff', fps, len(fr), tv[0], tv[1]) + fr.tobytes()
    if wanims:                                               # trailing block: weapon animations (older loaders ignore it)
        out += b'WPN1' + struct.pack('<I', len(wanims))
        for nm, fps, fr in wanims:
            out += nm.encode()[:32].ljust(32, b'\0') + struct.pack('<fI', fps, len(fr)) + fr.tobytes()
    open(a.out, 'wb').write(out)
    print(f"\nwrote {a.out}: {len(out)/1024:.0f} KB  ({nW} verts, {len(idx)//3} tris, {nB} bones, {len(anims)} anims)")

if __name__ == '__main__':
    main()
