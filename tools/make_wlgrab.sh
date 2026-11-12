#!/bin/bash
# Converts the hunter's own WL-grab animations (Hunter_WLGrabbed*) into hunter_anims3.bin
cd ~/bbpsx-vita || exit 1
PSK=$(find assets -name "SkM_AttireHunter.psk" | head -1)
[ -f hunter.bin ] || { echo "hunter.bin not found in ~/bbpsx-vita"; exit 1; }
D=assets/BP/PlayerWeapons/WLGrab/Anim; mkdir -p "$D"
for n in Start Loop Death; do f=$(find assets/Char/Bosses/WL/Anim -name "Hunter_WLGrabbed$n.psa" | head -1); [ -f "$f" ] && cp -v "$f" "$D/" || echo "missing: Hunter_WLGrabbed$n.psa"; done
python3 assets/tools/convert_hanims.py --hunter "$PSK" --hunterbin hunter.bin --psa "$D" --out hunter_anims3.bin 2>&1 | tee convert_logs/hanims3.txt | grep -E "skin bones|skip|anim |wrote|could not|Error|Traceback"
ls -l hunter_anims3.bin
echo "Copy hunter_anims3.bin to ux0:data/bbpsx/"
