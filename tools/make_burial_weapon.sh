#!/bin/bash
# make_burial_weapon.sh: builds the Burial Blade and puts it into weapons.bin in the Blood Spear's slot (the save file has fixed weapon slots), then copies weapons.bin to the card.
#   cp ~/Downloads/make_scythe_v3.py ~/bbpsx-vita/assets/tools/make_scythe.py; cp ~/Downloads/convert_weapons.py ~/bbpsx-vita/assets/tools/convert_weapons.py; cp ~/Downloads/make_burial_weapon.sh ~/bbpsx-vita/assets/tools/; bash ~/bbpsx-vita/assets/tools/make_burial_weapon.sh
# without --burial the usual weapons.bin comes out again (the Blood Spear is back).
cd ~/bbpsx-vita || exit 1
python3 assets/tools/make_scythe.py --out assets/BP/PlayerWeapons/BurialBlade $SARGS || exit 1
# how the hand holds it: BROT = rotation about the hand axes (deg), BOFF = slide in the hand frame (cm).
# default: handle out in front (0,0,90 / 0,-62,0) and then the weapon rolled 90 degrees about its own length (90,0,90) so the edge faces down; if the edge faces UP instead, run with BROT=-90,0,90
bash assets/tools/make_weapons.sh --burial --rot burial=${BROT:-90,0,90} --off burial=${BOFF:-9,-62,0} $WARGS
cp -v weapons.bin /run/media/deck/USD00/Data/bbpsx/weapons.bin
touch /run/media/deck/USD00/Data/bbpsx/burial.txt
echo "done: the Burial Blade is now a weapon of its own (burial.txt on the card puts it in the shop for 100 echoes, the Blood Spear stays)"
