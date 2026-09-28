extends SceneTree
## Measurement instrument: checks the retargeted import. Prints the character skeleton
## after renaming, which UAL tracks resolve on it, and clip loop modes.

func find_skeleton(n: Node) -> Skeleton3D:
	if n is Skeleton3D:
		return n
	for c in n.get_children():
		var s := find_skeleton(c)
		if s:
			return s
	return null

func _init() -> void:
	var lib: AnimationLibrary = load("res://anims/ual.glb")
	var clips := lib.get_animation_list()
	print("UAL library clips=", clips.size())
	var loops := []
	for c in clips:
		if lib.get_animation(c).loop_mode != Animation.LOOP_NONE:
			loops.append(str(c))
	print("looping clips: ", loops)
	var walk := lib.get_animation("Walk")
	var paths := []
	for t in walk.get_track_count():
		paths.append("%s(%d)" % [str(walk.track_get_path(t)), walk.track_get_type(t)])
	print("Walk tracks=", walk.get_track_count(), " sample: ", paths.slice(0, 6))
	for c in ["bouncer", "coat_woman", "old_civilian", "random_civilian"]:
		var inst: Node3D = load("res://chars/%s.glb" % c).instantiate()
		var sk := find_skeleton(inst)
		var names := []
		for i in sk.get_bone_count():
			names.append(str(sk.get_bone_name(i)))
		var lua := sk.get_bone_global_rest(sk.find_bone("LeftUpperArm")).origin
		var head := sk.get_bone_global_rest(sk.find_bone("Head")).origin
		var hips := sk.get_bone_global_rest(sk.find_bone("Hips")).origin
		var missing := {}
		for t in walk.get_track_count():
			var p := walk.track_get_path(t)
			if p.get_subname_count() > 0 and sk.find_bone(p.get_subname(0)) < 0:
				missing[str(p)] = true
		var meshes := inst.find_children("*", "MeshInstance3D", true, false)
		var surf := 0
		for m in meshes:
			surf += m.mesh.get_surface_count()
		print(c, ": skeleton node='", sk.name, "' unique=", sk.is_unique_name_in_owner(), " path=", inst.get_path_to(sk),
			" bones=", sk.get_bone_count(), " LeftUpperArm.x=", snapped(lua.x, 0.001), " head.y=", snapped(head.y, 0.001),
			" hips.y=", snapped(hips.y, 0.001), " unresolved Walk tracks=", missing.keys(), " surfaces=", surf)
		if c == "bouncer":
			print("bouncer bones: ", names)
		inst.free()
	quit()
