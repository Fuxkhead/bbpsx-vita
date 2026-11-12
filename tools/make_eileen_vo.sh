#!/bin/bash
# Eileen's three spoken lines -> ux0 sound files (e_oh_1.wav, e_mess_1.wav, e_welcome_1.wav), 48 kHz mono 16-bit.   usage: ./make_eileen_vo.sh
cd ~/bbpsx-vita || exit 1
mkdir -p snd_eileen
conv() {   # slot  filename-fragment  [variant number]
  F=$(find assets -iname "*$2*" \( -iname '*.wav' -o -iname '*.ogg' -o -iname '*.flac' -o -iname '*.mp3' \) | head -1)
  if [ -z "$F" ]; then echo "NOT FOUND: $2  (the audio for it isn't exported - it is in assets/Audio/VO/Eileen in the pak)"; return; fi
  ffmpeg -y -loglevel error -i "$F" -ar 48000 -ac 1 -sample_fmt s16 "snd_eileen/$1_${3:-1}.wav" && echo "$1_${3:-1} <- $F"
}
conv e_oh        A_Eileen1_OhAHunter
conv e_mess      A_Eileen2_WhatAMess
conv e_welcome   A_Eileen3_HereWelcomeNewHunter
# her fight voice (used by the hostile Eileen): several variants per slot
conv e_aggro  A_EileenAggro1 1;  conv e_aggro  A_EileenAggro2 2
conv e_taunt  A_EileenBoss1_whatgood 1;  conv e_taunt  A_EileenBoss2_yourblood 2;  conv e_taunt  A_EileenBoss3_ahuntersblood 3
conv e_taunt  A_EileenBoss6_enoughofthisdream 4;  conv e_taunt  A_EileenBoss7_laugh 5
conv e_kill   A_EileenKillYou1 1;  conv e_kill   A_EileenKillYou2 2;  conv e_kill   A_EileenBossKillYou1_lookatyou 3;  conv e_kill   A_EileenBossKillYou2_yourenodifferent 4
conv e_death  A_EileenDeath 1;  conv e_death  A_EileenBossdeath2_allhuntersmustdie 2
conv e_laugh A_EileenBoss7_laugh 1
ls -l snd_eileen
echo "Copy snd_eileen/*.wav to ux0:data/bbpsx/snd/"
