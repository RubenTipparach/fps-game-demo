extends SceneTree
## Measurement instrument (throwaway project): plays retargeted UAL clips on the imported
## MPFB characters and saves stills. Scene is assembled here because it is a capture rig,
## not game content. Run with a display (Xvfb :99, lavapipe):
##   godot --path godot_proj --resolution 960x720 --script res://tools/capture_anims.gd

const CLIPS := [
	["Idle", 1.0], ["Walk", 0.35], ["Jog_Fwd", 0.3], ["Idle_Talking", 1.2],
	["Sitting_Idle", 0.5], ["Pistol_Aim_Neutral", 0.1], ["Pistol_Shoot", 0.15], ["Hit_Chest", 0.2],
	["Punch_Cross", 0.4], ["Crouch_Idle", 0.5], ["Death01", 2.35], ["Sword_Attack", 0.6],
]
const GROUP := [["bouncer", "Pistol_Idle", 0.5], ["coat_woman", "Walk", 0.35],
	["old_civilian", "Idle_Talking", 1.2], ["random_civilian", "Jog_Fwd", 0.3]]

var out_dir := ProjectSettings.globalize_path("res://").path_join("../stills/anim")
var lib: AnimationLibrary
var cam := Camera3D.new()

func _initialize() -> void:
	DirAccess.make_dir_recursive_absolute(out_dir)
	lib = load("res://anims/ual.glb")
	var world := Node3D.new()
	root.add_child(world)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.09, 0.1, 0.13)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.45, 0.5, 0.6)
	env.environment.ambient_light_energy = 0.6
	env.environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	world.add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	sun.shadow_enabled = true
	sun.light_energy = 1.3
	world.add_child(sun)
	var floor_mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(30, 30)
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color(0.32, 0.32, 0.34)
	pm.material = fm
	floor_mi.mesh = pm
	world.add_child(floor_mi)
	world.add_child(cam)
	_run(world)

func spawn(world: Node3D, who: String, x: float) -> AnimationPlayer:
	var ch: Node3D = load("res://chars/%s.glb" % who).instantiate()
	ch.position.x = x
	world.add_child(ch)
	var ap := AnimationPlayer.new()
	ch.add_child(ap)
	ap.root_node = NodePath("..")
	ap.add_animation_library("", lib)
	return ap

func pose(ap: AnimationPlayer, clip: String, t: float) -> void:
	ap.play(clip)
	ap.seek(t, true)
	ap.pause()

func shot(name: String) -> void:
	for i in 4:
		await process_frame
	await RenderingServer.frame_post_draw
	var img := root.get_texture().get_image()
	img.save_png(out_dir.path_join(name + ".png"))
	print("wrote ", name)

func _run(world: Node3D) -> void:
	var t0 := Time.get_ticks_msec()
	var ap := spawn(world, "bouncer", 0.0)
	cam.fov = 38.0
	cam.look_at_from_position(Vector3(1.4, 1.35, 3.9), Vector3(0, 0.9, 0))
	for c in CLIPS:
		pose(ap, c[0], c[1])
		await shot("bouncer_" + c[0])
	ap.get_parent().queue_free()
	var x := -1.95
	for g in GROUP:
		pose(spawn(world, g[0], x), g[1], g[2])
		x += 1.3
	cam.look_at_from_position(Vector3(0.6, 1.3, 7.4), Vector3(0, 0.85, 0))
	await shot("group_shared_library")
	print("capture ms ", Time.get_ticks_msec() - t0)
	quit()
