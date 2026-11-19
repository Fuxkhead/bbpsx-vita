# If you own Bloodborne: the better Rom, her children, the Moon Presence and the extra voices

The kit builds everything without game data (placeholders). If you own Bloodborne you can make your own better versions from files you extract
from **your own legal copy**, with your usual extraction tools. They stay on your card (ux0:data/bbpsx/), for your personal use. **Never commit them or the files built from them to a public repository.**

## 1. Rom and her children, from the Child of Rom model
You need one thing extracted: the *Child of Rom* model as `c1400.obj` with its textures `c1400_c5100_body_a.png` and `c1400_c5100_leg_a.png`, together in one folder (call it `Child of Rom`).

    python3 tools/make_rom.py --dir "Child of Rom" --out rom.bin
    python3 tools/make_rom.py --dir "Child of Rom" --child 1 --out romchild.bin
    (add --preview rom.png to get a pose sheet to check)

Copy `rom.bin` and `romchild.bin` to ux0:data/bbpsx/ (they replace the placeholders: same names). Her lake itself (`make_romlake.py`) needs nothing.

## 2. The Moon Presence over the blood moon (flip-book)
Extract the first-form *Moon Presence* model (the folder `make_moonp.py --form 1 --dir "Moon Presence"` already expects). Then:

    python3 tools/make_moonp.py --form 1 --dir "Moon Presence" --budget 1.5 --out moonp1.bin
    python3 tools/moonpres_rip/pose_moon.py moonp1.bin posed.npy
    python3 tools/moonpres_rip/make_moonpres_rip.py moonp1.bin posed.npy moonpres.bin

`moonpres.bin` (2.4 MB) goes in ux0:data/bbpsx/ (it replaces the placeholder). It only shows after Rom, Gehrman and the Amygdala are dead, never in a boss rush.
Tune it with `ux0:data/bbpsx/moon_pres.txt` = "scale dy fps". The first two steps need numpy and Pillow. (A higher `--budget` gives a finer silhouette; 1.0 to 2.0 all work.)

## 3. Extra voice lines
The game plays these when the files exist and stays silent without them. Pick each line from your own audio, name it for its slot, and run:

    bash tools/voice_pack.sh my_clips snd_out        (then copy snd_out/* to ux0:data/bbpsx/snd/)

| slot | line (starts with) |
|---|---|
| doll_1 | Hello, good hunter. |
| doll_2 | I am a doll, here ... |
| doll_3 | Honourable hunter, pursue ... |
| doll_4 | ... and I will channel ... |
| doll_5 | Welcome home, good hunter. |
| doll_6 | Did you speak with Gehrman ... |
| doll_7 | He was a hunter long ... |
| doll_9 | Ahh, the little ones ... |
| doll_10 | But still, aren't they sweet ... |
| doll_13 | May you find your worth ... |
| doll_14 | They find hunters ... |
| doll_15 | Over time, countless ... |
| doll_16 | the farewell clip when you leave the Dream |
| doll_8, doll_11, doll_12 | Hunters have told me ... / I do love you. / Of course... Isn't that ... (no clip yet: she stays silent on these) |
| gh_l1 .. gh_l7 | Gehrman's lines, in the order he speaks them |
| e_oh, e_mess, e_welcome | Eileen: see `tools/make_eileen_vo.sh` (finds them by name) |
| e_laugh | Eileen's laugh |
| mus_hdintro, mus_hd, mus_hd3 | the Hunter's Dream music (mus_ files are stored at 24 kHz) |

The mixer plays every clip at the right speed and smooths it, so clips at 22.05 to 48 kHz all work. Run `python3 tools/check_data.py` to see which files are still missing.
