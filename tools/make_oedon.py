#!/usr/bin/env python3
"""Oedon Chapel (the Cathedral Ward arrival room) -> MP_OedonChapel.usda, in the same text format as the game's own maps, so convert_level.py reads it like any other map.
usage: python3 make_oedon.py --out assets/Maps/CathedralWard/MP_OedonChapel.usda [--preview chapel_plan.png]
Centimetres, Z up. Room x -1250..1250, y -1000..1000, ceiling 1000; the lantern stands at 0,0.
Exits: south = the way you came in (back to the Gascoigne arena), west = left exit (the courtyard, later), north = straight ahead (portcullis, later), east = right (locked great door).
"""
import argparse, math, os
NAME = 'MP_OedonChapel'
MESH = {'stairs': 'Env/Yharnam/Mesh/SM_Stairs1', 'sedge': 'Env/Yharnam/Mesh/SM_StairsEdge', 'sfence': 'Env/Yharnam/Mesh/SM_StairFence', 'window': 'Env/DerelictEstate/Mesh/SM_WindowIntact', 'dframe': 'Env/Yharnam/Mesh/SM_DoorframeDouble', 'plane': 'Env/General/Mesh/SM_EnvPlane', 'pillar': 'Env/Yharnam/Mesh/SM_Pillar', 'bench': 'Env/Clinic/Mesh/SM_HouseBench', 'door1': 'Env/Yharnam/Mesh/SM_DoorframeSingle', 'great': 'Env/Yharnam/Mesh/SM_GreatDoor',
        'port': 'Env/Yharnam/Mesh/SM_Portcullis', 'plinth': 'Env/Yharnam/Mesh/SM_Plinth1', 'statue': 'Env/Yharnam/Mesh/SM_Statue1', 'carpet': 'Env/HuntersDream/Mesh/SM_CarpetLong', 'chand': 'Env/DerelictEstate/Mesh/SM_Chandelier'}
MAT = {'MI_BrickGround': 'Env/Yharnam/Mat/MI_BrickGround', 'MI_BrickWallDesat': 'Env/Yharnam/Mat/MI_BrickWallDesat', 'MI_Stone': 'General/Mat/MI_Stone', 'MI_StoneCeilingDark': 'Env/Yharnam/Mat/MI_StoneCeilingDark', 'MI_BrickWallDark': 'Env/Yharnam/Mat/MI_BrickWallDark', 'MI_Arch5': 'Env/Yharnam/Mat/MI_Arch5', 'MI_Arch4': 'Env/Yharnam/Mat/MI_Arch4', 'MI_Stairs1Desat': 'Env/Yharnam/Mat/MI_Stairs1Desat', 'MI_ArchHalf': 'Env/Yharnam/Mat/MI_ArchHalf', 'MI_Arch': 'Env/Yharnam/Mat/MI_Arch', 'MI_ArchLitDesat': 'Env/Yharnam/Mat/MI_ArchLitDesat', 'MI_ArchWellBright': 'Env/Yharnam/Mat/MI_ArchWellBright', 'MI_CeilingArch': 'Env/HuntersDream/Mat/MI_CeilingArch'}      # (all three paths are ones the real maps use)
FLOOR_MAT, WALL_MAT, CEIL_MAT = 'MI_StoneCeilingDark', 'MI_BrickWallDark', 'MI_StoneCeilingDark'
def find_pillar_mat():      # the material the arch's stone pillars (SM_Pillar) wear in the game: read from your converted assets (assets/**/SM_Pillar.usda), so the panel over the arch can match them
    import glob, re
    root = os.path.expanduser(os.environ.get('BBPSX_ASSETS', '~/bbpsx-vita/assets'))
    for f in glob.glob(os.path.join(root, '**', 'SM_Pillar.usd*'), recursive=True):
        try: t = open(f, errors='ignore').read()
        except Exception: continue
        m = re.search(r'material:binding[^\n]*?(MI_[A-Za-z0-9_]+)', t) or re.search(r'(MI_[A-Za-z0-9_]+)', t)
        if not m: continue
        nm = m.group(1)
        for g in glob.glob(os.path.join(root, '**', nm + '.usd*'), recursive=True):
            rel = os.path.relpath(g, root); rel = os.path.splitext(rel)[0]
            MAT['PILLAR_MAT'] = rel; print('pillar material:', nm, '->', rel); return 'PILLAR_MAT'
        print('pillar material', nm, 'named but its file was not found; using MI_Stone')
    return 'MI_Stone'
PILLAR_MAT = find_pillar_mat()
ROOF_MAT = 'MI_CeilingArch'      # the main roof: the Hunter's Dream workshop's arched ceiling (t_ceilingarch)
X0, X1, Y0, Y1, H = -1250, 1250, -1000, 1000, 1000
OPEN = 250            # exits are 500 wide, centred: -250..250
pieces = []; plan = []; counts = {}; extra = []

