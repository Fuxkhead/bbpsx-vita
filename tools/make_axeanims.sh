#!/bin/bash
# Adds Gascoigne's two-handed axe animations (idle, run, transform, swings, spin) to hunter_anims.bin so the Hunter's Axe can use them.
# usage: ./make_axeanims.sh [other weapon folders already in your hunter_anims.bin, default: Flamesprayer]
cd ~/bbpsx-vita || exit 1
G=assets/Char/Bosses/Gascoigne/Anim
D=assets/BP/PlayerWeapons/GasAxe/Anim
mkdir -p "$D"
for n in Idle2H Run2H 2HTransform 2HSwingHori1 2HHeavyHori 2HStab1 2HSpinAttack 2H3HitCombo; do
  f="$G/AnimGas_$n.psa"; if [ -f "$f" ]; then cp -v "$f" "$D/"; else echo "missing: $f"; fi
done
./make_hanims.sh ${@:-Flamesprayer} GasAxe
ls -l hunter_anims.bin
echo "Copy hunter_anims.bin to ux0:data/bbpsx/"
