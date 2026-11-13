#!/usr/bin/env python3
"""Mixes the sounds of the opening cutscene (Seq_GameIntroP1 / P2) at their start times into ONE file per part:
   snd/mus_gi1.wav (24 kHz mono 16-bit).   usage: python3 make_intro_audio.py [--assets assets] [--out ux0data/snd] [--voice 1.0] [--music 0.7]
(Needs: pip install soundfile scipy numpy)"""
import argparse, os, sys, glob
import numpy as np
import subprocess, shutil
try: import soundfile as sf
except ImportError: sf = None
try:
    from scipy.signal import resample_poly
    from scipy.io import wavfile
except ImportError:
    sys.exit("needs: sudo apt install python3-soundfile python3-scipy python3-numpy")
if sf is None and not shutil.which('ffmpeg'): sys.exit("needs the python packages (sudo apt install python3-soundfile python3-scipy python3-numpy) or ffmpeg")
SR = 24000
# (sound file name, start s, end s of the section, volume)   from Seq_GameIntroP1 (VO volume curves in the sequence are muted: the lines are mixed at --voice instead)
P1 = [
 ("A_OpeningCutsceneP1", 0.767, 36.241, 'music'),
 ("A_CB_1OhYesPaleblood", 0.600, 4.812, 'voice'), ("A_CB_2YouveComeToRightPlace", 6.333, 9.216, 'voice'), ("A_CB_3YharnamHomeBloodMini", 10.233, 13.628, 'voice'),
 ("A_CB_4UnravelMystery", 14.841, 16.967, 'voice'), ("A_CB_5ButWhereOutsiderLikeYourself", 19.133, 21.697, 'voice'), ("A_CB_6EasyWithYhnrmBlood", 24.064, 27.067, 'voice'),
 ("A_CB_7ButFirstContract", 29.400, 32.223, 'voice'),
 ("A_MetalSqueak2", 9.567, 10.010, 1.0), ("A_MetalSqueak1", 11.400, 11.733, 1.0), ("A_MetalSqueak4", 12.677, 13.067, 1.0), ("A_body-lobe-b1", 15.633, 16.425, 0.2),
 ("A_body-lobe-b2", 17.833, 18.601, 0.05), ("A_MetalSqueak2", 19.133, 19.577, 1.0), ("A_MetalSqueak7", 20.500, 20.764, 1.0), ("A_MetalSqueak8", 22.918, 23.200, 1.0),
 ("A_MetalSqueak4", 23.410, 23.800, 1.0), ("A_MetalSqueak7", 29.233, 29.497, 1.0), ("A_body-lobe-b2", 29.497, 30.265, 0.08), ("A_MetalSqueak2", 29.867, 30.310, 1.0),
 ("A_body-lobe-b1", 33.167, 33.959, 0.04),
]
PARTS = {'1': (P1, 37.4)}
def find(root, name):
    for ext in ('ogg', 'wav', 'flac'):
        hit = [p for p in glob.glob(os.path.join(root, '**', name + '.' + ext), recursive=True) if 'NMKART' not in p] or glob.glob(os.path.join(root, '**', name + '.' + ext), recursive=True)
        if hit: return hit[0]
    return None
def load(path):
    if sf is None:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True)
        return np.frombuffer(r.stdout, np.float32).copy()
    d, sr = sf.read(path, dtype='float32', always_2d=True); d = d.mean(1)
    if sr != SR:
        from math import gcd
        g = gcd(sr, SR); d = resample_poly(d, SR // g, sr // g).astype(np.float32)
    return d
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--assets', default='assets'); ap.add_argument('--out', default='.'); ap.add_argument('--part', default='1')
    ap.add_argument('--voice', type=float, default=1.0); ap.add_argument('--music', type=float, default=0.7)
    a = ap.parse_args(); lst, total = PARTS[a.part]
    mix = np.zeros(int(total * SR), np.float32); miss = 0
    for name, t0, t1, vol in lst:
        p = find(a.assets, name)
        if not p: print('MISSING', name); miss += 1; continue
        d = load(p); n = min(len(d), int((t1 - t0) * SR) + (0 if vol == 'music' else 0))
        if vol == 'music': n = min(len(d), int((t1 - t0) * SR)); g = a.music
        elif vol == 'voice': n = len(d); g = a.voice      # voices play to their own end
        else: g = vol; n = min(len(d), int((t1 - t0) * SR))
        s = d[:n] * g
        if vol == 'music':
            fo = int(1.2 * SR); s[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32); fi = int(0.5 * SR); s[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
        i0 = int(t0 * SR); e = min(len(mix), i0 + len(s)); mix[i0:e] += s[:e - i0]
    pk = float(np.abs(mix).max()); 
    if pk > 0.95: mix *= 0.95 / pk
    os.makedirs(a.out, exist_ok=True); o = os.path.join(a.out, 'mus_gi%s.wav' % a.part)
    (sf.write(o, (mix * 32767).astype(np.int16), SR, subtype='PCM_16') if sf else wavfile.write(o, SR, (mix * 32767).astype(np.int16))); print('wrote', o, '%.1f s' % (len(mix) / SR), 'peak %.2f' % pk, '(%d missing)' % miss)
main()