def mat_quat(R):      # rotation matrix (columns = where local x, y, z go) -> quaternion (w, x, y, z)
    t = R[0][0] + R[1][1] + R[2][2]
    if t > 0: s = math.sqrt(t + 1) * 2; return (s / 4, (R[2][1] - R[1][2]) / s, (R[0][2] - R[2][0]) / s, (R[1][0] - R[0][1]) / s)
    if R[0][0] > R[1][1] and R[0][0] > R[2][2]: s = math.sqrt(1 + R[0][0] - R[1][1] - R[2][2]) * 2; return ((R[2][1] - R[1][2]) / s, s / 4, (R[0][1] + R[1][0]) / s, (R[0][2] + R[2][0]) / s)
    if R[1][1] > R[2][2]: s = math.sqrt(1 + R[1][1] - R[0][0] - R[2][2]) * 2; return ((R[0][2] - R[2][0]) / s, (R[0][1] + R[1][0]) / s, s / 4, (R[1][2] + R[2][1]) / s)
    s = math.sqrt(1 + R[2][2] - R[0][0] - R[1][1]) * 2; return ((R[1][0] - R[0][1]) / s, (R[0][2] + R[2][0]) / s, (R[1][2] + R[2][1]) / s, s / 4)
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def uniq(base): counts[base] = counts.get(base, 0) + 1; return '%s_%d' % (base, counts[base])
def yawq(deg): a = math.radians(deg) / 2; return (math.cos(a), 0.0, 0.0, math.sin(a))
def mesh(kind, o, q=(1, 0, 0, 0), s=(1, 1, 1), mat=None): pieces.append((uniq('SM_' + kind), kind, o, q, s, mat))
def plane(o, u, v, su, sv, mat):      # an EnvPlane (500 x 500, corner at its origin): local x along u, local y along v, scaled to su x sv; its front faces u x v
    n = cross(u, v); mesh('plane', o, mat_quat([[u[0], v[0], n[0]], [u[1], v[1], n[1]], [u[2], v[2], n[2]]]), (su / 500.0, sv / 500.0, 1), mat)
def spans(a0, a1, step=500):
    out = []; n = max(1, int(math.ceil((a1 - a0) / float(step) - 1e-6))); w = (a1 - a0) / float(n)
    return [(a0 + i * w, a0 + (i + 1) * w) for i in range(n)]

# Entrance: the wide doorway at the west end, from the courtyard (you arrive 3.3 m inside, facing the lantern; for now the loader links back to the arena until the courtyard map exists). South: stairs down to the Well area (shut for now); east end: the passage out (shut for now).
# Long hall, as on the map: x -1200..1200 (west = the low vestibule you arrive in, east = the raised apse with the lantern), y -475..475, ceiling 900.
# The middle steps climb 1 m to the apse. Doors: west end (the arena stairs, you arrive here), north wall near the west end (the left exit, up to the courtyard: shut for now), south wall (the right exit: locked great door),
# east end, middle, behind the steps' line of sight (the passage to a later area: shut for now); the Dweller sits between the two north incense plinths.
X0, X1, Y0, Y1, H, DZ = -1200, 1200, -475, 475, 1600, 100
ARCH_HW = 560; ARCH_H = int(ARCH_HW * 1.843)      # the east arch: half width and height (cm), the arena's proportions (425 x 783) so the picture is not stretched; wider than the wall's 475 (the outer edge hides in the side walls)
ARCH_TOP = DZ + ARCH_H      # the wall panels start over it
PIL_Y = int(293 * ARCH_HW / 425.0); PIL_K = 0.61 * ARCH_HW / 425.0      # the arch's pillars stand on its columns
S_DOOR = -350      # centre of the south wall's wooden double door (x, cm); clear of the bench at x -750
DOORC = {'N': -500, 'S': S_DOOR, 'W': 0}      # the wooden double doors: centre along the wall (cm)
EXITS = {}      # centre along the wall, width, arch height (cm)
for (a, b) in spans(X0, 0):
    for (c, d) in spans(Y0, Y1): plane((a, c, 0), (1, 0, 0), (0, 1, 0), b - a, d - c, FLOOR_MAT)
for (a, b) in spans(0, X1):
    for (c, d) in spans(Y0, Y1): plane((a, c, DZ), (1, 0, 0), (0, 1, 0), b - a, d - c, FLOOR_MAT)
ROOF_STONE_X = 800      # the last 4 m of roof, over the stairway arch, is plain stone (MI_Stone) instead of the workshop's wooden ceiling
RISE = 450      # the pointed (gabled) roof: two slopes meeting along a ridge down the middle of the hall, 4.5 m above the wall tops
RLEN = math.hypot(Y1, RISE)
for (x0_, x1_, mat_) in ((X0, ROOF_STONE_X, ROOF_MAT), (ROOF_STONE_X, X1, PILLAR_MAT)):
    for (a, b) in spans(x0_, x1_):
        for sg in (-1, 1):
            dv = (0.0, -sg * Y1 / RLEN, RISE / RLEN)
            for (c, d) in spans(0, RLEN, 500): plane((a, sg * Y1 - sg * Y1 * c / RLEN, H + RISE * c / RLEN), (1, 0, 0), dv, b - a, d - c, mat_)
# timber: a ridge beam, and three tie beams across the hall just under the ceiling line
def beam(p0, p1, w, mat, seg=120):
    d = [p1[i] - p0[i] for i in range(3)]; L = math.sqrt(sum(x * x for x in d)); d = [x / L for x in d]
    n1 = cross(d, (0, 0, 1)); l1 = math.sqrt(sum(x * x for x in n1)); n1 = [x / l1 for x in n1] if l1 > 1e-6 else [1, 0, 0]
    n2 = cross(d, n1); h = w / 2.0
    for (s1, s2, v, vv) in ((1, -1, n2, 0), (-1, -1, n2, 0), (-1, 1, n1, 1), (-1, -1, n1, 1)):
        o = [p0[i] + s1 * h * n1[i] + s2 * h * n2[i] for i in range(3)]
        for (a, b) in spans(0, L, seg): plane([o[i] + d[i] * a for i in range(3)], d, v, b - a, w, mat)
