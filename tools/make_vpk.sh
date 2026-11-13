#!/bin/bash
# Packs the built eboot into a release VPK. Run AFTER a successful `make` in ~/bbpsx-vita/build.
# Usage: bash make_vpk.sh [PROJECT_DIR] [OUT.vpk]
P="${1:-$HOME/bbpsx-vita}"
OUT="${2:-$HOME/Downloads/bbpsx.vpk}"
B="$P/build"
EBOOT="$B/eboot.bin"; [ -f "$EBOOT" ] || EBOOT=$(ls "$B"/*.self 2>/dev/null | head -1)      # the CMake build makes <name>.self; the VPK stores it as eboot.bin
SFO="$B/param.sfo"; [ -f "$SFO" ] || SFO=$(find "$B" -maxdepth 2 -name "*param.sfo" 2>/dev/null | head -1)      # the CMake build names it <name>.vpk_param.sfo
[ -f "$EBOOT" ] || { echo "no eboot.bin / *.self in $B - run make first. Found:"; ls "$B"; exit 1; }
[ -f "$SFO" ] || { echo "no param.sfo in $B - run make first. Found:"; ls "$B"; exit 1; }
echo "  eboot: $EBOOT"; echo "  param.sfo: $SFO"
ARGS=(-s "$SFO" -b "$EBOOT")
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
