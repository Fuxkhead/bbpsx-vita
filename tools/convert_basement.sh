#!/bin/bash
# re-converts only the basement (adds the dead werewolf the map places as "Were_Dead_2").   usage: bash convert_basement.sh
cd ~/bbpsx-vita || exit 1
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_level*.py | head -1)" assets/tools/convert_level.py
f=assets/Maps/DerelictEstate/MP_DE_Basement.usda
python3 assets/tools/convert_level.py --assets ~/bbpsx-vita/assets --map "${f#assets/}" --out ~/bbpsx-vita/level_de_basement.bin --skip SkyBox --skip Cube --skip WindowShaft --skip SM_Card --skip LightShaft 2>&1 | grep -E "^wrote|collision triangles|Error|Traceback"
ls -l level_de_basement.bin interact_de_basement.bin floor_de_basement.bin 2>/dev/null
echo "-> copy level_de_basement.bin (and interact_ / floor_) to ux0:data/bbpsx/"
