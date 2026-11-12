#!/bin/bash
# converts every map in assets/Maps (MP_*.usda) to level_<name>.bin + interact_<name>.bin + floor_<name>.bin in ~/bbpsx-vita
# full logs: ~/bbpsx-vita/convert_logs/<name>.txt ; a texture summary per map is printed here and saved to convert_logs/SUMMARY.txt
cd ~/bbpsx-vita || exit 1
mkdir -p convert_logs
: > convert_logs/SUMMARY.txt
find assets/Maps -name 'MP_*.usda' | sort | while read -r f; do
  b=$(basename "$f" .usda); n=$(echo "$b" | tr 'A-Z' 'a-z'); n=${n#mp_}; n=${n#cy_}; n=${n#ys_}
  {
  echo "=== $b -> level_$n.bin"
  python3 assets/tools/convert_level.py --assets ~/bbpsx-vita/assets --map "${f#assets/}" --out ~/bbpsx-vita/level_$n.bin --skip SkyBox --skip Cube --skip WindowShaft --skip SM_Card --skip LightShaft > convert_logs/$n.txt 2>&1
  if [ $? -ne 0 ]; then echo "   FAILED - see convert_logs/$n.txt"; tail -n 3 convert_logs/$n.txt; continue; fi
  grep -E "^wrote|textures:|floor materials|level loaders|collision triangles|WARNING: no PlayerStart" convert_logs/$n.txt | sed 's/^/   /'
  u=$(awk '/^UNTEXTURED PARTS/{f=1;next} /^$/{f=0} f' convert_logs/$n.txt | wc -l)
  m=$(awk '/^MISSING MATERIAL FILES/{f=1;next} /^$/{f=0} f' convert_logs/$n.txt | wc -l)
  t=$(awk '/^MISSING\/UNREADABLE TEXTURES/{f=1;next} /^$/{f=0} f' convert_logs/$n.txt | wc -l)
  echo "   untextured parts: $u   missing material files: $m   missing textures: $t"
  } | tee -a convert_logs/SUMMARY.txt
done
echo; ls -l level_*.bin 2>/dev/null | awk '{print $5, $9}'
echo; echo "Copy to the Vita (ux0:data/bbpsx/): level_*.bin interact_*.bin floor_*.bin"
