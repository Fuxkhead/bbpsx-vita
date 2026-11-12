#!/usr/bin/env python3
# extract_notes.py: the messenger notes of every map -> notes_<map>.txt ("x y|text" per line, metres) for ux0:data/bbpsx/
# reads the FModel JSON of each map (BP_NoteMessenger* actors carry a DisplayText) and the map's .usda for where each one stands
import os, re, sys, json, glob
root = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/bbpsx-vita/assets")
outdir = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/bbpsx-vita")
conv = ""
for c in ("~/bbpsx-vita/convert_all_maps.sh", "~/bbpsx-vita/assets/tools/convert_all_maps.sh"):
    if os.path.isfile(os.path.expanduser(c)): conv = open(os.path.expanduser(c), errors="replace").read(); break
BTN = {"PSL1": "L1", "PSR1": "R1", "PSL2": "L2", "PSR2": "R2", "PSSquare": "SQUARE", "PSCross": "X", "PSCircle": "O", "PSTriangle": "TRIANGLE", "PSStart": "START",
       "PSDPad": "D-PAD", "PSDPadU": "D-PAD UP", "PSDPadD": "D-PAD DOWN", "PSDPadL": "D-PAD LEFT", "PSDPadR": "D-PAD RIGHT", "PSLStick": "LEFT STICK", "PSRStick": "RIGHT STICK"}
def clean(t):
    t = re.sub(r'<img id=\\?"(\w+)\\?"></>', lambda m: "{" + BTN.get(m.group(1), m.group(1)) + "}", t)
    t = re.sub(r"</?\w*>", "", t).replace("\r", " ").replace("\n", " ").replace("|", "/")
    return re.sub(r"\s+", " ", t).strip()
total = 0
for jp in sorted(glob.glob(os.path.join(root, "**", "MP_*.json"), recursive=True)):
    try: data = json.load(open(jp, encoding="utf-8", errors="replace"))
    except Exception: continue
    if isinstance(data, dict): data = [data]
    notes = {}
    for ex in data:
        nm = ex.get("Name", "") if isinstance(ex, dict) else ""
        if not nm.startswith("BP_NoteMessenger"): continue
        dt = (ex.get("Properties") or {}).get("DisplayText")
        if isinstance(dt, dict): notes[nm] = clean(dt.get("SourceString") or dt.get("LocalizedString") or "")
    if not notes: continue
    stem = os.path.splitext(os.path.basename(jp))[0]
    up = os.path.join(os.path.dirname(jp), stem + ".usda")
    if not os.path.isfile(up): print(f"{stem}: {len(notes)} notes but no {stem}.usda next to the json"); continue
    mt = open(up, errors="replace").read()
    m = re.search(re.escape(stem) + r'\.usda[^\n]*?(level_\w+)\.bin', conv) or re.search(r'(level_\w+)\.bin[^\n]*?' + re.escape(stem), conv)
    mapname = m.group(1)[6:] if m else stem[3:].lower()
    lines = []
    for nm, txt in notes.items():
        b = re.search(r'\n    def Scope "' + re.escape(nm) + r'"\s*\{(.*?)(?=\n    def Scope |\Z)', mt, re.S)
        t = b and re.search(r'xformOp:translate\s*=\s*\(([^)]*)\)', b.group(1))
        if not (b and t and txt): print(f"  {nm}: skipped (no position or no text)"); continue
        v = [float(x) * 0.01 for x in t.group(1).split(",")]
        lines.append(f"{v[0]:.2f} {v[1]:.2f}|{txt}")
    op = os.path.join(outdir, f"notes_{mapname}.txt")
    open(op, "w", encoding="utf-8").write("\n".join(lines) + "\n"); total += len(lines)
    print(f"{stem} -> notes_{mapname}.txt: {len(lines)} notes")
    for l in lines[:3]: print("   ", l[:110])
print(f"{total} notes in all")
