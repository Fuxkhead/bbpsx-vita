#!/bin/bash
# builds werewolf.bin, rabiddog.bin, troll.bin from ~/bbpsx-vita/assets/Char/Enemies
cd ~/bbpsx-vita || exit 1
E=assets/Char/Enemies
python3 assets/tools/convert_hunter.py --psk $E/Werewolf/Mesh/SkM_Werewolf.psk --psa $E/Werewolf/Anim \
  --psaonly Were_ --tex $E/Werewolf/Mat/Tex --texmap MI_Werewolf=werewolfexp,MI_WerewolfBloody=werewolfbloodyexp \
  --tint none --fps 20 --out werewolf.bin | tail -3
python3 assets/tools/convert_hunter.py --psk $E/RabidDog/Mesh/SkM_RabidDog.psk --psa $E/RabidDog/Anim \
  --psaonly AnimDog_ --tex $E/RabidDog/Mat --texmap MI_RabidDog=t_rabiddog \
  --tint none --fps 20 --out rabiddog.bin | tail -3
python3 assets/tools/convert_hunter.py --psk $E/Troll/Mesh/SkM_Troll.psk $E/Troll/Mesh/SkM_TrollCape.psk --psa $E/Troll/Anim \
  --psaonly TrollAnim --tex $E/Troll/Mat --texmap MI_Troll=T_Troll,MI_TrollCape=T_trollcape \
  --tint none --fps 20 --out troll.bin | tail -3
ls -l werewolf.bin rabiddog.bin troll.bin
