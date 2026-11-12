#!/usr/bin/env python3
"""Bake panels_<map>.txt / texswap_<map>.txt files into main.c.
Usage: python3 embed_map_defaults.py main.c DIR [DIR ...]   (DIR = folders holding the files; a leading 'xxxxxxxx-' upload prefix is ignored)
Re-run any time: it replaces the block between BEGIN/END MAP DEFAULTS."""
import re, sys, os, glob
src = sys.argv[1]; dirs = sys.argv[2:]
pan, tsw = {}, {}
for d in dirs:
    for p in sorted(glob.glob(os.path.join(d, '*'))):
        b = os.path.basename(p); b = re.sub(r'^[0-9a-f]{8}-', '', b)
        m = re.match(r'^(panels|texswap)_(.+)\.txt$', b)
        if not m: continue
        txt = open(p, encoding='utf-8', errors='ignore').read().replace('\r', '')
        lines = [l.strip() for l in txt.split('\n') if l.strip()]
        if not lines: continue
        (pan if m.group(1) == 'panels' else tsw)[m.group(2)] = lines
def table(name, d):
    out = ['static const char *const %s[][2] = {' % name]
    for k in sorted(d):
        out.append('    { "%s",' % k)
        for l in d[k]: out.append('      "%s\\n"' % l.replace('\\', '\\\\').replace('"', '\\"'))
        out.append('    },')
    out.append('    { NULL, NULL } };')
    return '\n'.join(out)
block = '// BEGIN MAP DEFAULTS (written by embed_map_defaults.py: the panels_<map>.txt / texswap_<map>.txt files baked into the game; a file in ux0:data/bbpsx/ still wins)\n' + table('PAN_DEF', pan) + '\n' + table('TSW_DEF', tsw) + '\n// END MAP DEFAULTS'
s = open(src).read()
a = s.index('// BEGIN MAP DEFAULTS'); b = s.index('// END MAP DEFAULTS') + len('// END MAP DEFAULTS')
open(src, 'w').write(s[:a] + block + s[b:])
print('panels:', len(pan), 'maps,', sum(len(v) for v in pan.values()), 'panels | texswap:', len(tsw), 'maps')
