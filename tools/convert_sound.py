#!/usr/bin/env python3
"""Sounds for bbpsx-vita.

  python3 convert_sound.py scan  <exported_dir>                    -> writes sound_list.txt (every audio file found; send it to Claude)
  python3 convert_sound.py build <exported_dir> <out_dir> map.txt  -> converts the picked files to <out_dir>/<slot>_<n>.wav (48 kHz mono 16-bit)

map.txt has one line per slot:   slot: pattern1, pattern2, ...
A pattern is a piece of a file's path (any case, extension ignored); every file matching any pattern is used (at most 6 per slot, picked at random in game).
Slot names are whatever main.c expects (see map.txt).
Needs, either:  pip install soundfile scipy numpy   (no ffmpeg; reads .ogg .wav .flac .opus)
          or:  ffmpeg (sudo apt install ffmpeg)   (any format; used when soundfile is missing or can't read a file)
Force one:  BBPSX_SOUND=python  or  BBPSX_SOUND=ffmpeg.  Copy <out_dir> to ux0:data/bbpsx/snd/ on the Vita.
"""
import os, sys, subprocess, random
try:
    import numpy as np, soundfile as sf
    from scipy.signal import resample_poly
    from math import gcd
    HAVE_PY = True
except Exception:
    HAVE_PY = False
MODE = os.environ.get('BBPSX_SOUND', '').lower()      # '', 'python' or 'ffmpeg'

def convert_py(src, dst, length, rate, peak):
    """Python-only conversion: first `length` seconds, mono, `rate` Hz, 16-bit WAV, loudest sample at `peak` dB (None = leave the level)."""
    data, sr = sf.read(src, dtype='float32', always_2d=True)
    data = data[:int(length * sr)]
    if data.shape[0] == 0: raise ValueError('empty file')
    pk = float(np.max(np.abs(data)))
    gain = 1.0
    if peak is not None and pk > 1e-6: gain = 10.0 ** (peak / 20.0) / pk      # loudest sample of the original -> `peak` dB
    mono = data.mean(axis=1)
    if sr != rate:
        g = gcd(int(sr), int(rate)); mono = resample_poly(mono, int(rate) // g, int(sr) // g).astype(np.float32)
    out = np.clip(mono * gain, -1.0, 1.0)
    sf.write(dst, out, int(rate), subtype='PCM_16', format='WAV')
EXT = ('.ogg', '.wav', '.wem', '.mp3', '.flac', '.opus', '.m4a', '.adpcm', '.bnk')
SLOTS = ['swing', 'swing_heavy', 'hit', 'gun', 'parry', 'visc', 'enemy_swing', 'boss_swing', 'player_hurt', 'enemy_death', 'dodge']

def files(root):
    out = []
    for d, _, fs in os.walk(root):
        for f in fs:
            if f.lower().endswith(EXT):
                out.append(os.path.relpath(os.path.join(d, f), root))
    return sorted(out)

def scan(root):
    fl = files(root)
    with open('sound_list.txt', 'w') as f:
        for p in fl:
            f.write('%s\t%d\n' % (p, os.path.getsize(os.path.join(root, p))))
    print('%d audio files -> sound_list.txt' % len(fl))

def build(root, out, mp):
    if MODE == 'python' and not HAVE_PY: sys.exit('BBPSX_SOUND=python, but soundfile / scipy / numpy are not installed: python3 -m pip install --user soundfile scipy numpy')
    os.makedirs(out, exist_ok=True)
    fl = files(root)
    random.seed(1)
    for line in open(mp):
        line = line.split('#')[0].strip()
        if not line or ':' not in line:
            continue
        slot, pats = line.split(':', 1)
        slot = slot.strip()
        length = 8                                    # seconds kept of each file; optional "| len=20" for the long ambient loops
        rate = 48000                                  # optional "| rate=32000": the music is kept at a lower rate to save memory
        peak = -9.0                                   # every slot is levelled to this unless told otherwise; optional "| peak=-12": scale every file of the slot so its loudest sample is that many dB below full scale
        if '|' in pats:
            pats, opt = pats.split('|', 1)
            for o in opt.split(','):
                if o.strip().startswith('rate='): rate = int(o.strip()[5:])
                if o.strip().startswith('len='): length = int(float(o.strip()[4:]))
                if o.strip().startswith('peak='):
                    peak = None if o.strip()[5:] == 'off' else float(o.strip()[5:])
        pats = [x.strip().lower() for x in pats.split(',') if x.strip()]
        hit = [p for p in fl if any(x in os.path.splitext(p)[0].lower().replace('\\', '/') for x in pats)]
        if len(hit) > 6:
            hit = sorted(random.sample(hit, 6))
        for n, p in enumerate(hit, 1):
            dst = os.path.join(out, '%s_%d.wav' % (slot, n))
            src = os.path.join(root, p); ok = False; how = ''
            if HAVE_PY and MODE != 'ffmpeg':
                try: convert_py(src, dst, length, rate, peak); ok = True; how = 'python'
                except Exception as e:
                    if MODE == 'python': print('%-12s %d  <- %s   FAILED (%s)' % (slot, n, p, e)); continue
            if not ok:
                af = []
                if peak is not None:
                    v = subprocess.run(['ffmpeg', '-hide_banner', '-i', src, '-t', str(length), '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True).stderr
                    for ln in v.splitlines():
                        if 'max_volume:' in ln:
                            try: af = ['-af', 'volume=%.2fdB' % (peak - float(ln.split('max_volume:')[1].split('dB')[0]))]
                            except ValueError: pass
                r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-t', str(length), '-ac', '1', '-ar', str(rate)] + af + ['-sample_fmt', 's16', dst])
                ok = r.returncode == 0; how = 'ffmpeg'
            print('%-12s %d  <- %s%s' % (slot, n, p, ('   [' + how + ']') if ok else '   FAILED'))
        if not hit:
            print('%-12s (nothing matched %s)' % (slot, pats))

if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == 'scan': scan(a[1])
    elif len(a) == 4 and a[0] == 'build': build(a[1], a[2], a[3])
    else: print(__doc__)
