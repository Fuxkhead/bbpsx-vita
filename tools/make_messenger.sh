#!/bin/bash
# builds messenger.bin: the little messengers (model, the note in their hands, appear / hide / hold-a-message / hold-a-weapon animations) from ~/bbpsx-vita/assets
# the idle with the closed note is ${MIDLE:-Anim_Reach1} (try MIDLE=Anim_Reach1, Anim_Reach2, Anim_Cry or Anim_Dance for another); the note sits in a hand: NROT="x,y,z" (degrees) turns it, NOFF="x,y,z" (cm) slides it, NBONE=<bone name> picks another bone
cd ~/bbpsx-vita || exit 1
PSK=$(find assets -iname "SkM_Messenger.psk*" | head -1)
NOTE=$(find assets -iname "SM_MessengerNoteClosed.psk*" | head -1)      # held closed ...
NOTE2=$(find assets -iname "SM_MessengerNoteOpen.psk*" | head -1)      # ... and open while its message is up
F=$(find assets -iname "Anim_HoldMessage.psa" | head -1)
PSA=$([ -n "$F" ] && dirname "$F")
PSA2=$(find assets -type d -iname "HoldWeaponGrants" | head -1)
echo "body: ${PSK:-NOT FOUND}"; echo "notes: ${NOTE:-NOT FOUND} / ${NOTE2:-NOT FOUND}"; echo "anim folders: ${PSA:-NOT FOUND} ${PSA2:-none}"
[ -n "$PSK" ] && [ -n "$PSA" ] || { echo "missing files - run: find assets -iname '*Messenger*' | head -30   and paste it to me"; exit 1; }
# the hand bone to hold the note: the skeleton's own names, a right hand if there is one
BONES=$(python3 - "$PSK" <<'P'
import sys; sys.path.insert(0, 'assets/tools')
from convert_hunter import load_psk
n = [b['name'] for b in load_psk(sys.argv[1])['bones']]
print(' '.join(n))
P
)
echo "bones: $BONES"
BONE=${NBONE:-$(for b in $BONES; do case "$b" in hand_r|Hand_R|hand_R|RightHand|hand_r*) echo $b; break;; esac; done)}
[ -n "$BONE" ] || BONE=$(for b in $BONES; do case "$(echo $b | tr A-Z a-z)" in *hand*) echo $b; break;; esac; done)
echo "note bone: ${BONE:-none}"
# messenger_hats: the five hats the insight shop sells (hunters, rumpled, top, steepled, doll); every messenger wears the one that is chosen in the shop
HATARGS=""; HL=""
for H in SM_HatHunter SM_RumpledHat SM_TopHat SM_HatSteepled SM_HatDoll; do
  HF=$(find assets -iname "$H.pskx" -o -iname "$H.psk" | head -1); [ -n "$HF" ] || { echo "hat $H NOT FOUND"; HF=""; }
  [ -n "$HF" ] && HL="$HL${HL:+,}$HF"
done
if [ "$(echo $HL | tr ',' '\n' | wc -l)" = 5 ]; then
  # the hats go where the head bone is: MHZ adds height (cm), MHS scales them (the messengers are small), MHX / MHY slide them
  HOFF=$(python3 - "$PSK" "${MHX:-0}" "${MHY:-0}" "${MHZ:-0}" "${MHS:-0.6}" "$HL" <<'P'
import sys; sys.path.insert(0, 'assets/tools')
import numpy as np
from convert_hunter import load_psk, world_chain
m = load_psk(sys.argv[1]); sc = float(sys.argv[5])
names = [b['name'] for b in m['bones']]
W = world_chain(names, [b['parent'] for b in m['bones']], [(b['q'], b['p']) for b in m['bones']])
hn = 'head' if 'head' in names else names[0]; hp = W[hn][1]
top = float(np.max(m['pts'][:, 2]))      # the top of the messenger's own head
hats = [load_psk(f)['pts'] for f in sys.argv[6].split(',')]
lo = float(np.mean([h[:, 2].min() for h in hats])) * sc      # where the hats' own bottoms are, scaled
cx = float(np.mean([(h[:, 0].min() + h[:, 0].max()) / 2 for h in hats])) * sc; cy = float(np.mean([(h[:, 1].min() + h[:, 1].max()) / 2 for h in hats])) * sc
z = top - lo - 1.5      # the hats' bottoms rest 1.5 cm into the top of the head (MHZ moves them from there)
sys.stderr.write("messenger: head bone z %.1f, top of the head z %.1f; hats (scaled) bottom z %.1f\n" % (hp[2], top, lo))
print("%.2f,%.2f,%.2f" % (hp[0] - cx + float(sys.argv[2]), hp[1] - cy + float(sys.argv[3]), z + float(sys.argv[4])))
P
)
  echo "hats: head bone at $HOFF  (scale ${MHS:-0.6}; tune with MHZ=<cm up> MHS=<size> MHX= MHY=)"
  HATARGS="--mhats $HL --mhatoff $HOFF --mhatscale ${MHS:-0.6}"
