#!/usr/bin/env python3
"""bbpsx_unused.py - lists what is in your ux0:data/bbpsx folder that this build of the game never reads.
Usage:  python3 bbpsx_unused.py /run/media/deck/3442-9D77/data/bbpsx          (only lists)
        python3 bbpsx_unused.py /run/media/deck/3442-9D77/data/bbpsx --move   (moves the listed files into a _unused folder inside it; nothing is deleted)
Save files are never listed: save*.bin, story*.txt, ladders*.txt, lastpos*.txt, slot.txt. Built from main.c 2026-11-20t (v2: also knows the model files loaded through name tables)."""
import os, re, sys, fnmatch
root = sys.argv[1]; move = '--move' in sys.argv
KNOWN = set(['aimzoom.txt', 'alllamps.txt', 'allweapons.txt', 'ambient.txt', 'amyg.bin', 'amyg2.bin', 'amyg_dead.txt', 'anims.txt', 'attire.bin', 'audio.txt', 'audio_fx_off.txt', 'autores_off.txt', 'axe_boff.txt', 'axe_slide.txt', 'bt_item.txt', 'burial.txt', 'burial_now.txt', 'cb_easy.txt', 'cb_gate_h.txt', 'cb_land.txt', 'cb_nointro.txt', 'cb_spawn.txt', 'chair_dz.txt', 'cine_off.txt', 'clericbeast.bin', 'config.txt', 'config.txt.', 'corpse_dz.txt', 'crackdbg.txt', 'credits.txt', 'crosshair.bin', 'crow.bin', 'crowdog.bin', 'crt.txt', 'cut_test.txt', 'dark.txt', 'dlgfont.bin', 'dogcrow.bin', 'dograt.bin', 'doll.bin', 'dream_amyg.txt', 'dream_amyg_front.txt', 'dream_amyg_test.txt', 'dream_sky.txt', 'eileen.bin', 'eileen_noblades.txt', 'enemy.bin', 'extra_spawns.txt', 'fbflip.txt', 'fog_dist.txt', 'fog_k.txt', 'fps.txt', 'free_doors.txt', 'frenzy_test.txt', 'gas.bin', 'gasbeast.bin', 'gascut_test.txt', 'gb_easy.txt', 'gb_gate.txt', 'gehr.bin', 'gehr_test.txt', 'gehrman.bin', 'gh_death.txt', 'gh_easy.txt', 'gh_grip.txt', 'gh_half.txt', 'gh_keepadj.txt', 'gi_cfg.txt', 'gi_chair.bin', 'giantpig.bin', 'gilb.bin', 'givekey.txt', 'granter.bin', 'grow.txt', 'hat_off.txt', 'hat_tune.txt', 'hd_cfg.txt', 'hd_music.txt', 'hd_test.txt', 'hearing.txt', 'henryk.bin', 'hood_cfg.txt', 'house_fire.txt', 'house_fire_skip.txt', 'hunter.bin', 'hunter_anims.bin', 'hunter_anims2.bin', 'hunter_anims3.bin', 'hunter_cine.bin', 'hunter_layers.txt', 'insight_shop.txt', 'interact.bin', 'interact_ic_firstfloorsickroom.bin', 'interior.txt', 'interior_bg.txt', 'intro_cam.txt', 'intro_log.txt', 'intro_room.txt', 'intro_test.txt', 'intro_yaw.txt', 'itemicons.bin', 'lad_dismount.txt', 'lad_top_trim.txt', 'lad_trim.txt', 'ladders.txt', 'ladders_2.txt', 'ladders_3.txt', 'lamp_tex.bin', 'lastpos.txt', 'lastpos_2.txt', 'lastpos_3.txt', 'ldr_dis.txt', 'lefty.txt', 'level_huntersdream.bin', 'level_ic_firstfloorsickroom.bin', 'level_moonarena.bin', 'level_romarena.bin', 'level_romlake.bin', 'lever_yaw.txt', 'light.txt', 'light_amb.txt', 'light_int.txt', 'light_off.txt', 'links.txt', 'log_on.txt', 'logo.bin', 'maplog.txt', 'mblur.txt', 'menuart.bin', 'messenger.bin', 'modes_messenger.txt', 'moon.bin', 'moon.txt', 'moon_atk_all.txt', 'moon_blood_az.txt', 'moon_glow.txt', 'moon_hold.txt', 'moon_ik.txt', 'moon_lantern.txt', 'moon_phase.txt', 'moon_pres.txt', 'moon_scale.txt', 'moonlight_now.txt', 'moonp1.bin', 'moonp2.bin', 'moonpres.bin', 'near.txt', 'no_trails.txt', 'noblood.txt', 'nointro.txt', 'noroom.txt', 'nowrapfix.txt', 'npc_spawn.txt', 'nudge.txt', 'papericons.bin', 'poison_cfg.txt', 'pos_on.txt', 'rabiddog.bin', 'rain.txt', 'rat.bin', 'res3d.txt', 'rom.bin', 'rom_now.txt', 'romchild.bin', 'romfog.txt', 'save.bin', 'save_2.bin', 'save_3.bin', 'shop_unlock_all.txt', 'sky_all.txt', 'sky_dark.txt', 'sky_drop_all.txt', 'sky_dump.txt', 'sky_sil.txt', 'sky_sil_on.txt', 'slot.txt', 'snap.txt', 'snapgrid.txt', 'snd_log.txt', 'splash_log.txt', 'stick_noy.txt', 'storage_pos.txt', 'story.txt', 'story_2.txt', 'story_3.txt', 'switch.bin', 'tbias.txt', 'title.bin', 'tomb_messenger.txt', 'toni_glow.txt', 'toni_off.txt', 'troll.bin', 'trollbrick.bin', 'ui.bin', 'volume.txt', 'volumes_off.txt', 'weap_tune.txt', 'weapons.bin', 'werepig.bin', 'werewolf.bin', 'wheelchair.bin', 'wheelchair.txt', 'wl.bin', 'wlg_face.txt', 'yh_board.bin', 'yh_gun.bin', 'yh_shield.bin', 'yh_torch.bin'])
SND = set(['aggro', 'amb_lamp', 'amb_rain', 'amb_water', 'amb_wind', 'beast_step', 'bell', 'boss_axe', 'boss_beast', 'boss_dash', 'boss_death', 'boss_growl', 'boss_hurt', 'boss_step', 'boss_swing', 'boss_swing_b', 'boss_yell', 'boulder', 'boulder_hit', 'bullet', 'cb_death', 'cb_howl', 'cb_hurt', 'cb_impact', 'cb_roar', 'cb_step', 'cb_swing', 'crow_atk', 'crow_death', 'dodge', 'doll_1', 'doll_10', 'doll_11', 'doll_12', 'doll_13', 'doll_14', 'doll_15', 'doll_16', 'doll_2', 'doll_3', 'doll_4', 'doll_5', 'doll_6', 'doll_7', 'doll_8', 'doll_9', 'door', 'door_big', 'drink', 'e_aggro', 'e_death', 'e_kill', 'e_laugh', 'e_mess', 'e_oh', 'e_taunt', 'e_welcome', 'echo', 'enemy_death', 'enemy_hurt', 'enemy_swing', 'fog', 'gh_l1', 'gh_l2', 'gh_l3', 'gh_l4', 'gh_l5', 'gh_l6', 'gh_l7', 'gun', 'gun_draw', 'gun_empty', 'hit', 'holster', 'ladder', 'lantern', 'lift', 'lightning', 'musicbox', 'parry', 'pickup', 'player_death', 'player_hurt', 'rat_atk', 'rat_death', 'rat_hurt', 'rat_step', 'recover', 'refresh', 'splash', 'step', 'step_water', 'step_wood', 'swing', 'swing_heavy', 'switch', 'thunder', 'uibad', 'visc', 'w_bld_curve', 'w_bld_gleam', 'w_bld_slide', 'w_bld_whirl', 'w_bld_xform', 'w_cane_asm', 'w_cane_chain', 'w_cleav_xform', 'w_flame_start', 'w_shot_load', 'w_shot_shoot', 'w_spear_xform', 'w_toni_act', 'w_toni_break', 'youdied'])
MUS = ['mus_cb_intro', 'mus_cb_loop', 'mus_gascut', 'mus_intro', 'mus_loop1', 'mus_loop2', 'mus_night', 'mus_trans']
FAMILY = ['level_*.bin','floor_*.bin','sky_*.bin','interact_*.bin','panels_*.txt','texswap_*.txt','levers_*.txt','lamp_*.txt','nocol_*.txt','notes_*.txt','poison_*.txt','volumes_*.txt','breakables_*.txt','dark_*.txt','sky_drop_*.txt','mus_*.wav']
SAVES = ['save*.bin','story*.txt','ladders*.txt','lastpos*.txt','slot.txt']
LOGS = ['maplog*.txt','snd_log*.txt','splash_log*.txt','intro_log*.txt','skydump_*.ppm','*_test.txt','cut_test.txt']
def kind(rel):
    n = os.path.basename(rel)
    if any(fnmatch.fnmatch(n, p) for p in SAVES): return 'save'
    if rel.startswith('snd/'):
        m = re.match(r'^(.*)_(\d+)\.wav$', n)
        return 'ok' if (m and (m.group(1) in SND or m.group(1).startswith('mus_'))) or n.startswith('mus_') else 'unused'
    if '/' in rel: return 'skip'
    if re.match(r'^fog_.+\.txt$', n) and n not in ('fog_dist.txt','fog_k.txt'): return 'old'
    if any(fnmatch.fnmatch(n, p) for p in LOGS): return 'log'
    if n in KNOWN or any(fnmatch.fnmatch(n, p) for p in FAMILY): return 'ok'
    return 'unused'
