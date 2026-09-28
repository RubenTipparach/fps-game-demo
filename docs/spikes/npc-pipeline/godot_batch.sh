#!/bin/bash
# One lock acquisition for all Godot measurement runs (the lock is shared with other work).
# usage: flock /tmp/undercity-godot.lock scripts/godot_batch.sh
source /tmp/claude-0/-home-user-fps-game-demo/065b7c5a-a768-522f-9de5-fe5a1156ee6b/scratchpad/npc/scripts/godot_env.sh
g() { name=$1; t=$2; shift 2; timeout -k 5 $t godot --path $GPROJ "$@" > $NPC/logs/$name.log 2>&1; echo "$name exit=$?"; }
rd() { # label engine hz who joints exceptions
  printf '[physics]\n3d/physics_engine="%s"\n' "$2" > $GPROJ/override.cfg
  g ragdoll_$1_$4 120 --resolution 960x720 --fixed-fps 60 --rendering-driver vulkan --script res://tools/ragdoll.gd -- $1 $4 $3 $5 $6 $7
  grep -E "RESULT|SCRIPT ERROR|exception pairs|gaps at" $NPC/logs/ragdoll_$1_$4.log
  rm -f $GPROJ/override.cfg
}
g check_rd 60 --headless --check-only --script res://tools/ragdoll.gd; grep "SCRIPT ERROR\|Parse" $NPC/logs/check_rd.log
rd jolt60 "Jolt Physics" 60 bouncer noreload exc rebuild
rd godot60 "GodotPhysics3D" 60 bouncer noreload exc rebuild
rd jolt120 "Jolt Physics" 120 bouncer noreload exc rebuild
rd godot120 "GodotPhysics3D" 120 bouncer noreload exc rebuild
rd jolt60 "Jolt Physics" 60 coat_woman noreload exc rebuild
rd jolt60 "Jolt Physics" 60 old_civilian noreload exc rebuild
rd jolt60 "Jolt Physics" 60 random_civilian noreload exc rebuild
echo batch_done
