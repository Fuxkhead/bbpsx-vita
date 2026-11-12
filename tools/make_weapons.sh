#!/bin/bash
# builds weapons.bin (all the equippable weapon models) from ~/bbpsx-vita/assets/BP/PlayerWeapons - copy it to ux0:data/bbpsx/
cd ~/bbpsx-vita || exit 1
H=$(find assets -iname 'SkM_AttireHunter.psk' | head -1)
[ -n "$H" ] || { echo "couldn't find SkM_AttireHunter.psk under assets/ - tell me where it is"; exit 1; }
mkdir -p convert_logs
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp -v "$(ls -t ~/Downloads/convert_weapons*.py | head -1)" assets/tools/convert_weapons.py || exit 1
echo "hunter skeleton: $H"
# the torch has no texture of its own: the Yharnamite torch texture is searched too
python3 assets/tools/convert_weapons.py --hunter "$H" --root assets/BP/PlayerWeapons --tex assets/Char/Enemies/Yharnamites/Mat "$@" --out weapons.bin 2>&1 | tee convert_logs/weapons.txt | grep -v "^  texture"
ls -l weapons.bin
echo "Copy weapons.bin to ux0:data/bbpsx/"
