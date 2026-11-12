#!/usr/bin/env python3
"""Pack the Hunter's other attire into attire.bin ("BBA1"): body outfits (SkM_Attire*.psk, skinned to the Hunter's own skeleton) and hats (SM_Hat*.pskx,
glued to the head bone). The game appends them to the Hunter at start-up and draws the ones that are equipped; hunter.bin is not rebuilt.

  python3 assets/tools/convert_attire.py --hunter assets/Char/Hunter/Export/SkM_AttireHunter.psk --hunterbin hunter.bin --root assets/Char/Hunter --out attire.bin
  --tex DIR [DIR..]          more folders searched for PNG textures (default: --root and assets/Char)
  --keep MI_Name,..          body materials to force-keep (by default materials with head / face / hair / hat / mask in the name are dropped: the Hunter keeps his own head)
  --hatoff x,y,z             where hats sit on the head, cm in file space (default 0,2,155.6, the same as hunter.bin's hat);  --hatoffs NAME=x,y,z per hat
  --only crowfeather,tophat  build just these
Prints every material of every mesh and what was done with it - paste that log if something looks wrong.
bin layout: 'BBA1', u32 count; per item { char name[16]; u8 kind (0 body, 1 hat); u8 pad[3]; u32 nTex, nSec, nV, nI;
  nTex x { u8 nameLen, name, u16 w, u16 h, RGBA }; nSec x { u32 start, u32 count, u16 tex, u16 0 }; nV x { f32 x y z u v; u8 bone0, bone1, w0, 0 }; nI x u16 }"""
import argparse, glob, os, re, struct, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convert_hunter as ch
from convert_hanims import read_hunter_bin

BODIES = [('crowfeather', 'SkM_AttireCrowfeather'), ('doll', 'SkM_AttireDoll'), ('foreign', 'SkM_AttireForeign'), ('gas', 'SkM_AttireGas'),
          ('henryk', 'SkM_AttireHenryk'), ('unadorned', 'SkM_AttireUnadorned'), ('yharnam', 'SkM_AttireYharnamClothes')]
HATS = [('blackhood', 'SM_HatBlackHood'), ('crowfeather_h', 'SM_HatCrowfeather'), ('doll_h', 'SM_HatDoll'), ('gas_h', 'SM_HatGas'), ('hunter_h', 'SM_HatHunter'),
        ('merchant', 'SM_HatMerchant'), ('steepled', 'SM_HatSteepled'), ('rumpled', 'SM_RumpledHat'), ('tophat', 'SM_TopHat')]
