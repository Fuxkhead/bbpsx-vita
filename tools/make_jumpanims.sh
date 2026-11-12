#!/bin/bash
# Adds the Hunter's own sprint-jump animations (Hunter_SprintJumpStart / End) to hunter_anims.bin, keeping the earlier ones (Flamesprayer, GasAxe, BareHanded).
# usage: ./make_jumpanims.sh
cd ~/bbpsx-vita || exit 1
PSK=$(find assets -name "SkM_AttireHunter.psk" | head -1)
[ -f hunter.bin ] || { echo "hunter.bin not found in ~/bbpsx-vita"; exit 1; }
rm -rf assets/_jump; mkdir -p assets/_jump
find assets -iname "Hunter_SprintJump*.psa" -exec cp {} assets/_jump/ \;
ls assets/_jump
[ -n "$(ls assets/_jump)" ] || { echo "no Hunter_SprintJumpStart/End .psa found: export  Char/Hunter/Anim/Dodge  from the pak with FModel (psa), then run this again"; echo "(find assets -iname '*SprintJump*'  shows what you have)"; exit 1; }
ARGS=""; for f in Flamesprayer GasAxe BareHanded; do [ -d assets/BP/PlayerWeapons/$f/Anim ] && ARGS="$ARGS assets/BP/PlayerWeapons/$f/Anim"; done
mkdir -p convert_logs
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_hanims*.py 2>/dev/null | head -1)" assets/tools/convert_hanims.py 2>/dev/null
python3 assets/tools/convert_hanims.py --hunter "$PSK" --hunterbin hunter.bin --psa $ARGS assets/_jump --out hunter_anims.bin 2>&1 | tee convert_logs/jump.txt | grep -E "skin bones|skip|Jump|wrote|could not|Error|Traceback"
ls -l hunter_anims.bin
echo "Copy hunter_anims.bin to ux0:data/bbpsx/"
