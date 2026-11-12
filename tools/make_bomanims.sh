#!/bin/bash
# Rebuilds hunter_anims.bin with the Blades of Mercy swing animations (right blade, then left, then right...) ADDED to everything it already had:
# Flamesprayer, GasAxe, BareHanded and (when you have run make_jumpanims.sh) the sprint jumps.
# usage: ./make_bomanims.sh
cd ~/bbpsx-vita || exit 1
[ -d assets/BP/PlayerWeapons/BladesOfMercy/Anim ] || { echo "assets/BP/PlayerWeapons/BladesOfMercy/Anim is missing - export it from the pak"; exit 1; }
[ -f hunter.bin ] || { echo "hunter.bin not found in ~/bbpsx-vita"; exit 1; }
PSK=$(find assets -name "SkM_AttireHunter.psk" | head -1)
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_hanims*.py 2>/dev/null | head -1)" assets/tools/convert_hanims.py 2>/dev/null
ARGS=""; for f in Flamesprayer GasAxe BareHanded BladesOfMercy; do [ -d assets/BP/PlayerWeapons/$f/Anim ] && ARGS="$ARGS assets/BP/PlayerWeapons/$f/Anim"; done
[ -d assets/_jump ] && [ -n "$(ls assets/_jump 2>/dev/null)" ] && ARGS="$ARGS assets/_jump"
echo "folders:$ARGS"
mkdir -p convert_logs
python3 assets/tools/convert_hanims.py --hunter "$PSK" --hunterbin hunter.bin --psa $ARGS --out hunter_anims.bin 2>&1 | tee convert_logs/hanims.txt | grep -E "skin bones|skip|BoM|Jump|wrote|could not|Error|Traceback"
ls -l hunter_anims.bin
echo "Copy hunter_anims.bin to ux0:data/bbpsx/"
