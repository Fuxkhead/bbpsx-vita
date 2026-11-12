#!/usr/bin/env python3
"""
extract_map_props.py  -  reads the game's .pak and writes map_props.json: what every placed door and item pickup *really* is.

The FModel .usda export only keeps where things are. The things the designers typed into the editor for each placed Blueprint
(a door's LockedState / KeyToOpen, a pickup's InvDrops ...) live in the cooked .umap files inside the pak. This reads them.

    python3 extract_map_props.py  /path/to/BBPSX-WindowsNoEditor.pak  [map_props.json]

convert_level.py picks map_props.json up (from the same folder as itself, or --props) and bakes it into interact_<map>.bin.
"""
import json, re, struct, sys, zlib

# ---------------------------------------------------------------- .pak (version 8/9, zlib or stored, unencrypted)
class Pak:
    def __init__(self, path):
        self.f = open(path, 'rb'); f = self.f
        f.seek(0, 2); sz = f.tell()
        f.seek(max(0, sz - 300)); tail = f.read()
        i = tail.rfind(struct.pack('<I', 0x5A6F12E1))
        if i < 0: raise SystemExit("not a .pak file")
        ver, ioff, isz = struct.unpack('<IQQ', tail[i + 4:i + 24])
        if ver not in (8, 9): raise SystemExit("pak version %d is not supported (8 or 9 are)" % ver)
        f.seek(ioff); idx = f.read(isz); p = 0
        def rs():
            nonlocal p
            n = struct.unpack_from('<i', idx, p)[0]; p += 4
            s = idx[p:p + n - 1].decode('utf8', 'replace'); p += n; return s
        rs(); cnt = struct.unpack_from('<I', idx, p)[0]; p += 4
        self.ents = {}
        for _ in range(cnt):
            n = rs()
            off, size, usz, comp = struct.unpack_from('<QQQI', idx, p); p += 28 + 20
            blocks = []
            if comp:
                nb = struct.unpack_from('<I', idx, p)[0]; p += 4
                for _k in range(nb): blocks.append(struct.unpack_from('<QQ', idx, p)); p += 16
            p += 5
            self.ents[n] = (off, usz, comp, blocks)
    def read(self, n):
        off, usz, comp, blocks = self.ents[n]
        self.f.seek(off + 48 + (4 + 16 * len(blocks) if comp else 0) + 5)
        if not comp: return self.f.read(usz)
        out = b''
        for a, b in blocks:
            self.f.seek(off + a); out += zlib.decompress(self.f.read(b - a))
        return out

# ---------------------------------------------------------------- cooked UE4 package (names, imports, exports, tagged properties)
class Pkg:
    def __init__(self, pak, path):
        a = pak.read(path + ('.umap' if path + '.umap' in pak.ents else '.uasset')); self.a = a
        self.e = pak.read(path + '.uexp'); p = 0
        leg = struct.unpack_from('<i', a, 4)[0]; p = 8
        if leg != -4: p += 4
        p += 8
        if leg <= -2: n = struct.unpack_from('<i', a, p)[0]; p += 4 + n * 20
        self.hdr = struct.unpack_from('<i', a, p)[0]; p += 4
        n = struct.unpack_from('<i', a, p)[0]; p += 4 + n
        flags = struct.unpack_from('<I', a, p)[0]; p += 4
        nn, no = struct.unpack_from('<ii', a, p); p += 8
        if not flags & 0x80000000:
            n = struct.unpack_from('<i', a, p)[0]; p += 4 + (n if n > 0 else -2 * n)
        p += 8
        nex, eo, nim, io = struct.unpack_from('<iiii', a, p)
        q = no; self.names = []
        for _ in range(nn):
            n = struct.unpack_from('<i', a, q)[0]; q += 4
            if n > 0: self.names.append(a[q:q + n - 1].decode('latin1')); q += n
            else: self.names.append(a[q:q - 2 * n - 2].decode('utf-16le', 'replace')); q += -2 * n
            q += 4
        self.imp = []
        for i in range(nim):
            o = io + i * 28; _cp, _cpn, cn, _cnn, out, on, onn = struct.unpack_from('<iiiiiii', a, o)
            self.imp.append(self.names[on] + ('_%d' % (onn - 1) if onn else ''))
        self.exp = []
        for i in range(nex):
            o = eo + i * 104; ci, _si, _ti, oi, on, onn, _fl, ssz, sof = struct.unpack_from('<iiiiiiIqq', a, o)
            self.exp.append(dict(cls=ci, outer=oi, name=self.names[on] + ('_%d' % (onn - 1) if onn else ''), size=ssz, off=sof - self.hdr))
        self.classes = [self.cname(x['cls']) for x in self.exp]
    def cname(self, ci):
        if ci < 0: return self.imp[-ci - 1]
        if ci > 0: return self.exp[ci - 1]['name']
        return '?'
    def nm(self, i, n): return self.names[i] + ('_%d' % (n - 1) if n else '')
    def props(self, ex):
        e = self.e; p = ex['off']; end = p + ex['size']; N = self.names; out = {}
        def name():
            nonlocal p
            i, n = struct.unpack_from('<ii', e, p); p += 8
            if not 0 <= i < len(N): raise ValueError('bad name')
            return self.nm(i, n)
        while p < end - 8:
            pn = name()
            if pn == 'None': break
            t = name(); size, _ai = struct.unpack_from('<ii', e, p); p += 8; extra = None
            if t in ('ByteProperty', 'EnumProperty', 'ArrayProperty', 'SetProperty'): extra = name()
            elif t == 'StructProperty': extra = name(); p += 16
            elif t == 'MapProperty': extra = (name(), name())
            if t == 'BoolProperty':
                bv = e[p]; p += 1; hg = e[p]; p += 1
                if hg: p += 16
                out[pn] = (t, None, bytes([bv])); continue
            hg = e[p]; p += 1
            if hg: p += 16
            out[pn] = (t, extra, e[p:p + size]); p += size
        return out
    def name_at(self, b): i, n = struct.unpack_from('<ii', b, 0); return self.nm(i, n)

