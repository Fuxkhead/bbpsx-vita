#!/usr/bin/env python3
"""Builds links.txt from the FModel map JSONs (assets/Maps/**/MP_*.json).
Each BP_LevelLoader* has EntranceID (its own id), LevelToLoad and EntranceIDtoLoad; the destination is the loader in the target map whose EntranceID matches.
usage: python3 make_links.py ~/bbpsx-vita/assets/Maps ~/bbpsx-vita/links.txt"""
import json, os, sys, glob
def short(m):
    n = m.lower()
    if n.startswith("mp_"): n = n[3:]
    for p in ("cy_", "ys_"):
        if n.startswith(p): n = n[len(p):]
    return n
def walk(o, out):
    if isinstance(o, dict):
        if str(o.get("Name", "")).startswith("BP_LevelLoader") and isinstance(o.get("Properties"), dict) and "LevelToLoad" in o["Properties"]:
            out.append(o)
        for v in o.values(): walk(v, out)
    elif isinstance(o, list):
        for v in o: walk(v, out)
def val(v):
    if isinstance(v, dict): v = v.get("AssetPathName") or v.get("ObjectName") or v.get("Name") or ""
    v = str(v)
    return v.split("/")[-1].split(".")[-1].split("'")[0]
root, outp = sys.argv[1], sys.argv[2]
DEV = {"arena", "test", "template", "testrooma", "testroomb", "coreytestroom", "mainmenu", "ps1intro"}      # unused test maps: never linked
L = {}                                     # map -> {loadername: (eid, target map, eid to load)}
for f in sorted(glob.glob(os.path.join(root, "**", "MP_*.json"), recursive=True)):
    try: data = json.load(open(f, encoding="utf-8"))
    except Exception as e: print("skip", f, e); continue
    found = []; walk(data, found)
    m = short(os.path.basename(f)[:-5]); d = {}
    for o in found:
        p = o["Properties"]; d[o["Name"]] = (str(p.get("EntranceID", "A")), short(val(p["LevelToLoad"])) if val(p["LevelToLoad"]) else "", str(p.get("EntranceIDtoLoad", "A")))
    L[m] = d
print("maps read:", len(L), " loaders:", sum(len(d) for d in L.values()))
lines = ["start = junction"]; seen = set(); unres = []
used = {}
for m, d in sorted(L.items()):
    if m in DEV: continue
    for ln, (eid, tm, tid) in sorted(d.items()):
        if not tm or tm in DEV: continue
        if tm not in L: unres.append(f"{m}:{ln} -> {tm}:{tid}  (no JSON for target map)"); continue
        cand = [n for n, v in L[tm].items() if v[0] == tid]
        if not cand: unres.append(f"{m}:{ln} -> {tm}:{tid}  (no loader with that EntranceID)"); continue
        if len(cand) > 1: unres.append(f"{m}:{ln} -> {tm}:{tid}  (ambiguous: {', '.join(cand)}; using {cand[0]})")
        key = frozenset([(m, ln), (tm, cand[0])])
        if key in seen: continue
        seen.add(key); lines.append(f"{m}:{ln} = {tm}:{cand[0]}")
        for e in ((m, ln), (tm, cand[0])):
            used.setdefault(e, []).append(f"{m}:{ln} = {tm}:{cand[0]}")
open(outp, "w").write("\n".join(lines) + "\n")
print("links written:", len(lines) - 1, "->", outp)
for e, v in used.items():
    if len(v) > 1: unres.append(f"{e[0]}:{e[1]} is in {len(v)} links: " + " | ".join(v))
if unres: print("\nneeds a look:"); print("\n".join(unres))
