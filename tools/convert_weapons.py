#!/usr/bin/env python3
"""Pack the player's weapon meshes into weapons.bin ("BBW1"): every weapon is glued rigidly to the Hunter's hand_r (right-hand weapons)
or hand_l (left-hand weapons) in the Hunter's bind pose, exactly like the cleaver and the pistol inside hunter.bin. The game appends these
meshes to the Hunter at start-up and draws only the ones that are equipped, so hunter.bin does not need to be rebuilt.

  python3 assets/tools/convert_weapons.py --hunter assets/Char/Hunter/Mesh/SkM_AttireHunter.psk --root assets/BP/PlayerWeapons --out weapons.bin

Tuning a weapon that sits wrong in the hand (names: pistol axe bloodspear bom_r bom_l blunderbuss dbshotgun flamesprayer torch cane tonitrus):
  --map NAME=-z,-y,-x     which weapon-file axes become the hand's x,y,z (right-hand weapons; default = the cleaver's)
  --off NAME=x,y,z        slide it in the hand frame, cm (right hand) / in the weapon file's own axes (left hand)
  --rot NAME=rx,ry,rz     extra rotation, degrees (right hand: about the hand axes; left hand: about the gun file's axes)
  --gunrot rx,ry,rz       the tilt given to ALL held guns (default -20,0,0 = a subtle forward tilt); --gunrot 60,0,0 tilts the other way, 0,0,0 = untilted
  --size NAME=1.2         scale the weapon
  --only axe,torch        build just these (everything else keeps its default)
bin layout: u32 count; per weapon { char name[16]; u8 side (0 = right, 1 = left); u8 pad[3]; u32 nTex, nSec, nV, nI;
  nTex x { u8 nameLen, name, u16 w, u16 h, RGBA }; nSec x { u32 start, u32 count, u16 tex, u16 pad }; nV x { f32 x y z u v }; nI x u16 }   (positions: Hunter bind pose, game space, metres)"""
import argparse, glob, os, struct, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convert_hunter as ch

# name, side, mesh (under --root), material -> texture file (no .png) hints
WEAPONS = [
    ('axe',          'R', 'HunterAxe/Mesh/SkM_Axe.psk',                {'MI_Axe': 't_axe'}),
    ('bloodspear',   'R', 'BloodSpear/Mesh/SkM_BloodSpear.psk',        {'MI_Cleaver': 't_bloodspear', 'MI_BloodSpear': 't_bloodspear'}),
    ('bom_r',        'R', 'BladesOfMercy/Mesh/SM_BomR.pskx',           {'MI_BladesOfMercy': 't_bladesofmercy'}),
    ('bom_l',        'L', 'BladesOfMercy/Mesh/SM_BomL.pskx',           {'MI_BladesOfMercy': 't_bladesofmercy'}),
    ('pistol',       'L', 'HunterPistol/Mesh/SM_Hunter_Pistol.pskx',   {'MI_Pistol': 't_pistol'}),
    ('blunderbuss',  'L', 'Blunderbuss/Mesh/SM_Blunderbuss.pskx',      {'MI_Blunderbuss': 't_blunder'}),
    ('dbshotgun',    'L', 'DBShotgun/Mesh/SkM_DBShotgun.psk',          {'MI_DBShotgun': 'DBShotgun', 'MI_DBShotgunDesat': 'DBShotgun'}),
    ('flamesprayer', 'L', 'Flamesprayer/Mesh/SM_Flamesprayer.pskx',    {'MI_Flamesprayer': 'FlamesprayerTexSource'}),
    ('torch',        'L', 'Torch/Mesh/SM_Torch.pskx',                  {'MI_Torch': 'T_YhrmtTorch_Source', 'MI_Wood': 'T_YhrmtTorch_Source', 'MI_CloudySky': 'T_YhrmtTorch_Source'}),
    ('cane',         'R', 'ThreadedCane/Mesh/SM_ThreadedCane.pskx',    {'MI_ThreadedCane': 'T_Cane'}),
    ('cane_t',       'R', 'ThreadedCane/Mesh/SkM_ThreadedCaneTrans.psk', {'MI_ThreadedCane': 'T_Cane'}),      # the cane's second form: shown instead of 'cane' once it has transformed (placeholder swap half way through ThreadedCane_Transform)
    ('tonitrus',     'R', 'Tonitrus/Mesh/SkM_Tonitrus.psk',            {'MI_Tonitrus': 't_tonitrus'}),
    ('moonlight',    'R', 'Moonlight/Mesh/SkM_Moonlight.psk',          {'MI_MoonlightHilt': 't_moonlighthilt', 'MI_MoonlightBlade': 't_moonlightblade'}),      # the Holy Moonlight Sword (weapon id 15): skipped when its folder is not under --root (make_moonlight.sh copies it there)
    ('moonlight_t',  'R', 'Moonlight/Mesh/SkM_Moonlight.psk',          {'MI_MoonlightHilt': 't_moonlighthilt', 'MI_MoonlightBlade': 't_moonlightblade'}),      # its second form (drawn instead once it is gripped in both hands): the same mesh with its 'BladeOut' shape applied, which grows the blade of light out of the steel
]

