#!/bin/bash
# Adds the Hunter's bare-handed punch animations to hunter_anims.bin (keeps the ones from the earlier steps).
# usage: ./make_fistanims.sh        (rebuilds hunter_anims.bin from: Flamesprayer, GasAxe, BareHanded)
cd ~/bbpsx-vita || exit 1
[ -d assets/BP/PlayerWeapons/BareHanded/Anim ] || { echo "assets/BP/PlayerWeapons/BareHanded/Anim is missing - export it from the pak"; exit 1; }
./make_hanims.sh Flamesprayer GasAxe BareHanded
ls -l hunter_anims.bin
echo "Copy hunter_anims.bin to ux0:data/bbpsx/"
