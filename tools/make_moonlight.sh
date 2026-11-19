#!/bin/bash
# make_moonlight.sh: adds the Holy Moonlight Sword (weapon 15, and its two-handed form with the blade of light out) to weapons.bin,
# puts its icon into itemicons.bin, and copies both to the card.
#   cp ~/Downloads/convert_weapons.py ~/Downloads/make_moonlight.sh ~/bbpsx-vita/assets/tools/; bash ~/bbpsx-vita/assets/tools/make_moonlight.sh
# The sword is sold in the Dream for 12000 echoes once you have seen the Moon Presence. For testing, sell it from the start with:
#   touch /run/media/deck/USD00/Data/bbpsx/moonlight_now.txt
cd ~/bbpsx-vita || exit 1
CARD=/run/media/deck/USD00/Data/bbpsx
SRC=$(find assets -type d -ipath '*PlayerWeapons/Moonlight' ! -path 'assets/BP/PlayerWeapons/Moonlight' | head -n 1)
if [ -n "$SRC" ]; then mkdir -p assets/BP/PlayerWeapons/Moonlight; cp -r "$SRC"/. assets/BP/PlayerWeapons/Moonlight/; echo "sword files: $SRC"; fi
[ -f assets/BP/PlayerWeapons/Moonlight/Mesh/SkM_Moonlight.psk ] || { echo "SkM_Moonlight.psk not found under assets/"; exit 1; }
# the weapons (the same options the Burial Blade build uses, so it stays in the file as it was)
bash assets/tools/make_weapons.sh --burial --rot burial=${BROT:-90,0,90} --off burial=${BOFF:-9,-62,0} $WARGS || exit 1
grep -q "^moonlight_t " convert_logs/weapons.txt || echo "WARNING: the sword's second form is not in weapons.bin - send me convert_logs/weapons.txt"
grep "^moonlight\|moonlight_t:" convert_logs/weapons.txt
# the menu icon
D=assets/UI/ItemIcons; IC=$(find assets -name 'T_IconMoonlight.png' ! -path "$D/*" | head -n 1)
if [ -d "$D" ] && [ "$(ls $D/*.png 2>/dev/null | wc -l)" -ge 10 ] && [ -n "$IC" ]; then
  cp "$IC" $D/T_IconMoonlight.png
  python3 - <<'PY'
import os, struct
from PIL import Image
d = os.path.expanduser('~/bbpsx-vita/assets/UI/ItemIcons')
out = []
for f in sorted(os.listdir(d)):
    if not f.lower().endswith('.png'): continue
    n = os.path.splitext(f)[0]
    if len(n) > 31: print('skip (name too long):', n); continue
    im = Image.open(os.path.join(d, f)).convert('RGBA'); w, h = im.size
    out.append(bytes([len(n)]) + n.encode() + struct.pack('<HH', w, h) + im.tobytes())
open('itemicons.bin', 'wb').write(b'BBUI' + struct.pack('<I', len(out)) + b''.join(out))
print('packed', len(out), 'icons')
PY
  ICOK=1
else echo "icon NOT added (the icon folder $D is missing or nearly empty, or T_IconMoonlight.png was not found): the sword will show its name instead of a picture"; fi
if [ -d "$CARD" ]; then cp -v weapons.bin "$CARD/weapons.bin"; [ -n "$ICOK" ] && cp -v itemicons.bin "$CARD/itemicons.bin"; else echo "card not found at $CARD: copy weapons.bin (and itemicons.bin) to ux0:data/bbpsx/ yourself"; fi
echo "done: rebuild the game with the new main.c as well (the old game ignores the sword)"