TEXHINT = {'MI_CrowfeatherBody': 't_crowfeatherbody', 'MI_CrowfeatherHat': 't_crowfeatherhead', 'MI_ForeignBody': 't_foreignset', 'MI_HenrykBody': 't_henrykbody',
           'MI_HunterBody': 'T_HunterBody', 'MI_MerchantHat': 'T_merchantMask', 'MI_SweatyClothes': 't_contractgiver', 'MI_HunterHeadPrev': 'T_HunterHead', 'MI_HunterHead': 'T_HunterHead', 'MI_Bandage': 't_hair', 'MI_HunterBodyPrev': 'T_HunterBody', 'MI_DollBody': 't_doll_body', 'MI_DollBodyPrev': 't_doll_body', 'MI_GehrmanHatsAlt': 't_gehrmanbody', 'MI_Gehrman': 't_gehrmanbody'}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--hunter', required=True); ap.add_argument('--hunterbin', required=True); ap.add_argument('--root', required=True)
    ap.add_argument('--tex', nargs='*', default=[]); ap.add_argument('--out', default='attire.bin'); ap.add_argument('--maxtex', type=int, default=128)
    ap.add_argument('--keep', default=''); ap.add_argument('--hatoff', default='0,2,155.6'); ap.add_argument('--hatoffs', action='append'); ap.add_argument('--only', default=None)
    a = ap.parse_args()
    keep = set(x.strip() for x in a.keep.split(',') if x.strip()); hoffs = {}
    for s in a.hatoffs or []: k, v = s.split('=', 1); hoffs[k.strip()] = v.strip()
    only = set(x.strip() for x in a.only.split(',')) if a.only else None
    nB, nAt, attach, hverts = read_hunter_bin(a.hunterbin)
    hm = ch.load_psk(a.hunter); names = [b['name'] for b in hm['bones']]
    bind = ch.world_chain(names, [b['parent'] for b in hm['bones']], [(b['q'], b['p']) for b in hm['bones']])
    used = set(names[int(b)] for b in set(hm['weights']['bone'].tolist())); skin = None
    for extra in (['hand_r', 'hand_l'], ['hand_r', 'hand_l', 'head'], [], ['hand_r'], ['hand_r', 'hand_l', 'head', 'spine_2']):
        sn = [n for n in names if n in used or n in extra]
        if len(sn) == nB: skin = sn; break
    if skin is None: sys.exit(f"could not rebuild hunter.bin's skin-bone set ({len(used)} used vs {nB})")
    sidx = {n: i for i, n in enumerate(skin)}
    print(f"skin bones: {len(skin)}")
    pngs = {}
    for d in [a.root, os.path.dirname(os.path.dirname(a.root.rstrip('/'))) or '.'] + list(a.tex):
        for p in glob.glob(os.path.join(d, '**', '*.png'), recursive=True): pngs.setdefault(os.path.splitext(os.path.basename(p))[0].lower(), p)
    jsons = {}
    for d in [a.root, os.path.dirname(os.path.dirname(a.root.rstrip('/'))) or '.']:
        for p in glob.glob(os.path.join(d, '**', 'MI_*.json'), recursive=True): jsons.setdefault(os.path.basename(p)[:-5], p)
    def json_tex(mn):                      # the texture names the material itself refers to (FModel's MI_*.json)
        p = jsons.get(mn) or jsons.get(re.sub('Prev$', '', mn))
        if not p: return []
        try: txt = open(p, errors='ignore').read()
        except OSError: return []
        return [m for m in re.findall(r"Texture2D'(?:[^']*[/.])?([A-Za-z0-9_]+)'", txt) + re.findall(r'"Texture[A-Za-z0-9_]*"\s*:\s*"[^"]*?\.([A-Za-z0-9_]+)"', txt) if m]
    def find_tex(mn):
        for jt in json_tex(mn):
            if jt.lower() in pngs: print(f"    (material file says {jt})"); return jt, pngs[jt.lower()]
        jl = json_tex(mn)
        if jl: print(f"    material file refers to texture(s) {sorted(set(jl))} - none of them is exported as a .png")
        mn = re.sub('Prev$', '', mn) if mn not in TEXHINT else mn
        for base in (TEXHINT.get(mn), 'T_' + mn[3:], mn[3:], 't_' + mn[3:].replace('Body', '').lower(), 'T_' + mn[3:].replace('Body', '')):
            if base and base.lower() in pngs: return base, pngs[base.lower()]
        core = re.sub('body|prev|alt', '', mn[3:], flags=re.I).lower()                 # last resort: a texture whose name contains the start of the material's name
        for L in range(len(core), 3, -1):
            hit = sorted((k for k in pngs if core[:L] in k), key=len)
            if hit: return pngs[hit[0]] and os.path.splitext(os.path.basename(pngs[hit[0]]))[0], pngs[hit[0]]
        return None, None
    def locate(stem):
        for ext in ('.psk', '.pskx', '.usda'):
            h = glob.glob(os.path.join(a.root, '**', stem + ext), recursive=True) + glob.glob(os.path.join(os.path.dirname(os.path.dirname(a.root.rstrip('/'))) or '.', '**', stem + ext), recursive=True)
            if h: return h[0]
        return None
    out = []
    for kind, lst in ((0, BODIES), (1, HATS)):
        for name, stem in lst:
            if only and name not in only: continue
            path = locate(stem)
            if not path: print(f"{name}: {stem} not found - skipped"); continue
            mm = ch.load_psk(path); mats = mm['mats'] or ['MI_none']; pts = mm['pts'].astype(float)
            print(f"{name} ({'body' if kind == 0 else 'hat'}) <- {os.path.relpath(path)}: {len(pts)} points, {len(mm['faces'])} tris, materials {mats}")
            pt_b = np.zeros((len(pts), 3), np.uint8)
            if kind == 0:
                bn = [b['name'] for b in mm['bones']]
                if len(mm['bones']):
                    mbind = ch.world_chain(bn, [b['parent'] for b in mm['bones']], [(b['q'], b['p']) for b in mm['bones']])
                    dd = max((np.linalg.norm(np.array(mbind[n][1], float) - np.array(bind[n][1], float)) for n in bn if n in bind), default=0.0)
                    print(f"  bind-pose difference from the Hunter's skeleton: {dd:.2f} cm" + ("" if dd < 1.0 else "  <-- the outfit's skeleton differs: expect it to look off"))
                par = {b['name']: (bn[b['parent']] if b['parent'] >= 0 else None) for b in mm['bones']}
                def remap(n):
                    while n is not None and n not in sidx: n = par.get(n)
                    return n
                inf = [dict() for _ in range(len(pts))]; lost = 0
                for w in mm['weights']:
                    r = remap(bn[w['bone']])
                    if r is None: lost += 1; r = skin[0]
                    inf[w['pt']][sidx[r]] = inf[w['pt']].get(sidx[r], 0.0) + float(w['w'])
                if lost: print(f"  {lost} weights on bones with no ancestor in the skin set (put on {skin[0]})")
                for i, dct in enumerate(inf):
                    l = sorted(((w_, b_) for b_, w_ in dct.items()), reverse=True)[:2] or [(1.0, 0)]
                    sm = sum(x[0] for x in l); b0 = l[0][1]; b1 = l[1][1] if len(l) > 1 else b0
                    pt_b[i] = (b0, b1, int(round((l[0][0] / sm if len(l) > 1 else 1.0) * 255)))
            else:
                hb = sidx.get('head', sidx.get('spine_2', 0)); off = np.array([float(x) for x in hoffs.get(name, a.hatoff).split(',')])
                pts = pts + off
                pt_b[:] = (hb, hb, 255)
                print(f"  hat size {(pts.max(0) - pts.min(0)).round(1)} cm, centre {pts.mean(0).round(1)}")
            G = (ch.C @ pts.T).T * ch.SCALE
            wedge, faces = mm['wedge'], mm['faces']; nW = len(wedge)
            verts = np.zeros(nW, dtype=[('p', '<3f4'), ('uv', '<2f4'), ('b', 'u1', 4)])
            for i, w in enumerate(wedge):
                verts['p'][i] = G[w['pt']]; verts['uv'][i] = (w['u'], w['v']); verts['b'][i] = (*pt_b[w['pt']], 0)
            order = np.argsort(faces['mat'], kind='stable'); idx = []; secs = []; tex = []
            for mi, mn in enumerate(mats):
                fs = [f for f in faces[order] if f['mat'] == mi]
                if not fs: continue
                drop = kind == 0 and mn not in keep and re.search('head|face|hair|hat|mask', mn, re.I) and not re.search('body|clothes|set', mn, re.I)
                if drop: print(f"  material {mn}: {len(fs)} tris - dropped (head part; --keep {mn} to keep it)"); continue
                base, hit = find_tex(mn)
                if hit: im = ch.load_texture(hit, a.maxtex); print(f"  material {mn}: {len(fs)} tris, texture {base} {im.size}")
                else: print(f"  material {mn}: {len(fs)} tris, WARNING no texture found - flat grey (png names with a similar start: {sorted(k for k in pngs if k.replace('t_', '')[:4] == mn[3:7].lower())[:6]})"); base = 'grey'; im = Image.new('RGBA', (4, 4), (110, 105, 100, 255))
                tex.append((base, im)); st = len(idx)
                for f in fs:
                    i0, i1, i2 = (int(x) for x in f['w']); idx += [i0, i2, i1]
                secs.append((st, len(idx) - st, len(tex) - 1))
            if not secs: print(f"  nothing left to draw - skipped"); continue
            out.append((name, kind, tex, secs, verts, np.array(idx, '<u2')))
    with open(a.out, 'wb') as f:
        f.write(b'BBA1' + struct.pack('<I', len(out)))
        for name, kind, tex, secs, verts, idx in out:
            f.write(name.encode()[:15].ljust(16, b'\0') + bytes([kind, 0, 0, 0]) + struct.pack('<4I', len(tex), len(secs), len(verts), len(idx)))
            for tn, im in tex: f.write(bytes([len(tn)]) + tn.encode() + struct.pack('<HH', im.width, im.height) + im.tobytes())
            for st, cnt, mi in secs: f.write(struct.pack('<IIHH', st, cnt, mi, 0))
            f.write(verts.tobytes()); f.write(idx.tobytes())
    print(f"wrote {a.out}: {len(out)} items, {os.path.getsize(a.out)//1024} KB")

if __name__ == '__main__': main()
