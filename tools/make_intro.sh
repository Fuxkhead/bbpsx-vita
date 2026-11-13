#!/bin/bash
# the opening cutscene (Seq_GameIntroP1): builds granter.bin (the Contract Granter + his animation), gi_chair.bin (the wheelchair, moved by the camera rig) and snd/mus_gi1.wav (the whole sound track mixed).
#   usage: ./make_intro.sh        then copy granter.bin, gi_chair.bin and snd/mus_gi1.wav to ux0:data/bbpsx/ (and snd/)
cd ~/bbpsx-vita || exit 1
A=assets
G=$A/Cine/GameIntro
PSK=$(find $A -iname "SkM_ContractGranter.psk" | head -1)
CAMPSK=$(find $A -iname "SkM_CutsceneCameraRig.psk" | head -1)
WHEEL=$(find $A -ipath "*Clinic*" -iname "SM_Wheelchair.pskx" | head -1)
[ -n "$PSK" ] && [ -n "$CAMPSK" ] && [ -n "$WHEEL" ] || { echo "missing: granter ${PSK:-NO} / camera rig ${CAMPSK:-NO} / wheelchair ${WHEEL:-NO}"; exit 1; }
TEXD="$G/Mat $A/Char/Hunter/Mat/Tex"
for t in BbPSX_Head128v3Old t_hair t_carriage; do d=$(find $A -iname "$t.png" | head -1 | xargs -r dirname); [ -n "$d" ] && TEXD="$TEXD $d"; done
FACE=BbPSX_Head128v3Old; [ -n "$(find $A -iname "$FACE.png" | head -1)" ] || FACE=BbPSX_Head128v3OldMouthOpen
echo "granter: $PSK   face texture: $FACE"
python3 $A/tools/convert_hunter.py --psk "$PSK" --psa $G/Anim --psaonly AnimContractGranter_IntroP1 --tex $TEXD \
  --texmap "MI_ContractGranter=t_contractgiver,MI_ContractGranterAlt=t_contractgiver,MI_FaceContractGranter=$FACE,MI_HairContractGranter=t_hair,MI_BandageContractGranter=t_hair" \
  --tint none --fps 15 --maxtex 128 --out granter.bin 2>&1 | grep -E "WARNING|^wrote|Error|Traceback|anim"
python3 $A/tools/convert_hunter.py --psk "$CAMPSK" --psa $G/Anim --psaonly CutsceneCamRigAnim_IntroP1 --pistol "$WHEEL" --pistolbone prop1 --pistolframe socket --pistolsocket prop1 --pistoloff 0,0,0 \
  --tex $TEXD --texmap "MI_Carriage=t_carriage" --tint none --fps 15 --maxtex 128 --out gi_chair.bin 2>&1 | grep -E "WARNING|^wrote|Error|Traceback|anim"
mkdir -p snd
python3 $A/tools/make_intro_audio.py --assets $A --out snd --part 1
ls -l granter.bin gi_chair.bin snd/mus_gi1.wav
echo "Copy granter.bin and gi_chair.bin to ux0:data/bbpsx/ and snd/mus_gi1.wav to ux0:data/bbpsx/snd/ . The cutscene plays on a new hunter and on new game plus; ux0:data/bbpsx/intro_test.txt plays it at every start, nointro.txt turns it off. START / X / O skips it."
