#!/bin/bash
# re-converts only the clinic sickroom (so its wheelchairs can be lowered in the game).   usage: bash convert_sickroom.sh
cd ~/bbpsx-vita || exit 1
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_level*.py | head -1)" assets/tools/convert_level.py
f=$(find assets/Maps -iname 'MP_IC_FirstFloorSickroom.usda' | head -1)
[ -n "$f" ] || { echo "MP_IC_FirstFloorSickroom.usda not found in assets/Maps"; exit 1; }
python3 assets/tools/convert_level.py --assets ~/bbpsx-vita/assets --map "${f#assets/}" --out ~/bbpsx-vita/level_ic_firstfloorsickroom.bin --skip SkyBox --skip Cube --skip WindowShaft --skip SM_Card --skip LightShaft 2>&1 | grep -E "^wrote|collision triangles|Error|Traceback" 
ls -l level_ic_firstfloorsickroom.bin interact_ic_firstfloorsickroom.bin floor_ic_firstfloorsickroom.bin 2>/dev/null
echo "-> copy level_ic_firstfloorsickroom.bin (and interact_ / floor_ if listed) to ux0:data/bbpsx/"
