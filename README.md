# Bloodborne PSX for PS Vita: build kit

This kit builds the Vita port of Bloodborne PSX **from your own copy of the game's files**. It contains source code, converter scripts and
hand-written settings only: **no Bloodborne PSX art, models, maps, music or voices are included**. The data you build from them is derived
from the game's files, so keep it for your own use unless you have permission to share it.

> **Status: honest warning.** The game source was written and checked on a PC; everything here was only ever compiled and run by the me on my Vita.
> `pack_icons.py`, `pack_rgba.py` and `make_dlgfont.py` have **not** been tested by anyone. The included `CMakeLists.txt` is my own working file.
> The hunter.bin build is documented in the header of `tools/convert_hunter.py`; the weapon / pistol / tint options of my own last run are not tested from this kit, so expect some trial and error there.

## Quick start (short version)

1. Install VitaSDK + vitaGL + vitashark, Python 3 (`pillow numpy`), `ffmpeg`.
2. Export the game with FModel into `~/bbpsx-vita/assets/` (see section 1).
3. Copy `src/*` to `~/bbpsx-vita/`, `tools/*` to `~/bbpsx-vita/assets/tools/`.
4. Build the program: `cd ~/bbpsx-vita && mkdir build && cd build && cmake .. && make`, then `bash ../assets/tools/make_vpk.sh`.
5. Build the data folder (section 4), check it with `check_data.py`, copy it to `ux0:data/bbpsx/` on the Vita.
6. Install the VPK, make sure `libshacccg.suprx` is in `ur0:/data/`, play.

If the build stops with `vita-elf-create: Cannot allocate N bytes for SCE data ... segment 1 overlaps`, raise `#define BB_PAD` near the top of `main.c`.

## 1. What you need

