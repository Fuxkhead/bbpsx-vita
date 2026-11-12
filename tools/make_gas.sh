#!/bin/bash
# builds gas.bin (human Gascoigne) and gasbeast.bin from the FModel export in ~/bbpsx-vita/assets
cd ~/bbpsx-vita || exit 1
G=assets/Char/Bosses/Gascoigne
TM="MI_GasBody=t_gas,MI_FaceGas1=BbPSX_Head128vGAS1,MI_HairGas=t_hair,MI_Bandage=t_hair,MI_GasBeast=t_gasbeast"
python3 assets/tools/convert_hunter.py --psk $G/Mesh/SkM_Gas.psk --psa $G/Anim --psaonly AnimGas_ \
  --tex $G/Mat assets/Char/Hunter/Mat/Tex assets/BP/PlayerWeapons/HunterPistol/Mat/Tex assets/BP/PlayerWeapons/HunterAxe/Mat \
  --texmap $TM --tint none \
  --weapon assets/BP/PlayerWeapons/HunterAxe/Mesh/SkM_Axe.psk \
  --weaponanim assets/BP/PlayerWeapons/HunterAxe/Anim $G/Anim/Axe --transformbone Transformer --bladebones Transformer,Transformer_end,DamageStart,DamageEnd,TransSpark \
  --pistol assets/BP/PlayerWeapons/HunterPistol/Mesh/SM_Hunter_Pistol.pskx \
  --fps 20 --out gas.bin | tail -2
python3 assets/tools/convert_hunter.py --psk $G/Mesh/SkM_GasBeast.psk --psa $G/Anim --psaonly AnimGasB_ \
  --tex $G/Mat assets/Char/Hunter/Mat/Tex --texmap $TM --tint none --fps 20 --out gasbeast.bin | tail -2
ls -l gas.bin gasbeast.bin
