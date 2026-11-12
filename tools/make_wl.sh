#!/bin/bash
# builds wl.bin (WL, the frenzy-beam boss) from the FModel export in ~/bbpsx-vita/assets/Char/Bosses/WL
cd ~/bbpsx-vita || exit 1
C=assets/Char/Bosses/WL
PSK=$(find $C -iname "SkM_WL.psk*" | head -1)
echo "model: ${PSK:-NOT FOUND}"; ls $C/Anim | grep -c "^AnimWL_" | sed 's/^/AnimWL_ files: /'
[ -n "$PSK" ] || { echo "SkM_WL.psk not found - paste the output of: find ~/bbpsx-vita/assets -iname 'SkM_WL*'"; exit 1; }
python3 assets/tools/convert_hunter.py --psk "$PSK" --psa $C/Anim \
  --psaonly AnimWL_ \
  --tex $C/Mat --texmap MI_wl_body=t_wl_body,MI_brain=t_brain1 --tint none --fps 20 --out wl.bin 2>&1 | grep -E "WARNING|^wrote|bones missing|Error|Traceback|material|anims|tex" | head -20
ls -l wl.bin
echo "Copy wl.bin to ux0:data/bbpsx/"
