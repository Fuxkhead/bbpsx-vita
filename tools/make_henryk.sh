#!/bin/bash
# builds henryk.bin: Henryk (his outfit on the Hunter skeleton, the Hunter's idle / walk and now the fighting moves + the saw cleaver) from ~/bbpsx-vita/assets
# tune the cleaver in his hand like Eileen's:  EROT=0,0,90 EOFF=0,0,0 bash make_henryk.sh
cd ~/bbpsx-vita || exit 1
PSK=$(find assets -name "SkM_AttireHenryk.psk" | head -1)
F=$(grep -rl "Hunter_Idle" assets --include=*.psa 2>/dev/null | head -1)      # the animation file that holds Hunter_Idle
HAT=$(find assets -iname "SM_HatHunter.psk*" | head -1)      # Henryk wears the Hunter's hat
PSA=$([ -n "$F" ] && dirname "$F")
echo "hat: ${HAT:-none}"; echo "body: ${PSK:-NOT FOUND}"; echo "anim folder: ${PSA:-NOT FOUND}   (file: ${F:-none})"
[ -n "$PSK" ] && [ -n "$PSA" ] || { echo "missing files - paste these two lines to me"; exit 1; }
# the Hunter's own head / face / hair meshes (the outfit meshes have none): taken from your last hunter.bin build command
CMD=$(grep -h "convert_hunter.py.*SkM_AttireHunter.psk.*--out hunter.bin" ~/.bash_history | grep -v GasAnim | tail -1)
HEADS=$(python3 - "$CMD" <<'P'
import sys, shlex
try: a = shlex.split(sys.argv[1])
except Exception: a = []
out = []
if '--psk' in a:
    i = a.index('--psk') + 1
    while i < len(a) and not a[i].startswith('--'): out.append(a[i]); i += 1
print(' '.join(x for x in out if 'AttireHunter' not in x))
P
)
[ -n "$HEADS" ] || HEADS=$(find assets/Char/Hunter/Mesh -iname '*.psk' | grep -iE 'head|face|hair' | tr '\n' ' ')
PICK=""; for f in $HEADS; do case "$f" in *[Ff]ace0*|*SkM_HunterHair0.psk) PICK="$PICK $f";; esac; done      # one face and the plain hair (no _Hat variant: it is shaped for a hood); his hat sits on top of the head
[ -n "$PICK" ] && HEADS="$PICK"
HTM=$(python3 - "$CMD" <<'P'
import sys, shlex
try: a = shlex.split(sys.argv[1])
except Exception: a = []
print(a[a.index('--texmap') + 1] if '--texmap' in a and a.index('--texmap') + 1 < len(a) else '')
P
)      # the texture mapping your hunter.bin build used (hair / face materials)
echo "head meshes: ${HEADS:-NONE FOUND}"
TM="${HTM:+$HTM,}MI_HenrykBody=t_henrykbody,MI_HenrykBodyDark=t_henrykbody,MI_HenrykBodyPrev=t_henrykbody,MI_HunterHead=T_HunterHead,MI_HunterHeadPrev=T_HunterHead,MI_Bandage=t_hair,MI_ForeignBody=t_henrykbody,MI_HunterHair=t_hair,MI_HunterFace=T_HunterHead"
BLADE=$(find assets/BP/PlayerWeapons -iname '*Cleaver*' \( -name '*.psk' -o -name '*.pskx' \) 2>/dev/null | head -1)      # his weapon: the saw cleaver. NOCLEAVER=1 builds him without it
[ -n "$NOCLEAVER" ] && BLADE=""
PSAS="$PSA $(find assets/Char/Hunter/Anim assets/BP/PlayerWeapons -type d 2>/dev/null | tr '\n' ' ')"      # he fights with the Hunter's own moves now (the Eileen duel), so pack them too
echo "cleaver: ${BLADE:-none}"
TEXD="assets/Cine assets/Char/Hunter ${BLADE:+$(dirname "$(dirname "$BLADE")")}"
python3 assets/tools/convert_hunter.py --psk "$PSK" $HEADS --psa $PSAS --psaonly Hunter_Idle,Hunter_Walk,Hunter_Run,HunterDeath,HunterCleav_Attack,Small,Quickstep,HunterDodge_Roll \
  --tex $TEXD --texmap "$TM,MI_Cleaver=t_sawcleaver" --tint none ${HAT:+--hat "$HAT"} \
  ${BLADE:+--pistol "$BLADE" --pistolbone hand_r --pistolrot ${EROT:-0,0,0} ${EOFF:+--pistoloff $EOFF}} \
  --fps 15 --out henryk.bin 2>&1 | grep -E "WARNING|^wrote|bones missing|Error|Traceback|material" | head -20
ls -l henryk.bin
echo "Copy henryk.bin to ux0:data/bbpsx/"
