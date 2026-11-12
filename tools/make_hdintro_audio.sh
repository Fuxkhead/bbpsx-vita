#!/bin/bash
# Hunter's Dream intro sounds (the foley of the sequence: body movement + stone footsteps) mixed at their start times into ONE file, mus_hdintro.wav (24 kHz mono 16-bit, 30 s).  usage: bash make_hdintro_audio.sh
cd ~/bbpsx-vita || exit 1
mkdir -p snd_hdintro
ARGS=(); FILT=""; N=0; MISS=0; MIX=""
add() {   # exact-name  start-seconds  gain
  F=$(find assets -iname "$1.ogg" -o -iname "$1.wav" | head -1)
  if [ -z "$F" ]; then echo "NOT FOUND: $1"; MISS=$((MISS+1)); return; fi
  MS=$(python3 -c "print(int($2*1000))")
  ARGS+=(-i "$F"); FILT="$FILT[$N:a]aresample=24000,aformat=channel_layouts=mono,volume=$3,adelay=${MS}[a$N];"; MIX="$MIX[a$N]"; N=$((N+1)); echo "$1 @ $2 s <- $F"
}
add A_body-lobe-b1         2.7333   0.2
add A_body-lobe-b2         11.0333  0.2
add A_foot_stone_run_dry2  11.7333  1.0
add A_body-lobe-b1         12.9333  0.2
add A_foot_stone_run_dry1  15.5667  1.0
add A_foot_stone_run_dry2  17.4333  0.8
add A_foot_stone_run_dry0  19.3333  0.6
[ $N -eq 0 ] && { echo "nothing found"; exit 1; }
ffmpeg -y -loglevel error "${ARGS[@]}" -filter_complex "${FILT}${MIX}amix=inputs=$N:normalize=0:duration=longest,apad=whole_dur=30,atrim=0:30,alimiter=limit=0.95[o]" -map "[o]" -ar 24000 -ac 1 -sample_fmt s16 snd_hdintro/mus_hdintro.wav && ls -l snd_hdintro
echo "missing: $MISS   -> copy snd_hdintro/mus_hdintro.wav to ux0:data/bbpsx/snd/"
