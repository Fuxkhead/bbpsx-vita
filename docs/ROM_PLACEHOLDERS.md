# Rom and her children: build them with no game files

Rom's lake fight needs five files on the card (ux0:data/bbpsx/). None of them needs ripped game data:

| file | made by | needs |
|---|---|---|
| level_romlake.bin, interact_romlake.bin, floor_romlake.bin | `python3 tools/make_romlake.py --outdir ~/bbpsx-vita` | nothing (generated) |
| rom.bin | `python3 tools/make_rom.py --placeholder 1 --out rom.bin` | nothing (simple generated shapes) |
| romchild.bin | `python3 tools/make_rom.py --placeholder 1 --child 1 --out romchild.bin` | nothing |

The stand-ins are a pale body with a cream face, a white mound of petals on her back and spider legs, with every animation the fight uses
(Idle, WalkFast, MeteorSlam, IceRoll, BlastSlam, FlailCombo, damage reactions, Visceral, Death). The Child of Rom is the same body, small, with eight legs.

If you own the game and have ripped the Child of Rom model yourself, point the script at the rip instead and the result is her real shape; it stays on your own card, for personal use:

    python3 tools/make_rom.py --dir "Child of Rom" --out rom.bin
    python3 tools/make_rom.py --dir "Child of Rom" --child 1 --out romchild.bin

Never commit rom.bin / romchild.bin built from a rip to a public repository. The `--placeholder` files contain none of the game and may be shared.
Copy the five files to ux0:data/bbpsx/ (the game loads rom.bin and romchild.bin only inside her lake).
