#!/bin/bash
# builds eileen.bin: Eileen the Crow (Crowfeather outfit + hat on the Hunter skeleton): her arms-crossed idle, plus the Hunter's own moves and a blade for the arena fight
# tune the blade in her hand with:  EROT=0,0,90 EOFF=0,0,0 ./make_eileen.sh     (rotation in degrees about the blade's x,y,z; offset in cm)
cd ~/bbpsx-vita || exit 1
PSK=$(find assets -name "SkM_AttireCrowfeather.psk" | head -1)
HAT=$(find assets -iname "SM_HatCrowfeather.psk*" | head -1)
[ -n "$NOHAT" ] && HAT=""      # NOHAT=1 ./make_eileen.sh builds her without the hat
PSA=$(dirname "$(find assets -iname 'EileenAnim_IdleArmsCrossed.psa' | head -1)")
BLADE=""      # her blades are the Blades of Mercy now: the game adds them from weapons.bin (build that first). KEEPCLEAVER=1 ./make_eileen.sh puts the old cleaver back
[ -n "$KEEPCLEAVER" ] && BLADE=$(find assets/BP/PlayerWeapons -iname '*Cleaver*' \( -name '*.psk' -o -name '*.pskx' \) 2>/dev/null | head -1)
PSAS="$PSA $(find assets/Char/Hunter/Anim assets/BP/PlayerWeapons -type d 2>/dev/null | tr '\n' ' ')"
echo "body: ${PSK:-NOT FOUND}"; echo "hat: ${HAT:-NOT FOUND}"; echo "anim: $PSA"; echo "blade: ${BLADE:-none here (the Blades of Mercy come from weapons.bin in the game)}"
[ -n "$PSK" ] && [ -f "$PSA/EileenAnim_IdleArmsCrossed.psa" ] || { echo "missing files - paste these lines to me"; exit 1; }
TEXD="assets/Cine assets/Char/Hunter ${BLADE:+$(dirname "$(dirname "$BLADE")")}"
TM="MI_CrowfeatherBody=t_crowfeatherbody,MI_CrowfeatherHat=t_crowfeatherhead,MI_HunterHead=T_HunterHead,MI_HunterHeadPrev=T_HunterHead,MI_Bandage=t_hair,MI_HunterBody=t_crowfeatherbody"
python3 assets/tools/convert_hunter.py --psk "$PSK" --psa $PSAS \
  --psaonly EileenAnim_,Hunter_Idle,Hunter_Run,Hunter_Walk,HunterDeath,HunterCleav_Attack,HunterBoM_R-L,HunterBoM_L-R,Small,Quickstep,HunterDodge_Roll \
  --tex $TEXD --texmap "$TM" --tint none ${HAT:+--hat "$HAT"} \
  ${BLADE:+--pistol "$BLADE" --pistolbone hand_r --pistolrot ${EROT:-0,0,0} ${EOFF:+--pistoloff $EOFF}} \
  --fps 20 --out eileen.bin 2>&1 | grep -E "WARNING|^wrote|bones missing|Error|Traceback|material" | head -20
ls -l eileen.bin
echo "Copy eileen.bin to ux0:data/bbpsx/"
