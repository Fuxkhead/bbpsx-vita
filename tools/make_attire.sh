#!/bin/bash
# Builds attire.bin: the Hunter's other body outfits and hats.   usage: ./make_attire.sh [extra convert_attire.py options, e.g. --hatoff 0,2,157]
cd ~/bbpsx-vita || exit 1
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_attire*.py | head -1)" assets/tools/convert_attire.py
# (kit) disabled: copied a tool from ~/Downloads - the kit has the tools already: cp "$(ls -t ~/Downloads/convert_hanims*.py | head -1)" assets/tools/convert_hanims.py 2>/dev/null
PSK=$(find assets -name "SkM_AttireHunter.psk" | head -1)
[ -f hunter.bin ] || { echo "hunter.bin not found in ~/bbpsx-vita"; exit 1; }
mkdir -p convert_logs
python3 assets/tools/convert_attire.py --hunter "$PSK" --hunterbin hunter.bin --root assets/Char/Hunter --tex assets/Cine --out attire.bin "$@" 2>&1 | tee convert_logs/attire.txt | grep -E "skin bones|<-|material|bind-pose|hat size|skipped|WARNING|wrote|could not|Error|Traceback|weights"
ls -l attire.bin
echo "Copy attire.bin to ux0:data/bbpsx/"
