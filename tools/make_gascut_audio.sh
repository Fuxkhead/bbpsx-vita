#!/bin/bash
# Gascoigne intro soundtrack: the sequence's music + voice lines mixed at their start times into ONE file, mus_gascut_1.wav (24 kHz mono 16-bit, 46.3 s).  usage: ./make_gascut_audio.sh
cd ~/bbpsx-vita || exit 1
mkdir -p snd_gascut
ARGS=(); FILT=""; N=0; MISS=0
add() {   # name-fragment  start-seconds  gain
  F=$(find assets -iname "*$1*" \( -iname '*.wav' -o -iname '*.ogg' -o -iname '*.flac' -o -iname '*.mp3' \) | head -1)
  if [ -z "$F" ]; then echo "NOT FOUND: $1"; MISS=$((MISS+1)); return; fi
  MS=$(python3 -c "print(int($2*1000))")
  ARGS+=(-i "$F"); FILT="$FILT[$N:a]aresample=24000,aformat=channel_layouts=mono,volume=$3,adelay=${MS}[a$N];"; MIX="$MIX[a$N]"; N=$((N+1)); echo "$1 @ $2 s <- $F"
}
MIX=""
add A_TheHunterCutscene   0        0.55
add A_blood_com2          1.4333   1.0
add A_blood_com1          7.0667   1.0
add A_GasScene_Slice1     12.3333  1.0
add A_GasScene_Slice2     18.4     1.0
add A_GasDia_SceneExhale1 23.2     1.0
add A_GasDia_SceneExahle2 25.2333  1.0
add A_GasDia_SceneExahle3 27.2     1.0
add A_Gas_Exhale          40.3333  1.0
[ $N -eq 0 ] && { echo "nothing found"; exit 1; }
ffmpeg -y -loglevel error "${ARGS[@]}" -filter_complex "${FILT}${MIX}amix=inputs=$N:normalize=0:duration=longest,atrim=0:46.3,alimiter=limit=0.95[o]" -map "[o]" -ar 24000 -ac 1 -sample_fmt s16 snd_gascut/mus_gascut_1.wav && ls -l snd_gascut
echo "missing: $MISS   -> copy snd_gascut/mus_gascut_1.wav to ux0:data/bbpsx/snd/"