beam((X0 + 5, 0, H + RISE - 20), (X1 - 5, 0, H + RISE - 20), 40, CEIL_MAT, 240)
for bx in (-800, 0, 700): beam((bx, Y0 + 10, H - 25), (bx, Y1 - 10, H - 25), 40, CEIL_MAT, 240)
BZ, BD, BAL_X1 = 500, 160, 250      # the balcony: floor height, depth, and where it ends along the long walls (x)
def wpanel(side, a, b, c, d, mat):      # one wall panel: along the wall a..b, height c..d (fronts face into the room)
    if side == 'S': plane((a, Y0, c), (1, 0, 0), (0, 0, 1), b - a, d - c, mat)
    elif side == 'N': plane((b, Y1, c), (-1, 0, 0), (0, 0, 1), b - a, d - c, mat)
    elif side == 'W': plane((X0, b, c), (0, -1, 0), (0, 0, 1), b - a, d - c, mat)
    else: plane((X1, a, c), (0, 1, 0), (0, 0, 1), b - a, d - c, mat)
def wall(side, lo, hi, z0, z1):      # the walls are all your arch pictures: arcade (t_arch4) below, three-arch band (t_arch2) in the middle, tall arch windows (t_arch2_half) above
    for (b0, b1, mat, step) in ((0, 500, 'MI_Arch4', 500), (500, 1000, 'MI_Arch', 500), (1000, 100000, 'MI_ArchHalf', 300)):
        za, zb = max(z0, b0), min(z1, b1)
        if zb <= za + 1e-6: continue
        for (a, b) in spans(lo, hi, step):
            for (c, d) in spans(za, zb, 600): wpanel(side, a, b, c, d, 'MI_ArchLitDesat' if (mat == 'MI_Arch' and ((side in ('S', 'N') and b <= BAL_X1 + 10) or side == 'W')) else mat)      # balcony_tint: the middle band is the warmer lit-window picture along the balcony's walls
for side, (lo, hi) in (('S', (X0, X1)), ('N', (X0, X1)), ('W', (Y0, Y1)), ('E', (Y0, Y1))):
    if side == 'E': wall(side, lo, hi, ARCH_TOP, H); continue      # the east wall: the arch (below) takes the whole width up to 10 m
    if side in DOORC:      # a wooden double door (300 x 400 frame): the wall panels stay full size everywhere; only the lower band is cut away behind the door (plain stone lintel over it), the bands above run on unbroken
        dc = DOORC[side]
        if side in ('S', 'N'): wall(side, lo, 600, 500, H); wall(side, 900, hi, 500, H); wpanel(side, 600, 900, 500, 600, CEIL_MAT); wpanel(side, 600, 900, 1400, H, CEIL_MAT)      # window_hole: no wall behind the two windows by the lantern end (x 600..900, 600..1400 cm), so you see through their glass; plain stone round the hole
        else: wall(side, lo, hi, 500, H)
        wall(side, lo, dc - 150, 0, 500); wall(side, dc + 150, hi, 0, 500); wpanel(side, dc - 150, dc + 150, 400, 500, CEIL_MAT); continue
    if side not in EXITS: wall(side, lo, hi, 0, H); continue
    c, w, h = EXITS[side]; a, b = c - w / 2.0, c + w / 2.0
    wall(side, lo, a, 0, H); wall(side, b, hi, 0, H); wall(side, a, b, h, H)      # (a tall doorway; the upper corners are stepped in so it reads as a pointed archway)
    for (z0, z1, k) in (() if side in ('N', 'S', 'W') else ((0.72 * h, 0.88 * h, 0.15), (0.88 * h, h, 0.32)) if side == 'E' else ((0.62 * h, 0.72 * h, 0.08), (0.72 * h, 0.82 * h, 0.17), (0.82 * h, 0.91 * h, 0.28), (0.91 * h, h, 0.40))): wall(side, a, a + k * w, z0, z1); wall(side, b - k * w, b, z0, z1)
