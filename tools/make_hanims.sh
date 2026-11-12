#!/bin/bash
# Converts the weapons' own Hunter animations (shooting / attacks) into hunter_anims.bin.   usage: ./make_hanims.sh [WeaponFolder ...]   (default: Flamesprayer)
# e.g.  ./make_hanims.sh Flamesprayer Blunderbuss DBShotgun
cd ~/bbpsx-vita || exit 1
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_hanims*.py | head -1)" assets/tools/convert_hanims.py
PSK=$(find assets -name "SkM_AttireHunter.psk" | head -1)
[ -f hunter.bin ] || { echo "hunter.bin not found in ~/bbpsx-vita"; exit 1; }
FOLDERS=${@:-Flamesprayer}
ARGS=""; for f in $FOLDERS; do ARGS="$ARGS assets/BP/PlayerWeapons/$f/Anim"; done
mkdir -p convert_logs
python3 assets/tools/convert_hanims.py --hunter "$PSK" --hunterbin hunter.bin --psa $ARGS --out hunter_anims.bin 2>&1 | tee convert_logs/hanims.txt | grep -E "skin bones|skip|anim |wrote|could not|Error|Traceback"
