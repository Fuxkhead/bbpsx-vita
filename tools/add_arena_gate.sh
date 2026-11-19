#!/bin/bash
# Makes the closed gate at the top of the Gascoigne arena's stairs lead to the Oedon Chapel.   usage: bash assets/tools/add_arena_gate.sh
# The closed gate becomes a working gate: press X on it to open it, then walk through the dark panel to travel.
# The gate (two SM_EnvPlane with MI_Gate1 at x 3.6..8.6 m, y 59.9 m, floor z 10 m in the map) gets a loader in front of it; the chapel's stairway panel links back to it.
cd ~/bbpsx-vita || exit 1
CARD=/run/media/deck/USD00/Data/bbpsx
f=$(find assets/Maps -iname 'MP_GascoigneArena.usda' | head -1)
[ -n "$f" ] || { echo "MP_GascoigneArena.usda not found under assets/Maps"; exit 1; }
[ -f "$f.orig" ] || cp "$f" "$f.orig"
if ! grep -q 'def Scope "BP_LevelLoader_3"' "$f"; then
python3 - "$f" <<'PY' || exit 1
import sys
p = sys.argv[1]; s = open(p).read().rstrip()
loader = '''
    def Scope "BP_LevelLoader_3"

    {
        def Xform "DefaultSceneRoot"
        {
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]
            float3 xformOp:translate = (606, 6000, 1000)
            quatf xformOp:orient = (0, 0, 0, 1)
            float3 xformOp:scale = (1, 1, 1)
            
            def Xform "Box"
            {
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]
                float3 xformOp:translate = (0, 0, 195)
                quatf xformOp:orient = (1, 0, 0, 0)
                float3 xformOp:scale = (1, 1, 1)
            }
            
            def Xform "EntranceVector"
            {
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]
                float3 xformOp:translate = (0, 330, 0)
                quatf xformOp:orient = (0.7071068, 0, 0, -0.7071068)
                float3 xformOp:scale = (1, 1, 1)
            }
        }
    }
'''
# the map ends with the closing brace of its top scope: put the loader just inside it
if not s.endswith('}'): sys.exit('unexpected end of file')
open(p, 'w').write(s[:-1].rstrip() + '\n' + loader + '}\n')
print('loader BP_LevelLoader_3 added to', p)
PY
fi
# the gate itself becomes a working gate (a BP_DoorBig like the courtyard gate in front of Gilbert's house: press X on it to open it): the two static gate planes and any earlier wooden door are taken out
if ! grep -q 'def Scope "BP_DoorBig_ChapelGate"' "$f"; then
cat > /tmp/chapel_gate_big.txt <<'DOOREOF'
    def Scope "BP_DoorBig_ChapelGate"
    {
        def Xform "DefaultSceneRoot"
        {
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]
            float3 xformOp:translate = (606, 5994, 1000)
            quatf xformOp:orient = (0.7071068, 0, 0, -0.7071068)
            float3 xformOp:scale = (1, 1, 1)
            
            def Mesh "SM_DoorL" (
                prepend references = @../../Env/General/Mesh/SM_EnvPlane.usda@
            )
            {
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]
                float3 xformOp:translate = (0, -250, 0)
                quatf xformOp:orient = (0.0530181, 0.05301811, 0.7051164, 0.7051163)
                float3 xformOp:scale = (0.5, 1.15, 0.1)
                
                def Scope "OverrideMaterials"
                {
                    def Material "MI_Gate1" (
                        prepend references = @../../Env/Yharnam/Mat/MI_Gate1.usda@
                    )
                    {
                    }
                }
                
                over GeomSubset "Section_0" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    rel material:binding = </MP_GascoigneArena/BP_DoorBig_ChapelGate/DefaultSceneRoot/SM_DoorL/OverrideMaterials/MI_Gate1>
                }
            }
            
            def Mesh "SM_DoorR" (
                prepend references = @../../Env/General/Mesh/SM_EnvPlane.usda@
            )
            {
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]
                float3 xformOp:translate = (0, 250, 0)
                quatf xformOp:orient = (0.0530181, 0.05301811, -0.7051164, -0.7051163)
                float3 xformOp:scale = (0.5, 1.15, -0.1)
                
                def Scope "OverrideMaterials"
                {
                    def Material "MI_Gate1" (
                        prepend references = @../../Env/Yharnam/Mat/MI_Gate1.usda@
                    )
                    {
                    }
                }
                
                over GeomSubset "Section_0" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    rel material:binding = </MP_GascoigneArena/BP_DoorBig_ChapelGate/DefaultSceneRoot/SM_DoorR/OverrideMaterials/MI_Gate1>
                }
            }
            
            def Xform "Arrow"
            {
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]
                float3 xformOp:translate = (-34.80553, 50, 104.33882)
                quatf xformOp:orient = (1.6252175E-06, -1.13249E-06, 1.0877842E-06, -1)
                float3 xformOp:scale = (1, 0.99999994, 1)
            }
            
            def Xform "Arrow1"
            {
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]
                float3 xformOp:translate = (120.74875, 50, 104.33794)
                quatf xformOp:orient = (1.9470718E-07, 5.9604645E-08, 2.2521675E-08, 1)
                float3 xformOp:scale = (1, 0.99999994, 1)
            }
            
            def Xform "InsightCounter1"
            {
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]
                float3 xformOp:translate = (15, -0, 180)
                quatf xformOp:orient = (1, -0, -0, -0)
                float3 xformOp:scale = (1, 1, 1)
            }
            
            def Xform "InsightCounter2"
            {
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]
                float3 xformOp:translate = (-15, -0, 180)
                quatf xformOp:orient = (-4.371139E-08, -0, 0, -1)
                float3 xformOp:scale = (1, 1, 1)
            }
            
            def Xform "NavLink"
            {
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]
                float3 xformOp:translate = (-6.228685E-05, 45.658573, 0.0005493164)
                quatf xformOp:orient = (1, -0, -0, -0)
                float3 xformOp:scale = (1, 1, 1)
            }
        }
    }
