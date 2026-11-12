#!/bin/bash
# Run this ON YOUR OWN MACHINE (where the project was built) to add the pieces a stranger's build needs and that
# only exist in your project folder / shell history. Output goes into ./extras next to this script's kit.
#   bash collect_kit.sh [PROJECT_DIR=~/bbpsx-vita] [OUT=./extras]
P="${1:-$HOME/bbpsx-vita}"; OUT="${2:-./extras}"
mkdir -p "$OUT/sce_sys" "$OUT/tools_extra"
[ -f "$P/CMakeLists.txt" ] && cp -v "$P/CMakeLists.txt" "$OUT/CMakeLists.txt" || echo "no $P/CMakeLists.txt"
[ -d "$P/sce_sys" ] && cp -rv "$P/sce_sys/." "$OUT/sce_sys/" || echo "no $P/sce_sys (icon / LiveArea art)"
# every converter command you ever ran (the hunter.bin / weapons.bin / sky / ui builds were typed by hand)
history -r ~/.bash_history 2>/dev/null
grep -hE "convert_(hunter|weapons|ui|level|attire|hanims|sound)\.py|embed_map_defaults|make_[a-z_]+\.sh" ~/.bash_history 2>/dev/null | awk '!seen[$0]++' > "$OUT/commands_you_ran.txt"
echo "$(wc -l < "$OUT/commands_you_ran.txt") commands saved to $OUT/commands_you_ran.txt (read it through: remove anything private before sharing)"
# every extra script in the project's tools folder that is not in this kit
for f in "$P"/assets/tools/*; do [ -f "$f" ] && cp -n "$f" "$OUT/tools_extra/"; done
echo "done. Add the extras folder to the kit before you zip it."
