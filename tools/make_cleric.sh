#!/bin/bash
# builds clericbeast.bin from the FModel export in ~/bbpsx-vita/assets/Char/Bosses/ClericBeast
cd ~/bbpsx-vita || exit 1
C=assets/Char/Bosses/ClericBeast
python3 assets/tools/convert_hunter.py --psk $C/Mesh/SkM_ClericBeast.psk --psa $C/Anim \
  --psaonly ClericB_,ClericBAtt_,ClericBReact_ \
  --tex $C/Mat --texmap MI_ClericBeast=t_clericbeast --tint none --fps 20 --out clericbeast.bin | tail -4
ls -l clericbeast.bin
