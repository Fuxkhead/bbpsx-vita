#!/bin/bash
# builds gehr.bin: Gehrman's model (same skeleton as Gascoigne's) with Gascoigne's hunter animations, the axe and the pistol, from the FModel export in ~/bbpsx-vita/assets
cd ~/bbpsx-vita || exit 1
N=assets/Char/NPCs/Gehrman; G=assets/Char/Bosses/Gascoigne
# SPEAR=0 (default): the Hunter's Axe; SPEAR=1: the Blood Spear, normal handle (HANDLE=1.5 thickens it), unfolded only half way in the game; SPEAR=0: the old Hunter's Axe
# add WARGS="--weaponrotx 0" etc. if the spear sits wrong in his hand
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_hunter*.py | head -1)" assets/tools/convert_hunter.py
S=assets/BP/PlayerWeapons/BloodSpear
B=assets/BP/PlayerWeapons/BurialBlade
# SCYTHE=1: Gehrman's own Burial Blade (a curved sword that opens into a scythe), built by assets/tools/make_scythe.py (SARGS="--open 110 --length 120" etc. reshape it; WARGS="--weaponrotx 0" etc. if it sits wrong in his hand)
if [ "${SCYTHE:-0}" = "1" ]; then
  python3 assets/tools/make_scythe.py --out $B $SARGS || exit 1
  WEAPON_ARGS="--weapon $B/Mesh/SkM_BurialBlade.psk --weaponanim $B/Anim/BurialBlade_open.psa $B/Anim/BurialBlade_closedidle.psa --transformbone transformer --bladebones transformer,transformer_end --damagebones transformer,transformer_end --weaponmap=${GMAP:--x,-z,-y} --weaponoff=${GOFF:-9,-62,0} $WARGS"      # GMAP / GOFF: the same hold as the hunter's Burial Blade (blade forward, edge down, the haft through the palm); GMAP=-z,y,x GOFF=0,0,0 is the old mapping
elif [ "${SPEAR:-0}" = "1" ]; then
  WEAPON_ARGS="--weapon $S/Mesh/SkM_BloodSpear.psk --weaponanim $S/Anim/BloodSpear_open.psa $S/Anim/BloodSpear_closedidle.psa --transformbone transformer --bladebones transformer,transformer_end --damagebones transformer,transformer_end --handlescale ${HANDLE:-1.0} $WARGS"
else
  WEAPON_ARGS="--weapon assets/BP/PlayerWeapons/HunterAxe/Mesh/SkM_Axe.psk --weaponanim assets/BP/PlayerWeapons/HunterAxe/Anim $G/Anim/Axe --transformbone Transformer --bladebones Transformer,Transformer_end,DamageStart,DamageEnd,TransSpark"
fi
python3 assets/tools/convert_hunter.py --psk $N/Mesh/SkM_Gehrman.psk --psa $G/Anim --psaonly AnimGas_ \
  --tex assets/Char/NPCs/Gehrman assets/Char/Hunter assets/Env/Yharnam assets/General assets/BP/PlayerWeapons/HunterPistol/Mat/Tex assets/BP/PlayerWeapons/HunterAxe/Mat assets/BP/PlayerWeapons/BloodSpear/Mat assets/BP/PlayerWeapons/BurialBlade/Mat assets/BP/PlayerWeapons/Torch assets/Char/Enemies/Yharnamites/Mat \
  --texmap MI_Gehrman=t_gehrmanbody,MI_GehrmanHatsAlt=t_gehrmanbody,MI_FaceGehrman=BbPSX_Head128v3Old,MI_HairGas=t_hair,MI_Wood=T_Wood,MI_Torch=T_YhrmtTorch_Source,MI_CloudySky=T_YhrmtTorch_Source,MI_Cleaver=t_bloodspear,MI_BloodSpear=t_bloodspear,MI_BurialBlade=t_burialblade --tint "MI_FaceGehrman=${SKIN:-214,172,146}" \
  $WEAPON_ARGS \
  --pistol assets/BP/PlayerWeapons/HunterPistol/Mesh/SM_Hunter_Pistol.pskx \
  --fps 20 --out gehr.bin | grep -i -E "warn|texture|wrote|tinted|weapon|handle|skip"
ls -l gehr.bin
echo "-> copy gehr.bin to ux0:data/bbpsx/"
