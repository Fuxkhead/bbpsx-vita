#!/bin/bash
# builds gilb.bin (Gilbert, the boss in the Gilberts cabin) from the FModel export in ~/bbpsx-vita/assets, and shows what the fight will have to work with
cd ~/bbpsx-vita || exit 1
G=assets/Char/Bosses/Gilb
echo "== export check"; ls $G $G/Mesh $G/Mat 2>&1 | head -30; ls $G/Anim 2>/dev/null | wc -l
PSK=$(ls $G/Mesh/SkM_Gilbert.psk $G/Mesh/SkM_Gilbert*.psk 2>/dev/null | head -1)
[ -n "$PSK" ] || { echo "NO SkM_Gilbert.psk in $G/Mesh - export it with FModel (Char/Bosses/Gilb: Mesh, Mat, Anim) and run again"; exit 1; }
python3 assets/tools/convert_hunter.py --psk $PSK --psa $G/Anim --psaonly AnimGilb_ \
  --tex $G/Mat assets/Char/Enemies/Werewolf/Mat/Tex --texmap MI_Gilb=t_gilb,MI_WerewolfBloody=werewolfbloodyexp --tint none --fps 20 --out gilb.bin | grep -i -E "warn|texture|wrote"
ls -l gilb.bin
echo "== animations in gilb.bin"; strings -n 6 gilb.bin | grep -o -E 'AnimGilb_[A-Za-z0-9]*' | sort -u | tr '\n' ' '; echo
echo "== Gilbert in the boss arena"; grep -n -A14 'def Scope "BPC_Gilb_2"' assets/Maps/GsEstate/MP_GE_BossArena.usda | grep -E "translate|orient|scale" | head
echo "== table + lantern + fog wall placement"; grep -n -A12 -E 'def Scope "(BP_FogWall_2|BP_SavePointLantern_2|BP_HunterTriggerVolume_2|BP_Credits_2)"' assets/Maps/GsEstate/MP_GE_BossArena.usda | grep -E "def Scope|translate|scale" | head -20
echo "-> copy gilb.bin to ux0:data/bbpsx/"