XFORM = ('bloodspear', 'axe', 'burial')      # weapons with a transform (Open/Close) animation set: their moving blade part is split off and animated at run time like the cleaver's

# weapons whose transform animations are not called Open/Close: .psa base name (lower case) -> role. A missing 'close' is made by playing 'open' backwards.
XALIAS = {'axe': {'animaxe_2htransform': 'open', 'animaxe_idletrans': 'openidle', 'animaxe_idleuntrans': 'closedidle'}}

# default slide of left-hand weapons in the gun file's own axes, cm (x,y,z); z = up the gun's top. The flamesprayer sat too low in the hand: +4 cm
DEFOFF = {'flamesprayer': '1.6,-7,7'}

AUTOOFF = '6,0,0'      # cm along the hand bone (down the arm): the fist is further along than the wrist bone, so a blade held at the bone sat too high. Lower numbers = higher, bigger = lower
AUTO = ('bom_r', 'bom_l')      # blades: no fixed file axes to rely on, so each blade's own shape decides: its long axis becomes the hand's forward (+X), its flat face the hand's Y, and the grip (just in from the handle end) sits in the palm
GUNS = ('pistol', 'blunderbuss', 'dbshotgun', 'flamesprayer')      # held guns: tilted with --gunrot so the barrel points forward and the stock lies along the forearm

def kv(items):
    d = {}
    for s in items or []:
        k, v = s.split('=', 1); d[k.strip()] = v.strip()
    return d

