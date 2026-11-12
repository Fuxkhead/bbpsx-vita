#!/usr/bin/env python3
"""
convert_level.py - turn an FModel USD map export into a compact binary level
file for the Vita renderer.

Usage:
  python3 convert_level.py --assets ~/bbpsx-vita/assets \
      --map Maps/YharnamSewers/MP_YS_Junction.usda \
      --out ~/bbpsx-vita/level_junction.bin [--maxtex 128]

Needs Python 3 and Pillow (sudo apt install python3-pil).

Conventions in the output (all little-endian):
  * Units are metres (Unreal centimetres * 0.01), Z up, right-handed as in the USD.
  * UV v is already flipped (v' = 1 - v) so PNG row 0 can be uploaded as GL row 0.
  * Instance matrices are 3x4 row-major: [r00 r01 r02 tx, r10 ..., r20 ...],
    applied as p' = A*p + t.

File layout:
  char[4] "BBL2"
  u32 nTextures, nGeometries, nDrawables, nInstances, nCollisionTris
  f32 spawnX, spawnY, spawnZ   (PlayerStart capsule centre, metres)
  nCollisionTris x f32[9]   (3 vertices, world space, metres)
  nTextures x   { u8 nameLen, name, u16 w, u16 h, u8[w*h*4] rgba }
  nGeometries x { u32 nVerts, u32 nIdx, f32[nVerts*5] (x y z u v), u16[nIdx] }
  nDrawables x  { u16 nParts, nParts x { u32 geometryIndex, u16 textureIndex (0xFFFF=none) } }
  nInstances x  { u32 drawableIndex, f32[12] matrix }
"""
import math
import argparse, collections, math, os, re, struct, sys
from collections import Counter, defaultdict

try:
    from PIL import Image
except ImportError:
    Image = None

CM_TO_M = 0.01
SKIP_DEFAULT = ["SkyBox", "Cube"]          # meshes not worth drawing on the Vita (yet)
SEC_MAT = {"SM_HouseSmall": {      # house_sections: SM_HouseSmall ships 15 sections but only 4 materials (roof, stone, arch, trim)
    "Section_4": "MI_ArchAlt", "Section_5": "MI_RailTrim", "Section_6": "MI_RailTrim", "Section_7": "MI_RailTrim", "Section_8": "MI_RailTrim",
    "Section_9": "MI_Roof", "Section_10": "MI_RailTrim", "Section_11": "MI_ArchAlt", "Section_12": "MI_Stone", "Section_13": "MI_RailTrim", "Section_14": "MI_Stone"}}
MESH_MAT_DEFAULT = {"SM_Shelf2": "Env/HuntersDream/Mat/MI_Shelf2.usda"}      # mesh name -> material (relative to --assets) for meshes exported without one
NOCOLLIDE_DEFAULT = ["Chain", "Rope", "Card", "Light", "DeadBody", "Tarp"]   # decorations: no collision (spheres/bags ARE solid: they are the canal boulders)
NOCOLLIDE_TEX = ["water", "groundfog_gen"]                  # parts whose texture name contains these: no collision

# ---------------------------------------------------------------- USDA prim tree
class Prim:
    def __init__(self, kind, name, parent):
        self.kind, self.name, self.parent = kind, name, parent
        self.refs, self.children = [], []
        self.t, self.q, self.s = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
        self.binding = None

BOSS_ONLY_MESHES = ("tomb", "grave", "headstone")      # the player can never break these; only the beast Gascoigne charges through them (kind 1 in the file)
UNBREAKABLE_MESHES = ("carriage", "cart", "wagon", "wheel", "coach")      # meshes under a destructible blueprint that must stay solid (lower-case parts of the mesh name). Add more here if something else breaks that should not

def nums(s):
    return [float(x) for x in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', s)]

def parse_tree(path):
    root = Prim("Root", "", None)
    stack, pending, in_meta = [root], None, False
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if in_meta:
                m = re.search(r'references\s*=\s*@([^@]+)@', line)
                if m and pending:
                    pending.refs.append(m.group(1))
                if line.startswith(")"):
                    in_meta = False
                continue
            m = re.match(r'(?:def|over|class)\s+(?:(\w+)\s+)?"([^"]+)"\s*(\()?', line)
            if m:
                pending = Prim(m.group(1) or "", m.group(2), stack[-1])
                stack[-1].children.append(pending)
                if m.group(3):
                    if line.rstrip().endswith(")"):       # one-line metadata
                        mm = re.search(r'references\s*=\s*@([^@]+)@', line)
                        if mm:
                            pending.refs.append(mm.group(1))
                    else:
                        in_meta = True
                continue
            if line == "{":
                if pending is not None:
                    stack.append(pending)
                    pending = None
                continue
            if line == "}":
                if len(stack) > 1:
                    stack.pop()
                continue
            cur = stack[-1]
            if "xformOp:translate" in line and "=" in line and "uniform" not in line:
                v = nums(line.split("=", 1)[1]);  cur.t = tuple(v[:3]) if len(v) >= 3 else cur.t
            elif "xformOp:orient" in line and "=" in line and "uniform" not in line:
                v = nums(line.split("=", 1)[1]);  cur.q = tuple(v[:4]) if len(v) >= 4 else cur.q
            elif "xformOp:scale" in line and "=" in line and "uniform" not in line:
                v = nums(line.split("=", 1)[1]);  cur.s = tuple(v[:3]) if len(v) >= 3 else cur.s
            elif "material:binding" in line:
                m = re.search(r'<([^>]+)>', line)
                if m:
                    cur.binding = m.group(1)
    return root

# ---------------------------------------------------------------- transforms
def quat_to_mat(q):
    w, x, y, z = q
    n = math.sqrt(w*w + x*x + y*y + z*z) or 1.0
    w, x, y, z = w/n, x/n, y/n, z/n
    return [[1-2*(y*y+z*z), 2*(x*y-z*w),   2*(x*z+y*w)],
            [2*(x*y+z*w),   1-2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w),   2*(y*z+x*w),   1-2*(x*x+y*y)]]

def local_xf(p):
    R = quat_to_mat(p.q)
    A = [[R[i][j] * p.s[j] for j in range(3)] for i in range(3)]   # R * diag(s)
    return A, list(p.t)

