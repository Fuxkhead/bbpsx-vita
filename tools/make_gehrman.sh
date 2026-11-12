#!/bin/bash
# builds gehrman.bin: Gehrman (his own model + his wheelchair, idle and death animations) from ~/bbpsx-vita/assets
cd ~/bbpsx-vita || exit 1
PSK=$(find assets -iname "SkM_Gehrman.psk*" | head -1)
CHAIR=$(find assets -iname "SM_WheelchairGehr.psk*" | head -1)
F=$(find assets -iname "AnimGehr_Idle.psa" | head -1)
PSA=$([ -n "$F" ] && dirname "$F")
echo "body: ${PSK:-NOT FOUND}"; echo "chair: ${CHAIR:-NOT FOUND}"; echo "anim folder: ${PSA:-NOT FOUND}"
[ -n "$PSK" ] && [ -n "$PSA" ] || { echo "missing files - run: find assets -iname '*Gehr*' | head -30   and paste it to me"; exit 1; }
# face = the Hunter's aged head texture, hair = t_hair, chair = t_carriage (found in the materials)
CUP=${CUP:-40}      # how many cm the chair is lifted under him: CUP=60 ./make_gehrman.sh for more, CUP=20 for less
TM="MI_Gehrman=t_gehrmanbody,MI_GehrmanHatsAlt=t_gehrmanbody,MI_FaceGehrman=BbPSX_Head128v3Old,MI_HairGas=t_hair,MI_Wood=T_Wood,MI_Carriage=t_carriage"
python3 assets/tools/convert_hunter.py --psk "$PSK" $CHAIR --psa "$PSA" --psaonly AnimGehr_Idle,AnimGher_Death \
  --tex assets/Char/NPCs/Gehrman assets/Char/Hunter assets/Env/Yharnam assets/General --texmap "$TM" ${CUP:+--shift "Wheelchair=0,0,$CUP"} --tint none --fps 20 --out gehrman.bin 2>&1 | grep -E "WARNING|^wrote|bones missing|Error|Traceback|points" | head -20
ls -l gehrman.bin
echo "Copy gehrman.bin to ux0:data/bbpsx/"
