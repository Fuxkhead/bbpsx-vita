#!/bin/bash
# builds switch.bin: the lever model (SkM_Switch) with its idle and pull animations, from ~/bbpsx-vita/assets
# needs  BP/General/FlippableSwitch  exported from the pak with FModel: SkM_Switch (psk), Switch_Idle + Switch_SwitchPull (psa), t_switch (png)
cd ~/bbpsx-vita || exit 1
PSK=$(find assets -iname "SkM_Switch.psk*" | head -1)
F=$(find assets -iname "Switch_Idle.psa" | head -1)
PSA=$([ -n "$F" ] && dirname "$F")
TEXD=$(dirname "$(find assets -iname "t_switch.png" | head -1)" 2>/dev/null)
echo "body: ${PSK:-NOT FOUND}"; echo "anim folder: ${PSA:-NOT FOUND}"; echo "texture folder: ${TEXD:-NOT FOUND}"
[ -n "$PSK" ] && [ -n "$PSA" ] || { echo "missing files: export  BP/General/FlippableSwitch  from the pak with FModel (mesh as psk, animations as psa, textures as png), then run this again"; echo "(find assets -iname '*Switch*' | head -30  shows what you have)"; exit 1; }
python3 assets/tools/convert_hunter.py --psk "$PSK" --psa "$PSA" --psaonly Switch_ \
  --tex "${TEXD:-assets}" --texmap "MI_Switch=t_switch" --tint none --rootmotion keep --fps 20 --out switch.bin 2>&1 | grep -E "WARNING|^wrote|bones missing|Error|Traceback|skip|anim|texture" | head -20
ls -l switch.bin
echo "Copy switch.bin and the levers_*.txt files to ux0:data/bbpsx/"
