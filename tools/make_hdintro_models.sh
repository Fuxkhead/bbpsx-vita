#!/bin/bash
# Hunter's Dream intro: converts the Hunter's HunterCutscene_HuntersDreamIntro animation (15 fps) into hunter_cine.bin.   usage: bash make_hdintro_models.sh
cd ~/bbpsx-vita || exit 1
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_hanims*.py | head -1)" assets/tools/convert_hanims.py
PSK=$(find assets -name "SkM_AttireHunter.psk" | head -1)
[ -f hunter.bin ] || { echo "hunter.bin not found in ~/bbpsx-vita"; exit 1; }
python3 assets/tools/convert_hanims.py --hunter "$PSK" --hunterbin hunter.bin --psa assets/Cine/HuntersDreamIntro --only HunterCutscene --maxfps 15 --out hunter_cine.bin 2>&1 | grep -E "skin bones|skip|anim |wrote|could not|Error|Traceback"
ls -l hunter_cine.bin
echo "-> copy hunter_cine.bin to ux0:data/bbpsx/"
