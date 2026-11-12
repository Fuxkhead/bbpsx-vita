#!/bin/bash
# Packs the built eboot into a release VPK. Run AFTER a successful `make` in ~/bbpsx-vita/build.
# Usage: bash make_vpk.sh [PROJECT_DIR] [OUT.vpk]
P="${1:-$HOME/bbpsx-vita}"
OUT="${2:-$HOME/Downloads/bbpsx.vpk}"
B="$P/build"
[ -f "$B/eboot.bin" ] || { echo "no $B/eboot.bin - run make first"; exit 1; }
[ -f "$B/param.sfo" ] || { echo "no $B/param.sfo - run make first"; exit 1; }
ARGS=(-s "$B/param.sfo" -b "$B/eboot.bin")
S="$P/sce_sys"
add() { [ -f "$S/$1" ] && { ARGS+=(-a "$S/$1=sce_sys/$1"); echo "  + sce_sys/$1"; } || echo "  - missing sce_sys/$1 (skipped)"; }
add icon0.png
add pic0.png
add livearea/contents/bg0.png
add livearea/contents/startup.png
add livearea/contents/template.xml
rm -f "$OUT"
vita-pack-vpk "${ARGS[@]}" "$OUT" || exit 1
echo "Wrote $OUT ($(du -h "$OUT" | cut -f1))"
echo "Players also need: the bbpsx_release folder copied to ux0:data/bbpsx/ and libshacccg.suprx installed (ur0:/data/)."