# ---------------------------------------------------------------- user-defined enums: stored value and display label of every entry
_enums = {}
def enum_table(pak, enum):
    """-> {NewEnumeratorN: (value, label)}   (the stored order is NOT the displayed order in this project)"""
    if enum in _enums: return _enums[enum]
    path = [k[:-7] for k in pak.ents if k.endswith('/' + enum + '.uasset')]
    tab = {}
    if path:
        P = Pkg(pak, path[0]); e = P.e; prefix = enum + '::'
        ne = {P.names.index(n): n.split('::')[1] for n in P.names if n.startswith(prefix) and 'NewEnumerator' in n}
        for i in range(len(e) - 16):                                        # Names array: (FName, int64 value) pairs, 7 entries incl. E_MAX
            a, b = struct.unpack_from('<ii', e, i)
            if a in ne and b == 0:
                q = i; vals = {}
                while q + 16 <= len(e):
                    a2, b2, v = struct.unpack_from('<iiq', e, q)
                    if a2 not in ne and P.names[a2:a2 + 1] != [enum + '::E_MAX']: break
                    if a2 in ne: vals[ne[a2]] = v
                    q += 16
                if len(vals) >= len(ne): tab = {k: (v, None) for k, v in vals.items()}; break
        labels = {}                                                          # DisplayNameMap: FName key, then an FText whose source string is the label
        for m in re.finditer(rb'([\x00-\xff])\x00\x00\x00\x00\x00\x00\x00.{0,16}?\x21\x00\x00\x00([0-9A-F]{32})\x00.{4}([^\x00]+)\x00', e, re.S):
            idx = m.group(1)[0]
            if idx < len(P.names) and P.names[idx].startswith('NewEnumerator'): labels[P.names[idx]] = m.group(3).decode('latin1')
        for k in tab: tab[k] = (tab[k][0], labels.get(k, k))
    _enums[enum] = tab
    return tab
def enum_of(pak, pkg, t):
    """a ByteProperty carrying an enum -> (label, value)"""
    if t[0] != 'ByteProperty' or len(t[2]) != 8: return None
    full = pkg.name_at(t[2]); en, _, ne = full.partition('::')
    tb = enum_table(pak, en)
    if ne in tb: return tb[ne][1], tb[ne][0]
    return ne, -1

def norm_key(s): return re.sub(r'\s+', '', s or '')
def fstr_map(b):                                                             # TMap<FString,int32>
    n = struct.unpack_from('<i', b, 4)[0]; p = 8; out = {}
    for _ in range(n):
        l = struct.unpack_from('<i', b, p)[0]; p += 4; s = b[p:p + l - 1].decode('latin1'); p += l
        out[s] = struct.unpack_from('<i', b, p)[0]; p += 4
    return out

