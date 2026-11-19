#!/bin/bash
# Builds the Oedon Chapel (first room of the Cathedral Ward) and puts it on the card.   usage: bash assets/tools/make_oedon.sh
cd ~/bbpsx-vita || exit 1
CARD=/run/media/deck/USD00/Data/bbpsx
mkdir -p assets/Maps/CathedralWard convert_logs
python3 assets/tools/make_oedon.py --out assets/Maps/CathedralWard/MP_OedonChapel.usda --preview convert_logs/chapel_plan.png || exit 1
f=assets/Maps/CathedralWard/MP_OedonChapel.usda
python3 assets/tools/convert_level.py --assets ~/bbpsx-vita/assets --map "${f#assets/}" --out ~/bbpsx-vita/level_oedonchapel.bin --skip SkyBox --skip Cube --skip WindowShaft --skip SM_Card --skip LightShaft 2>&1 | tee convert_logs/oedonchapel.txt | grep -E "^wrote|textures:|floor materials|level loaders|collision triangles|WARNING|lantern|UNTEXTURED|MISSING|Error|Traceback"
ls -l level_oedonchapel.bin interact_oedonchapel.bin floor_oedonchapel.bin 2>/dev/null
cp -v level_oedonchapel.bin interact_oedonchapel.bin floor_oedonchapel.bin $CARD/ 2>/dev/null
# (the link to the arena gate is made by add_arena_gate.sh)
# the dark see-through panel across the stairs, where the map change happens (centre x y z, width, height, turn; metres). Only written if there is none yet, so panels you place with the editor are kept.
[ -f $CARD/panels_oedonchapel.txt ] || echo "22.000 0.000 1.500 7.600 11.000 1.5708" > $CARD/panels_oedonchapel.txt
grep -n oedonchapel $CARD/links.txt
echo "done: also put alllamps.txt on the card to see the chapel's lantern in the travel list (rm it afterwards)"
