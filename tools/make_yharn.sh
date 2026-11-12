#!/bin/bash
# builds yh_board.bin, yh_shield.bin, yh_torch.bin, yh_gun.bin (the other Yharnamites) from ~/bbpsx-vita/assets/Char/Enemies/Yharnamites
cd ~/bbpsx-vita || exit 1
Y=assets/Char/Enemies/Yharnamites
TORCH=assets/BP/PlayerWeapons/Torch/Mesh/SM_Torch.usda
[ -f "$TORCH" ] || TORCH=$(find assets -iname 'SM_Torch.usda' | head -1)
TORCHTEX=assets/BP/PlayerWeapons/Torch
TORCHMAP=""
find "$TORCHTEX" -name '*.png' 2>/dev/null | grep -q . || TORCHMAP=",MI_Torch=T_YhrmtTorch_Source"      # no torch texture of its own: use the Yharnamite torch texture
WOODPNG=$(find assets -iname '*WoodBroken*.png' | head -1)
[ -n "$WOODPNG" ] || WOODPNG=$(find assets -iname '*wood*.png' | head -1)
if [ -n "$WOODPNG" ]; then WOODDIR=$(dirname "$WOODPNG"); WOODNAME=$(basename "$WOODPNG" .png); else WOODDIR=$Y/Mat; WOODNAME=T_YhrmtTorch_Source; fi
echo "shield wood texture: $WOODNAME ($WOODDIR)"
GUNTEX=assets/BP/PlayerWeapons/DBShotgun/Mat
echo "torch mesh: ${TORCH:-NOT FOUND}   torch textures: $TORCHTEX ${TORCHMAP:+(none, using T_YhrmtTorch_Source)}"
TM="MI_WoodBroken=$WOODNAME,MI_DBShotgunDesat=DBShotgun,MI_DBShotgun=DBShotgun,MI_Wood=T_YhrmtTorch_Source,MI_CloudySky=T_YhrmtTorch_Source,MI_Torch=T_YhrmtTorch_Source,MI_Yhnmt1H=T_Yhrmt1H_Source,MI_Yhnmt1HDark=T_Yhrmt1H_Source,MI_YhnmtHead=T_YhrmtHead_Source,MI_YhnmtTorch=T_YhrmtTorch_Source,MI_YhnmtGun=T_YhrmtGun_Source,MI_Sabre=t_sabre,MI_HandAxe=t_handaxe"
COMMON="--tint none --fps 20"
W="--weaponmap=-z,-y,-x"
mkdir -p convert_logs; : > convert_logs/yharn.txt
conv() { echo "--- ${@: -1}"; python3 assets/tools/convert_hunter.py "$@" 2>&1 | tee -a convert_logs/yharn.txt | grep -E "WARNING|^wrote|bones missing|Error" ; }
# board + sabre (these wear the rifleman's outfit in the maps)
conv --psk $Y/Mesh/SkM_YhnmtBoard.psk --psa $Y/Anim --psaonly YhnmtBoard_,Yhnmt_ --tex $Y/Mat --texmap "$TM,MI_YhnmtBoard=T_YhrmtGun_Source" \
  --weapon $Y/Mesh/SM_Sabre.pskx $W $COMMON --out yh_board.bin
# board + wooden shield (right) + torch (left): turned 90 degrees about the arm from the sabre mapping so it faces front on; if it faces the wrong way round try SHIELDMAP=x,-y,-z ./make_yharn.sh
conv --psk $Y/Mesh/SkM_YhnmtBoard.psk --psa $Y/Anim --psaonly YhnmtBoard_,Yhnmt_ --tex $Y/Mat $TORCHTEX $WOODDIR --texmap "$TM$TORCHMAP,MI_YhnmtBoard=T_YhrmtBoard_Source" \
  --weapon $Y/Mesh/SM_WoodenShield.pskx --weaponmap=${SHIELDMAP:--x,-y,z} ${TORCH:+--pistol $TORCH} $COMMON --out yh_shield.bin
# torch skeleton: torch (right) + hand axe (left)
conv --psk $Y/Mesh/SkM_YhnmtTorch.psk --psa $Y/Anim --psaonly YhnmtTrchAxe_,Yhnmt_ --tex $Y/Mat $TORCHTEX --texmap "$TM$TORCHMAP" \
  ${TORCH:+--weapon $TORCH} $W --pistol $Y/Mesh/SM_HandAxe.pskx $COMMON --out yh_torch.bin
# rifleman
conv --psk $Y/Mesh/SkM_YhnmtGun.psk --psa $Y/Anim --psaonly YhnmtGun_,Yhnmt_ --tex $Y/Mat $GUNTEX --texmap "$TM" \
  --weapon $Y/Mesh/SM_Rifle.pskx $W $COMMON --out yh_gun.bin
ls -l yh_board.bin yh_shield.bin yh_torch.bin yh_gun.bin
