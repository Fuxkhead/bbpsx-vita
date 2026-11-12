#!/usr/bin/env python3
"""
extract_volumes.py  -  reads the game's .pak and writes, for every map, what the designers placed as invisible volumes / ambience actors:

    volumes_<map>.txt   (game metres, x / -y_ue / z; yaw is Unreal's, in degrees; hx hy hz are half-extents with the actor's scale applied)
        F  cx cy cz hx hy hz yaw water      BP_FallToDeathVolume   - touching it is death (water=1: a drowning void)
        T  cx cy cz hx hy hz yaw delay | text   BP_LevelTitleTrigger - the area name shown when the hunter walks in
        A  cx cy cz hx hy hz yaw            BP_AIAutoLosePlayerVolume - enemies that enter forget the hunter
        D  cx cy cz hx hy hz yaw dps freq kind  BP_ContinuousDamageVolume (kind = fire / poison / other)
        I  x y z yaw amount                 BP_InsightPickup
        E  x y z yaw                        BP_EchoRecovery
        B  x y z minT maxT                  BP_ChurchBellRinger (seconds between tolls)
        C  x y z yaw                        BP_CorpseBag
    poison_<map>.txt    the 'D ... poison' lines in the older 7-number format (cx cy cz hx hy hz dps)

    python3 extract_volumes.py /path/to/BBPSX-WindowsNoEditor.pak  out_dir
"""
import math, os, re, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_map_props import Pak, Pkg

CLS = {'BP_FallToDeathVolume_C': 'BP/General/BP_FallToDeathVolume', 'BP_LevelTitleTrigger_C': 'BP/General/BP_LevelTitleTrigger',
       'BP_AIAutoLosePlayerVolume_C': 'BP/General/BP_AIAutoLosePlayerVolume', 'BP_ContinuousDamageVolume_C': 'BP/General/BP_ContinuousDamageVolume',
       'BP_InsightPickup_C': 'BP/General/BP_InsightPickup', 'BP_EchoRecovery_C': 'BP/General/BP_EchoRecovery',
       'BP_ChurchBellRinger_C': 'BP/General/BP_ChurchBellRinger', 'BP_CorpseBag_C': 'BP/General/BP_CorpseBag'}

def ftext(b):
    try:
        ht = struct.unpack_from('<b', b, 4)[0]
        if ht != 0: return None
        p = 5; out = []
        for _ in range(3):
            n = struct.unpack_from('<i', b, p)[0]; p += 4
            if n > 0: out.append(b[p:p + n - 1].decode('latin1')); p += n
            elif n < 0: out.append(b[p:p - 2 * n - 2].decode('utf-16le', 'replace')); p += -2 * n
            else: out.append('')
        return out[2]
    except Exception: return None

def getv(P, pr, k, default=None):
    t = pr.get(k)
    if not t: return default
    d = t[2]
    if t[0] == 'FloatProperty': return struct.unpack('<f', d)[0]
    if t[0] == 'IntProperty': return struct.unpack('<i', d)[0]
    if t[0] == 'BoolProperty': return bool(d[0])
    if t[0] == 'TextProperty': return ftext(d)
    if t[0] == 'StructProperty': return struct.unpack('<3f', d[:12]) if len(d) == 12 else None
    if t[0] == 'ObjectProperty':
        i = struct.unpack('<i', d[:4])[0]
        return P.imp[-i - 1] if i < 0 else (P.exp[i - 1]['name'] if i > 0 else None)
    return default

def comp(P, ai, names):
    for r in P.exp:
        if r['outer'] == ai and any(r['name'].startswith(n) for n in names): return r
    return None