DOOREOF
python3 - "$f" <<'PY' || exit 1
import sys, re
p = sys.argv[1]; s = open(p).read(); door = open('/tmp/chapel_gate_big.txt').read()
for nm in ('SM_EnvPlane2_2', 'SM_EnvPlane3', 'BP_Doors3_ChapelGate'):
    s, n = re.subn(r'\n    def Scope "%s"\n(?:.*\n)*?    }\n' % nm, '\n', s, count=1)
    print('removed', nm, n)
s = s.rstrip()
if not s.endswith('}'): sys.exit('unexpected end of file')
open(p, 'w').write(s[:-1].rstrip() + '\n' + door + '\n}\n')
print('gate BP_DoorBig_ChapelGate added to', p)
PY
fi
python3 assets/tools/convert_level.py --assets ~/bbpsx-vita/assets --map "${f#assets/}" --out ~/bbpsx-vita/level_gascoignearena.bin --skip SkyBox --skip Cube --skip WindowShaft --skip SM_Card --skip LightShaft 2>&1 | tee convert_logs/gascoignearena.txt | grep -E "^wrote|loader|level loaders|collision triangles|Error|Traceback"
ls -l level_gascoignearena.bin interact_gascoignearena.bin floor_gascoignearena.bin sky_gascoignearena.bin 2>/dev/null
mkdir -p $CARD/backup_arena; for b in level interact floor sky; do [ -f $CARD/${b}_gascoignearena.bin ] && cp -n $CARD/${b}_gascoignearena.bin $CARD/backup_arena/; done
cp -v level_gascoignearena.bin interact_gascoignearena.bin floor_gascoignearena.bin $CARD/ 2>/dev/null
[ -f sky_gascoignearena.bin ] && cp -v sky_gascoignearena.bin $CARD/
# the dark see-through panel just behind the gate, like the other map links (centre x y z, width, height, turn; metres); added to the arena's panels file only once
grep -qs "^6.060 60.100 " $CARD/panels_gascoignearena.txt || echo "6.060 60.100 13.000 5.400 6.200 0.0000" >> $CARD/panels_gascoignearena.txt
# links: the chapel's stairway panel <-> the arena gate (the old chapel line pointed at the arena's Boulder Bridge door)
sed -i '/^oedonchapel:BP_LevelLoader_2 *=/d' $CARD/links.txt
grep -q '^gascoignearena:BP_LevelLoader_3' $CARD/links.txt || echo "gascoignearena:BP_LevelLoader_3 = oedonchapel:BP_LevelLoader_2" >> $CARD/links.txt
grep -n "gascoignearena\|oedonchapel" $CARD/links.txt
echo "done. (The arena's old files are in $CARD/backup_arena; the original map is kept as $f.orig)"