| Need | Notes |
|---|---|
| A hacked PS Vita / PS TV (HENkaku, with Enso or re-run each boot) | `libshacccg.suprx` must be installed (ur0:/data/libshacccg.suprx, from the usual "shader compiler" install step of vitaGL homebrew) |
| Linux (a Steam Deck desktop works) | the scripts are bash + Python 3 |
| [VitaSDK](https://vitasdk.org) with [vitaGL](https://github.com/Rinnegatamante/vitaGL) and vitashark built | `vdpm` can install them |
| Python 3 with `Pillow` and `numpy` | `pip install pillow numpy` |
| `ffmpeg` | sound conversion |
| The game's files exported with **FModel** | meshes as `.psk/.pskx`, animations `.psa`, maps as `.usda` + `.json`, textures as `.png`, keep the pak's folder names |
| The game's `.pak` file | only for `extract_map_props.py` and `extract_volumes.py` |

## 2. Folder layout

Everything assumes the project lives in `~/bbpsx-vita` (scripts `cd` there):

```
~/bbpsx-vita/
  main.c collision.h ps1shader.h mipgen.h CMakeLists.txt      <- all from src/
  sce_sys/                                                    <- icon0.png, pic0.png, livearea/... (optional: your own art; the VPK builds without it)
  assets/                                                     <- your FModel export (Maps/, Char/, BP/, UI/, Cine/ ...)
  assets/tools/                                               <- everything from tools/
  build/                                                      <- cmake build folder
```

## 3. Build the program (eboot / VPK)

```
mkdir -p ~/bbpsx-vita/assets/tools
cp src/* ~/bbpsx-vita/
cp tools/* ~/bbpsx-vita/assets/tools/
cd ~/bbpsx-vita && mkdir -p build && cd build
cmake .. && make                              # produces eboot.bin and param.sfo
bash ~/bbpsx-vita/assets/tools/make_vpk.sh    # -> ~/Downloads/bbpsx.vpk
```
Install the VPK on the Vita (VitaShell). The data folder (step 4) goes to `ux0:data/bbpsx/` (the program only reads that path).

## 4. Build the data folder

Run everything from `~/bbpsx-vita`; outputs land in that folder. At the end, copy **the files, not the scripts** to `ux0:data/bbpsx/`.
Order matters where noted. Each script prints what it did and complains when an export folder is missing.

### 4a. Characters, weapons, animations (`*.bin`)

| Output | Script | Needs first |
|---|---|---|
| `hunter.bin` (the player) | `make_hunter.sh` (reconstructed from the finished file; weapon/pistol offsets may need tuning, see the script) | - |
| `weapons.bin` | `make_weapons.sh` (and `make_eileen.sh` shares its tuning) | hunter.bin |
| `attire.bin` | `make_attire.sh` | hunter.bin |
| `hunter_anims.bin` | `make_hanims.sh`, then `make_jumpanims.sh`, `make_fistanims.sh`, `make_axeanims.sh`, `make_bomanims.sh` | hunter.bin. Each script rebuilds the whole file from the weapon/animation folders it lists, so run them in that order and finish with the last one: its header says which folders it keeps. Check the file afterwards with a quick in-game test of each weapon |
| `hunter_anims2.bin` | `make_heavyanims.sh` | hunter.bin |
| `hunter_anims3.bin` | `make_wlgrab.sh` | hunter.bin |
| `hunter_cine.bin` | `make_hdintro_models.sh` | hunter.bin |
| `gas.bin`, `gasbeast.bin` | `make_gas.sh` (+ `make_gascut_models.sh` for the intro actors) | - |
| `gehr.bin`, `gehrman.bin` | `make_gehr.sh`, `make_gehrman.sh` | - |
| `gilb.bin` | `make_gilb.sh` | - |
| `clericbeast.bin` | `make_cleric.sh` | - |
| `wl.bin` | `make_wl.sh` | - |
| `doll.bin`, `eileen.bin`, `henryk.bin` | `make_doll.sh`, `make_eileen.sh`, `make_henryk.sh` | hunter.bin (eileen, henryk) |
| `messenger.bin`, `switch.bin` | `make_messenger.sh`, `make_switch.sh` | - |
| `werewolf.bin`, `rabiddog.bin`, `troll.bin`, `trollbrick.bin` | `make_enemies2.sh`, `make_troll.sh` | - |
| `dograt.bin dogcrow.bin crowdog.bin werepig.bin giantpig.bin wheelchair.bin` | `make_chimera.sh` | - |
| `yh_board.bin yh_shield.bin yh_torch.bin yh_gun.bin` | `make_yharn.sh` | - |

### 4b. UI and pictures

| Output | How |
|---|---|
| `ui.bin` | `python3 assets/tools/convert_ui.py --tex assets/UI --out ui.bin` (HUD pieces and button art, searched by name) |
| `itemicons.bin` | `bash assets/tools/make_itemicons.sh` |
| `papericons.bin` | `python3 assets/tools/pack_icons.py papericons.bin T_IconFirePaper=<png>:128 T_IconBoltPaper=<png>:128` |
| `menuart.bin` | `python3 assets/tools/pack_icons.py menuart.bin M_Slot=<png>:96 M_TabItems=<png>:72 M_TabStatus=<png>:72 M_TabSystem=<png>:72` |
| `logo.bin` | `bash assets/tools/make_logo.sh` (needs `T_BloodbornePSXLogoShadow.png`) |
| `crosshair.bin` | `bash assets/tools/make_crosshair.sh` |
| `title.bin` | `python3 assets/tools/pack_rgba.py <title picture>.png title.bin 588 330` |
| `dlgfont.bin` (subtitle font) | `python3 assets/tools/make_dlgfont.py <bold serif>.ttf dlgfont.bin 48` (untested; the game works without it using a plain capitals font) |

`lamp_tex.bin` is created by the game itself the first time it runs.

### 4c. Maps

```
bash assets/tools/convert_all_maps.sh          # every MP_*.usda -> level_<map>.bin + interact_<map>.bin + floor_<map>.bin (logs in convert_logs/)
bash assets/tools/convert_basement.sh          # then the maps that need special handling:
bash assets/tools/convert_bossarena.sh
bash assets/tools/convert_cleric.sh
bash assets/tools/convert_sickroom.sh
python3 assets/tools/make_links.py assets/Maps links.txt     # which door goes where (or use data/links.txt)
python3 assets/tools/extract_notes.py                         # notes_<map>.txt (messenger texts)
python3 assets/tools/extract_map_props.py <game>.pak map_props.json    # BEFORE convert_all_maps.sh: bakes door locks / pickup contents in
python3 assets/tools/extract_volumes.py <game>.pak            # volumes_<map>.txt (or unzip data/volumes_all.zip)
```
Order: run `extract_map_props.py` first (so `convert_level.py` finds `map_props.json` beside it in `assets/tools/`), then convert the maps.
Check each map's line in `convert_logs/SUMMARY.txt` for missing textures.

### 4d. Sound (`snd/`)

`convert_sound.py scan <export dir>` lists every audio file; `convert_sound.py build <export dir> snd data/map.txt` converts the slots named in `data/map.txt` to `snd/<name>_1.wav` (48 kHz mono 16-bit).
Special mixes: `make_gascut_audio.sh`, `make_hdintro_audio.sh`, `make_eileen_vo.sh`.
Voice clips for Gehrman (`gh_l1_1.wav` ... `gh_l5_1.wav`), Eileen's laugh (`e_laugh_1.wav`) and the Hunter's Dream intro (`mus_hdintro.wav`) are not produced by a script here: any 22.05-48 kHz mono 16-bit WAV with that name works (Gehrman's five are his offer lines 1-4 and the refusal speech).

### 4e. Settings and tuning

Copy `data/*` into the data folder: `config.txt` (`resolution = halfhud`), `links.txt`, `interior.txt`, `credits.txt`, `levers/`, `poison/`, `item_descriptions.txt`, `npc_dialogue.txt` (reference text), `volumes_all.zip` (unzip it).
Panel and texture-swap fixes for every map are baked into `main.c`; to bake new ones use `embed_map_defaults.py main.c <folder holding your panels_*.txt / texswap_*.txt>`.

### 4f. Check you have everything

```
python3 assets/tools/check_data.py ~/bbpsx-vita/main.c <your data folder>
```
It lists missing required files (the `.txt` tuning files are optional). Expect the voice clips above to show if you have not made them: the game runs without them.

## 5. Install and play

1. Install `bbpsx.vpk`.
2. Copy the data folder to `ux0:data/bbpsx/` (create it if needed).
3. Make sure `ur0:/data/libshacccg.suprx` exists, then launch.
4. Saves go in the same folder: `save.bin`, `lastpos.txt`, `ladders.txt` (slot 2 and 3 add `_2` / `_3`) and `slot.txt`.

To hand the data to other people, `make_release_data.sh SRC DEST` copies a working data folder minus saves, logs, debug switches and the removed kart race.

## 6. Known gaps

* `hunter.bin`: `make_hunter.sh` was reconstructed from the finished file (the author's original command was not saved), so weapon and pistol placement may need small tweaks; `inspect_bin.py` prints a built file's header to compare.
* The kart race was removed from the game; its scripts are left out.
* `src/CMakeLists.txt` is the author's working file (VitaSDK + vitaGL + vitashark). If your VitaSDK names a library differently, change the `target_link_libraries` list.
* The format of every `.bin` file is described in the header of the script that makes it, and each loader is in `main.c` (search the file name).
