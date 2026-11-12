#!/usr/bin/env python3
"""Convert extra Hunter animations (weapon attack / shoot sets) into hunter_anims.bin ("HAN1"), which the game appends to the Hunter's own
animations at start-up - hunter.bin does not need to be rebuilt.

  python3 assets/tools/convert_hanims.py --hunter assets/Char/Hunter/Mesh/SkM_AttireHunter.psk --hunterbin hunter.bin \\
          --psa assets/BP/PlayerWeapons/Flamesprayer/Anim --out hunter_anims.bin
  --only flame,spray     keep only sequences whose name contains one of these (case-insensitive)
  --skip AM_             drop sequences containing these (default AM_ = the montage exports, duplicates of the single sequences)
Needs the same skin-bone set as hunter.bin: it is rebuilt from the attire mesh and checked against hunter.bin (nB); a mismatch is reported.
bin layout: 'HAN1', u32 count; per anim { char name[32]; f32 fps; u32 nf; f32 tx, ty; nf x (nB + nAt) x 12 f32 }"""
import argparse, glob, os, struct, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convert_hunter as ch

def read_hunter_bin(path):
    d = open(path, 'rb').read(); assert d[:4] == b'BBH2', 'hunter.bin is not BBH2'
    nV, nI, nB, nA, nAt, nS, nT = struct.unpack('<7I', d[4:32]); p = 32
    for _ in range(nT):
        l = d[p]; p += 1 + l; w, h = struct.unpack('<HH', d[p:p + 4]); p += 4 + w * h * 4
    p += 12 * nS
    verts = np.frombuffer(d[p:p + 24 * nV], dtype=np.dtype([('f', '<5f4'), ('b', 'u1', 4)])); p += 24 * nV + 2 * nI
    att = [d[p + 16 * i:p + 16 * i + 16].split(b'\0')[0].decode() for i in range(nAt)]
    return nB, nAt, att, verts

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--hunter', required=True); ap.add_argument('--hunterbin', required=True)
    ap.add_argument('--psa', nargs='+', required=True); ap.add_argument('--out', default='hunter_anims.bin')
    ap.add_argument('--layers', default=None, help='write the skin bone names (index name) to this file: the game splits legs / upper body with it')
    ap.add_argument('--only', default=None); ap.add_argument('--skip', default='AM_')
    ap.add_argument('--rootmotion', default='strip', choices=['strip', 'keep'])
    ap.add_argument('--maxfps', type=float, default=0.0, help='keep every n-th frame so the animation is at most this many frames per second (long cutscene animations)')
    ap.add_argument('--extra', default='hand_r,hand_l', help='bones skinned besides the attire mesh\'s own (the weapons and the pistol ride on them)')
    a = ap.parse_args()
    nB, nAt, attach, hverts = read_hunter_bin(a.hunterbin)
    hm = ch.load_psk(a.hunter); bones = hm['bones']; names = [b['name'] for b in bones]
    bind = ch.world_chain(names, [b['parent'] for b in bones], [(b['q'], b['p']) for b in bones])
    used = set(names[int(b)] for b in set(hm['weights']['bone'].tolist()))
    cand = [x.strip() for x in a.extra.split(',') if x.strip()]
    skin = None
    for extra in ([cand, cand + ['head'], [], ['hand_r'], cand + ['head', 'spine_2']]):
        sn = [n for n in names if n in used or n in extra]
        if len(sn) == nB: skin = sn; break
    if skin is None:
        sys.exit(f"could not rebuild hunter.bin's skin-bone set: the attire mesh uses {len(used)} bones, hunter.bin has {nB}. bones used: {sorted(used)}")
    idx = {n: i for i, n in enumerate(skin)}
    if a.layers:
        open(a.layers, 'w').write('\n'.join('%d %s' % (i, n) for i, n in enumerate(skin)) + '\n'); print('wrote', a.layers, '(%d bones)' % len(skin))
    # check: the first attire vertices must use the same bone numbers as hunter.bin
    inf = [[] for _ in range(len(hm['pts']))]
    for w in hm['weights']: inf[w['pt']].append((float(w['w']), idx.get(names[w['bone']], -1)))
    bad = 0; n_ck = min(len(hm['wedge']), len(hverts), 3000)
    for i in range(n_ck):
        l = sorted(inf[hm['wedge'][i]['pt']], reverse=True)[:2]
        if l and l[0][1] != int(hverts['b'][i][0]): bad += 1
    print(f"skin bones: {len(skin)} (hunter.bin: {nB}); first {n_ck} vertices: {bad} bone mismatches" + ("" if bad == 0 else "  <-- the bone set differs from the one hunter.bin was built with; animations will look wrong"))
    only = [x.strip().lower() for x in a.only.split(',')] if a.only else None
    skipw = [x.strip().lower() for x in a.skip.split(',')] if a.skip else []
    files = []
    for src in a.psa: files += [src] if os.path.isfile(src) else sorted(glob.glob(os.path.join(src, '**', '*.psa'), recursive=True))
    out = []
    for f in files:
        for s in ch.load_psa(f):
            nm = s['name']
            if only and not any(t in nm.lower() for t in only): continue
            if any(t in nm.lower() for t in skipw): continue
            if any(x[0] == nm for x in out): continue
            if not all(n in s['bones'] for n in skin): print(f"skip {nm}: missing skin bones"); continue
            if not all(n in s['bones'] or True for n in attach): pass
            tvec = (0.0, 0.0)
            rn = 'root@@@' if 'root@@@' in s['bones'] else s['bones'][0]
            keys = np.array(s['keys'])
            if a.rootmotion == 'strip' and rn in s['bones']:
                ri = s['bones'].index(rn); pi = s['parents'][ri]
                Ws = [ch.world_chain(s['bones'], s['parents'], [(keys[fr][i]['q'], keys[fr][i]['p']) for i in range(len(s['bones']))]) for fr in range(s['n'])]
                p0 = np.array(Ws[0][rn][1], float)
                travel = max(np.linalg.norm((np.array(W_[rn][1], float) - p0)[:2]) for W_ in Ws)
                if travel > 30.0:
                    pname = s['bones'][pi] if pi >= 0 else None
                    for fr in range(s['n']):
                        dd = np.array(Ws[fr][rn][1], float) - p0; dd[2] = 0.0
                        pq = np.array(Ws[fr][pname][0], float) if pname else np.array([0, 0, 0, 1.0])
                        keys[fr][ri]['p'] = np.array(keys[fr][ri]['p'], float) - ch.qrot(ch.qconj(pq), dd)
                    dend = np.array(Ws[-1][rn][1], float) - p0
                    tvec = (float(-dend[1] * ch.SCALE), float(-dend[0] * ch.SCALE))
            frames = []
            step = max(1, int(round(s['fps'] / a.maxfps))) if a.maxfps > 0 and s['fps'] > a.maxfps else 1
            sel = list(range(0, s['n'], step))
            if sel[-1] != s['n'] - 1: sel.append(s['n'] - 1)
            for fr in sel:
                W = ch.world_chain(s['bones'], s['parents'], [(keys[fr][i]['q'], keys[fr][i]['p']) for i in range(len(s['bones']))])
                mats = []
                for n in skin:
                    aq, ap_ = W[n]; bq, bp = bind[n]
                    R = ch.qmat(aq) @ ch.qmat(ch.qconj(bq)); t = ap_ - R @ bp
                    Rg, tg = ch.convert_mat(R, t); mats.append(ch.to34(Rg, tg))
                att = []
                for n in attach:
                    aq, ap_ = W[n] if n in W else W[skin[0]]; Rg, tg = ch.convert_mat(ch.qmat(aq), ap_); att.append(ch.to34(Rg, tg))
                frames.append(np.concatenate(mats + att))
            out.append((nm, s['fps'] / step, np.array(frames, '<f4'), tvec))
            print(f"anim {nm}: {len(frames)} frames @ {s['fps']:.1f} fps  (travel {tvec[0]:.2f}, {tvec[1]:.2f} m)")
    with open(a.out, 'wb') as f:
        f.write(b'HAN1' + struct.pack('<I', len(out)))
        for nm, fps, fr, tv in out:
            f.write(nm.encode()[:31].ljust(32, b'\0') + struct.pack('<fIff', fps, len(fr), tv[0], tv[1]) + fr.tobytes())
    print(f"wrote {a.out}: {len(out)} animations, {os.path.getsize(a.out)//1024} KB")

if __name__ == '__main__': main()
