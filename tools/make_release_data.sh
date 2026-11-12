#!/bin/bash
# Builds a clean copy of the Bloodborne PSX Vita data folder for handing out.
# Your working folder is NOT touched. Usage:  bash make_release_data.sh [SRC] [DEST]
SRC="${1:-/run/media/deck/USD00/bbpsx}"
DEST="${2:-/run/media/deck/USD00/bbpsx_release}"
[ -d "$SRC" ] || { echo "no such folder: $SRC"; exit 1; }
rm -rf "$DEST"; mkdir -p "$DEST" || exit 1
cp -r "$SRC"/. "$DEST"/ || exit 1
cd "$DEST" || exit 1
shopt -s nullglob

# 1. kart race (feature removed)
rm -f kart.bin karts.bin hunter_kart.bin kart_seat*.txt kartpath_*.txt
rm -f floor_kart_* interact_kart_* breakables_kart_* level_kart_* sky_kart_* volumes_kart_*

# 2. maps that no link reaches (test rooms, templates, old arena, menu stubs)
for m in arena coreytestroom mainmenu ps1intro template test testrooma testroomb; do
  rm -f level_$m.bin floor_$m.bin interact_$m.bin sky_$m.bin breakables_$m.txt volumes_$m.txt \
        fog_$m.txt panels_$m.txt levers_$m.txt notes_$m.txt lamp_$m.txt dark_$m.txt poison_$m.txt
done

# 3. your saves, position, logs
rm -f save*.bin slot.txt lastpos*.txt ladders*.txt maplog.txt snd_log.txt splash_log.txt

# 4. test / debug switches
rm -f crackdbg.txt cut_test.txt gascut_test.txt hd_test.txt frenzy_test.txt alllamps.txt no_trails.txt

# 5. build tools, scripts, source, backups, archives
rm -rf tools
rm -f *.py *.sh *.tgz *.zip *.png *.part *.bak *.old *.c *.h CMakeLists.txt
rm -f hunter_before_gasanims.bin hunter_before_retex.bin henrykkkkk.bin
rm -f arena_convert.txt bb_convert.txt gas_files.txt gas_info.txt sound_list.txt weapons_list.txt weapons_rest.txt map.txt

# 6. old tuning files nothing reads any more
rm -f chair_z.txt doll_pos.txt gilb_bed.txt grave_pos.txt dark_hunter.txt shade.txt lefty.txt
rm -f switch_gilbert.txt switch_streets1.txt

echo "Done. $(ls -1 | wc -l) files, $(du -sh . | cut -f1) in $DEST"
echo "Kept as your tuned defaults (edit or delete if you want the built-in ones): config.txt dark.txt fog_k.txt crt.txt light.txt light_amb.txt res3d.txt stick_noy.txt audio.txt ambient.txt"
