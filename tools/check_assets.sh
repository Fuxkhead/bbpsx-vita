#!/bin/bash
# Usage: bash check_assets.sh   (run inside the container)
A=~/bbpsx-vita/assets
echo "=== needed meshes: found as .glb vs missing ==="
while read -r n; do
  if find "$A" -iname "$n.glb" | grep -q .; then echo "OK       $n"; else echo "MISSING  $n"; fi
done <<'NAMES'
Cube
SM_Card
SM_ChainStraightSingle
SM_CoffinMetal
SM_DeadBody1
SM_DoorSmall
SM_DoorframeDouble
SM_EnvCorner10A
SM_EnvCorner10B
SM_EnvPlane
SM_EnvPlaneHalfHori
SM_EnvPlaneHalfVert
SM_EnvPlaneLight
SM_EnvPlaneMirror45Alt
SM_EnvPlaneMirrorVert
SM_EnvPlaneQuarter
SM_Pillar
SM_Pyre
SM_SewerArchTall
SM_SewerArchway23Way
SM_SewerArchway2Corner
SM_SewerArchway2Decline
SM_SewerArchway2Junction
SM_SewerArchway2Straight
SM_SewerBridge
SM_SewerWallCorner
SM_SewerWallCornerShort
SM_SkyBoxTowerWarp
SM_Sphere
SM_Stairs1
SM_Stairs1_EndCap
SM_StairsFill
SM_StorageBags
SM_StorageBagsSm
SM_WoodBeam2
SM_WoodBeam2B
SM_ladder_segment
SM_ladder_top
SM_ladder_top_step
NAMES
echo
echo "=== all .glb files and sizes ==="
find "$A" -name '*.glb' -exec ls -lh {} \; | awk '{print $5, $9}' | sed "s|$A/||"