else HATARGS=""; echo "hats skipped (not all five found)"; fi
# messenger_weapons: what the two gift messengers hold out (cleaver + cane / pistol + blunderbuss); the game shows the right pair. MWS = size (0.6), MWROT="x,y,z" degrees, MWOFF="x,y,z" cm; the game can also nudge them (SELECT in a gift shop)
WL=""; for P in "Cleaver/Mesh/SkM_Cleaver.psk" "ThreadedCane/Mesh/SM_ThreadedCane.pskx" "HunterPistol/Mesh/SM_Hunter_Pistol.pskx" "Blunderbuss/Mesh/SM_Blunderbuss.pskx"; do
  WF=$(find assets/BP -ipath "*PlayerWeapons/$P" | head -1); [ -n "$WF" ] || { echo "weapon $P NOT FOUND"; WL=""; break; }
  WL="$WL${WL:+,}$WF"
done
if [ -n "$WL" ]; then WEAPARGS="--mweaps $WL --mwscale ${MWS:-0.6} --mwrot ${MWROT:-0,0,0} --mwoff ${MWOFF:-0,0,0}"; echo "weapons: $WL"; else WEAPARGS=""; echo "weapons skipped"; fi
# (the hat materials have no texture of their own in the export: the texmap below lends them the closest ones)
NOTEARGS=""
if [ -n "$NOTE" ] && echo " $BONES " | grep -q " NoteSocket "; then      # the game's own socket for the note (BP_NoteMessenger attaches it to "NoteSocket")
  echo "note: attached at the NoteSocket (the original holding position)"
  NOTEARGS="--pistol $NOTE ${NOTE2:+--pistol2 $NOTE2} --pistolbone NoteSocket --pistolframe socket --pistolsocket NoteSocket --pistolrot ${NROT:-0,0,0} --pistoloff ${NOFF:-0,0,0} --cbone ${CBONE:-hand_l} --cframe hand --crot ${CROT:-0,0,0} ${COFF:+--coff $COFF}"      # the OPEN note stays at the NoteSocket; the CLOSED note (idle) is in the left hand (CBONE=hand_r for the right; CROT / COFF tune it)
elif [ -n "$NOTE" ] && [ -n "$BONE" ]; then NOTEARGS="--pistol $NOTE ${NOTE2:+--pistol2 $NOTE2} --pistolbone $BONE --pistolframe hand --pistolrot ${NROT:-0,0,0} ${NOFF:+--pistoloff $NOFF}"; fi
python3 assets/tools/convert_hunter.py --psk "$PSK" --psa "$PSA" --psaonly HoldMessage,CloseMessage,Appear,Hide,${MIDLE:-Reach1},HoldCleaver,HoldPistol \
  $NOTEARGS $HATARGS $WEAPARGS --tex assets/Char/NPCs/Messenger assets/Cine assets/Char/Hunter assets/Char assets/BP/PlayerWeapons assets/NMKART --texmap "MI_Cleaver=t_sawcleaver,MI_Pistol=t_pistol,MI_Blunderbuss=t_blunder,MI_ThreadedCane=T_Cane,MI_Messenger=t_messenger,MI_MessengerNote=t_messenger,MI_Gehrman=t_gehrmanbody,MI_GehrmanHatsAlt=t_gehrmanbody,MI_DollBodyPrev=t_doll_body,MI_HunterHeadPrev=t_hunterredehat" --tint none --fps 20 --out messenger.bin 2>&1 | grep -E "WARNING|^wrote|bones missing|Error|Traceback|points|skip|anim" | head -60
ls -l messenger.bin
echo "Copy messenger.bin to ux0:data/bbpsx/"
