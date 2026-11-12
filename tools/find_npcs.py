#!/usr/bin/env python3
"""find_npcs.py [assets_dir]  - lists every NPC placement in every map: map, scope name, x y z (metres), yaw (degrees)"""
import os, re, sys, math
root = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/bbpsx-vita/assets")
pat = re.compile(r'def Scope "(BP_Eileen\w*|BP_Doll\w*|BPC_Gehrman\w*|BP_Gehrman\w*|BP_Henryk\w*|BPC_Henryk\w*|BP_\w*Messenger\w*|BP_\w*NPC\w*|BPC_\w*NPC\w*|BP_Girl\w*|BP_Gilb\w*|BPC_Gilb\w*|BPC_WL\w*|BP_Store\w*|BP_WeaponWorkshop\w*)"\s*\{.*?xformOp:translate\s*=\s*\(([^)]*)\)(?:.*?xformOp:orient\s*=\s*\(([^)]*)\))?', re.S)
for d, _, fs in os.walk(root):
    for f in sorted(fs):
        if not (f.startswith("MP_") and f.endswith(".usda")): continue
        t = open(os.path.join(d, f), encoding="utf-8", errors="replace").read()
        for m in pat.finditer(t):
            v = [float(x) / 100 for x in m.group(2).split(",")]
            yaw = ""
            if m.group(3):
                w, x, y, z = [float(q) for q in m.group(3).split(",")]
                yaw = "%.0f" % math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))
            print("%-26s %-34s %7.1f %7.1f %7.1f  yaw %s" % (f[3:-5], m.group(1), v[0], v[1], v[2], yaw))