def read_props(pak, P, x, defaults):
    pr = P.props(x); d = dict(defaults)
    for k, t in pr.items():
        try:
            if t[0] == 'ByteProperty': r = enum_of(pak, P, t); d[k] = r if r else t[2][0]
            elif t[0] == 'BoolProperty': d[k] = bool(t[2][0])
            elif t[0] == 'IntProperty': d[k] = struct.unpack('<i', t[2])[0]
            elif t[0] == 'FloatProperty': d[k] = struct.unpack('<f', t[2])[0]
            elif t[0] == 'NameProperty': d[k] = P.name_at(t[2])
            elif t[0] == 'StrProperty': l = struct.unpack_from('<i', t[2])[0]; d[k] = t[2][4:4 + l - 1].decode('latin1')
            elif t[0] == 'MapProperty' and k == 'InvDrops': d[k] = fstr_map(t[2])
        except Exception: pass
    return d

def main():
    if len(sys.argv) < 2: raise SystemExit(__doc__)
    pak = Pak(sys.argv[1]); outp = sys.argv[2] if len(sys.argv) > 2 else 'map_props.json'
    cdo = {}
    for cls, path in (('BP_Doors_C', 'BBPSX/Content/BP/General/Doors/BP_Doors'), ('BP_InvPickup_C', 'BBPSX/Content/BP/General/BP_InvPickup')):
        P = Pkg(pak, path); x = [x for x in P.exp if x['name'] == 'Default__' + cls][0]
        cdo[cls] = read_props(pak, P, x, {})
    print("class defaults:", {k: {a: b for a, b in v.items() if a in ('LockedState', 'WhichDoor', 'InvDrops', 'WillNotInvRefresh')} for k, v in cdo.items()})
    res = {}
    for m in sorted(k for k in pak.ents if k.endswith('.umap') and k.startswith('BBPSX/Content/Maps/')):
        name = m.split('/')[-1][:-5]
        try: P = Pkg(pak, m[:-5])
        except Exception as ex: print("  !! %s: %s" % (name, ex)); continue
        doors, picks, insight = {}, {}, {}
        def where(ai):
            """-> (x, y, z, forward_x, forward_y) in the game's metres / frame (Unreal's Y is negated), from the actor's root component"""
            for r in P.exp:
                if r['outer'] == ai and r['name'].startswith('DefaultSceneRoot'):
                    try:
                        pr = P.props(r); loc = struct.unpack('<3f', pr['RelativeLocation'][2][:12]) if 'RelativeLocation' in pr else (0, 0, 0)
                        yaw = struct.unpack('<3f', pr['RelativeRotation'][2][:12])[1] if 'RelativeRotation' in pr else 0.0
                    except Exception: return None
                    import math
                    return [round(loc[0] / 100, 2), round(-loc[1] / 100, 2), round(loc[2] / 100, 2), round(math.cos(math.radians(yaw)), 3), round(-math.sin(math.radians(yaw)), 3)]
            return None
        for ai, (x, cn) in enumerate(zip(P.exp, P.classes), 1):
            if cn not in ('BP_Doors_C', 'BP_InvPickup_C', 'BP_InsightPickup_C'): continue
            try: d = read_props(pak, P, x, cdo.get(cn, {}))
            except Exception as ex: print("  !! %s %s: %s" % (name, x['name'], ex)); continue
            at = where(ai)
            if cn == 'BP_Doors_C':
                st, sv = d.get('LockedState', ('Unlocked', 1)); wh = d.get('WhichDoor', ('Double', 1))[0]
                doors[x['name']] = dict(state=st, value=sv, which=wh, key=norm_key(d.get('KeyToOpen', '')) if d.get('KeyToOpen', 'None') != 'None' else '',
                                        key_label=d.get('KeyToOpen', '') if d.get('KeyToOpen', 'None') != 'None' else '', insight=d.get('InsightRequirement', 0),
                                        autoexit=bool(d.get('AutoExit', False)), save_opened=bool(d.get('SaveOpenedToFile', False)), at=at)
            elif cn == 'BP_InvPickup_C':
                w = d.get('WeaponToUnlock')
                picks[x['name']] = dict(drops=d.get('InvDrops', {}), weapon=(w[0] if isinstance(w, tuple) and d.get('WeaponUnlock') else ''), norefresh=bool(d.get('WillNotInvRefresh', False)), at=at)
            else:
                insight[x['name']] = d.get('HowMuchInsightToGrant', 0)
        res[name] = dict(doors=doors, pickups=picks, insight=insight)
        print("  %-26s %2d doors  %2d pickups  %d insight" % (name, len(doors), len(picks), len(insight)))
    json.dump(res, open(outp, 'w'), indent=1, sort_keys=True)
    print("wrote", outp)

if __name__ == '__main__': main()
