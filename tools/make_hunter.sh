#!/bin/bash
# Rebuilds hunter.bin (the player: body, face, hair, cleaver, pistol + the base animations). Run from ~/bbpsx-vita.
# RECONSTRUCTED from the finished file (7 textures: body, head, BbPSX_Head128v3 face, hair, cleaver, pistol; 4 attach bones; 101 anims),
# not from the author's original command, which was not saved. Defaults of convert_hunter.py cover face tint, texmap, root motion.
# If something looks off in game (weapon angle, pistol position) tune --weaponoff/--weaponroty/--pistoloff/--pistolrot (see --help).
cd ~/bbpsx-vita || exit 1; mkdir -p convert_logs
H=assets/Char/Hunter
TEXDIRS=("$H/Mat/Tex")
for n in t_sawcleaver.png T_Pistol.png BbPSX_Head128v3.png t_hair.png; do
  f=$(find assets -iname "$n" -not -path "*NMKART*" 2>/dev/null | head -1)
  [ -n "$f" ] && TEXDIRS+=("$(dirname "$f")") || echo "note: $n not found under assets/ (put it in a folder and add it to TEXDIRS)"
done
TEXDIRS=($(printf '%s\n' "${TEXDIRS[@]}" | awk '!s[$0]++'))
python3 assets/tools/convert_hunter.py \
  --psk "$H/Mesh/SkM_AttireHunter.psk" "$H/Mesh/SkM_Hunterface0.psk" "$H/Mesh/SkM_HunterHair0.psk" \
  --psa "$H/Anim" \
  --tex "${TEXDIRS[@]}" \
  --weapon assets/BP/PlayerWeapons/Cleaver/Mesh/SkM_Cleaver.psk \
  --pistol assets/BP/PlayerWeapons/HunterPistol/Mesh/SM_Hunter_Pistol.pskx \
  --out hunter.bin 2>&1 | tee convert_logs/hunter.txt
ls -l hunter.bin
echo "Compare: python3 assets/tools/inspect_bin.py hunter.bin  (expect 7 textures, 4 attach, ~101 anims, ~1246 verts)"