def mat_mul(A, B):
    return [[sum(A[i][k]*B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

def compose(parent, local):
    Ap, tp = parent
    Al, tl = local
    A = mat_mul(Ap, Al)
    t = [sum(Ap[i][k]*tl[k] for k in range(3)) + tp[i] for i in range(3)]
    return A, t

def compose_ue(parent, p):
    """Unreal's child * parent: rotation multiplies, scale multiplies per axis (no shear), translation is scaled by the parent's scale.
    The ladder blueprints stretch a card along its length and give the segments the inverse scale; as plain matrices the rotation between the two turns that
    into a net stretch of every rung texture (the shorter the ladder the worse)."""
    Ap, tp = parent
    Sp = [math.sqrt(sum(Ap[i][j] ** 2 for i in range(3))) or 1.0 for j in range(3)]
    Rp = [[Ap[i][j] / Sp[j] for j in range(3)] for i in range(3)]
    Rl = quat_to_mat(p.q)
    R = mat_mul(Rp, Rl)
    S = [Sp[j] * p.s[j] for j in range(3)]
    A = [[R[i][j] * S[j] for j in range(3)] for i in range(3)]
    t = [sum(Ap[i][k] * p.t[k] for k in range(3)) + tp[i] for i in range(3)]
    return A, t

# ---------------------------------------------------------------- mesh files
def parse_array(text, key):
    m = re.search(re.escape(key) + r'\s*=\s*\[(.*?)\]', text, re.S)
    return nums(m.group(1)) if m else None

def load_mesh(path):
    """Return {'sections': [(positions, uvs, indices, material_ref_path_or_None)]}"""
    text = open(path, encoding="utf-8", errors="replace").read()
    pts = parse_array(text, "point3f[] points")
    counts = parse_array(text, "int[] faceVertexCounts")
    idx = parse_array(text, "int[] faceVertexIndices")
    if not (pts and counts and idx):
        raise ValueError("no mesh data")
    pts = [tuple(pts[i:i+3]) for i in range(0, len(pts), 3)]
    idx = [int(i) for i in idx]
    counts = [int(c) for c in counts]

    st = None
    m = re.search(r'texCoord2f\[\]\s+primvars:st\s*=\s*\[(.*?)\]\s*(\(.*?\))?', text, re.S)
    interp = "vertex"
    if m:
        v = nums(m.group(1))
        st = [(v[i], v[i+1]) for i in range(0, len(v), 2)]
        mi = re.search(r'interpolation\s*=\s*"(\w+)"', m.group(2) or "")
        if mi:
            interp = mi.group(1)
        m2 = re.search(r'primvars:st:indices\s*=\s*\[(.*?)\]', text, re.S)
        if m2:
            ind = [int(i) for i in nums(m2.group(1))]
            st = [st[i] for i in ind]

    # triangulate (fan), remembering which face each triangle came from
    tris, tri_face, pos, f = [], [], 0, 0
    for fi, c in enumerate(counts):
        for k in range(1, c - 1):
            tris.append((pos, pos + k, pos + k + 1))
            tri_face.append(fi)
        pos += c

    def uv_for(corner):
        if st is None:
            return (0.0, 0.0)
        if interp == "faceVarying" and len(st) == len(idx):
            u, v = st[corner]
        else:
            u, v = st[idx[corner]] if idx[corner] < len(st) else (0.0, 0.0)
        return (u, 1.0 - v)

    # sections via GeomSubset
    tree = parse_tree(path)
    mesh_prim = tree.children[0] if tree.children else None
    mats = {}
    subsets = {}
    def walk(p):
        if p.kind == "Material" and p.refs:
            mats[p.name] = p.refs[0]
        if p.kind == "GeomSubset":
            subsets[p.name] = p
        for c in p.children:
            walk(c)
    if mesh_prim:
        walk(mesh_prim)
    sub_faces = {}
    for m in re.finditer(r'GeomSubset\s+"(\w+)".*?int\[\]\s+indices\s*=\s*\[(.*?)\]', text, re.S):
        sub_faces[m.group(1)] = set(int(i) for i in nums(m.group(2)))

    # gravestone faces tile their texture twice across the stone: the right-hand tile is the left one mirrored, so split each wide face
    # at the middle of its U range and flip the right half's U about that line (both planes of the stone)
    is_stone = "gravestone" in os.path.basename(path).lower()
    def _clip(poly, mid, keep_right):
        out = []
        for i in range(len(poly)):
            A_, B_ = poly[i], poly[(i + 1) % len(poly)]
            ia = (A_[3] >= mid) if keep_right else (A_[3] <= mid); ib = (B_[3] >= mid) if keep_right else (B_[3] <= mid)
            if ia: out.append(A_)
            if ia != ib:
                t_ = (mid - A_[3]) / (B_[3] - A_[3])
                out.append(tuple(A_[k] + (B_[k] - A_[k]) * t_ for k in range(5)))
        return out
    def _stone_tris(tri):                     # tri = 3 corners (x, y, z, u, v) -> list of triangles (corners), right halves mirrored
        us = [c[3] for c in tri]; lo, hi = min(us), max(us)
        if hi - lo < 1.5: return [tri]
        mid = (lo + hi) / 2.0; res = []
        for keep_right in (False, True):
            poly = _clip(list(tri), mid, keep_right)
            if len(poly) < 3: continue
            if keep_right: poly = [(c[0], c[1], c[2], 2 * mid - c[3], c[4]) for c in poly]
            for k in range(1, len(poly) - 1): res.append([poly[0], poly[k], poly[k + 1]])
        return res
    sections = []
    def build(face_filter, mat_ref):
        positions, uvs, indices = [], [], []
        for (a, b, c), fi in zip(tris, tri_face):
            if face_filter is not None and fi not in face_filter:
                continue
            cs_ = []
            for corner in (a, b, c):
                p = pts[idx[corner]]; u_, v_ = uv_for(corner); cs_.append((p[0]*CM_TO_M, p[1]*CM_TO_M, p[2]*CM_TO_M, u_, v_))
            for tri_ in (_stone_tris(cs_) if is_stone else [cs_]):
                base = len(positions)
                for q_ in tri_:
                    positions.append(q_[0:3]); uvs.append((q_[3], q_[4]))
                indices += [base, base+1, base+2]
        return positions, uvs, indices, mat_ref

    if sub_faces:
        for name in sorted(sub_faces, key=lambda n: int(re.sub(r'\D', '', n) or 0)):
            ref = None
            b = subsets[name].binding if name in subsets else None
            if b:
                ref = mats.get(b.rstrip('/').split('/')[-1])
            sections.append((name, build(sub_faces[name], ref)))
    else:
        sections.append(("Section_0", build(None, next(iter(mats.values()), None))))
    return sections

# ---------------------------------------------------------------- materials / textures
_mat_cache = {}
def material_texture(mat_path, depth=0):
    """Follow a material .usda to the first texture PNG; returns absolute path or None."""
    if mat_path in _mat_cache:
        return _mat_cache[mat_path]
    result = None
    if os.path.isfile(mat_path) and depth < 4:
        text = open(mat_path, encoding="utf-8", errors="replace").read()
        m = re.search(r'asset\s+inputs:file\s*=\s*@([^@]+)@', text)
        if m:
            result = os.path.normpath(os.path.join(os.path.dirname(mat_path), m.group(1)))
        else:
            for r in re.findall(r'references\s*=\s*@([^@]+)@', text):
                result = material_texture(os.path.normpath(os.path.join(os.path.dirname(mat_path), r)), depth + 1)
                if result:
                    break
    _mat_cache[mat_path] = result
    return result

# ---------------------------------------------------------------- material parameters (from FModel Properties .json)
import json
_S2L = [((c/255.0)/12.92 if c/255.0 <= 0.04045 else ((c/255.0 + 0.055)/1.055) ** 2.4) for c in range(256)]
def _lin2srgb(x):
    x = 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)
    return 12.92*x if x <= 0.0031308 else 1.055*(x ** (1/2.4)) - 0.055
_L2S = [int(_lin2srgb(i/4095.0)*255.0 + 0.5) for i in range(4096)]
def L2S(x):
    x = 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)
    return _L2S[int(x*4095.0 + 0.5)]

_param_cache = {}
def material_params(mat_path):
    """Read <material>.json next to the material .usda. Returns dict or None."""
    if not mat_path:
        return None
    if mat_path in _param_cache:
        return _param_cache[mat_path]
    jp = os.path.splitext(mat_path)[0] + ".json"
    res = None
    if os.path.isfile(jp):
        try:
            j = json.load(open(jp, encoding="utf-8"))
            P = j.get("Parameters", {})
            col = P.get("Colors", {}); sc = P.get("Scalars", {})
            lt = col.get("LocalTint")
            ov = P.get("Properties", {}).get("BasePropertyOverrides", {})
            res = {
                "tint": (lt["R"], lt["G"], lt["B"]) if lt else None,
                "desat": float(sc.get("Desat", 0.0)),
                "scalars": {k: v for k, v in sc.items() if k not in ("Desat", "RefractionDepthBias")},
                "colors": {k: (v["R"], v["G"], v["B"]) for k, v in col.items() if k != "LocalTint"},
                "blend": ov.get("BlendMode", "(parent)"),
                "twosided": bool(ov.get("TwoSided", False)),
            }
        except Exception as e:
            print(f"WARNING: could not read {jp}: {e}")
    _param_cache[mat_path] = res
    return res

def bake_material(im, params):
    """Apply desaturation then LocalTint, in linear light, like the Unreal material does."""
    if not params:
        return im
    tint = params["tint"] or (1.0, 1.0, 1.0)
    desat = params["desat"]
    if tint == (1.0, 1.0, 1.0) and desat == 0.0:
        return im
    tr, tg, tb = tint
    out = []
    for r, g, b, a in im.getdata():
        lr, lg, lb = _S2L[r], _S2L[g], _S2L[b]
        l = 0.3*lr + 0.59*lg + 0.11*lb
        lr += (l - lr)*desat; lg += (l - lg)*desat; lb += (l - lb)*desat
        out.append((L2S(lr*tr), L2S(lg*tg), L2S(lb*tb), a))
    n = Image.new("RGBA", im.size)
    n.putdata(out)
    return n

def pot_floor(n, cap):
    p = 1
    while p * 2 <= min(n, cap):
        p *= 2
    return p

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True)
    ap.add_argument("--map", required=True, help="map .usda, relative to --assets")
    ap.add_argument("--out", required=True)
    ap.add_argument("--maxtex", type=int, default=128)
    ap.add_argument("--pickup", action="append", default=None, help="what each BP_InvPickup in the map gives, in map order: vials:3 or bullets:10 (default vials:3)")
    ap.add_argument("--props", default=None, help="map_props.json from extract_map_props.py (default: next to this script): what each door / pickup really is")
    ap.add_argument("--skip", action="append", default=None, help="substring of mesh names to skip")
    ap.add_argument("--nocollide", action="append", default=None, help="substring of mesh names with no collision")
    ap.add_argument("--tile", choices=["mul", "div", "off"], default="mul",
                    help="how to apply the material TextureTileAmt to UVs (default mul; off disables)")
    ap.add_argument("--diag", action="append", default=None, help="print UV/texture details for meshes whose name contains this (repeatable)")
    args = ap.parse_args()
    skip = args.skip if args.skip is not None else SKIP_DEFAULT
    assets = os.path.expanduser(args.assets)
    map_path = os.path.join(assets, args.map)
    map_dir = os.path.dirname(map_path)
    if Image is None:
        print("Pillow missing: sudo apt install python3-pil"); sys.exit(1)

    tree = parse_tree(map_path)
    placements = []   # (mesh_path, matrix, overrides{section_name: material_path})
    def walk(p, xf, grp=None, eil=False):
        eil = eil or (p.kind == "Scope" and ("EileenTheCrow" in p.name or "HenrykNPC" in p.name or p.name.startswith("BP_Doll") or p.name.startswith("BP_NoteMessenger") or p.name.startswith("BP_MessengerWeapGrant")))      # eileen_npc: everything under her placement scope
        if p.kind == "Scope" and (p.name.startswith("BP_Doors") or p.name.startswith("BP_DoorBig") or p.name.startswith("SM_DoorframeSingle")): grp = ("door", p.name)
        elif p.kind == "Scope" and p.name.startswith("BP_Ladder"): grp = ("ladder", p.name)
        elif p.kind == "Scope" and (p.name.startswith("BPC_Dest_") or p.name.startswith("BP_Destruct")) and not (grp and grp[0] == "dest"): grp = ("dest", p.name)      # breakables: a destructible blueprint (BPC_Dest_Barrel, BPC_Dest_BarrelStack ...): everything under it breaks together
        if p.kind in ("Xform", "Mesh", "Scope"):
            if p.kind == "Scope" and not p.refs:
                local = ([[1,0,0],[0,1,0],[0,0,1]], [0, 0, 0])
            else:
                local = local_xf(p)
            xf = (compose_ue(xf, p) if (grp and grp[0] == "ladder") else compose(xf, local)) if p.kind != "Scope" else xf      # ladder_scale: inside a BP_Ladder the scales multiply per axis like Unreal's (the card's stretch and its segments' inverse stretch cancel)
        if p.kind == "Mesh" and p.refs and not p.name.startswith("SM_Prop") and p.name != "SM_FogWall" and p.name != "SM_Weapon" and "SM_BrickProp" not in str(p.refs):         # SM_PropR / SM_PropL: weapons held by a character; SM_FogWall: the boss-gate fog sheet (an untextured white plane until we give it a fog effect)
            over_mats, over = {}, {}
            def collect(q):
                if q.kind == "Material" and q.refs:
                    over_mats[q.name] = q.refs[0]
                if q.kind == "GeomSubset" and q.binding:
                    over[q.name] = q.binding.rstrip('/').split('/')[-1]
                for c in q.children:
                    collect(c)
            collect(p)
            ov = {sec: os.path.normpath(os.path.join(map_dir, over_mats[mn]))
                  for sec, mn in over.items() if mn in over_mats}
            placements.append((os.path.normpath(os.path.join(map_dir, p.refs[0])), xf, ov, grp, ("@EileenTheCrow:" if eil else "") + p.name))
        for c in p.children:
            walk(c, xf, grp, eil)
    walk(tree, ([[1,0,0],[0,1,0],[0,0,1]], [0, 0, 0]))
    print(f"placements in map: {len(placements)}")

    geoms, geom_ids = [], {}          # geometry blocks
    tex_names, tex_data, tex_ids = [], [], {}
    mat_of_tex = {}                  # texture index -> names of the materials that use it (for footstep floor classes)
    drawables, draw_ids = [], {}
    instances = []
    mesh_cache, missing_meshes, missing_tex, missing_mat, no_tex_mat = {}, Counter(), Counter(), Counter(), Counter()
    skipped = Counter()
    fallbacks = Counter()            # sections with no material anywhere, given the mesh's stone material
    psx_fixed = Counter(); same_fixed = Counter()
    untex = Counter()                # parts drawn with no texture at all (these show up white)
    drawable_mesh = {}

    tex_info = {}
    part_diag = {}
    mat_report = {}
    def get_tex(png_path, params=None):
        if png_path is None:
            return 0xFFFF
        tkey = (png_path, params["tint"] if params else None, params["desat"] if params else 0.0)
        if tkey in tex_ids:
            return tex_ids[tkey]
        if png_path == "__fog__":                                              # ground fog sheet: faint translucent white haze, no collision
            tex_ids[tkey] = len(tex_names); tex_names.append("groundfog_gen.png"); tex_data.append((8, 8, bytes([235, 235, 245, 70]) * 64)); return tex_ids[tkey]
        if png_path == "__invisible__":                                        # bare parent material = hidden collision/kill plane: transparent, still solid
            tex_ids[tkey] = len(tex_names); tex_names.append("invisible.png"); tex_data.append((8, 8, bytes(8*8*4))); return tex_ids[tkey]
        try:
            im0 = Image.open(png_path)
            mode0, size0 = im0.mode, im0.size
            im = im0.convert("RGBA")
            h_ = im.getchannel("A").histogram(); tot_ = float(sum(h_))
            tex_info[png_path] = (os.path.basename(png_path), size0, mode0,
                                  sum(h_[:86]) / tot_, sum(h_[86:250]) / tot_)
        except Exception:
            missing_tex[os.path.relpath(png_path, assets) if png_path else "?"] += 1
            im = Image.new("RGBA", (8, 8), (128, 128, 128, 255))
        w, h = pot_floor(im.width, args.maxtex), pot_floor(im.height, args.maxtex)
        im = im.resize((w, h), Image.BOX)
        im = bake_material(im, params)
        if os.path.basename(png_path).lower().startswith("t_grid"):         # the editor's placeholder grid (used on hidden collision planes): invisible, still solid
            im = Image.new("RGBA", im.size, (0, 0, 0, 0))
        tex_ids[tkey] = len(tex_names)
        tex_names.append(os.path.basename(png_path))
        tex_data.append((w, h, im.tobytes()))
        return tex_ids[tkey]

    creature_dropped = Counter()
    inst_info = []                   # per instance: (group or None, mesh name)
    sky_parts = []                   # sky_export: (png, positions (m, world), uvs, indices) of every SkyBox placement
    for mesh_path, xf, ov, grp, pname in placements:
        name = os.path.splitext(os.path.basename(mesh_path))[0]
        if "SkyBox" in name:      # sky_export: kept apart from the level, written to sky_<map>.bin and drawn behind everything
            try:
                _sm = load_mesh(mesh_path)
            except (OSError, ValueError):
                _sm = []
            _A, _t = xf
            for _sn, (_pos, _uv, _ind, _mref) in _sm:
                if not _ind: continue
                _mp = ov.get(_sn)
                if _mp is None and _mref: _mp = os.path.normpath(os.path.join(os.path.dirname(mesh_path), _mref))
                _png = material_texture(_mp) if _mp and os.path.isfile(_mp) else None
                _wp = [tuple(sum(_A[i][k] * q[k] for k in range(3)) + _t[i] * CM_TO_M for i in range(3)) for q in _pos]
                sky_parts.append((_png, _wp, _uv, _ind))
            skipped[name] += 1
            continue
        if any(s in name for s in skip):
            skipped[name] += 1
            continue
        if name.startswith("SkM_Gilb") or name == "SM_GilbTableLArm":      # gilbert_table: his own model is drawn by the game (a baked copy would lie in the level), and the spare arm piece is invisible in the map
            creature_dropped[name + " (in " + pname + ")"] += 1
            continue
        if "EileenTheCrow" in pname:      # eileen_npc: everything in her placement scope (shadow plane, fader, the stick) is dropped - the game draws her itself
            creature_dropped[name + " (in " + pname + ")"] += 1
            continue
        if any(k in name for k in ("Troll", "Werewolf", "RabidDog")) and not name.startswith("SM_"):          # a creature model standing in the level as scenery (the game spawns the real, animated one); static props such as SM_PyreWerewolf (the burning werewolf on the pyre) and the dead beasts stay
            creature_dropped[name + " (in " + pname + ")"] += 1
            continue
        if mesh_path not in mesh_cache:
            try:
                mesh_cache[mesh_path] = load_mesh(mesh_path)
            except (OSError, ValueError):
                mesh_cache[mesh_path] = None
        sections = mesh_cache[mesh_path]
        if sections is None:
            missing_meshes[name] += 1
            continue
        parts = []
        _cands = [os.path.normpath(os.path.join(os.path.dirname(mesh_path), sc[3])) for _sn, sc in sections if sc[3]]
        fallback_mat = next((c for c in _cands if 'stone' in os.path.basename(c).lower()), _cands[0] if _cands else None)      # sections the mesh gives no material: use its stone (or first) material instead of flat white
        for sec_name, (pos, uv, ind, mat_ref) in sections:
            if not ind:
                continue
            mpath = ov.get(sec_name)
            _red = False
            if mpath and 'railtrim' in os.path.basename(mpath).lower() and 'huntersdream' in map_path.lower() and 'workshop' in name.lower():      # dream_house: the Hunter's Dream house is overridden with the fence-trim material: use the mesh's own dark brick wall instead
                _bw = next((c for c in _cands if 'brickwall' in os.path.basename(c).lower()), None)
                if _bw: mpath = _bw
                elif fallback_mat: mpath = fallback_mat
            if 'huntersdream' in map_path.lower() and 'ground4' in name.lower() and sec_name == 'Section_8':      # dream_floor: this 6x5 m flat patch at the house (z 5) is bound to the gravestone material; it is the floor, so it gets the brick path
                _bp = next((c for c in _cands if 'brickpath' in os.path.basename(c).lower()), None)
                if _bp: mpath = _bp
            if mpath is None and mat_ref:
                mpath = os.path.normpath(os.path.join(os.path.dirname(mesh_path), mat_ref))
            if mpath is None:                                                      # house_sections: the mesh has more sections than material slots; pick each one's material from what it is (worked out from the geometry)
                _want = SEC_MAT.get(os.path.splitext(os.path.basename(mesh_path))[0], {}).get(sec_name)
                if _want == 'MI_RailTrim' and 'huntersdream' in map_path.lower(): _want = 'MI_Stone'      # dream_house: in the Hunter's Dream the house's trim sections read as brick
                if _want:
                    _hit = next((c for c in _cands if os.path.splitext(os.path.basename(c))[0].lower() == _want.lower()), None)
                    if _hit: mpath = _hit
            if mpath is None and fallback_mat:
                mpath = fallback_mat; fallbacks[(name, sec_name)] += 1
            if mpath is None:                                                      # a few props ship with no material at all: give them their known one
                for _k, _rel in MESH_MAT_DEFAULT.items():
                    if _k in name and os.path.isfile(os.path.join(assets, _rel)): mpath = os.path.join(assets, _rel); break
            _inv = False
            _fog = False          # Gate1 sheets (both ends of the Cleric Beast arena) now draw with their real iron-gate texture and stay solid
            if mpath and os.path.basename(mpath).lower() == "m_psxparent.usda":          # bare parent material, no texture: hidden plane (Dry Dock fall-through) -> invisible but solid
                _inv = True; psx_fixed[name] += 1     # drawn as the same ground-fog haze, no collision
            elif mpath and os.path.isfile(mpath) and material_texture(mpath) is None:     # e.g. General/Mat/MI_Stone (Cleric Beast floor): borrow the same-named material from Env/Yharnam/Mat
                for _d in ("Env/Yharnam/Mat", "Env/General/Mat", "General/Mat"):
                    _alt = os.path.join(assets, _d, os.path.basename(mpath))
                    if os.path.normpath(_alt) != os.path.normpath(mpath) and os.path.isfile(_alt) and material_texture(_alt):
                        mpath = _alt; same_fixed[(name, os.path.basename(mpath))] += 1; break
            if mpath and os.path.basename(mpath).lower().startswith("mi_blankclear"): continue            # invisible glass-like sheet
            mparams = material_params(mpath) if mpath else None
            if _red and mparams: mparams = dict(mparams); mparams['tint'] = (0.85, 0.30, 0.24)
            tile = 1.0
            if mparams and args.tile != "off":
                t = mparams["scalars"].get("TextureTileAmt")
                if t:
                    tile = float(t) if args.tile == "mul" else 1.0 / float(t)
            key = (mesh_path, sec_name, round(tile, 4))
            if key not in geom_ids:
                geom_ids[key] = len(geoms)
                guv = uv if tile == 1.0 else [(u * tile, v * tile) for u, v in uv]
                geoms.append((pos, guv, ind))
            tex = material_texture(mpath) if mpath else None
            if _inv: tex = "__fog__"
            if _fog: tex = "__fog__"
            if mpath and not os.path.isfile(mpath):
                missing_mat[os.path.relpath(mpath, assets)] += 1
            elif mpath and tex is None:
                no_tex_mat[os.path.basename(mpath)] += 1
            if mpath and tex:
                mat_report[os.path.basename(mpath)] = mparams
            if not tex: untex[(name, sec_name, os.path.basename(mpath) if mpath else "NO MATERIAL ON THIS SECTION")] += 1
            _tid = get_tex(tex, mparams) if tex else 0xFFFF
            if mpath and _tid != 0xFFFF: mat_of_tex.setdefault(_tid, set()).add(os.path.basename(mpath).lower())
            parts.append((geom_ids[key], _tid))
            if args.diag and any(d in name for d in args.diag):
                us = [u for u, v in uv] or [0]; vs = [v for u, v in uv] or [0]
                part_diag[(name, sec_name)] = (os.path.basename(tex) if tex else None, len(ind) // 3,
                                               min(us), max(us), min(vs), max(vs))
        dkey = tuple(parts)
        if dkey not in draw_ids:
            draw_ids[dkey] = len(drawables)
            drawables.append(dkey)
            drawable_mesh[draw_ids[dkey]] = name
        A, t = xf
        mat = [A[0][0], A[0][1], A[0][2], t[0]*CM_TO_M,
               A[1][0], A[1][1], A[1][2], t[1]*CM_TO_M,
               A[2][0], A[2][1], A[2][2], t[2]*CM_TO_M]
        instances.append((draw_ids[dkey], mat))
        inst_info.append((grp, pname + ' ' + name))

    for _k, _n in sorted(creature_dropped.items()): print(f"  creature mesh dropped from the level: {_k} x{_n}")
    # wheelchairs that belong to a wheelchair ENEMY (the game moves them with him, so they get no baked collision); empty ones (and every one in the clinic) stay level scenery
    _wc_sp = []
    if 'IC_FirstFloorSickroom' not in map_path:
        try:
            for _m2 in re.finditer(r'def Scope "BPC_Wheelchair\w*"\s*\{.*?xformOp:translate\s*=\s*\(([^)]*)\)', open(map_path, encoding="utf-8", errors="replace").read(), re.S):
                _v2 = [float(x) for x in _m2.group(1).split(',')]; _wc_sp.append((_v2[0]*CM_TO_M, _v2[1]*CM_TO_M))
        except OSError: pass
    def _chair_bound(ii_):
        m_ = instances[ii_][1]
        if 'IC_FirstFloorSickroom' in map_path: return True      # clinic_chairs: the sickroom's chairs are movable too (the game lowers them onto the floor; no baked collision)
        return any(abs(m_[3] - x_) < 2.0 and abs(m_[7] - y_) < 2.0 for x_, y_ in _wc_sp)
    # ---- collision triangles (world space, metres)
    nocol = args.nocollide if args.nocollide is not None else NOCOLLIDE_DEFAULT
    col = []
    inst_col = {}                    # instance index -> (first collision triangle, count)
    for ii, (d, m) in enumerate(instances):
        col_start = len(col)
        if 'SM_Wheelchair' in drawable_mesh[d] and 'Gehr' not in drawable_mesh[d] and _chair_bound(ii): continue
        if 'SM_GilbTable' in drawable_mesh[d]: continue      # gilbert_table: his bed is movable (the game moves it with him), so no baked collision
        if any(x in drawable_mesh[d] for x in nocol) and ('Chain' in drawable_mesh[d] or 'Tarp' in drawable_mesh[d] or not any(t != 0xFFFF and tex_names[t].lower().startswith('t_gate1') for g, t in drawables[d])):      # chains use the iron gate texture, but they hang loose from the roof and must never block you      # iron gates stay solid even when their mesh name says Light
            continue
        for g, t in drawables[d]:
            if t != 0xFFFF and any(w in tex_names[t].lower() for w in NOCOLLIDE_TEX):
                continue
            pos, uv, ind = geoms[g]
            W = [(m[0]*p[0] + m[1]*p[1] + m[2]*p[2] + m[3],
                  m[4]*p[0] + m[5]*p[1] + m[6]*p[2] + m[7],
                  m[8]*p[0] + m[9]*p[1] + m[10]*p[2] + m[11]) for p in pos]
            for i in range(0, len(ind), 3):
                a, b, c = W[ind[i]], W[ind[i+1]], W[ind[i+2]]
                ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
                vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
                cx_, cy_, cz_ = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
                if cx_*cx_ + cy_*cy_ + cz_*cz_ < 1e-10:
                    continue                      # degenerate
                col.append(a + b + c)
        inst_col[ii] = (col_start, len(col) - col_start)

    # ---- floor materials for the footstep sounds: wooden and watery triangles -> floor_<map>.bin (class 1 = wood, 2 = water)
    def _floor_class(t):
        nm = " ".join(sorted(mat_of_tex.get(t, ()))) + " " + tex_names[t].lower()
        if "water" in nm: return 2
        if "wood" in nm and "panel" not in nm: return 1
        return 0
    floor_tris = []
    for ii, (d, m) in enumerate(instances):
        for g, t in drawables[d]:
            fc = _floor_class(t) if t != 0xFFFF else 0
            if not fc: continue
            pos, uv, ind = geoms[g]
            W = [(m[0]*p[0] + m[1]*p[1] + m[2]*p[2] + m[3], m[4]*p[0] + m[5]*p[1] + m[6]*p[2] + m[7], m[8]*p[0] + m[9]*p[1] + m[10]*p[2] + m[11]) for p in pos]
            for i in range(0, len(ind), 3):
                a, b, c = W[ind[i]], W[ind[i+1]], W[ind[i+2]]
                nz = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                if fc == 1 and nz <= 0.0: continue          # wood: only the upward-facing planks (the walkable top)
                if abs(nz) < 1e-6: continue
                floor_tris.append((fc,) + a + b + c)
    print(f"floor materials: {sum(1 for f in floor_tris if f[0]==1)} wood triangles, {sum(1 for f in floor_tris if f[0]==2)} water triangles")

    # ---- interactables: doors (leaf instances + hinges) and ladders, written to interact.bin next to the level
    import numpy as np
    def inst_verts(ii):
        d, m = instances[ii]; P = []
        for g, t in drawables[d]:
            pos = geoms[g][0]
            P += [(m[0]*p[0]+m[1]*p[1]+m[2]*p[2]+m[3], m[4]*p[0]+m[5]*p[1]+m[6]*p[2]+m[7], m[8]*p[0]+m[9]*p[1]+m[10]*p[2]+m[11]) for p in pos]
        return np.array(P) if P else np.zeros((1, 3))
    groups = {}
    for ii, (grp, nm) in enumerate(inst_info):
        if grp: groups.setdefault(grp, []).append((ii, nm))
    doors, ladders = [], []
    lad_slide = []      # lever_slide: per ladder (drop distance, [moving segment instances])
    for (kind, gname), members in sorted(groups.items(), key=lambda kv: kv[0][1]):
        if kind == "door":
            leaves = [ii for ii, nm in members if 'door' in nm.lower() and 'frame' not in nm.lower()]
            if not leaves: continue
            V = [inst_verts(ii) for ii in leaves]
            cen = [v[:, :2].mean(0) for v in V]
            c = np.mean(cen, 0); zc = float(np.mean([v[:, 2].min() for v in V]))
            if len(leaves) >= 2:
                sv = cen[-1] - cen[0]
            else:
                cov = np.cov((V[0][:, :2] - cen[0]).T); w, vec = np.linalg.eigh(cov); sv = vec[:, 1]
            sv = sv / (np.linalg.norm(sv) or 1.0); fv = np.array([-sv[1], sv[0]])
            lv = []
            for ii, v in zip(leaves, V):
                pr = (v[:, :2] - c) @ sv
                if len(leaves) >= 2:
                    ext = pr.max() if abs(pr.max()) > abs(pr.min()) else pr.min()          # outer end
                    far = pr.min() if ext == pr.max() else pr.max()
                else:
                    o = np.array(instances[ii][1][3:12:4][:2]); ends = [pr.min(), pr.max()]
                    ext = min(ends, key=lambda e: np.linalg.norm((c + sv * e) - o)); far = pr.max() if ext == pr.min() else pr.min()
                sel = np.abs(pr - ext) < 0.03
                h = v[sel][:, :2].mean(0)
                fe = v[np.abs(pr - far) < 0.03][:, :2].mean(0); u = fe - h; u = u / (np.linalg.norm(u) or 1.0)
                cs, cc = inst_col.get(ii, (0, 0))
                lv.append((ii, h, u, cs, cc))
            doors.append((gname, c, zc, fv, len(leaves) >= 2, lv))
        elif kind == "ladder":
            segs = [ii for ii, nm in members]
            allv = np.vstack([inst_verts(ii) for ii in segs])
            body = [ii for ii, nm in members if 'segment' in nm.lower()] or segs
            bv = np.vstack([inst_verts(ii) for ii in body])
            cxy = (bv[:, :2].min(0) + bv[:, :2].max(0)) / 2
            tops = [ii for ii, nm in members if 'top' in nm.lower()]
            pdir = np.zeros(2)
            if tops:
                tv = np.vstack([inst_verts(ii) for ii in tops]); d_ = tv[:, :2].mean(0) - cxy
                if np.linalg.norm(d_) > 0.15: pdir = d_ / np.linalg.norm(d_)
            ladders.append((gname, cxy, float(allv[:, 2].min()), float(allv[:, 2].max()), pdir))
            _dz = 0.0; _mv = []
            if tops:
                _tm = [ii for ii, nm in members if 'top' in nm.lower() and 'step' not in nm.lower()] or tops      # the top piece itself: its hanging steps reach below where the segments should end
                _tmv = np.vstack([inst_verts(ii) for ii in _tm])
                _dz = float(bv[:, 2].max() - _tmv[:, 2].min()); _mv = [ii for ii in segs if ii not in tops]
                if _dz < 1.0: _dz = 0.0; _mv = []
            lad_slide.append((_dz, _mv))
    # item pickups (BP_InvPickup*): the map only stores where they are, not what they give, so --pickup chooses
    items = []
    _mt = open(map_path, encoding="utf-8", errors="replace").read()
    for mm in re.finditer(r'def Scope "(BP_InvPickup[^"]*)"\s*\{.*?xformOp:translate\s*=\s*\(([^)]*)\)', _mt, re.S):
        v = [float(x) for x in mm.group(2).split(',')]
        spec = (args.pickup or ["vials:3"])[min(len(items), len(args.pickup or ["vials:3"]) - 1)]
        kind, _, cnt = spec.partition(':')
        items.append((mm.group(1), v[0]*CM_TO_M, v[1]*CM_TO_M, v[2]*CM_TO_M, 1 if kind.startswith('bul') else 0, int(cnt or 1)))
    # ---- what the designers set on each placed door / pickup (map_props.json, made from the game's .pak by extract_map_props.py)
    _map_stem = os.path.splitext(os.path.basename(map_path))[0]
    _pp = None
    for _cand in ([os.path.expanduser(args.props)] if args.props else []) + [os.path.join(os.path.dirname(os.path.abspath(__file__)), "map_props.json"), "map_props.json"]:
        if os.path.isfile(_cand):
            try: _pp = json.load(open(_cand)); print("map properties:", _cand); break
            except Exception as _e: print("WARNING: could not read", _cand, _e)
    if _pp is None: print("WARNING: no map_props.json found - doors keep their old behaviour and every pickup gives blood vials (run extract_map_props.py)")
    _mp = (_pp or {}).get(_map_stem, {"doors": {}, "pickups": {}})
    if _pp is not None and _map_stem not in _pp: print(f"WARNING: {_map_stem} is not in map_props.json")
    STATE_VAL = {"Open": 0, "Unlocked": 1, "Locked": 2, "LockedFromInside": 3, "LockedFromOutside": 4, "LockedByDevice": 5}
    WHICH_VAL = {"Single": 0, "Double": 1, "Gate": 2}
    def _scope_forward(name):
        """the placed Blueprint's own forward direction (its +X axis), from its root orientation in the map (game frame)"""
        mm_ = re.search(r'def Scope "' + re.escape(name) + r'"\s*\{.*?xformOp:orient\s*=\s*\(([^)]*)\)', _mt, re.S)
        if not mm_: return None
        w_, x_, y_, z_ = [float(t) for t in mm_.group(1).split(',')]
        fx_, fy_ = 1 - 2 * (y_ * y_ + z_ * z_), 2 * (x_ * y_ + w_ * z_)
        n_ = math.hypot(fx_, fy_)
        return (fx_ / n_, fy_ / n_) if n_ > 1e-6 else None
    def _pretty(k):
        t = re.sub(r'(?<=[a-z])(?=[A-Z0-9])', ' ', re.sub(r'(?<=[0-9])(?=[A-Z])', ' ', k)).strip()
        return t[:27]
    def norm_item(k): return re.sub(r'\s+', '', k)
    def _item_cat(k):
        kl = k.lower().replace(' ', '')
        if kl.startswith('bloodvial'): return 0
        if kl.startswith('quicksilverbullet'): return 1
        if kl.startswith('weapon:'): return 7
        if 'key' in kl: return 3
        if any(w in kl for w in ('hat', 'body', 'garb', 'mask')): return 4
        if any(w in kl for w in ('shard', 'chunk', 'stone', 'dew', 'coldblood', 'blackskyeye', 'huntersmark')): return 5
        if any(w in kl for w in ('molotov', 'antidote', 'sedative', 'pebble', 'bullettrans', 'monocular')): return 2
        return 6
    # creature placements (BPC_Rat*, BPC_CarrionCrow*): position of the collision cylinder + yaw from its orientation
    spawns = []
    _bricks = []      # troll_brick: stand-alone SM_BrickProp meshes (the brick a troll carries), by position
    for _bm in re.finditer(r'\n    def Scope "([^"]+)"\s*\{(.*?)(?=\n    def Scope |\Z)', _mt, re.S):
        if 'SM_BrickProp' in _bm.group(2) and not _bm.group(1).startswith('BPC_Troll'):
            _bt = re.search(r'xformOp:translate\s*=\s*\(([^)]*)\)', _bm.group(2))
            if _bt: _bricks.append([float(x) * CM_TO_M for x in _bt.group(1).split(',')])
    for mm in re.finditer(r'def Scope "(BPC_Rat\w*|BPC_CarrionCrow\w*|BPC_Huntsman\w*|BPC_Yharnamite\w*|BPC_Werewolf\w*|BPC_RabidDog\w*|BPC_Troll\w*|BPC_DogRat\w*|BPC_DogCrow\w*|BPC_CrowDog\w*|BPC_GiantPig\w*|BPC_Werepig\w*|BPC_Wheelchair\w*)"\s*\{.*?xformOp:translate\s*=\s*\(([^)]*)\).*?xformOp:orient\s*=\s*\(([^)]*)\)', _mt, re.S):
        v = [float(x) for x in mm.group(2).split(',')]; qw, qx, qy, qz = [float(x) for x in mm.group(3).split(',')]
        yaw = math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
        _ty = 19 if 'Eileen' in mm.group(1) else 23 if 'Henryk' in mm.group(1) else None      # eileen_npc: Eileen the Crow (spawn code 19)
        if 'Huntsman' in mm.group(1) or 'Yharnamite' in mm.group(1):      # which Yharnamite is it? the scope names its skeleton and weapons: board+sabre 8, board+shield+torch 9, torch+axe 10, rifle 11, else the 1H swordsman 3
            _nx = _mt.find("\n    def Scope ", mm.start() + 10); _ch = _mt[mm.start(): _nx if _nx > 0 else mm.start() + 20000]
            _sk = re.search(r'Mesh/SkM_(Yhnmt\w+)\.usda', _ch); _sk = _sk.group(1) if _sk else ""
            _pr = re.search(r'"SM_PropR".*?Mesh/(SM_\w+)\.usda', _ch, re.S); _pr = _pr.group(1) if _pr else ""
            _ty = 8 if (_sk == "YhnmtBoard" and "Shield" not in _pr) else 9 if _sk == "YhnmtBoard" else 10 if _sk == "YhnmtTorch" else 11 if _sk == "YhnmtGun" else 3
        if 'Troll' in mm.group(1):      # the troll that holds the brick (a child of its scope, or a brick lying within 4 m) is spawn type 18
            _nx = _mt.find("\n    def Scope ", mm.start() + 10); _ch = _mt[mm.start(): _nx if _nx > 0 else mm.start() + 20000]
            if 'SM_BrickProp' in _ch or any(math.hypot(b[0] - v[0] * CM_TO_M, b[1] - v[1] * CM_TO_M) < 4.0 for b in _bricks): _ty = 18
        _nx = _mt.find("\n    def Scope ", mm.start() + 10); _cb = _mt[mm.start(): _nx if _nx > 0 else mm.start() + 20000]      # corpse_lay: a creature placed already dead (its pose asset names it)
        if 'CarrionCrow' in mm.group(1) and 'crow_DeathFrame' in _cb: _ty = 20; yaw -= math.pi / 2
        elif 'RabidDog' in mm.group(1) and 'AnimDog_DeathFrame' in _cb: _ty = 21; yaw -= math.pi / 2
        elif 'Werewolf' in mm.group(1) and 'Were_Dead' in _cb: _ty = 22; yaw -= math.pi / 2
        spawns.append((mm.group(1), v[0]*CM_TO_M, v[1]*CM_TO_M, v[2]*CM_TO_M, yaw, _ty if _ty else (12 if 'DogRat' in mm.group(1) else 14 if 'DogCrow' in mm.group(1) else 14 if 'CrowDog' in mm.group(1) else 15 if 'GiantPig' in mm.group(1) else 16 if 'Werepig' in mm.group(1) else 17 if 'Wheelchair' in mm.group(1) else 3 if ('Huntsman' in mm.group(1) or 'Yharnamite' in mm.group(1)) else (2 if 'Crow' in mm.group(1) else (5 if 'Werewolf' in mm.group(1) else (6 if 'RabidDog' in mm.group(1) else (7 if 'Troll' in mm.group(1) else 1)))))))
    # were_dead_scope: a werewolf corpse placed as a plain scope (e.g. "Were_Dead_2" in the basement), not a BPC_ blueprint
    for _nb in re.finditer(r'\n    def Scope "(Were_Dead\w*)"\s*\{(.*?)(?=\n    def Scope |\Z)', _mt, re.S):
        _nt = re.search(r'xformOp:translate\s*=\s*\(([^)]*)\)', _nb.group(2)); _nq = re.search(r'xformOp:orient\s*=\s*\(([^)]*)\)', _nb.group(2))
        if not _nt: continue
        _v = [float(x) for x in _nt.group(1).split(',')]; _yw = 0.0
        if _nq:
            _w, _qx, _qy, _qz = [float(x) for x in _nq.group(1).split(',')]; _yw = math.atan2(2 * (_w * _qz + _qx * _qy), 1 - 2 * (_qy * _qy + _qz * _qz))
        spawns.append((_nb.group(1), _v[0] * CM_TO_M, _v[1] * CM_TO_M, _v[2] * CM_TO_M, _yw - math.pi / 2, 22))
    # NPCs (Eileen the Crow = spawn code 19, Henryk = 23): each parsed from its own top-level scope block, so a neighbouring scope can never swallow it
    for _nb in re.finditer(r'\n    def Scope "(BP_EileenTheCrow\w*|BP_HenrykNPC\w*|BP_Doll\w*|BP_CharLightVolumeDoll\w*|BP_CharLightVolume2\b|BP_NoteMessenger\w*|BP_MessengerWeapGrant\w*|BP_WLPoint\w*|BP_Store\w*)"\s*\{(.*?)(?=\n    def Scope |\Z)', _mt, re.S):
        _nt = re.search(r'xformOp:translate\s*=\s*\(([^)]*)\)', _nb.group(2)); _nq = re.search(r'xformOp:orient\s*=\s*\(([^)]*)\)', _nb.group(2))
        if not _nt: continue
        _v = [float(x) for x in _nt.group(1).split(',')]; _yw = 0.0
        if _nq:
            _w, _qx, _qy, _qz = [float(x) for x in _nq.group(1).split(',')]; _yw = math.atan2(2 * (_w * _qz + _qx * _qy), 1 - 2 * (_qy * _qy + _qz * _qz))
        spawns.append((_nb.group(1), _v[0] * CM_TO_M, _v[1] * CM_TO_M, _v[2] * CM_TO_M, _yw, 30 if 'BP_Store' in _nb.group(1) else 29 if 'WLPoint' in _nb.group(1) else 19 if 'Eileen' in _nb.group(1) else 24 if 'Doll' in _nb.group(1) else 25 if 'LightVolume2' in _nb.group(1) else (28 if 'GrantL' in _nb.group(1) else 27) if 'WeapGrant' in _nb.group(1) else 26 if 'NoteMessenger' in _nb.group(1) else 23))
    # save-point lanterns (BP_SavePointLantern*): where they stand; the lantern sprite and its gleam come along so main.c needs no extra file
    lamps = []
    for mm in re.finditer(r'def Scope "(BP_SavePointLantern\w*)"\s*\{\s*def Xform "DefaultSceneRoot"\s*\{[^}]*?xformOp:translate\s*=\s*\(([^)]*)\)', _mt, re.S):
        v = [float(x) for x in mm.group(2).split(',')]
        lamps.append((mm.group(1), v[0]*CM_TO_M, v[1]*CM_TO_M, v[2]*CM_TO_M))
    # fires: placed fire particle systems (P_FireFlame*: the bonfires) and pyres (SM_Pyre*): x, y, z (m), scale, kind (0 small, 1 medium, 2 large)
    fires = []
    for mm in re.finditer(r'def Scope "(P_Fire\w*)"\s*\{\s*def Xform "ParticleSystemComponent0"\s*\{[^}]*?xformOp:translate\s*=\s*\(([^)]*)\)(?:[^}]*?xformOp:scale\s*=\s*\(([^)]*)\))?', _mt, re.S):
        v = [float(x) for x in mm.group(2).split(',')]; sc_ = float(mm.group(3).split(',')[0]) if mm.group(3) else 1.0
        kd_ = 0 if "Small" in mm.group(1) else (1 if "Med" in mm.group(1) else 2)
        fires.append((mm.group(1), v[0]*CM_TO_M, v[1]*CM_TO_M, v[2]*CM_TO_M, sc_, kd_))
    for mm in re.finditer(r'def Scope "(SM_Pyre\w*)"\s*\{\s*def Mesh "StaticMeshComponent0"[^{]*\{[^}]*?xformOp:translate\s*=\s*\(([^)]*)\)(?:[^}]*?xformOp:scale\s*=\s*\(([^)]*)\))?', _mt, re.S):
        v = [float(x) for x in mm.group(2).split(',')]; sc_ = float(mm.group(3).split(',')[0]) if mm.group(3) else 1.0
        fires.append((mm.group(1), v[0]*CM_TO_M, v[1]*CM_TO_M, v[2]*CM_TO_M + 0.6*sc_, sc_, 2))
    lamp_tex = []
    if lamps:
        for _fn, _sz in (("T_LanternLightPlaced.png", (32, 64)), ("T_Gleam.png", (64, 64)), ("T_LanternBeam.png", (64, 128))):
            _p = os.path.join(assets, "BP", "Save", "Mat", _fn)
            try:
                _im = Image.open(_p).convert("RGBA").resize(_sz, Image.BOX)
                lamp_tex.append((_sz[0], _sz[1], _im.tobytes()))
            except Exception:
                print(f"WARNING: lamp texture {_p} not found: the lantern will not be drawn")
                lamp_tex = []; break
    # level loaders (BP_LevelLoader*): trigger box, arrival point (EntranceVector) and type, for linking maps
    loaders = []
    for mm in re.finditer(r'\n    def Scope "(BP_LevelLoader\w*)"\s*\{(.*?)\n    \}', _mt, re.S):
        body = mm.group(2)
        def _xf(blk):
            t = nums(re.search(r'xformOp:translate\s*=\s*\(([^)]*)\)', blk).group(1)); q = nums(re.search(r'xformOp:orient\s*=\s*\(([^)]*)\)', blk).group(1))
            return t, q
        root = re.search(r'def Xform "DefaultSceneRoot"\s*\{(.*)', body, re.S)
        if not root: continue
        rt, rq = _xf(root.group(1))
        Rr = quat_to_mat(rq)
        def child(nm):
            c = re.search(r'def Xform "%s"\s*\{(.*?)(?=\n            def Xform|\n        \}|$)' % nm, root.group(1), re.S)
            if not c: return None
            t, q = _xf(c.group(1))
            return [rt[i] + sum(Rr[i][k] * t[k] for k in range(3)) for i in range(3)]
        box, ent = child("Box"), child("EntranceVector")
        if box is None: continue
        if ent is None: ent = list(rt)
        etype = 1 if abs(nums(re.search(r'def Xform "Box"\s*\{.*?translate\s*=\s*\(([^)]*)\)', root.group(1), re.S).group(1))[2] - 195.0) < 1.0 else 2   # 1 = door, 2 = ladder
        o = [rt[0], rt[1], rt[2]]
        yaw = math.atan2(ent[1] - o[1], ent[0] - o[0])        # arrive facing away from the loader
        loaders.append((mm.group(1), etype, [v * CM_TO_M for v in box], [v * CM_TO_M for v in ent], yaw, [v * CM_TO_M for v in o]))
    # rolling boulders (BoulderSpawner*): where they start and which way they roll (the spawner's forward = +X turned by its yaw)
    boulders = []
    for mm in re.finditer(r'def Scope "(BoulderSpawner\w*)"\s*\{.*?xformOp:translate\s*=\s*\(([^)]*)\).*?xformOp:orient\s*=\s*\(([^)]*)\)', _mt, re.S):
        v = [float(x) for x in mm.group(2).split(',')]; qw, qx, qy, qz = [float(x) for x in mm.group(3).split(',')]
        yaw = math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
        boulders.append((mm.group(1), v[0]*CM_TO_M, v[1]*CM_TO_M, v[2]*CM_TO_M, yaw))
    # elevators (SM_Elevator1 + the BP_Switch riding on it): footprint, bottom / top floor height and the switch position
    elevators = []
    for em in re.finditer(r'def Scope "(SM_Elevator\d\w*)"\s*\{.*?xformOp:translate\s*=\s*\(([^)]*)\)', _mt, re.S):
        _et = [float(x) * CM_TO_M for x in em.group(2).split(',')]
        parts = [(ii, ) + inst_col.get(ii, (0, 0)) for ii, (grp_, nm_) in enumerate(inst_info) if 'SM_Elevator' in nm_ and abs(instances[ii][1][3] - _et[0]) < 0.05 and abs(instances[ii][1][7] - _et[1]) < 0.05 and abs(instances[ii][1][11] - _et[2]) < 0.05]
        if not parts: continue
        ev = np.vstack([inst_verts(p[0]) for p in parts])
        zb = float(instances[parts[0][0]][1][11]); fl = ev[ev[:, 2] < zb + 0.3]
        ex0, ex1, ey0, ey1 = float(fl[:, 0].min()), float(fl[:, 0].max()), float(fl[:, 1].min()), float(fl[:, 1].max())
        ecx, ecy = (ex0 + ex1) / 2, (ey0 + ey1) / 2
        zt = zb + 12.0
        for nm_, ty_, bx_, en_, yw_, og_ in loaders:                    # the top stop is a loader (door) whose origin sits over the shaft, above the car
            if ex0 - 1.0 <= og_[0] <= ex1 + 1.0 and ey0 - 1.0 <= og_[1] <= ey1 + 1.0 and og_[2] > zb + 3.0: zt = og_[2]
        zdn = None
        for nm_, ty_, bx_, en_, yw_, og_ in loaders:                    # lift_down: a loader over the shaft BELOW the car = a lift that rides down (Backstreets -> Operating Room); the car starts at its top (zt) and the bottom stop is the loader
            if zt == zb + 12.0 and ex0 - 1.0 <= og_[0] <= ex1 + 1.0 and ey0 - 1.0 <= og_[1] <= ey1 + 1.0 and og_[2] < zb - 3.0: zdn = og_[2]
        if zdn is not None: zt, zb = zb, zdn
        sm = re.search(r'def Scope "BP_Switch\w*"\s*\{\s*def Xform "DefaultSceneRoot"\s*\{.*?xformOp:translate\s*=\s*\(([^)]*)\)', _mt[em.end():em.end() + 6000], re.S)
        sw = [ecx, ecy]
        if sm:
            rel = [float(x) for x in sm.group(1).split(',')]
            et = [float(x) for x in em.group(2).split(',')]
            sw = [(et[0] + rel[0]) * CM_TO_M, (et[1] + rel[1]) * CM_TO_M]
        elevators.append((em.group(1), ecx, ecy, (ex1 - ex0) / 2, (ey1 - ey0) / 2, zb, zt, sw[0], sw[1], parts))
    portc = []      # ptc_lift: every SM_Portcullis*: footprint centre, how far it rises (its own height) and its instance(s) + collision, so a lever can raise it
    for pm in re.finditer(r'def Scope "(SM_Portcullis\w*)"\s*\{.*?xformOp:translate\s*=\s*\(([^)]*)\)', _mt, re.S):
        _pt = [float(x) * CM_TO_M for x in pm.group(2).split(',')]
        _pp = [(ii, ) + inst_col.get(ii, (0, 0)) for ii, (grp_, nm_) in enumerate(inst_info) if 'SM_Portcullis' in nm_ and abs(instances[ii][1][3] - _pt[0]) < 0.05 and abs(instances[ii][1][7] - _pt[1]) < 0.05 and abs(instances[ii][1][11] - _pt[2]) < 0.05]
        if not _pp: continue
        _pv = np.vstack([inst_verts(q[0]) for q in _pp])
        _c2 = _pv[:, :2] - _pv[:, :2].mean(0); _ev, _evec = np.linalg.eigh(np.cov(_c2.T) if len(_c2) > 2 else np.eye(2))
        _u = _evec[:, 1]; _nrm = _evec[:, 0]                                     # width axis (long) and thickness axis (short), horizontal
        _th = float((_c2 @ _nrm).max() - (_c2 @ _nrm).min()); _hh = float(_pv[:, 2].max() - _pv[:, 2].min())
        _up = _hh > 1.0 and _hh > 1.5 * _th                                        # standing upright = the raised drawbridge; one lying flat is left alone
        portc.append((pm.group(1), float(_pv[:, 0].mean()), float(_pv[:, 1].mean()), _hh if _up else 0.0, float(_pv[:, 2].min()), float(_u[0]), float(_u[1]), float(_nrm[0]), float(_nrm[1]), _th, _pp[:4]))
    if "DeepSewers" in os.path.basename(map_path):      # ptc_beam: the main room's wooden drawbridge is the plain mesh SM_WoodBeam7 (the level script's LowerBridge timeline tilts it from 70 degrees to flat about its origin)
        for pm in re.finditer(r'def Scope "(SM_WoodBeam7)"\s*\{.*?xformOp:translate\s*=\s*\(([^)]*)\)', _mt, re.S):
            _pt = [float(x) * CM_TO_M for x in pm.group(2).split(',')]
            _pp = [(ii, ) + inst_col.get(ii, (0, 0)) for ii, (grp_, nm_) in enumerate(inst_info) if 'WoodBeam' in nm_ and abs(instances[ii][1][3] - _pt[0]) < 0.05 and abs(instances[ii][1][7] - _pt[1]) < 0.05 and abs(instances[ii][1][11] - _pt[2]) < 0.05]
            if not _pp: print(f"  drawbridge beam {pm.group(1)}: no mesh instance at ({_pt[0]:.1f},{_pt[1]:.1f},{_pt[2]:.1f}) - not found"); continue
            _pv = np.vstack([inst_verts(q[0]) for q in _pp]); _ev, _evec = np.linalg.eigh(np.cov((_pv - _pv.mean(0)).T)); _a = _evec[:, 2]
            for _sn in ("SM_WoodBeam8", "SM_WoodBeam_259"):      # ptc_side: the planks either side are attached to the beam in the map (+/-1 m along its Y), so they swing with it
                _sm = re.search(r'def Scope "%s"\s*\{.*?xformOp:translate\s*=\s*\(([^)]*)\)' % _sn, _mt, re.S)
                if not _sm: print(f"  drawbridge side plank {_sn}: scope not found"); continue
                _st = [float(x) * CM_TO_M for x in _sm.group(1).split(',')]
                _sp = [(ii, ) + inst_col.get(ii, (0, 0)) for ii, (grp_, nm_) in enumerate(inst_info) if 'WoodBeam' in nm_ and abs(instances[ii][1][3] - _st[0]) < 0.05 and abs(instances[ii][1][7] - _st[1]) < 0.05 and abs(instances[ii][1][11] - _st[2]) < 0.05]
                print(f"  drawbridge side plank {_sn}: at ({_st[0]:.1f},{_st[1]:.1f},{_st[2]:.1f}) {len(_sp)} instance(s)"); _pp = _pp + _sp
            if len(_pp) < 3:      # ptc_side2: the planks are children of the beam, so their scope translate is relative to it; take the WoodBeam meshes lying beside the beam instead
                _bc = _pv.mean(0); _have = {q[0] for q in _pp}; _cand = []
                for ii, (grp_, nm_) in enumerate(inst_info):
                    if 'WoodBeam' not in nm_ or ii in _have: continue
                    _cv = inst_verts(ii); _cc = _cv.mean(0); _d = float(np.linalg.norm(_cc - _bc))
                    _cand.append((_d, ii, nm_, _cc))
                _cand.sort(key=lambda q: q[0])
                for _d, ii, nm_, _cc in _cand[:6]: print(f"  WoodBeam near the drawbridge: instance {ii} {nm_} centre ({_cc[0]:.1f},{_cc[1]:.1f},{_cc[2]:.1f}) {_d:.1f} m from the beam")
                for _d, ii, nm_, _cc in _cand:
                    if _d < 4.5 and len(_pp) < 4: _pp.append((ii, ) + inst_col.get(ii, (0, 0))); print(f"  drawbridge side plank (by distance): instance {ii} {nm_}")
            if _a[2] < 0: _a = -_a
            _al = float(np.arcsin(min(1.0, abs(_a[2])))); _hxy = _a[:2] / (np.linalg.norm(_a[:2]) or 1.0)
            if _al < 0.17: print(f"  drawbridge beam {pm.group(1)} lies flat already: left alone"); continue
            print(f"  drawbridge beam {pm.group(1)}: hinge ({_pt[0]:.1f},{_pt[1]:.1f},{_pt[2]:.1f}) tilted {math.degrees(_al):.0f} deg, swings toward ({_hxy[0]:.2f},{_hxy[1]:.2f})")
            portc.append((pm.group(1), _pt[0], _pt[1], 1.0, _pt[2], 0.0, 0.0, float(_hxy[0]), float(_hxy[1]), -_al, _pp[:4]))      # thick < 0 = swing by that many radians toward (nx, ny), hinge at the origin
    if sky_parts:      # sky_export: sky_<map>.bin = "SKY1", parts: w,h, RGBA, vertex count, index count, (x y z u v)*, indices
        _sp = os.path.join(os.path.dirname(os.path.expanduser(args.out)) or ".", "sky_" + (os.path.basename(args.out)[6:] if os.path.basename(args.out).startswith("level_") else os.path.basename(args.out)))
        with open(_sp, "wb") as f:
            f.write(b"SKY1"); f.write(struct.pack("<I", len(sky_parts)))
            for _png, _wp, _uv, _ind in sky_parts:
                try:
                    _im = Image.open(_png).convert("RGBA"); _im = _im.resize((pot_floor(_im.width, 256), pot_floor(_im.height, 256)), Image.BOX)
                except Exception:
                    _im = Image.new("RGBA", (8, 8), (90, 90, 110, 255))
                f.write(struct.pack("<HH", _im.width, _im.height)); f.write(_im.tobytes())
                f.write(struct.pack("<II", len(_wp), len(_ind)))
                for q, uv in zip(_wp, _uv): f.write(struct.pack("<5f", q[0], q[1], q[2], uv[0], uv[1]))
                f.write(struct.pack("<%dI" % len(_ind), *_ind))
        print(f"  sky: {len(sky_parts)} parts -> {os.path.basename(_sp)} (" + ", ".join(os.path.basename(x[0]) if x[0] else "no texture" for x in sky_parts) + ")")
    _stem = os.path.basename(os.path.expanduser(args.out))
    _ibase = ("interact_" + _stem[len("level_"):]) if _stem.startswith("level_") else ("interact_" + _stem)
    ipath = os.path.join(os.path.dirname(os.path.expanduser(args.out)) or ".", _ibase)
    with open(ipath, "wb") as f:
        f.write(b"BBI1"); f.write(struct.pack("<I", len(doors)))
        for gname, c, zc, fv, dbl, lv in doors:
            f.write(struct.pack("<3f2fII", float(c[0]), float(c[1]), zc, float(fv[0]), float(fv[1]), int(dbl), len(lv)))
            for ii, h, u, cs, cc in lv:
                f.write(struct.pack("<I4fII", ii, float(h[0]), float(h[1]), float(u[0]), float(u[1]), cs, cc))
        f.write(struct.pack("<I", len(ladders)))
        for gname, cxy, z0, z1, pdir in ladders:
            f.write(struct.pack("<2f2f2f", float(cxy[0]), float(cxy[1]), z0, z1, float(pdir[0]), float(pdir[1])))
        _eil = [(sp[1], sp[2]) for sp in spawns if sp[5] == 19] if spawns and len(spawns[0]) > 5 else []      # eileen_npc: a pickup standing on Eileen's spot is a placeholder - drop it
        _keep = []
        for _it in items:
            if any(math.hypot(_it[1] - ex_, _it[2] - ey_) < 1.6 for ex_, ey_ in _eil): print(f"  dropped pickup {_it[0]} at Eileen's spot ({_it[1]:.1f}, {_it[2]:.1f})")
            else: _keep.append(_it)
        items = _keep
        f.write(b"ITM1"); f.write(struct.pack("<I", len(items)))
        for nm_, x_, y_, z_, k_, c_ in items: f.write(struct.pack("<3fII", x_, y_, z_, k_, c_))
        f.write(b"SPN1"); f.write(struct.pack("<I", len(spawns)))
        for nm_, x_, y_, z_, yw_, ty_ in spawns: f.write(struct.pack("<4fI", x_, y_, z_, yw_, ty_))
        f.write(b"LDR1"); f.write(struct.pack("<I", len(loaders)))
        for nm_, ty_, bx_, en_, yw_, og_ in loaders:
            f.write(nm_.encode()[:31].ljust(32, b"\0")); f.write(struct.pack("<I3f3ff3f", ty_, *bx_, *en_, yw_, *og_))
        f.write(b"BLD1"); f.write(struct.pack("<I", len(boulders)))
        for nm_, x_, y_, z_, yw_ in boulders: f.write(struct.pack("<4f", x_, y_, z_, yw_))
        f.write(b"ELV1"); f.write(struct.pack("<I", len(elevators)))
        for nm_, cx_, cy_, hx_, hy_, zb_, zt_, sx_, sy_, parts_ in elevators:
            f.write(struct.pack("<8fI", cx_, cy_, hx_, hy_, zb_, zt_, sx_, sy_, len(parts_)))
            for p_ in parts_: f.write(struct.pack("<3I", p_[0], p_[1], p_[2]))
        # DST1: what each door is (state / which / key / the Blueprint's forward direction); same order as the doors above
        f.write(b"DST1"); f.write(struct.pack("<I", len(doors)))
        for gname, c, zc, fv, dbl, lv in doors:
            dp_ = _mp["doors"].get(gname)
            fw_ = _scope_forward(gname) or (float(fv[0]), float(fv[1]))
            stv_ = STATE_VAL.get(dp_["state"], 255) if dp_ else 255
            wh_ = WHICH_VAL.get(dp_["which"], 1) if dp_ else (1 if dbl else 0)
            fl_ = (1 if (dp_ and dp_.get("autoexit")) else 0)
            f.write(struct.pack("<BBBBff", stv_, wh_, fl_, 0, fw_[0], fw_[1]))
            f.write(((dp_ or {}).get("key", "")).encode("latin1", "replace")[:23].ljust(24, b"\0"))
            kl_ = (dp_ or {}).get("key_label", "") or ""
            f.write(((kl_ if (" " in kl_ or not kl_) else _pretty(kl_))).upper().encode("latin1", "replace")[:27].ljust(28, b"\0"))
        # ITM2: what each pickup gives (up to 2 things: name, count, category) + whether it comes back after resting at a lantern
        f.write(b"ITM2"); f.write(struct.pack("<I", len(items)))
        for nm_, x_, y_, z_, k_, c_ in items:
            pp_ = _mp["pickups"].get(nm_); ents_ = []
            if pp_ is not None:
                for dn_, dc_ in pp_.get("drops", {}).items(): ents_.append((norm_item(dn_), dn_ if " " in dn_ else _pretty(dn_), dc_))
                if pp_.get("weapon"): ents_.append(("WEAPON:" + pp_["weapon"].replace(" ", ""), pp_["weapon"] + " UNLOCKED", 1))
            else:
                ents_.append(("QuicksilverBullets" if k_ else "BloodVial", "", c_))
            ents_ = ents_[:2]
            f.write(struct.pack("<3fBBBB", x_, y_, z_, len(ents_), 1 if (pp_ and pp_.get("norefresh")) else 0, 0, 0))
            for _i in range(2):
                if _i < len(ents_):
                    key_, lab_, cnt_ = ents_[_i]
                    f.write(struct.pack("<iBBBB", int(cnt_), _item_cat(key_), 0, 0, 0)); f.write(key_.encode("latin1", "replace")[:23].ljust(24, b"\0"))
                    f.write((lab_ or _pretty(key_)).upper().encode("latin1", "replace")[:27].ljust(28, b"\0"))
                else: f.write(b"\0" * (8 + 24 + 28))
        f.write(b"FIR1"); f.write(struct.pack("<I", len(fires)))
        for nm_, x_, y_, z_, sc_, kd_ in fires: f.write(struct.pack("<4fI", x_, y_, z_, sc_, kd_))
        _wch = [ii for ii, (grp_, nm_) in enumerate(inst_info) if ('SM_Wheelchair' in nm_ and 'Gehr' not in nm_ and _chair_bound(ii)) or 'SM_GilbTable' in nm_]      # WCH1: wheelchair meshes (the game moves the one next to each wheelchair enemy with him)
        f.write(b"WCH1"); f.write(struct.pack("<I", len(_wch)))
        for _i in _wch: f.write(struct.pack("<I", _i))
        f.write(b"LSL1"); f.write(struct.pack("<I", len(lad_slide)))      # lever_slide: exported ladder = raised pose; dz = how far its segments drop (top of segments -> base of the top piece)
        for _dz, _mv in lad_slide:
            f.write(struct.pack("<fI", _dz, len(_mv)))
            for _i in _mv: f.write(struct.pack("<I", _i))
        f.write(b"PTC1"); f.write(struct.pack("<I", len(portc)))      # ptc_lift
        for _n, _cx, _cy, _h, _zm, _ux, _uy, _nx, _ny, _th, _pp in portc:
            f.write(struct.pack("<9fI", _cx, _cy, _h, _zm, _ux, _uy, _nx, _ny, _th, len(_pp)))
            for _q in _pp: f.write(struct.pack("<3I", _q[0], _q[1], _q[2]))
        f.write(b"LMP1"); f.write(struct.pack("<I", len(lamps)))
        for nm_, x_, y_, z_ in lamps: f.write(struct.pack("<3f", x_, y_, z_))
        f.write(struct.pack("<I", len(lamp_tex)))
        for w_, h_, raw_ in lamp_tex: f.write(struct.pack("<HH", w_, h_)); f.write(raw_)
    for nm_, x_, y_, z_, sc_, kd_ in fires: print(f"  fire {nm_}: ({x_:.2f},{y_:.2f},{z_:.2f}) scale {sc_:g} kind {kd_}")
    for nm_, x_, y_, z_ in lamps: print(f"  lantern {nm_}: ({x_:.2f},{y_:.2f},{z_:.2f})")
    for nm_, cx_, cy_, hx_, hy_, zb_, zt_, sx_, sy_, parts_ in elevators: print(f"  elevator {nm_}: centre ({cx_:.2f},{cy_:.2f}) half-size ({hx_:.2f},{hy_:.2f}) floor {zb_:.2f} -> {zt_:.2f}, switch ({sx_:.2f},{sy_:.2f}), {len(parts_)} parts")
    for nm_, x_, y_, z_, yw_ in boulders: print(f"  boulder spawner {nm_}: ({x_:.2f},{y_:.2f},{z_:.2f}) rolls toward yaw {math.degrees(yw_):.0f}")
    for nm_, ty_, bx_, en_, yw_, og_ in loaders: print(f"  loader {nm_} ({'door' if ty_ == 1 else 'ladder'}): trigger ({bx_[0]:.2f},{bx_[1]:.2f},{bx_[2]:.2f}) arrive ({en_[0]:.2f},{en_[1]:.2f},{en_[2]:.2f})")
    print(f"{_ibase}: {len(loaders)} level loaders, {len(doors)} doors, {len(ladders)} ladders, {len(items)} pickups, {len(spawns)} creatures")
    _nodata = 0
    for gname, c, zc, fv, dbl, lv in doors:
        dp_ = _mp["doors"].get(gname); fw_ = _scope_forward(gname)
        if dp_ is None: _nodata += 1; print(f"  door {gname}: no data in map_props.json - behaves as before"); continue
        print(f"  door {gname}: {dp_['state']}" + (f" key {dp_['key_label']}" if dp_.get('key') else "") + f", {dp_['which']}" + (f", forward ({fw_[0]:.2f},{fw_[1]:.2f})" if fw_ else ", forward unknown") + (" - ONE WAY" if dp_['state'] in ('LockedFromInside', 'LockedFromOutside') else ""))
    for nm_, x_, y_, z_, k_, c_ in items:
        pp_ = _mp["pickups"].get(nm_)
        if pp_ is None: _nodata += 1; print(f"  pickup {nm_}: no data in map_props.json - gives blood vials x{c_}"); continue
        print(f"  pickup {nm_}: " + ", ".join(f"{n} x{c}" for n, c in pp_.get("drops", {}).items()) + (f" + weapon {pp_['weapon']}" if pp_.get('weapon') else "") + ("" if pp_.get('norefresh') else " (comes back after resting)"))
    if _pp is not None and _nodata: print(f"WARNING: {_nodata} doors/pickups of this map have no entry in map_props.json (name mismatch?)")
    for nm_, x_, y_, z_, yw_, ty_ in spawns: print(f"  {'huntsman' if ty_ == 3 else ('crow' if ty_ == 2 else ('npc  ' if ty_ in (19, 23, 24, 25, 26, 27, 28) else 'rat '))} {nm_}: ({x_:.2f},{y_:.2f},{z_:.2f}) yaw {math.degrees(yw_):.0f}")
    for nm_, x_, y_, z_, k_, c_ in items: print(f"  pickup {nm_}: ({x_:.2f},{y_:.2f},{z_:.2f}) {'bullets' if k_ else 'blood vials'} x{c_}")
    for gname, c, zc, fv, dbl, lv in doors: print(f"  door {gname}: centre ({c[0]:.1f},{c[1]:.1f},{zc:.1f}) {'double' if dbl else 'single'}, hinges {[tuple(round(float(x),2) for x in l[1]) for l in lv]}")
    for _n, _cx, _cy, _h, _zm, _ux, _uy, _nx, _ny, _th, _pp in portc: print(f"  portcullis {_n}: ({_cx:.1f},{_cy:.1f}) z {_zm:.1f} height {_h:.1f} m thick {_th:.2f} m ({'upright: hinged drawbridge' if _h > 0 else 'flat: left alone'})")
    for _k, _ls in enumerate(lad_slide): print(f"  ladder {_k}: slides {_ls[0]:.2f} m ({len(_ls[1])} segments)")
    for gname, cxy, z0, z1, pdir in ladders: print(f"  ladder {gname}: ({cxy[0]:.1f},{cxy[1]:.1f}) z {z0:.1f}..{z1:.1f} top side ({pdir[0]:.2f},{pdir[1]:.2f})")

    # ---- spawn point (PlayerStart capsule centre), metres
    spawn = None
    mtxt = open(map_path, encoding="utf-8", errors="replace").read()
    ms = re.search(r'def Scope "PlayerStart[^"]*"\s*\{.*?xformOp:translate\s*=\s*\(([^)]*)\)', mtxt, re.S)
    if ms:
        v = nums(ms.group(1))
        spawn = (v[0]*CM_TO_M, v[1]*CM_TO_M, v[2]*CM_TO_M)
    else:
        print("WARNING: no PlayerStart found; spawning at origin + 2m")
        spawn = (0.0, 0.0, 2.0)

    # ---- write
    # breakables: everything the map places under a destructible blueprint (BPC_Dest_*: barrels, barrel stacks ...) goes into breakables_<map>.txt, one instance per line:
    #   instance  first-collision-triangle  collision-triangle-count  centre-x  centre-y  bottom-z  half-width-x  half-width-y  height  group     (metres; instances with the same group break together)
    # the game hides the instances and removes their collision when a swing, a roll, a shot or a fire hits one of them
    _mp = os.path.basename(os.path.expanduser(args.out)).lower()      # the map this file is for, e.g. level_gascoignearena.bin
    _gasmap = "gascoignearena" in _mp
    _cbmap = "clericbeast" in _mp      # the Cleric Beast's arena: its carriages stay solid for you but the beast smashes them (kind 1)
    # kind 1 = boss only. In Gascoigne's arena everything that is not a barrel / crate / box counts, because the tombstone's mesh name is not known for sure
    _kind = lambda nm: 1 if (any(k_ in nm.split()[-1].lower() for k_ in BOSS_ONLY_MESHES) or (_cbmap and any(k_ in nm.split()[-1].lower() for k_ in UNBREAKABLE_MESHES)) or (_gasmap and not any(k_ in nm.split()[-1].lower() for k_ in ("barrel", "crate", "box")))) else 0
    _dest = {}; _skipped = {}
    for ii, (grp_, nm_) in enumerate(inst_info):
        if grp_ and grp_[0] == "dest":
            if _cbmap or not any(k_ in nm_.split()[-1].lower() for k_ in UNBREAKABLE_MESHES): _dest.setdefault(grp_[1], []).append(ii)      # everything under a destructible blueprint except the unbreakable list
            else: _skipped[nm_.split()[-1]] = _skipped.get(nm_.split()[-1], 0) + 1
    _bk = []
    if _skipped: print("  under a destructible blueprint but NOT made breakable: " + ", ".join(f"{k} x{v}" for k, v in sorted(_skipped.items())))
    if _dest:
        print(f"  destructible blueprints in this map: {len(_dest)}")
        for _gi, (_gn, _mem) in enumerate(sorted(_dest.items())):
            print(f"    {_gn}: " + ", ".join(sorted(set(inst_info[m][1].split()[-1] for m in _mem))) + f" (x{len(_mem)})")
            for ii in _mem:
                _V = inst_verts(ii); _lo = _V.min(0); _hi = _V.max(0); _cs, _cc = inst_col.get(ii, (0, 0))
                _bk.append((ii, _cs, _cc, (_lo[0] + _hi[0]) / 2, (_lo[1] + _hi[1]) / 2, _lo[2], (_hi[0] - _lo[0]) / 2, (_hi[1] - _lo[1]) / 2, _hi[2] - _lo[2], _gi, _kind(inst_info[ii][1])))
        _loose = [ii for ii, (g_, n_) in enumerate(inst_info) if not (g_ and g_[0] == "dest") and n_.split()[-1] == 'SM_Barrel']
        if _loose: print(f"  note: {len(_loose)} SM_Barrel instances are NOT under a destructible blueprint (left unbreakable)")
    else:      # the map has no BPC_Dest_ scopes (or they are named differently): every SM_Barrel counts, one by one
        for ii, (grp_, nm_) in enumerate(inst_info):
            if nm_.split()[-1] != 'SM_Barrel': continue
            _V = inst_verts(ii); _lo = _V.min(0); _hi = _V.max(0); _cs, _cc = inst_col.get(ii, (0, 0))
            _bk.append((ii, _cs, _cc, (_lo[0] + _hi[0]) / 2, (_lo[1] + _hi[1]) / 2, _lo[2], (_hi[0] - _lo[0]) / 2, (_hi[1] - _lo[1]) / 2, _hi[2] - _lo[2], -1, 0))
        if _bk: print("  note: no BPC_Dest_ blueprint found in this map: every SM_Barrel was made breakable instead")
    _bn = os.path.basename(os.path.expanduser(args.out)); _bn = "breakables_" + (_bn[len("level_"):-4] if _bn.startswith("level_") and _bn.endswith(".bin") else _bn) + ".txt"
    _bp = os.path.join(os.path.dirname(os.path.expanduser(args.out)) or ".", _bn)
    if _bk:
        with open(_bp, "w") as _bf:
            for _r in _bk: _bf.write("%d %d %d %.3f %.3f %.3f %.3f %.3f %.3f %d %d\n" % _r)
        print(f"  breakables: {len(_bk)} pieces -> {_bn}")
    elif os.path.exists(_bp):
        os.remove(_bp)
    out = os.path.expanduser(args.out)
    _fst = os.path.basename(out)
    _fname = ("floor_" + _fst[len("level_"):]) if _fst.startswith("level_") else ("floor_" + _fst)
    with open(os.path.join(os.path.dirname(out) or ".", _fname), "wb") as f:
        f.write(b"FLR1"); f.write(struct.pack("<I", len(floor_tris)))
        for ft in floor_tris: f.write(struct.pack("<I9f", ft[0], *ft[1:]))
    with open(out, "wb") as f:
        f.write(b"BBL2")
        f.write(struct.pack("<IIIII", len(tex_names), len(geoms), len(drawables), len(instances), len(col)))
        f.write(struct.pack("<3f", *spawn))
        for tri in col:
            f.write(struct.pack("<9f", *tri))
        for n, (w, h, data) in zip(tex_names, tex_data):
            nb = n.encode()[:255]
            f.write(struct.pack("<B", len(nb)) + nb + struct.pack("<HH", w, h) + data)
        for pos, uv, ind in geoms:
            if len(pos) > 65535:
                print("ERROR: geometry with >65535 vertices"); sys.exit(1)
            f.write(struct.pack("<II", len(pos), len(ind)))
            for p, u in zip(pos, uv):
                f.write(struct.pack("<5f", p[0], p[1], p[2], u[0], u[1]))
            f.write(struct.pack(f"<{len(ind)}H", *ind))
        for parts in drawables:
            f.write(struct.pack("<H", len(parts)))
            for g, t in parts:
                f.write(struct.pack("<IH", g, t))
        for d, mat in instances:
            f.write(struct.pack("<I12f", d, *mat))

    # ---- report
    tri_total = sum(len(geoms[g][2]) // 3 * 1 for parts in [drawables[d] for d, _ in instances] for g, _ in parts)
    tex_bytes = sum(w*h*4 for w, h, _ in tex_data)
    print(f"\nwrote {out} ({os.path.getsize(out)/1024:.0f} KB)")
    print(f"  textures: {len(tex_names)} ({tex_bytes/1024:.0f} KB raw RGBA)")
    print(f"  geometry blocks: {len(geoms)}, drawables: {len(drawables)}, instances drawn: {len(instances)}")
    print(f"  triangles if ALL instances drawn at once: {tri_total}")
    print(f"  collision triangles: {len(col)}")
    print(f"  spawn (m): {spawn[0]:.2f} {spawn[1]:.2f} {spawn[2]:.2f}")
    if skipped:
        print("\nskipped by design:", dict(skipped))
    if missing_meshes:
        print("\nMISSING MESH FILES (export these):")
        for n, c in missing_meshes.most_common():
            print(f"  {n}  (x{c})")
    nc = Counter()
    for d, m in instances:
        if any(x in drawable_mesh[d] for x in nocol):
            nc[drawable_mesh[d]] += 1
    if nc:
        print("\nno collision for (decorations):", dict(nc))
    print("\nTEXTURE REPORT  (name, original size, mode, %fully-transparent, %semi-transparent):")
    for n, sz, mode, lo, mid in sorted(tex_info.values()):
        flag = "  <-- has alpha" if (lo > 0.01 or mid > 0.01) else ""
        print(f"  {n:28s} {sz[0]}x{sz[1]:<5} {mode:5s} {lo*100:5.1f}% {mid*100:5.1f}%{flag}")
    if fallbacks: print("\nSECTIONS WITH NO MATERIAL ANYWHERE (given the mesh's stone material):", ", ".join(sorted({f"{n}/{sc}" for n, sc in fallbacks})))
    print("\nBARE M_PSXParent PARTS made invisible (still solid):", dict(psx_fixed))
    print("SAME-NAME MATERIAL SWAPS:", dict(same_fixed))
    print("\nUNTEXTURED PARTS  (drawn flat white; mesh, section, material):")
    for (_n, _s, _m), _c in sorted(untex.items()): print(f"  {_n}/{_s}  [{_m}]  x{_c}")
    if not untex: print("  (none)")
    print("\nBRIGHT TEXTURES  (average colour of the opaque pixels after tint, 0-255; above 150 looks white):")
    for _i, _tn in enumerate(tex_names):
        _w, _h, _raw = tex_data[_i]
        _px = [(_raw[k], _raw[k+1], _raw[k+2]) for k in range(0, len(_raw), 4) if _raw[k+3] > 128]
        if _px:
            _mean = sum(sum(p) for p in _px) / (3.0 * len(_px))
            if _mean > 150: print(f"  {_tn:28s} {_mean:5.0f}")
    print("\nTEXTURE USERS  (texture -> meshes drawing it, with instance counts):")
    _users = {}
    for _d, _m in instances:
        for _g, _t in drawables[_d]:
            if _t != 0xFFFF: _users.setdefault(tex_names[_t], collections.Counter())[drawable_mesh[_d]] += 1
    for _tn in sorted(_users): print(f"  {_tn:28s} " + ", ".join(f"{k} x{v}" for k, v in _users[_tn].most_common(4)))
    print("\nMATERIAL REPORT  (tint is LINEAR rgb; blend/twosided from the material json):")
    for n, p in sorted(mat_report.items()):
        if p is None:
            print(f"  {n:30s} (no .json found -> no tint/desat applied)")
            continue
        t = p["tint"]
        ts = f"tint=({t[0]:.2f},{t[1]:.2f},{t[2]:.2f})" if t else "tint=none"
        extra = ("  other=" + str(p["scalars"])) if p["scalars"] else ""
        extra += ("  colors=" + str({k: tuple(round(x, 2) for x in v) for k, v in p["colors"].items()})) if p["colors"] else ""
        print(f"  {n:30s} {ts} desat={p['desat']:.2f} blend={p['blend']} twosided={p['twosided']}{extra}")
    if part_diag:
        print("\nDIAG  (mesh, section -> texture, triangles, UV u-range, v-range):")
        for (n, sec), (t, tr, u0, u1, v0, v1) in sorted(part_diag.items()):
            print(f"  {n}/{sec} -> {t}  tris={tr}  u[{u0:.2f},{u1:.2f}] v[{v0:.2f},{v1:.2f}]")
    if missing_mat:
        print("\nMISSING MATERIAL FILES (no texture applied; export these folders):")
        for n, c in missing_mat.most_common():
            print(f"  {n}  (x{c})")
    if no_tex_mat:
        print("\nMaterials with no texture (flat/untextured):", dict(no_tex_mat))
    if missing_tex:
        print("\nMISSING/UNREADABLE TEXTURES (grey placeholder used):")
        for n, c in missing_tex.most_common():
            print(f"  {n}  (x{c})")

if __name__ == "__main__":
    main()
