#!/usr/bin/env python3
"""Lists files the game expects in the data folder that are missing.
Usage: python3 check_data.py ~/bbpsx-vita/main.c /run/media/deck/USD00/Data/bbpsx
Only the binary data, sound clips, level files and credits are checked: the .txt tuning/settings files are optional."""
import re, sys, os
src, root = sys.argv[1], sys.argv[2]
s = open(src, errors='ignore').read()
OPT = re.compile(r'(save|lastpos|ladders|mstate|echo|volume|crt|light|dark|fog|res3d|stick|config|panels_|texswap_|extra_|maplog|skip|dbg|debug|dream_sky|\.log|slot)', re.I)
static = sorted(set(re.findall(r'"ux0:data/bbpsx/([A-Za-z0-9_./\-]+\.[a-z0-9]+)"', s)))
# sound clips: SND_NAMES -> snd/<name>_1.wav
m = re.search(r'SND_NAMES\[S_COUNT\]\s*=\s*\{(.*?)\};', s, re.S)
snd = ['snd/%s_1.wav' % n for n in re.findall(r'"([^"]+)"', m.group(1))] if m else []
need, opt = [], []
maps = sorted(set(re.findall(r'^    \{ "([a-z0-9_]+)",$', s, re.M)))      # every map the game has defaults for
lv = ['level_%s.bin' % mp for mp in maps]
for f in static + snd + lv:
    (opt if (OPT.search(f) or (f.endswith('.txt') and f != 'credits.txt')) else need).append(f)
need = sorted(set(need))
miss = [f for f in need if not os.path.exists(os.path.join(root, f))]
print('checked %d expected files in %s' % (len(need), root))
print('MISSING (%d):' % len(miss)); [print('  ' + f) for f in miss]
have_lv = sorted(f for f in os.listdir(root) if f.startswith('level_')) if os.path.isdir(root) else []
print('level files present: %d' % len(have_lv))
if not os.path.isdir(root): print('!! folder not found')
