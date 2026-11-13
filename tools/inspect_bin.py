#!/usr/bin/env python3
"""python3 inspect_bin.py hunter.bin  -> prints the header facts of a BBH2 file (no game data is shown)."""
import struct, sys
d = open(sys.argv[1], 'rb').read(); p = 0
assert d[:4] == b'BBH2', 'not a BBH2 file: %r' % d[:4]
nV, nI, nB, nA, nAt, nS, nT = struct.unpack('<7I', d[4:32]); p = 32
print('verts %d idx %d bones %d anims %d attach %d sections %d textures %d' % (nV, nI, nB, nA, nAt, nS, nT))
print('textures:')
for _ in range(nT):
    l = d[p]; name = d[p+1:p+1+l].decode('latin1'); w, h = struct.unpack('<HH', d[p+1+l:p+5+l]); p += 5 + l + w*h*4
    print('  %s %dx%d' % (name, w, h))
p += nS*12 + nV*24 + nI*2
at = [d[p+i*16:p+i*16+16].split(b'\0')[0].decode('latin1') for i in range(nAt)]; p += nAt*16
print('attach:', at)
names = []
for _ in range(nA):
    nm = d[p:p+32].split(b'\0')[0].decode('latin1'); fps, nf = struct.unpack('<fI', d[p+32:p+40]); p += 48 + nf*(nB+nAt)*48
    names.append('%s(%d@%g)' % (nm, nf, fps))
print('total anims', len(names))
open(sys.argv[1] + '.anims.txt', 'w').write('\n'.join(sorted(n.split('(')[0] for n in names)) + '\n'); print('names written to', sys.argv[1] + '.anims.txt')
