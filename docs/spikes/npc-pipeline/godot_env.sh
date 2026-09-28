# Source before running godot: isolates Godot's user/config dirs inside the scratchpad.
export NPC=/tmp/claude-0/-home-user-fps-game-demo/065b7c5a-a768-522f-9de5-fe5a1156ee6b/scratchpad/npc
export GPROJ=$NPC/godot_proj
export XDG_CONFIG_HOME=$GPROJ/xdg/config XDG_DATA_HOME=$GPROJ/xdg/data XDG_CACHE_HOME=$GPROJ/xdg/cache
export DISPLAY=:99
