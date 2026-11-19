#!/bin/bash
# Turns the voice clips you picked from YOUR OWN copy of the game into the files the game plays.
#   bash voice_pack.sh <folder with your clips> <output folder>
# In the input folder name each clip after its slot:   doll_5.wav  doll_5.ogg  gh_l1.wav  e_oh.flac  ...   (see docs/OWNERS_EXTRAS.md for the slot list).
# Every clip becomes <slot>_1.wav: mono, 22.05 kHz, 16-bit, loudest sample at about -9 dB. Copy the output folder's files to ux0:data/bbpsx/snd/.  Needs ffmpeg.
IN="${1:?input folder}"; OUT="${2:?output folder}"; mkdir -p "$OUT"
command -v ffmpeg >/dev/null || { echo "ffmpeg not found"; exit 1; }
for f in "$IN"/*; do
  b=$(basename "$f"); s="${b%.*}"; case "$s" in doll_*|gh_l*|e_*|mus_*) ;; *) echo "skipped (not a slot name): $b"; continue;; esac
  case "$s" in mus_*) rate=24000;; *) rate=22050;; esac
  ffmpeg -y -loglevel error -i "$f" -ac 1 -ar $rate -af "alimiter=limit=0.8:level=disabled,volume=-1dB" -c:a pcm_s16le "$OUT/${s}_1.wav" && echo "$s -> $OUT/${s}_1.wav"
done
