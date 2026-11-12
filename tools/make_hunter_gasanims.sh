#!/bin/bash
# adds Gascoigne's Countered + 1HVisceraled animations to hunter.bin (re-runs your last hunter.bin build with one extra --psa folder)
cd ~/bbpsx-vita || exit 1
G=assets/Char/Bosses/Gascoigne/Anim
mkdir -p assets/Char/Hunter/GasAnim
cp -v $G/AnimGas_Countered.psa $G/AnimGas_1HVisceraled.psa assets/Char/Hunter/GasAnim/ || exit 1
CMD=$(grep -h "convert_hunter.py.*SkM_AttireHunter.psk.*--out hunter.bin" ~/.bash_history | grep -v GasAnim | tail -1)
if [ -z "$CMD" ]; then echo "couldn't find your last hunter.bin build command in the history - run 'history -a' first, or paste the command to me"; exit 1; fi
CMD="${CMD/--psa assets\/Char\/Hunter\/Export/--psa assets/Char/Hunter/GasAnim assets/Char/Hunter/Export}"
case "$CMD" in *GasAnim*) ;; *) echo "couldn't insert the extra folder - paste your hunter.bin command to me"; exit 1;; esac
cp -v hunter.bin hunter_before_gasanims.bin 2>/dev/null
echo "$CMD" | cut -c1-200
eval "$CMD" | tail -5
ls -l hunter.bin