def main():
    pak = Pak(sys.argv[1]); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    cdo = {}
    for cn, path in CLS.items():
        P = Pkg(pak, 'BBPSX/Content/' + path); x = [x for x in P.exp if x['name'] == 'Default__' + cn][0]
        cdo[cn] = {k: getv(P, P.props(x), k) for k in P.props(x)}
    print("class defaults:", {k: {a: b for a, b in v.items() if a in ('BoxExtent', 'DamagePerSecond', 'DamageCheckFreq', 'LevelTitle', 'MinTimeToToll', 'MaxTimeToToll', 'DamageType')} for k, v in cdo.items()})
    for m in sorted(k for k in pak.ents if k.endswith('.umap') and k.startswith('BBPSX/Content/Maps/')):
        full = m.split('/')[-1][:-5]; name = re.sub(r'^MP_([A-Z]{2}_)?', '', full).lower()
        try: P = Pkg(pak, m[:-5])
        except Exception as ex: print("  !! %s: %s" % (full, ex)); continue
        lines = []; pois = []
        for ai, (x, cn) in enumerate(zip(P.exp, P.classes), 1):
            if cn not in CLS: continue
            try: pr = P.props(x)
            except Exception: continue
            d = dict(cdo[cn]); d.update({k: getv(P, pr, k) for k in pr})
            rootc = comp(P, ai, ('DefaultSceneRoot', 'Box')) if cn in ('BP_LevelTitleTrigger_C',) else comp(P, ai, ('DefaultSceneRoot',)) or comp(P, ai, ('Box',))
            loc, rot, sc = (0, 0, 0), (0, 0, 0), (1, 1, 1)
            if rootc:
                rp = P.props(rootc)
                if 'RelativeLocation' in rp: loc = struct.unpack('<3f', rp['RelativeLocation'][2][:12])
                if 'RelativeRotation' in rp: rot = struct.unpack('<3f', rp['RelativeRotation'][2][:12])
                if 'RelativeScale3D' in rp: sc = struct.unpack('<3f', rp['RelativeScale3D'][2][:12])
            cx, cy, cz = loc[0] / 100.0, -loc[1] / 100.0, loc[2] / 100.0; yaw = rot[1]
            ext = d.get('BoxExtent') or (150, 150, 150)
            hx, hy, hz = ext[0] * sc[0] / 100.0, ext[1] * sc[1] / 100.0, ext[2] * sc[2] / 100.0
            box = "%.3f %.3f %.3f %.3f %.3f %.3f %.1f" % (cx, cy, cz, hx, hy, hz, yaw)
            if cn == 'BP_FallToDeathVolume_C': lines.append("F %s %d" % (box, 1 if d.get('IsWaterDeathVoid') else 0))
            elif cn == 'BP_LevelTitleTrigger_C': lines.append("T %s %d | %s" % (box, 1 if d.get('DelayTitle', True) else 0, (d.get('LevelTitle') or '').replace('\n', ' ')))
            elif cn == 'BP_AIAutoLosePlayerVolume_C': lines.append("A " + box)
            elif cn == 'BP_ContinuousDamageVolume_C':
                dt = str(d.get('DamageType') or ''); kind = 'fire' if 'Fire' in dt else ('poison' if 'Pois' in dt else 'other')
                dps = d.get('DamagePerSecond') or 50.0
                lines.append("D %s %.1f %.2f %s" % (box, dps, d.get('DamageCheckFreq') or 0.75, kind + ':' + dt))
                if kind == 'poison': pois.append("%.3f %.3f %.3f %.3f %.3f %.3f %g" % (cx, cy, cz, hx, hy, hz, dps))
            elif cn == 'BP_InsightPickup_C': lines.append("I %.3f %.3f %.3f %.1f %d" % (cx, cy, cz, yaw, d.get('HowMuchInsightToGrant') or 1))
            elif cn == 'BP_EchoRecovery_C': lines.append("E %.3f %.3f %.3f %.1f" % (cx, cy, cz, yaw))
            elif cn == 'BP_ChurchBellRinger_C':
                mx = d.get('MaxTimeToToll') if d.get('MaxTimeToToll') is not None else d.get('MaxTimeToToll ')
                lines.append("B %.3f %.3f %.3f %g %g %d" % (cx, cy, cz, d.get('MinTimeToToll') or 50.0, mx or 500.0, 1 if d.get('StartTimerOnBeginPlay', True) else 0))
            elif cn == 'BP_CorpseBag_C': lines.append("C %.3f %.3f %.3f %.1f" % (cx, cy, cz, yaw))
        if lines:
            open(os.path.join(out, 'volumes_%s.txt' % name), 'w').write("\n".join(lines) + "\n")
            print("  %-26s -> volumes_%s.txt  %d lines (%s)" % (full, name, len(lines), ' '.join(sorted({l[0] for l in lines}))))
        if pois: open(os.path.join(out, 'poison_%s.txt' % name), 'w').write("\n".join(pois) + "\n")
if __name__ == '__main__': main()
