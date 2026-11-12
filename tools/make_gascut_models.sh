#!/bin/bash
# the Gascoigne intro actors: rebuilds gas.bin (+ his two scene animations) and werewolf.bin (+ WereAnim_GasCutscene).   usage: ./make_gascut_models.sh
cd ~/bbpsx-vita || exit 1
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_hunter*.py | head -1)" assets/tools/convert_hunter.py
G=assets/Char/Bosses/Gascoigne
C=assets/Cine/GasIntro/Anim
TM="MI_GasBody=t_gas,MI_FaceGas1=BbPSX_Head128vGAS1,MI_HairGas=t_hair,MI_Bandage=t_hair,MI_GasBeast=t_gasbeast"
python3 assets/tools/convert_hunter.py --psk $G/Mesh/SkM_Gas.psk --psa $G/Anim $C --psaonly AnimGas_ \
  --tex $G/Mat assets/Char/Hunter/Mat/Tex assets/BP/PlayerWeapons/HunterPistol/Mat/Tex assets/BP/PlayerWeapons/HunterAxe/Mat \
  --texmap $TM --tint none \
  --weapon assets/BP/PlayerWeapons/HunterAxe/Mesh/SkM_Axe.psk \
  --weaponanim assets/BP/PlayerWeapons/HunterAxe/Anim $G/Anim/Axe --transformbone Transformer --bladebones Transformer,Transformer_end,DamageStart,DamageEnd,TransSpark \
  --pistol assets/BP/PlayerWeapons/HunterPistol/Mesh/SM_Hunter_Pistol.pskx \
  --fps 20 --slowfps Scene=10 --out gas.bin 2>&1 | tail -3
E=assets/Char/Enemies
python3 assets/tools/convert_hunter.py --psk $E/Werewolf/Mesh/SkM_Werewolf.psk --psa $E/Werewolf/Anim $C \
  --psaonly Were_,WereAnim_GasCutscene --tex $E/Werewolf/Mat/Tex --texmap MI_Werewolf=werewolfexp,MI_WerewolfBloody=werewolfbloodyexp \
  --tint none --fps 20 --slowfps GasCutscene=10 --out werewolf.bin 2>&1 | tail -3
ls -l gas.bin werewolf.bin
for f in gas.bin werewolf.bin; do for n in AnimGas_SceneP1 AnimGas_SceneExhale WereAnim_GasCutscene; do grep -c -a "$n" $f | sed "s/^/$f $n: /"; done; done
echo "Copy gas.bin and werewolf.bin to ux0:data/bbpsx/ (the intro needs AnimGas_* in gas.bin and WereAnim_GasCutscene in werewolf.bin)"
