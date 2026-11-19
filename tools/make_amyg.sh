#!/bin/bash
# Builds the Amygdala's two models and copies them to the card:
#   amyg.bin  = as he starts (now with the ArmTear animation he plays at 30% health)
#   amyg2.bin = after it: the two torn arms carried in his front hands as clubs
# Each model takes several minutes to build (both are built at the same time).
set -e
TEX=${1:-512}      # texture size: bash make_amyg.sh 512 (default), 256 (the old size) or 1024 (sharpest, but 3 MB more memory per model)
A=~/bbpsx-vita/assets; T=~/bbpsx-vita/assets/tools; CARD=/run/media/deck/USD00/Data/bbpsx
U=$(find "$A" -name 'SM_Amyg2.usd*' | head -n 1)
if [ -z "$U" ]; then echo "SM_Amyg2.usda not found under $A"; exit 1; fi
echo "mesh: $U"
mkdir -p ~/bbpsx-vita/build/amyg; cd ~/bbpsx-vita/build/amyg
python3 "$T/make_amyg.py" --usda "$U" --tex "$A" --maxtex $TEX --upscale 1 --out amyg.bin > amyg.log 2>&1 &
python3 "$T/make_amyg.py" --usda "$U" --tex "$A" --torn 1 --maxtex $TEX --upscale 1 --out amyg2.bin > amyg2.log 2>&1 &
wait
tail -n 1 amyg.log; tail -n 1 amyg2.log
grep -h "texture" amyg.log || true
if [ -d "$CARD" ]; then cp amyg.bin amyg2.bin "$CARD/"; echo "copied amyg.bin and amyg2.bin to the card"; else echo "card not found at $CARD: copy ~/bbpsx-vita/build/amyg/amyg.bin and amyg2.bin to ux0:data/bbpsx/ yourself"; fi