# the apse's step: risers on both sides of the stairs, the stairs themselves (5 steps of 20 cm, built from planes so the direction is certain) and their cheeks
for (c, d) in ((Y0, -250), (250, Y1)): plane((0, d, 0), (0, -1, 0), (0, 0, 1), d - c, DZ, WALL_MAT)
SK2 = 250 / 375.0      # steps_match: the small steps are now one module of the same stair the way out of the chapel is built from (SM_Stairs1 x2 + SM_StairsEdge x2, in the same material), turned to climb east and narrowed to 5 m; it rises 1 m over 2.5 m, exactly the apse's height. No fence, no rail
mesh('stairs', (-250, 0, 0), yawq(270), (-1.5 * SK2, 1, 1), 'MI_Stairs1Desat'); mesh('stairs', (-250, 0, 0), yawq(270), (1.5 * SK2, 1, 1), 'MI_Stairs1Desat')
mesh('sedge', (-250, 0, 0), yawq(270), (-1.5 * SK2, 1, 1)); mesh('sedge', (-250, 0, 0), yawq(270), (1.5 * SK2, 1, 1))
# (the stepped stone blocks that stood along both sides of the short steps are gone)
# door frames, and what shuts the exits that lead nowhere yet
# the stairway out of the east entrance: the Gascoigne arena's own stair module (SM_Stairs1 x2 + SM_StairsEdge x2, a fence every other module) repeated 8 times, going DOWN to the east (the arena climbs it going up), then a landing with the arena trigger at its end
AX0, AX1, AW, AZ, NMOD = 1200, 3900, int(PIL_Y - 14), DZ - 1000, 8      # (AW: the stairway is as wide as the arch's opening, 530 cm)
SK, TH = AW / 375.0, 1000      # the arena's stair module is 750 wide: scaled to fit; the tunnel's roof height (the arch picture is 10 m tall)      # (the apse floor the stairs arrive at is DZ = 100 cm up)
XB = AX0 + 250 * NMOD
for k in range(NMOD):
    ox, oz = XB - 250 * k, AZ + 125 * k; q = yawq(90)
    mesh('stairs', (ox, 0, oz), q, (-1.5 * SK, 1, 1.25), 'MI_Stairs1Desat'); mesh('stairs', (ox, 0, oz), q, (1.5 * SK, 1, 1.25), 'MI_Stairs1Desat')
    mesh('sedge', (ox, 0, oz), q, (-1.5 * SK, 1, 1.25)); mesh('sedge', (ox, 0, oz), q, (1.5 * SK, 1, 1.25))
    if k % 2 == 0: mesh('sfence', (ox, -350 * SK, oz), q, (1, 1, 1.25)); mesh('sfence', (ox, 350 * SK, oz), q, (1, 1, 1.25))
for (a, b) in spans(XB, AX1):
    for (c, d) in spans(-AW, AW): plane((a, c, AZ), (1, 0, 0), (0, 1, 0), b - a, d - c, FLOOR_MAT)
for (a, b) in spans(AX0, AX1):
    for (c, d) in spans(-AW, AW): plane((a, d, TH), (1, 0, 0), (0, -1, 0), b - a, d - c, CEIL_MAT)
    for (c, d) in spans(AZ, TH): plane((b, AW, c), (-1, 0, 0), (0, 0, 1), b - a, d - c, WALL_MAT); plane((a, -AW, c), (1, 0, 0), (0, 0, 1), b - a, d - c, WALL_MAT)
for (c, d) in spans(-AW, AW):
    for (e, g) in spans(AZ, TH): plane((AX1, c, e), (0, 1, 0), (0, 0, 1), d - c, g - e, WALL_MAT)
# pillars flanking the steps and in the apse, pews in the vestibule and the apse, the carpet from the door to the steps, the chandelier
def octagon_pillar(x, y, z0, z1, ap=95):      # faces carry t_arch5 (1:4), cut into bands 400 cm tall
    sd = 2 * ap * math.tan(math.radians(22.5))
    for k in range(8):
        t = math.radians(45 * k); n = (math.cos(t), math.sin(t)); u = (-math.sin(t), math.cos(t))
        for jb, (c, d) in enumerate(spans(z0, z1, 400)):      # mirrored every second face round, and turned 180 degrees every second band up
            hm = (k + jb) % 2; vf = jb % 2
            o0 = (x + ap * n[0] - u[0] * sd / 2, y + ap * n[1] - u[1] * sd / 2); uu = u
            if hm: o0 = (o0[0] + u[0] * sd, o0[1] + u[1] * sd); uu = (-u[0], -u[1])
            plane((o0[0], o0[1], d if vf else c), (uu[0], uu[1], 0), (0, 0, -1 if vf else 1), sd, d - c, 'MI_Arch5')
for (x, y, z) in ((0, -340, 0), (0, 340, 0)):      # (the two free pillars beside the lantern platform are gone)
    octagon_pillar(x, y, z, H + int(RISE * (1 - abs(y) / Y1)) + 10); plan.append(('pillar', x, y, 190, 190))      # (up into the pointed roof)
