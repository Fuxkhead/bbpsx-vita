#!/bin/bash
# builds dograt.bin dogcrow.bin crowdog.bin werepig.bin giantpig.bin wheelchair.bin from the FModel export in ~/bbpsx-vita/assets/Char/Enemies
cd ~/bbpsx-vita || exit 1
E=assets/Char/Enemies
mkdir -p convert_logs; : > convert_logs/chimera.txt
TEXDIRS=$(find "$E" -type d \( -iname Mat -o -iname Tex \) 2>/dev/null | tr '\n' ' ')
TEXDIRS="$TEXDIRS $(find assets/BP/PlayerWeapons/HunterPistol -type d \( -iname Mat -o -iname Tex \) 2>/dev/null | tr '\n' ' ')"      # pistol texture
TM="MI_GiantPig=t_pig,MI_GiantPigDarkRed=t_pig,MI_WheelchairEnemy=t_wheelchairenemy,MI_FaceWheelchair=t_facewheelchair,MI_HairWheelchair=t_hairwheelchair,MI_Bandage=t_hairwheelchair,MI_Werewolf=werewolfexp,MI_WerewolfBloody=werewolfbloodyexp"
build() {   # out  mesh-name  anim-root(s)  psaonly
  local out=$1 mesh; mesh=$(find "$E" -iname "$2" 2>/dev/null | head -1)
  echo "--- $out"
  if [ -z "$mesh" ]; then echo "MISSING $2: export it from FModel (skeletal mesh as PSK) into assets/Char/Enemies/..."; return; fi
  if ! find $3 -iname '*.psa' 2>/dev/null | grep -q .; then echo "MISSING animations (.psa) under $3: export them from FModel"; return; fi
  python3 assets/tools/convert_hunter.py --psk "$mesh" --psa $3 --psaonly "$4" --tex $TEXDIRS --texmap "$TM" --tint none --fps 20 $5 --out $out.bin 2>&1 | tee -a convert_logs/chimera.txt | grep -E "WARNING|^wrote|bones missing|Error|Traceback|material" | head -12
}
build dograt     SkM_DogRat.psk          $E/Chimera/DogRat                      "DogRat_"
build dogcrow    SkM_DogCrow.psk         "$E/Chimera/DogCrow $E/Chimera/DogRat" "DogCrow_,DogRat_"
build crowdog    SkM_CrowDog.psk         "$E/Chimera/CrowDog $E/Chimera/DogRat" "AnimDogCrow_,DogRat_" "--bindpos"
build werepig    SkM_WerePig.psk         $E/Chimera/WerePig                     "WerePig_"
build giantpig   SkM_GiantPig.psk        $E/GiantPig                            "PigAnim_"
# the wheelchair man's pistol: glued to the hand that moves in the shoot animation
PISTOL=$(find assets -iname 'SM_Hunter_Pistol.pskx' | head -1)
HAND=$(python3 - <<'PY'
import sys, glob, os, numpy as np
sys.path.insert(0, 'assets/tools')
import convert_hunter as ch
best = {'l': 0.0, 'r': 0.0}
for f in glob.glob('assets/Char/Enemies/Wheelchair/**/*.psa', recursive=True):
    for s in ch.load_psa(f):
        if 'Shoot' not in s['name']: continue
        q = s['keys']['q']; n = s['n']; bn = s['bones']
        for side in 'lr':
            for b in ('upperarm_' + side, 'lowerarm_' + side, 'hand_' + side):
                if b not in bn: continue
                i = bn.index(b)
                for fr in range(1, n):
                    d = abs(float(np.dot(q[0][i], q[fr][i]))); best[side] += 2 * np.arccos(min(1.0, d))
print('r' if best['r'] > best['l'] else 'l')
PY
)
echo "wheelchair shoots with the $HAND hand; pistol: $PISTOL"
if [ -n "$PISTOL" ]; then PX="--pistol $PISTOL --pistolbone hand_$HAND --pistolsocket hand_${HAND}Socket"; else PX=""; fi
build wheelchair SkM_WheelchairEnemy.psk $E/Wheelchair "AnimWhlchr_" "$PX"
ls -l dograt.bin dogcrow.bin crowdog.bin werepig.bin giantpig.bin wheelchair.bin 2>&1 | sed 's/^ls: cannot access //'
echo "full log: convert_logs/chimera.txt"
