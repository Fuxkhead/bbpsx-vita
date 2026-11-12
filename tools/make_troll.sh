#!/bin/bash
# builds troll.bin (statue in his hand) and trollbrick.bin (the Derelict Estate troll, brick in his left hand)
# the prop's middle sits on the hand bone, then TROLLOFF slides it (default 0,-8,0: 8 cm toward the fingers; x/y/z are the prop's own axes, y = along the fingers, negative = further out)
# tune:  TROLLOFF="x,y,z" (slides the prop in the hand, cm, prop's own axes)  TROLLROT="rx,ry,rz" (degrees)  TROLLHAND=bonename  TROLLFRAME=hand|socket
#   e.g.  TROLLROT=0,90,0 bash make_troll.sh        (applies to both; BRICKOFF / BRICKROT override for the brick only)
cd ~/bbpsx-vita || exit 1
E=assets/Char/Enemies
ST=$(find assets -iname 'SM_Statue1.usda' | head -1); [ -n "$ST" ] || ST=$(find assets -iname 'SM_Statue1.psk*' | head -1)
BR=$(find assets -iname 'SM_BrickProp.usda' | head -1); [ -n "$BR" ] || BR=$(find assets -iname 'SM_BrickProp.psk*' | head -1)
echo "statue mesh: ${ST:-NOT FOUND}   brick mesh: ${BR:-NOT FOUND}"
STEX=$(dirname "$(find assets -iname 't_statue1.png' | head -1)")
BTEX=$(dirname "$(find assets -iname 't_brickwall.png' | head -1)")
HAND=${TROLLHAND:-$(python3 -I - <<PY
import sys, re
sys.path.insert(0, 'assets/tools')
import convert_hunter as c
m = c.load_psk('$E/Troll/Mesh/SkM_Troll.psk')
names = [b['name'] for b in m['bones']]
print('bones with hand:', [n for n in names if 'hand' in n.lower()], file=sys.stderr)
# the troll model's hand_l bone is the hand that shows on his right side in the game, so the prop goes on hand_r (TROLLHAND=hand_l to go back)
cand = [n for n in names if n.lower() in ('hand_r', 'r_hand', 'righthand', 'hand_right')] or [n for n in names if re.search(r'hand', n, re.I) and re.search(r'(_r$|^r_|right)', n, re.I)]
print(cand[0] if cand else 'hand_r')
PY
)}
echo "hand bone: $HAND"
build() {   # build <prop mesh> <texture dir> <extra texmap> <off> <rot> <out>
  python3 assets/tools/convert_hunter.py --psk $E/Troll/Mesh/SkM_Troll.psk $E/Troll/Mesh/SkM_TrollCape.psk --psa $E/Troll/Anim \
    --psaonly TrollAnim --tex $E/Troll/Mat $E/Troll/Mesh $2 --texmap MI_Troll=T_Troll,MI_TrollCape=T_trollcape,$3 \
    --pistol "$1" --pistolcenter --pistolbone "$HAND" --pistolframe ${TROLLFRAME:-hand} ${4:+--pistoloff $4} ${5:+--pistolrot $5} \
    --tint none --fps 20 --out $6 2>&1 | grep -E "WARNING|^wrote|bones missing|Error|bones with"
}
[ -n "$ST" ] && build "$ST" "$STEX" "MI_Statue1=t_statue1,MI_Statue=t_statue1,MI_Statue1Dark=t_statue1" "${TROLLOFF:-0,-8,0}" "$TROLLROT" troll.bin
[ -n "$BR" ] && build "$BR" "$BTEX" "MI_BrickProp=t_brickwall,MI_Brick=t_brickwall,MI_BrickWall=t_brickwall" "${BRICKOFF:-${TROLLOFF:-0,-8,0}}" "${BRICKROT:-$TROLLROT}" trollbrick.bin
ls -l troll.bin trollbrick.bin