# the three-cornered end walls under the roof: the same arch-picture bands, stepped in 1 m at a time (a little wider than the roof slope, so no gap)
for k in range(0, RISE // 100):
    hw = Y1 * (1.0 - 100.0 * k / RISE)
    for sd in ('W', 'E'): wall(sd, -hw, hw, H + 100 * k, H + 100 * (k + 1))
RS = math.hypot(250, DZ)      # the slope of the steps
# (steps_match: the small steps have no rail any more)
for (x, y, z) in ((-750, -345, 0), (250, -345, DZ), (250, 345, DZ), (830, -345, DZ), (830, 345, DZ)):      # (kept clear of the pilasters, the platform, the doors and the future exits: nothing in the middle of the west wall, the north door or the south wall's east half)
    mesh('bench', (x, y, z), yawq(180 if y < 0 else 0)); plan.append(('bench', x, y, 305, 83))
mesh('carpet', (-640, 0, 2), yawq(90)); mesh('chand', (0, 0, 1300))

# church bays on the long walls: a pilaster (half-octagon column) every 5 m, a tall window with a stepped pointed stone surround in each bay, string courses at 5 m and under the ceiling
ARCH_FLIP = False      # True turns the facade pictures upside down (if they come out upside down in the game, set this)
def facade(side, cx, w, z0, z1, mat, off=3):      # a picture panel (arch window / arcade) on the long wall, centred at cx
    a, b = cx - w / 2.0, cx + w / 2.0
    if side == 'S': o, u = (a, Y0 + off), (1, 0, 0)
    else: o, u = (b, Y1 - off), (-1, 0, 0)
    if ARCH_FLIP: plane((o[0], o[1], z1), u, (0, 0, -1), w, z1 - z0, mat)
    else: plane((o[0], o[1], z0), u, (0, 0, 1), w, z1 - z0, mat)
def surround(side, cx):
    if cx == 750: facade(side, cx, 400, 700, 1100, 'MI_ArchLitDesat')      # the lit three-arch window (t_arch2_lit) by the lantern end
    else: facade(side, cx, 340, 560, 1240, 'MI_ArchHalf')      # the tall pointed arch window (t_arch2_half is 1:2)
for side, yw in (('S', Y0), ('N', Y1)):
    for px in (-1000, -500, 0, 500):      # (no pilasters in the east corners)
        if side == 'N' and -660 < px < -340: continue
        if side == 'S' and S_DOOR - 160 < px < S_DOOR + 160: continue
        octagon_pillar(px, yw + (45 if side == 'S' else -45), 0, H + int(RISE * 45 / Y1) + 10, 60)
    yy_ = Y0 + 6 if side == 'S' else Y1 - 6      # the first version's window panels (SM_WindowIntact) by the lantern end
    mesh('window', (750 + 150, yy_, 600), yawq(0), (0.6, 1, 0.8)); mesh('window', (750 - 150, yy_, 600), yawq(180), (0.6, 1, 0.8))
# the lantern at the middle of the apse, four plinths with flames (incense) round it; the statues at the east end
DAIS = DZ + 20
def octagon_dais(cx, cy, z, ap=300, hgt=20):
    sd = 2 * ap * math.tan(math.radians(22.5))
    for k in range(8):      # the low side
        t = math.radians(45 * k); n = (math.cos(t), math.sin(t)); u = (-math.sin(t), math.cos(t))
        plane((cx + ap * n[0] - u[0] * sd / 2, cy + ap * n[1] - u[1] * sd / 2, z), (u[0], u[1], 0), (0, 0, 1), sd, hgt, WALL_MAT)
    for k in range(4):      # the top: four overlapping bars make the octagon
        t = math.radians(45 * k); u = (math.cos(t), math.sin(t)); v = (-math.sin(t), math.cos(t))
        plane((cx - ap * u[0] - v[0] * sd / 2, cy - ap * u[1] - v[1] * sd / 2, z + hgt + 0.2 * k), (u[0], u[1], 0), (v[0], v[1], 0), 2 * ap, sd, FLOOR_MAT)
octagon_dais(600, 0, DZ)
LANT = (600, 0, DAIS)
PLINTH_TOP = 170      # height of the plinth's top over its base (cm): the statues stand on it; change it if they sink into it or float
for (x, y) in ((600, -240), (600, 240)):      # two plinths left (centred on the lantern, one each side), each with an angel statue facing the lantern in place of the fire
    mesh('plinth', (x, y, DAIS)); plan.append(('plinth', x, y, 116, 116))
    mesh('statue', (x, y, DAIS + PLINTH_TOP), yawq(180 if y < 0 else 0))
mesh('statue', (1070, -330, DZ), yawq(180)); mesh('statue', (1070, 330, DZ), yawq(0))      # (the Dweller sits between the two north incense plinths, (600, 240): a placeholder until the NPC is added)
# north: a regular double door like the one by the Gilbert lantern (SM_DoorframeDouble + BP_Doors3 pair), with a small closet behind it so it opens onto something
mesh('dframe', (-500 + 150, Y1 - 10, 0), yawq(180))
plane((-650, Y1, 0), (1, 0, 0), (0, 1, 0), 300, 300, FLOOR_MAT); plane((-650, Y1 + 300, 400), (1, 0, 0), (0, -1, 0), 300, 300, CEIL_MAT)
plane((-350, Y1 + 300, 0), (-1, 0, 0), (0, 0, 1), 300, 400, WALL_MAT); plane((-650, Y1 + 300, 0), (0, -1, 0), (0, 0, 1), 300, 400, WALL_MAT); plane((-350, Y1, 0), (0, 1, 0), (0, 0, 1), 300, 400, WALL_MAT)
# the north arch: the wall above the double door (frame 300 wide x 400 high) is filled flush; the opening's sides are the wall, 500 wide at the bottom
pass      # (the rest of the arch's opening, beside and above the double door, filled with the same wall pictures)
# west: the same regular double door, with its own small closet behind it
mesh('dframe', (X0 + 10, 150, 0), yawq(270))
plane((X0 - 300, -150, 0), (1, 0, 0), (0, 1, 0), 300, 300, FLOOR_MAT); plane((X0 - 300, 150, 400), (1, 0, 0), (0, -1, 0), 300, 300, CEIL_MAT)
plane((X0 - 300, -150, 0), (0, 1, 0), (0, 0, 1), 300, 400, WALL_MAT); plane((X0, -150, 0), (-1, 0, 0), (0, 0, 1), 300, 400, WALL_MAT); plane((X0 - 300, 150, 0), (1, 0, 0), (0, 0, 1), 300, 400, WALL_MAT)
pass      # (the rest of the west arch's opening, beside and above the door)
# south: the same regular double door, with its own small closet behind it
mesh('dframe', (S_DOOR - 150, Y0 + 10, 0), yawq(0))
plane((S_DOOR - 150, Y0 - 300, 0), (1, 0, 0), (0, 1, 0), 300, 300, FLOOR_MAT); plane((S_DOOR - 150, Y0, 400), (1, 0, 0), (0, -1, 0), 300, 300, CEIL_MAT)
plane((S_DOOR + 150, Y0 - 300, 0), (-1, 0, 0), (0, 0, 1), 300, 400, WALL_MAT); plane((S_DOOR - 150, Y0 - 300, 0), (0, 1, 0), (0, 0, 1), 300, 400, WALL_MAT); plane((S_DOOR + 150, Y0, 0), (0, -1, 0), (0, 0, 1), 300, 400, WALL_MAT)
pass
# the east arch: the arena arch (two mirrored SM_EnvPlane with MI_ArchWellBright, t_archwell is a half arch with a column) IS the east wall: it spans the wall's full width, 475 per half, 9 m tall from the floor, and its opening is the stairway's mouth; no wall is built behind its middle.
# Its square pillars stand on the texture's columns (293/425 of the half width out); the stairway is as wide as the opening between them; the wall panels only go above it. (The arch planes are made non-solid by convert_level.py: texture name contains "archwell".)
for dx in (-27, 27):      # two arch pairs, 54 cm apart like the arena's, both inside the pillars; the gap between them takes the wall
    for sg in (1, -1): plane((X1 + dx, 0, DZ), (0, sg, 0), (0, 0, 1), ARCH_HW, ARCH_H, 'MI_ArchWellBright')
SP_Z = DZ + int(0.81 * ARCH_H)      # where the arch's stone arm tops out at the columns: everything above it, between the pictures, is stone (no see-through gap at the top)
for (a_, b_) in spans(-PIL_Y, PIL_Y, 250): plane((X1, a_, SP_Z), (0, 1, 0), (0, 0, 1), b_ - a_, ARCH_TOP - SP_Z, PILLAR_MAT)      # the panel over the arch wears the same stone as the pillars either side (cut into near-square pieces so it is not stretched)
for sy in (-1, 1): mesh('pillar', (X1, sy * PIL_Y, DZ - 10), (1, 0, 0, 0), (PIL_K, PIL_K, (0.58 * ARCH_H + 10) / 949.0))
for sy in (-1, 1): plane((X1, PIL_Y if sy > 0 else -Y1, DZ), (0, 1, 0), (0, 0, 1), Y1 - PIL_Y, ARCH_H, CEIL_MAT)      # the wall round the arch, between the two pictures, starting half way into each pillar
# the balcony: a U round the west end and along the south and north walls, at the height where the wall pictures change (not reachable: for looks), with a stone railing (posts in the pillar picture, a low kick wall and a top rail in the chapel's dark stone)
BAL_E = X1 - 70      # the long strips end at the east arch's pillars (they stand at x 1130..1270); the balcony crosses the east wall between them and touches the wall
def bbox(x0, x1, y0, y1, sides, z0=BZ - 55, z1=BZ):      # a solid slab: floor tiles on top, plain stone underneath and on the exposed edges (sides = which of 'n' 's' 'e' 'w' show). Every piece is kept near square (never more than 2:1) so no picture is stretched.
    tp = max(8, min(BD, x1 - x0, y1 - y0)); h = z1 - z0
    for (a, b) in spans(x0, x1, tp):
        for (c, d) in spans(y0, y1, tp): plane((a, c, z1), (1, 0, 0), (0, 1, 0), b - a, d - c, FLOOR_MAT)
    for (a, b) in spans(x0, x1, 2 * tp):
        for (c, d) in spans(y0, y1, 2 * tp): plane((a, d, z0), (1, 0, 0), (0, -1, 0), b - a, d - c, CEIL_MAT)      # (the underside)
    if 's' in sides:
        for (a, b) in spans(x0, x1, 2 * h): plane((a, y0, z0), (1, 0, 0), (0, 0, 1), b - a, h, CEIL_MAT)
    if 'n' in sides:
        for (a, b) in spans(x0, x1, 2 * h): plane((b, y1, z0), (-1, 0, 0), (0, 0, 1), b - a, h, CEIL_MAT)
    if 'w' in sides:
        for (c, d) in spans(y0, y1, 2 * h): plane((x0, d, z0), (0, -1, 0), (0, 0, 1), d - c, h, CEIL_MAT)
    if 'e' in sides:
        for (c, d) in spans(y0, y1, 2 * h): plane((x1, c, z0), (0, 1, 0), (0, 0, 1), d - c, h, CEIL_MAT)
PILS = (-1000, 0, 500); BIG = ((0, -340), (0, 340))      # the big octagon pillars (195 across) beside the steps: no balcony round them either      # the wall pilasters on the long walls (the south and north doors take the one at -500); the balcony is built round them
def bal_long(side):
    sg = 1 if side == 'S' else -1; wy = Y0 if side == 'S' else Y1; fy = wy + sg * 112; ey = wy + sg * BD      # wall, pilaster depth, railing edge
    lo, hi = (wy, fy) if side == 'S' else (fy, wy); f0, f1 = (fy, ey) if side == 'S' else (ey, fy)
    bbox(X0, BAL_E, f0, f1, 'e' + ('n' if side == 'S' else 's'))      # the walkway in front of the pilasters, the whole way, apart from the big pillar's 2.2 m
    xs = [X0] + [v for p in PILS for v in ((p - 66, p + 66) if p != 0 else (0, 0))] + [BAL_E]      # (no gap at the big pillars: the slab runs straight through and the pillar stands up through it)
    for k in range(0, len(xs), 2): bbox(xs[k], xs[k + 1], lo, hi, 'we' if True else '')      # and the strips between the pilasters, up to the wall
bal_long('S'); bal_long('N')
bbox(X0, X0 + BD, Y0 + BD, Y1 - BD, 'e')      # the west end
bbox(BAL_E, X1, Y0, -PIL_Y - int(PIL_K * 87.5), ''); bbox(BAL_E, X1, PIL_Y + int(PIL_K * 87.5), Y1, '')      # the east end: the strips end at the arch's pillars and only the slivers beside them touch the wall; nothing crosses over the stairs
def brail(x0, y0, x1, y1):      # a straight railing, axis-aligned: posts, a top rail 24 wide and a kick wall 40 high, in pieces no longer than 3:1
    L = abs(x1 - x0) + abs(y1 - y0); n = max(1, int(math.ceil(L / 200.0))); dx, dy = (x1 - x0) / float(n), (y1 - y0) / float(n)
    for i in range(n + 1): octagon_pillar(x0 + dx * i, y0 + dy * i, BZ, BZ + 105, 10)
    if y0 == y1:
        a, b = min(x0, x1), max(x0, x1)
        for (p, q) in spans(a, b, 72): plane((p, y0 - 12, BZ + 105), (1, 0, 0), (0, 1, 0), q - p, 24, CEIL_MAT)
        for (p, q) in spans(a, b, 120): plane((p, y0, BZ), (1, 0, 0), (0, 0, 1), q - p, 40, CEIL_MAT)
    else:
        a, b = min(y0, y1), max(y0, y1)
        for (p, q) in spans(a, b, 72): plane((x0 - 12, p, BZ + 105), (1, 0, 0), (0, 1, 0), 24, q - p, CEIL_MAT)
        for (p, q) in spans(a, b, 120): plane((x0, p, BZ), (0, 1, 0), (0, 0, 1), q - p, 40, CEIL_MAT)
brail(X0 + BD - 8, Y0 + BD, X0 + BD - 8, Y1 - BD); brail(X0 + BD - 8, Y0 + BD - 8, BAL_E, Y0 + BD - 8); brail(X0 + BD - 8, Y1 - BD + 8, BAL_E, Y1 - BD + 8)
# a soft warm glow for the chandelier: four small candle flames in a ring under it (the game puts a warm halo round every flame)
for k in range(4): extra.append(('P_FireFlameSmall', (60 * math.cos(math.radians(90 * k)), 60 * math.sin(math.radians(90 * k)), 1275)))
ARRIVE = (850, 0, 125)

def f(v): return ('%.5g' % v) if abs(v) > 1e-9 else '0'
def block(name, kind, o, q, s, mat):
    L = ['    def Scope "%s"' % name, '', '    {', '        def Mesh "StaticMeshComponent0" (', '            prepend references = @../../%s.usda@' % MESH[kind], '        )', '        {',
         '            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]', '            float3 xformOp:translate = (%s, %s, %s)' % tuple(f(v) for v in o),
         '            quatf xformOp:orient = (%s, %s, %s, %s)' % tuple(f(v) for v in q), '            float3 xformOp:scale = (%s, %s, %s)' % tuple(f(v) for v in s)]
    if mat:
        L += ['            ', '            def Scope "OverrideMaterials"', '            {', '                def Material "%s" (' % mat, '                    prepend references = @../../%s.usda@' % MAT[mat], '                )', '                {', '                }', '            }', '            ',
              '            over GeomSubset "Section_0" (', '                prepend apiSchemas = ["MaterialBindingAPI"]', '            )', '            {', '                rel material:binding = </%s/%s/StaticMeshComponent0/OverrideMaterials/%s>' % (NAME, name, mat), '            }']
    L += ['        }', '    }', '    ']; return '\n'.join(L)
def xf(o, q=(1, 0, 0, 0), ind=12): p = ' ' * ind; return '\n'.join([p + 'uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]', p + 'float3 xformOp:translate = (%s, %s, %s)' % tuple(f(v) for v in o), p + 'quatf xformOp:orient = (%s, %s, %s, %s)' % tuple(f(v) for v in q), p + 'float3 xformOp:scale = (1, 1, 1)'])
def xform_child(name, o, q): return '            def Xform "%s"\n            {\n%s\n            }\n            ' % (name, xf(o, q, 16))
def loader(name, root, q, entrance):
    return '    def Scope "%s"\n\n    {\n        def Xform "DefaultSceneRoot"\n        {\n%s\n            \n%s\n%s\n        }\n    }\n    ' % (name, xf(root, q), xform_child('Box', (0, 0, 195), (1, 0, 0, 0)), xform_child('EntranceVector', entrance, yawq(-90)))
def door_pair(name, o, q):
    def leaf(n, y, qq):
        return ['            def Mesh "%s" (' % n, '                prepend references = @../../BP/General/Doors/SM_DoorMed.usda@', '            )', '            {', xf((0, y, 0), qq, 16), '                ', '                def Scope "OverrideMaterials"', '                {', '                    def Material "MI_DoorMed" (', '                        prepend references = @../../BP/General/Doors/MI_DoorMed.usda@', '                    )', '                    {', '                    }', '                }', '                ',
                '                over GeomSubset "Section_0" (', '                    prepend apiSchemas = ["MaterialBindingAPI"]', '                )', '                {', '                    rel material:binding = </%s/%s/DefaultSceneRoot/%s/OverrideMaterials/MI_DoorMed>' % (NAME, name, n), '                }', '            }', '            ']
    L = ['    def Scope "%s"' % name, '    {', '        def Xform "DefaultSceneRoot"', '        {', xf(o, q), '            ']
    L += leaf('SM_DoorL', -100, (0.7071068, 0, 0, 0.7071067)) + leaf('SM_DoorR', 100, (0.7071067, 0, 0, -0.7071068))
    L += [xform_child('Arrow', (-34.8, 50, 104.3), (0, 0, 0, -1)), xform_child('Arrow1', (120.7, 50, 104.3), (0, 0, 0, 1)), xform_child('InsightCounter1', (15, 0, 180), (1, 0, 0, 0)), xform_child('InsightCounter2', (-15, 0, 180), (0, 0, 0, -1)), xform_child('NavLink', (0, 45.7, 0), (1, 0, 0, 0)), '        }', '    }', '    ']
    return '\n'.join(L)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--preview', default=None); a = ap.parse_args()
    out = ['#usda 1.0', '(', '    defaultPrim = "%s"' % NAME, '    metersPerUnit = 0.01', '    upAxis = "Z"', ')', '', 'def Scope "%s"' % NAME, '{',
           '    def Scope "WorldSettings"', '', '    {', '        def Xform "SceneComponent"', '        {', xf((0, 0, 0)), '        }', '    }', '    ']
    for p in pieces: out.append(block(*p))
    # the lantern (the Cathedral Ward's first), the spawn point, the flames, and the loader back to the arena in the south doorway: you arrive 3.3 m inside, facing the lantern
    out.append('    def Scope "BP_SavePointLantern_1"\n\n    {\n        def Xform "DefaultSceneRoot"\n        {\n%s\n        }\n    }\n    ' % xf(LANT, yawq(0)))
    out.append('    def Scope "PlayerStart_1"\n\n    {\n        def Xform "CollisionCapsule"\n        {\n%s\n        }\n    }\n    ' % xf(ARRIVE))
    for i, (nm, o) in enumerate(extra):
        out.append('    def Scope "%s_%d"\n    {\n        def Xform "ParticleSystemComponent0"\n        {\n%s\n        }\n    }\n    ' % (nm, i + 1, xf(o)))
    out.append(door_pair('BP_Doors3_1', (-350 - 149.2, Y1 + 7.6, 0), yawq(270)))
    out.append(door_pair('BP_Doors3_2', (X0 - 7.6, 0.8, 0), yawq(0)))
    out.append(door_pair('BP_Doors3_3', (S_DOOR - 0.8, Y0 - 7.6, 0), yawq(90)))
    out.append(loader('BP_LevelLoader_2', (2200, 0, DZ - 450), yawq(90), (0, 160, 0)))
    out.append('    def Scope "%s_C_1"\n    {\n    }\n}\n' % NAME)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True); open(a.out, 'w').write('\n'.join(out))
    print('wrote', a.out, len(pieces), 'pieces')
    if a.preview:
        from PIL import Image, ImageDraw
        S = 0.32; W, Hh = int(2700 * S), int(1250 * S); im = Image.new('RGB', (W, Hh), (30, 30, 34)); d = ImageDraw.Draw(im)
        def P(x, y): return (W / 2 + x * S, Hh / 2 - y * S)
        d.rectangle([P(X0, Y1), P(X1, Y0)], outline=(200, 200, 200), width=3); d.rectangle([P(0, Y1), P(X1, Y0)], fill=(60, 56, 62)); d.rectangle([P(-250, 250), P(0, -250)], fill=(110, 100, 90))
        for kk, x, y, w, h in plan:
            c = {'pillar': (150, 150, 170), 'bench': (140, 100, 60), 'plinth': (220, 160, 60)}[kk]; d.rectangle([P(x - w / 2, y + h / 2), P(x + w / 2, y - h / 2)], fill=c)
        d.ellipse([P(660, 40), P(740, -40)], fill=(255, 220, 120)); d.text(P(640, 90), 'lantern (apse, +1 m)', fill=(255, 255, 255)); d.text(P(-230, 200), 'steps up', fill=(255, 255, 255))
        for t, x, y in (('W: courtyard doorway (shut)', -1190, -140), ('S: stairs to the Well area (shut)', -560, -520), ('N: door behind the steps (shut)', -800, 520), ('E: ENTRANCE (from the arena)', 900, -520), ('Dweller (later)', 880, 520)): d.text(P(x, y), t, fill=(150, 220, 150))
        d.ellipse([P(825, 25), P(875, -25)], fill=(80, 160, 255)); d.text(P(890, 20), 'you arrive', fill=(120, 190, 255)); im.save(a.preview); print('preview', a.preview)
main()