def find_png(dirs, base):
    for d in dirs:
        for p in glob.glob(os.path.join(d, '**', '*.png'), recursive=True):
            if os.path.splitext(os.path.basename(p))[0].lower() == base.lower(): return p
    return None

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--hunter', required=True, help='SkM_AttireHunter.psk (the Hunter\'s skeleton: gives the hand bones\' bind pose)')
    ap.add_argument('--root', required=True, help='assets/BP/PlayerWeapons')
    ap.add_argument('--tex', nargs='*', default=[], help='extra folders searched for PNG textures (the torch has none of its own: Yharnamites/Mat has T_YhrmtTorch_Source)')
    ap.add_argument('--out', default='weapons.bin')
    ap.add_argument('--maxtex', type=int, default=128)
    ap.add_argument('--map', action='append'); ap.add_argument('--off', action='append'); ap.add_argument('--rot', action='append'); ap.add_argument('--size', action='append')
    ap.add_argument('--gunrot', default='-20,0,0', help='tilt of every held gun (pistol, blunderbuss, shotgun, flamesprayer) about the gun file axes, degrees rx,ry,rz: rx negative pitches the barrel up toward the thumb side (forward when the arm hangs), positive pitches it the other way; 0,0,0 = as before')
    ap.add_argument('--only', default=None)
    ap.add_argument('--burial', action='store_true', help="adds Gehrman's Burial Blade as its own weapon (id 14) (assets/BP/PlayerWeapons/BurialBlade, built by make_scythe.py); the hand is slid 62 cm up the haft toward the blade (override with --off bloodspear=x,y,z)")
    ap.add_argument('--noauto', action='store_true', help='use the old fixed axes for the Blades of Mercy instead of working them out from the mesh')
    ap.add_argument('--grip', default='0.12', help='how far in from the handle end the hand holds an auto-oriented blade (fraction of its length)')
    ap.add_argument('--bladebones', default='transformer,transformer_end,damagestart,damageend,transspark', help='bones (lower case) of the weapon skeleton that belong to the moving blade part')
    ap.add_argument('--xbone', default='transformer', help='the bone the Open/Close animations move (case-insensitive)')
    ap.add_argument('--damagebones', default='damagestart,damageend', help='the two bones marking the damaging edge')
    ap.add_argument('--noanim', action='store_true', help='skip the transform animations')
    ap.add_argument('--keepflip', action='store_true', help='cane whip form: keep the root bone motion of its animations (by default it is cancelled so the cane does not flip over)')
    a = ap.parse_args()
    maps, offs, rots, sizes = kv(a.map), kv(a.off), kv(a.rot), kv(a.size)
    for d_ in (maps, offs, rots, sizes):
        if 'cane' in d_ and 'cane_t' not in d_: d_['cane_t'] = d_['cane']                # both forms share the tuning
    only = set(x.strip() for x in a.only.split(',')) if a.only else None
    if a.burial:      # the Burial Blade is its own weapon (id 14), next to the Blood Spear
        WEAPONS.append(('burial', 'R', 'BurialBlade/Mesh/SkM_BurialBlade.psk', {'MI_BurialBlade': 't_burialblade'}))
        offs.setdefault('burial', '9,-62,0'); rots.setdefault('burial', '90,0,90')      # the hand bones lie along the arm (+X points down): blade onto the hand's +Y, rolled so the edge faces down; the hand slid up the haft along that axis

    hm = ch.load_psk(a.hunter); bones = hm['bones']; names = [b['name'] for b in bones]
    bind = ch.world_chain(names, [b['parent'] for b in bones], [(b['q'], b['p']) for b in bones])
    texdirs = [a.root] + list(a.tex)
    out = []; total_v = 0; wanims_all = {}; vanims_all = {}
    for name, side, rel, mathint in WEAPONS:
        if only and name not in only: continue
        path = os.path.join(a.root, rel)
        if not os.path.exists(path):
            alt = path.rsplit('.', 1)[0] + '.usda'
            if os.path.exists(alt): path = alt
            else: print(f"{name}: {rel} not found - skipped"); continue
        mm = ch.load_psk(path)
        if name == 'moonlight_t':      # the blade of light lies folded flat inside the steel in the file; its morph target ('BladeOut') spreads it out. (The export stores the morph's Y the other way round from the points, like the other .psk morphs: flipped back here, so the blade grows longer, not shorter)
            raw = open(path, 'rb').read(); o_ = 0; mp = None
            while o_ + 32 <= len(raw):
                cn = raw[o_:o_ + 20].split(b'\0')[0]; _f, csz, cnt = struct.unpack_from('<iii', raw, o_ + 20); o_ += 32
                if cn == b'MRPHDATA': mp = [struct.unpack_from('<6fI', raw, o_ + i * csz) for i in range(cnt)]
                o_ += csz * cnt
            if mp:
                pts_ = mm['pts'].astype(np.float32).copy(); k_ = float(os.environ.get('ML_MORPH', '1.0')); sy_ = float(os.environ.get('ML_MORPH_Y', '-1'))
                r0_ = mm['pts'].astype(np.float32); dl_ = {int(pi): np.array([dx * k_, sy_ * dy * k_, dz * k_], np.float32) for dx, dy, dz, _nx, _ny, _nz, pi in mp}; tw_ = 0
                for i_ in range(len(r0_)):      # blade_gap: the export leaves out the copies of a point (the mesh stores a corner once per face that meets there), so those copies stayed behind and tore a gap in the blade of light. Every point that sits exactly where a moved point sits moves with it
                    if i_ in dl_: continue
                    for j_ in list(dl_):
                        if j_ < len(r0_) and float(np.abs(r0_[i_] - r0_[j_]).max()) < 0.05: dl_[i_] = dl_[j_]; tw_ += 1; break
                for pi, dv in dl_.items(): pts_[pi] += dv
                print(f"  moonlight_t: {tw_} copied points moved with their twins")
                mm['pts'] = pts_; print(f"  moonlight_t: blade of light spread out ({len(mp)} points), now {np.ptp(pts_[:, 1]):.0f} cm long")
            else: print('  moonlight_t: no BladeOut shape in the file - the second form looks like the first')
        pts = mm['pts'].astype(float) * float(sizes.get(name, 1.0))
        Mauto = None
        if name in AUTO and not a.noauto:
            c0 = pts.mean(0); w_, v_ = np.linalg.eigh(np.cov((pts - c0).T)); d = v_[:, 2]; nrm = v_[:, 0]      # long axis, flattest axis
            t_ = (pts - c0) @ d; lo, hi = t_.min(), t_.max(); L = hi - lo
            def rad(sel): q_ = pts[sel] - c0; q_ = q_ - np.outer(q_ @ d, d); return float(np.sqrt((q_ ** 2).sum(1)).mean()) if sel.any() else 0.0
            if rad(t_ < lo + 0.25 * L) > rad(t_ > hi - 0.25 * L): d = -d; t_ = -t_; lo, hi = t_.min(), t_.max()      # the wider end is the blade: point it forward
            nrm = nrm - (nrm @ d) * d; nrm /= np.linalg.norm(nrm)
            grip = c0 + d * (lo + float(a.grip) * L)
            # the hand bones lie along the arm (hand +X points down and out in the bind pose), so a blade along +X pointed at the floor. A blade held in a fist points forward, which is the hand's +Y (right hand) or -Y (left hand: its Y axis is mirrored)
            # the flat face looks outward (hand +Z, away from the body), so the blade is seen broadside from the side, not edge-on from behind
            Mauto = np.array([np.cross(d, nrm), d, nrm]) if side == 'R' else np.array([np.cross(-d, nrm), -d, nrm])
            pts = pts - grip
            print(f"  {name}: auto orientation. length {L:.1f} cm, long axis in the file {np.round(d, 2)}, flat face {np.round(nrm, 2)}, grip in the palm, blade pointing forward")
        if side == 'R':
            # the cleaver's mapping (see convert_hunter.py): weapon file -> hand_r bone space, blade out along +X, rolled 180 about X
            tx = np.radians(180.0); Rx = np.array([[1, 0, 0], [0, np.cos(tx), -np.sin(tx)], [0, np.sin(tx), np.cos(tx)]])
            Mw = Rx @ np.array([[0, 0, -1.0], [0, 1, 0], [1, 0, 0]])
            if Mauto is not None: Mw = Mauto
            if name in maps:
                Mw = np.zeros((3, 3))
                for i, t in enumerate(maps[name].split(',')):
                    t = t.strip(); Mw[i, 'xyz'.index(t[-1])] = -1.0 if t.startswith('-') else 1.0
            rx, ry, rz = [np.radians(float(x)) for x in rots.get(name, '0,0,0').split(',')]
            Rx_ = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
            Ry_ = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
            Rz_ = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
            off = np.array([float(x) for x in offs.get(name, AUTOOFF if Mauto is not None else '0,0,0').split(',')])
            hq, hp = bind['hand_r']
            P = np.array(hp, float)[None, :] + (ch.qmat(np.array(hq, float)) @ (Rz_ @ Ry_ @ Rx_ @ Mw @ pts.T + off[:, None])).T
            Mg = ch.SCALE * (ch.C @ ch.qmat(np.array(hq, float)) @ (Rz_ @ Ry_ @ Rx_ @ Mw)) * float(sizes.get(name, 1.0))
            tg = ch.SCALE * (ch.C @ (np.array(hp, float) + ch.qmat(np.array(hq, float)) @ off))
        else:
            # the pistol's mapping: barrel = file -Y, top = file +Z; it lies along the fingers of hand_l
            sq, sp = bind['hand_l']; Rs = ch.qmat(np.array(sq, float)) @ (Mauto if Mauto is not None else np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]], float))
            rx, ry, rz = [np.radians(float(x)) for x in rots.get(name, a.gunrot if name in GUNS else '0,0,0').split(',')]
            Rx_ = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
            Ry_ = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
            Rz_ = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
            if Mauto is not None:      # auto blades: --off is in the hand frame (cm) here too, like the right hand
                offh = np.array([float(x) for x in offs.get(name, AUTOOFF).split(',')])
                P = np.array(sp, float)[None, :] + (Rs @ (Rz_ @ Ry_ @ Rx_ @ pts.T)).T + (ch.qmat(np.array(sq, float)) @ offh)[None, :]
            else:
                off = np.array([float(x) for x in offs.get(name, DEFOFF.get(name, '1.6,-7,3')).split(',')])
                P = np.array(sp, float)[None, :] + (Rs @ (Rz_ @ Ry_ @ Rx_ @ (pts + off).T)).T
        G = (ch.C @ P.T).T * ch.SCALE                                    # file space (cm) -> game space (m)
        mats = mm['mats'] or ['MI_none']
        # textures: one per material
        tex = []
        for mn in mats:
            base = mathint.get(mn) or ('T_' + mn[3:] if mn.startswith('MI_') else mn)
            hit = find_png(texdirs, base) or find_png(texdirs, "T_" + mn[3:])
            if not hit:                                              # fall back: the only PNG in this weapon's own folder
                own = glob.glob(os.path.join(os.path.dirname(os.path.dirname(path)), '**', '*.png'), recursive=True)
                if len(own) == 1: hit = own[0]
            if hit:
                im = ch.load_texture(hit, a.maxtex); tex.append((base, im)); print(f"  texture {base}: {im.size}")
            else:
                print(f"  WARNING {name}: no texture for material {mn} (looked for {base}.png) - flat grey")
                tex.append((base, Image.new('RGBA', (4, 4), (110, 105, 100, 255))))
        wedge, faces = mm['wedge'], mm['faces']
        nW = len(wedge)
        verts = np.zeros((nW, 5), '<f4')
        for i, w in enumerate(wedge):
            verts[i, :3] = G[w['pt']]; verts[i, 3] = w['u']; verts[i, 4] = w['v']
        order = np.argsort(faces['mat'], kind='stable'); idx = []; secs = []
        blade_pt = None
        if name in XFORM and side == 'R' and not a.noanim and len(mm.get('weights', [])):
            bnames = [b['name'] for b in mm['bones']]; bb = set(x.strip().lower() for x in a.bladebones.split(','))
            dom = np.zeros(len(mm['pts']), int) - 1; domw = np.zeros(len(mm['pts']))
            for w in mm['weights']:
                if w['w'] > domw[w['pt']]: domw[w['pt']] = w['w']; dom[w['pt']] = w['bone']
            blade_pt = np.array([d >= 0 and bnames[d].lower() in bb for d in dom])
            print(f"  {name} skeleton bones: {bnames}\n  blade split: {int(blade_pt.sum())} blade points of {len(blade_pt)}")
            if not blade_pt.any(): blade_pt = None
        extra = []
        for mi in range(len(mats)):
            fs = [f for f in faces[order] if f['mat'] == mi]
            if not fs: continue
            groups = [fs] if blade_pt is None else [[f for f in fs if sum(bool(blade_pt[wedge[int(x)]['pt']]) for x in f['w']) < 2], [f for f in fs if sum(bool(blade_pt[wedge[int(x)]['pt']]) for x in f['w']) >= 2]]
            for gi, grp in enumerate(groups):
                if not grp: continue
                st = len(idx)
                for f in grp:
                    if gi == 1:                                  # blade face: private copies of its vertices
                        ids = []
                        for x in f['w']: extra.append(verts[int(x)].copy()); ids.append(nW + len(extra) - 1)
                        i0, i1, i2 = ids
                    else:
                        i0, i1, i2 = (int(x) for x in f['w'])
                    idx += [i0, i2, i1]                          # the axis map mirrors: flip the winding
                secs.append((st, len(idx) - st, mi, gi))
        if extra: verts = np.concatenate([verts, np.array(extra, '<f4')]); nW += len(extra)
        if blade_pt is not None:
            wf = []
            for fp in sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(path)), 'Anim', '*.psa'))):
                bn = os.path.splitext(os.path.basename(fp))[0].lower()
                if bn.rsplit('_', 1)[-1] in ('open', 'close', 'openidle', 'closedidle') or bn in ('open', 'close', 'openidle', 'closedidle') or bn in XALIAS.get(name, {}): wf.append(fp)
            allpsa = sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(path)), 'Anim', '*.psa')))
            print(f"  {name}: transform .psa files used: {[os.path.basename(x) for x in wf]}  (all in its Anim folder: {[os.path.basename(x) for x in allpsa]})")
            xb = a.xbone.lower(); d0, d1 = [x.strip().lower() for x in a.damagebones.split(',')]
            if name == 'burial': d0, d1 = 'transformer', 'transformer_end'      # the Burial Blade has no DamageStart / DamageEnd bones: its edge runs hinge -> tip, so the paper's fire / sparks and the hits sit on the blade, not the haft
            Mgi = np.linalg.inv(Mg); bw = ch.world_chain(bnames, [b['parent'] for b in mm['bones']], [(b['q'], b['p']) for b in mm['bones']])
            bwl = {k.lower(): v for k, v in bw.items()}; anl = []
            for fp in wf:
                for s_ in ch.load_psa(fp):
                    bl = {n_.lower(): n_ for n_ in s_['bones']}
                    if xb not in bl: print(f"  skip anim {s_['name']}: no '{xb}' bone (it has {s_['bones']})"); continue
                    if any(x[0] == s_['name'] for x in anl): continue
                    frames = []
                    for fr in range(s_['n']):
                        W = ch.world_chain(s_['bones'], s_['parents'], [(s_['keys'][fr][i]['q'], s_['keys'][fr][i]['p']) for i in range(len(s_['bones']))])
                        Wl = {k.lower(): v for k, v in W.items()}
                        bq, bp = bwl[xb]; aq, ap_ = Wl[xb]
                        Rw = ch.qmat(aq) @ ch.qmat(ch.qconj(bq)); tw = ap_ - Rw @ bp
                        R = Mg @ Rw @ Mgi; t = tg - R @ tg + Mg @ tw
                        def bpos(nm):
                            if nm in Wl: return np.array(Wl[nm][1], float)
                            return Rw @ np.array(bwl[nm][1], float) + tw
                        ds = Mg @ bpos(d0) + tg if d0 in bwl else tg; de = Mg @ bpos(d1) + tg if d1 in bwl else tg
                        frames.append(np.concatenate([ch.to34(R, t), ds.astype('<f4'), de.astype('<f4')]))
                    role = XALIAS.get(name, {}).get(os.path.splitext(os.path.basename(fp))[0].lower())
                    anl.append((f"{name}_{role}" if role else s_['name'], s_['fps'], np.array(frames, '<f4')))
                    print(f"  transform anim {s_['name']}: {len(frames)} frames @ {s_['fps']:.1f} fps")
                    fa_ = np.array(frames); Rs_ = fa_[:, :9].reshape(-1, 3, 3); cs_ = np.clip((np.einsum('fij,ij->f', Rs_, Rs_[0]) - 1) / 2, -1, 1)
                    mv_ = []
                    for bi_, bn_ in enumerate(s_['bones']):
                        k0, k1 = s_['keys'][0][bi_], s_['keys'][-1][bi_]
                        mv_.append((float(np.linalg.norm(np.array(k1['p'], float) - np.array(k0['p'], float))) + 100 * float(np.linalg.norm(np.array(k1['q'], float) - np.array(k0['q'], float))), bn_))
                    print(f"    moves: blade part turns up to {np.degrees(np.arccos(cs_.min())):.0f} deg; bones that change most in this .psa: {[b_ for m_, b_ in sorted(mv_, reverse=True)[:5]]}")
            have = [x[0].lower().rsplit('_', 1)[-1] for x in anl]
            if 'open' in have and 'close' not in have:                   # no close animation: the open one played backwards
                o = next(x for x in anl if x[0].lower().rsplit('_', 1)[-1] == 'open')
                anl.append((f"{name}_close", o[1], np.ascontiguousarray(o[2][::-1])))
                print(f"  {name}: no close animation found - using the open animation reversed")
            if anl: wanims_all[name] = anl
        if name == 'cane_t' and len(mm.get('weights', [])):                  # the whip form: its skeleton's animations baked into per-vertex positions
            bn2 = [b['name'] for b in mm['bones']]; bw2 = ch.world_chain(bn2, [b['parent'] for b in mm['bones']], [(b['q'], b['p']) for b in mm['bones']])
            P0 = mm['pts'].astype(float); wsum = np.zeros(len(P0)); 
            for w in mm['weights']: wsum[w['pt']] += float(w['w'])
            Rmap = ch.qmat(np.array(hq, float)); Rrot = Rz_ @ Ry_ @ Rx_ @ Mw; sz = float(sizes.get(name, 1.0)); va = []
            for fp in sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(path)), 'Anim', 'ThreadedCane_*.psa'))):
                bnm = os.path.splitext(os.path.basename(fp))[0].lower()
                if not (bnm.endswith('_transform') or bnm.endswith('_idle')): continue
                for s_ in ch.load_psa(fp):
                    fr_all = []
                    for fr in range(s_['n']):
                        W = ch.world_chain(s_['bones'], s_['parents'], [(s_['keys'][fr][i]['q'], s_['keys'][fr][i]['p']) for i in range(len(s_['bones']))])
                        Wl = {k.lower(): v for k, v in W.items()}; sk = np.zeros_like(P0)
                        for w in mm['weights']:
                            nm_ = bn2[w['bone']]; pt = w['pt']; ww = float(w['w']) / max(wsum[pt], 1e-6)
                            if nm_.lower() in Wl:
                                aq, ap_ = Wl[nm_.lower()]; bq, bp = bw2[nm_]; M = ch.qmat(aq) @ ch.qmat(ch.qconj(bq)); sk[pt] += ww * (M @ P0[pt] + (np.array(ap_, float) - M @ np.array(bp, float)))
                            else: sk[pt] += ww * P0[pt]
                        for pt in np.nonzero(wsum < 1e-6)[0]: sk[pt] = P0[pt]
                        if not a.keepflip and bn2[0].lower() in Wl:                      # cancel the root bone's motion: the cane stays the way up it is held, it only unfolds
                            aq0, ap0 = Wl[bn2[0].lower()]; bq0, bp0 = bw2[bn2[0]]; Rr = ch.qmat(aq0) @ ch.qmat(ch.qconj(bq0)); tr0 = np.array(ap0, float) - Rr @ np.array(bp0, float)
                            sk = (Rr.T @ (sk - tr0).T).T
                        Pf = np.array(hp, float)[None, :] + (Rmap @ (Rrot @ (sk * sz).T + off[:, None])).T
                        Gf = (ch.C @ Pf.T).T * ch.SCALE
                        fr_all.append(np.array([Gf[w['pt']] for w in wedge], '<f4'))
                    va.append((s_['name'], s_['fps'], np.array(fr_all, '<f4')))
                    d0_, d1_ = fr_all[0], fr_all[-1]
                    print(f"  whip animation {s_['name']}: {len(fr_all)} frames @ {s_['fps']:.1f} fps, first->last frame: size {np.ptp(d0_, axis=0).round(2)} -> {np.ptp(d1_, axis=0).round(2)} m")
            if va: vanims_all[name] = (len(wedge), va)
        if name == 'cane':                                                   # no moving blade part: only the timing of ThreadedCane_Transform (the model swap happens half way)
            tp = os.path.join(os.path.dirname(os.path.dirname(path)), 'Anim', 'ThreadedCane_Transform.psa')
            if os.path.exists(tp):
                sq_ = ch.load_psa(tp)[0]; ident = np.array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0], '<f4')
                tf = np.tile(ident, (max(2, sq_['n']), 1)); idl = np.tile(ident, (2, 1))
                wanims_all['cane'] = [('cane_open', sq_['fps'], tf), ('cane_close', sq_['fps'], tf), ('cane_openidle', 30.0, idl), ('cane_closedidle', 30.0, idl)]
                print(f"  cane: transform timing {sq_['n']} frames @ {sq_['fps']:.1f} fps")
            else: print('  cane: ThreadedCane_Transform.psa not found - no transform')
        if nW > 65535: print(f"{name}: too many vertices"); continue
        ext = G.max(0) - G.min(0)
        print(f"{name} ({'right' if side == 'R' else 'left'} hand): {nW} verts, {len(idx)//3} tris, size {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} m")
        out.append((name, side, tex, secs, verts, np.array(idx, '<u2')))
        total_v += nW
    with open(a.out, 'wb') as f:
        f.write(b'BBW1' + struct.pack('<I', len(out)))
        for name, side, tex, secs, verts, idx in out:
            f.write(name.encode()[:15].ljust(16, b'\0') + bytes([0 if side == 'R' else 1, 0, 0, 0]) + struct.pack('<4I', len(tex), len(secs), len(verts), len(idx)))
            for tn, im in tex:
                f.write(bytes([len(tn)]) + tn.encode() + struct.pack('<HH', im.width, im.height) + im.tobytes())
            for sc_ in secs: f.write(struct.pack('<IIHH', sc_[0], sc_[1], sc_[2], sc_[3] if len(sc_) > 3 else 0))
            f.write(verts.tobytes()); f.write(idx.tobytes())
        if wanims_all:                                   # trailer: transform animations (older loaders ignore it)
            f.write(b'WAN1' + struct.pack('<I', len(wanims_all)))
            for nm, anl in wanims_all.items():
                f.write(nm.encode()[:15].ljust(16, b'\0') + struct.pack('<I', len(anl)))
                for an_, fps_, fr_ in anl: f.write(an_.encode()[:31].ljust(32, b'\0') + struct.pack('<fI', fps_, len(fr_)) + fr_.tobytes())
    if vanims_all:
        with open(a.out, 'ab') as f:
            f.write(b'VAN1' + struct.pack('<I', len(vanims_all)))
            for nm, (nv_, va) in vanims_all.items():
                f.write(nm.encode()[:15].ljust(16, b'\0') + struct.pack('<2I', nv_, len(va)))
                for an_, fps_, fr_ in va: f.write(an_.encode()[:31].ljust(32, b'\0') + struct.pack('<fI', fps_, len(fr_)) + fr_.tobytes())
    print(f"wrote {a.out}: {len(out)} weapons, {total_v} vertices, {os.path.getsize(a.out)//1024} KB")

if __name__ == '__main__': main()
