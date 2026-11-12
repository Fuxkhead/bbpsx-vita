#!/bin/bash
# re-converts only the Cleric Beast's arena (its carriages become boss-only breakables).   usage: bash ~/Downloads/convert_cleric.sh
cd ~/bbpsx-vita || exit 1
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_level*.py | head -1)" assets/tools/convert_level.py
f=$(find assets/Maps -iname 'MP_*ClericBeast*.usda' | head -1)
[ -n "$f" ] || { echo "map not found - paste me: find ~/bbpsx-vita/assets/Maps -iname '*cleric*'"; exit 1; }
n=$(basename "$f" .usda | tr 'A-Z' 'a-z'); n=${n#mp_}; n=${n#cy_}; n=${n#ys_}
echo "map: $f -> level_$n.bin"
python3 assets/tools/convert_level.py --assets ~/bbpsx-vita/assets --map "${f#assets/}" --out ~/bbpsx-vita/level_$n.bin --skip SkyBox --skip Cube --skip WindowShaft --skip SM_Card --skip LightShaft 2>&1 | grep -E "^wrote|collision triangles|destructible|NOT made breakable|^    " | head -30
ls -l level_$n.bin interact_$n.bin floor_$n.bin breakables_$n.txt 2>/dev/null
echo "-> copy those files to ux0:data/bbpsx/"
