#!/bin/bash
# Converts every weapon's charge / heavy / slam animations of the Hunter into hunter_anims2.bin (the game loads it next to hunter_anims.bin).
cd ~/bbpsx-vita || exit 1
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_hanims*.py | head -1)" assets/tools/convert_hanims.py
PSK=$(find assets -name "SkM_AttireHunter.psk" | head -1)
[ -f hunter.bin ] || { echo "hunter.bin not found in ~/bbpsx-vita"; exit 1; }
ARGS=""
for f in Cleaver HunterAxe BloodSpear BladesOfMercy ThreadedCane Tonitrus BareHanded; do
  if [ -d "assets/BP/PlayerWeapons/$f/Anim" ]; then ARGS="$ARGS assets/BP/PlayerWeapons/$f/Anim"; else echo "missing folder: assets/BP/PlayerWeapons/$f/Anim"; fi
done
mkdir -p convert_logs
python3 assets/tools/convert_hanims.py --hunter "$PSK" --hunterbin hunter.bin --psa $ARGS --only charge,heavy,slam --layers hunter_layers.txt --out hunter_anims2.bin 2>&1 | tee convert_logs/hanims2.txt | grep -E "skin bones|skip|anim |wrote|could not|Error|Traceback"
ls -l hunter_anims2.bin hunter_layers.txt
echo "Copy hunter_anims2.bin AND hunter_layers.txt to ux0:data/bbpsx/"
