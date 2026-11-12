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
NOTEARGS=""
if [ -n "$NOTE" ] && echo " $BONES " | grep -q " NoteSocket "; then      # the game's own socket for the note (BP_NoteMessenger attaches it to "NoteSocket")
  echo "note: attached at the NoteSocket (the original holding position)"
  NOTEARGS="--pistol $NOTE ${NOTE2:+--pistol2 $NOTE2} --pistolbone NoteSocket --pistolframe socket --pistolsocket NoteSocket --pistolrot ${NROT:-0,0,0} --pistoloff ${NOFF:-0,0,0} --cbone ${CBONE:-hand_l} --cframe hand --crot ${CROT:-0,0,0} ${COFF:+--coff $COFF}"      # the OPEN note stays at the NoteSocket; the CLOSED note (idle) is in the left hand (CBONE=hand_r for the right; CROT / COFF tune it)
elif [ -n "$NOTE" ] && [ -n "$BONE" ]; then NOTEARGS="--pistol $NOTE ${NOTE2:+--pistol2 $NOTE2} --pistolbone $BONE --pistolframe hand --pistolrot ${NROT:-0,0,0} ${NOFF:+--pistoloff $NOFF}"; fi
python3 assets/tools/convert_hunter.py --psk "$PSK" --psa "$PSA" --psaonly HoldMessage,CloseMessage,Appear,Hide,${MIDLE:-Reach1},HoldCleaver,HoldPistol \
  $NOTEARGS --tex assets/Char/NPCs/Messenger --texmap "MI_Messenger=t_messenger,MI_MessengerNote=t_messenger" --tint none --fps 20 --out messenger.bin 2>&1 | grep -E "WARNING|^wrote|bones missing|Error|Traceback|points|skip|anim" | head -20
ls -l messenger.bin
echo "Copy messenger.bin to ux0:data/bbpsx/"