rows = {'old': [], 'log': [], 'unused': []}; tot = {}
for d, ds, fs in os.walk(root):
    if os.path.basename(d) == '_unused': ds[:] = []; continue
    for f in fs:
        p = os.path.join(d, f); rel = os.path.relpath(p, root).replace(os.sep, '/')
        k = kind(rel)
        if k in rows: rows[k].append((rel, os.path.getsize(p)))
titles = {'old': 'OLD per-map fog distances (the game now uses one distance and ignores these)', 'log': 'LOG / TEST files (safe to delete; the game rewrites logs when it needs them)', 'unused': 'NOT READ by this build (leftovers, tool intermediates, misspelt names)'}
allsz = 0
for k in ('old', 'log', 'unused'):
    if not rows[k]: continue
    sz = sum(s for _, s in rows[k]); allsz += sz
    print('\n== %s: %d files, %.1f MB' % (titles[k], len(rows[k]), sz / 1e6))
    for rel, s in sorted(rows[k]): print('  %8.1f KB  %s' % (s / 1e3, rel))
print('\nTotal listed: %.1f MB. Saves (save*.bin, story*.txt, ladders*.txt, lastpos*.txt, slot.txt) are never touched.' % (allsz / 1e6))
if move:
    for k in rows:
        for rel, _ in rows[k]:
            dst = os.path.join(root, '_unused', rel); os.makedirs(os.path.dirname(dst), exist_ok=True); os.replace(os.path.join(root, rel), dst)
    print('Moved into', os.path.join(root, '_unused'), '- delete that folder when you are happy the game still runs.')
