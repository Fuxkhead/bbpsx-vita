#!/bin/bash
# builds doll.bin: the Doll (her own model and animations) from ~/bbpsx-vita/assets
cd ~/bbpsx-vita || exit 1
PSK=$(find assets -iname "SkM_Doll.psk*" | head -1)
F=$(find assets -iname "Doll_Idle.psa" | head -1)
PSA=$([ -n "$F" ] && dirname "$F")
echo "body: ${PSK:-NOT FOUND}"; echo "anim folder: ${PSA:-NOT FOUND}"
[ -n "$PSK" ] && [ -n "$PSA" ] || { echo "missing files - run: find assets -iname '*Doll*' | head -30   and paste it to me"; exit 1; }
TM="MI_DollBody=t_doll_body,MI_DollBodyPrev=t_doll_body,MI_DollHead=t_doll_face"
python3 assets/tools/convert_hunter.py --psk "$PSK" --psa "$PSA" --psaonly Doll_Idle,Doll_Kneel,Doll_LevelUp \
  --tex assets/Char/NPCs/Doll --texmap "$TM" --tint none --fps 20 --out doll.bin 2>&1 | grep -E "WARNING|^wrote|bones missing|Error|Traceback" | head -20
ls -l doll.bin
echo "Copy doll.bin to ux0:data/bbpsx/"
