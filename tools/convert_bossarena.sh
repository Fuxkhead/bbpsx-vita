#!/bin/bash
# re-converts only Gilbert's cabin (his bed becomes a movable mesh that rides with him).   usage: bash convert_bossarena.sh
cd ~/bbpsx-vita || exit 1
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_level*.py | head -1)" assets/tools/convert_level.py
f=$(find assets/Maps -iname 'MP_GE_BossArena.usda' | head -1)
python3 assets/tools/convert_level.py --assets ~/bbpsx-vita/assets --map "${f#assets/}" --out ~/bbpsx-vita/level_ge_bossarena.bin --skip SkyBox --skip Cube --skip WindowShaft --skip SM_Card --skip LightShaft 2>&1 | grep -E "^wrote|collision triangles|Error|Traceback"
ls -l level_ge_bossarena.bin interact_ge_bossarena.bin floor_ge_bossarena.bin 2>/dev/null
echo "-> copy level_ge_bossarena.bin (and interact_ / floor_ if listed) to ux0:data/bbpsx/"
