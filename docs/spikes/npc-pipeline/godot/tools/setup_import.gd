extends SceneTree
## Measurement instrument (throwaway project). Writes hand-made BoneMaps for
## SkeletonProfileHumanoid and patches the .import files of the MPFB characters and the
## UAL library with the retarget options (bone map, bone renamer, rest fixer).
## BoneMapper (the editor's auto-mapper) is not exposed to scripts, so the maps are written here.
## Run: godot --headless --path godot_proj --script res://tools/setup_import.gd

const SIDES := {"Left": ["_l", ".L"], "Right": ["_r", ".R"]}

func mpfb_map() -> Dictionary:
	var m := {"Root": "Root", "Hips": "pelvis", "Spine": "spine_01", "Chest": "spine_02",
		"UpperChest": "spine_03", "Neck": "neck_01", "Head": "head"}
	for side in SIDES:
		var s: String = SIDES[side][0]
		m[side + "Shoulder"] = "clavicle" + s
		m[side + "UpperArm"] = "upperarm" + s
		m[side + "LowerArm"] = "lowerarm" + s
		m[side + "Hand"] = "hand" + s
		m[side + "ThumbMetacarpal"] = "thumb_01" + s
		m[side + "ThumbProximal"] = "thumb_02" + s
		m[side + "ThumbDistal"] = "thumb_03" + s
		for f in [["Index", "index"], ["Middle", "middle"], ["Ring", "ring"], ["Little", "pinky"]]:
			m[side + f[0] + "Proximal"] = f[1] + "_01" + s
			m[side + f[0] + "Intermediate"] = f[1] + "_02" + s
			m[side + f[0] + "Distal"] = f[1] + "_03" + s
		m[side + "UpperLeg"] = "thigh" + s
		m[side + "LowerLeg"] = "calf" + s
		m[side + "Foot"] = "foot" + s
		m[side + "Toes"] = "ball" + s
	return m

func ual_map() -> Dictionary:
	var m := {"Root": "root", "Hips": "DEF-hips", "Spine": "DEF-spine.001", "Chest": "DEF-spine.002",
		"UpperChest": "DEF-spine.003", "Neck": "DEF-neck", "Head": "DEF-head"}
	for side in SIDES:
		var s: String = SIDES[side][1]
		m[side + "Shoulder"] = "DEF-shoulder" + s
		m[side + "UpperArm"] = "DEF-upper_arm" + s
		m[side + "LowerArm"] = "DEF-forearm" + s
		m[side + "Hand"] = "DEF-hand" + s
		m[side + "ThumbMetacarpal"] = "DEF-thumb.01" + s
		m[side + "ThumbProximal"] = "DEF-thumb.02" + s
		m[side + "ThumbDistal"] = "DEF-thumb.03" + s
		for f in [["Index", "f_index"], ["Middle", "f_middle"], ["Ring", "f_ring"], ["Little", "f_pinky"]]:
			m[side + f[0] + "Proximal"] = "DEF-" + f[1] + ".01" + s
			m[side + f[0] + "Intermediate"] = "DEF-" + f[1] + ".02" + s
			m[side + f[0] + "Distal"] = "DEF-" + f[1] + ".03" + s
		m[side + "UpperLeg"] = "DEF-thigh" + s
		m[side + "LowerLeg"] = "DEF-shin" + s
		m[side + "Foot"] = "DEF-foot" + s
		m[side + "Toes"] = "DEF-toe" + s
	return m

func make_bonemap(mapping: Dictionary, path: String) -> BoneMap:
	var bm := BoneMap.new()
	bm.profile = SkeletonProfileHumanoid.new()
	var unmapped := []
	for i in bm.profile.bone_size:
		var pn: StringName = bm.profile.get_bone_name(i)
		if mapping.has(str(pn)):
			bm.set_skeleton_bone_name(pn, StringName(mapping[str(pn)]))
		else:
			unmapped.append(str(pn))
	print("bonemap ", path, " mapped=", mapping.size(), " unmapped profile bones=", unmapped)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(path.get_base_dir()))
	var err := ResourceSaver.save(bm, path)
	assert(err == OK)
	return load(path)

func find_skeleton(n: Node) -> Skeleton3D:
	if n is Skeleton3D:
		return n
	for c in n.get_children():
		var s := find_skeleton(c)
		if s:
			return s
	return null

func patch(glb: String, bonemap: BoneMap, as_library: bool) -> void:
	var skel_path := "Skeleton3D"
	var ps = load(glb)
	if ps is PackedScene:
		var inst: Node = ps.instantiate()
		var sk := find_skeleton(inst)
		skel_path = str(inst.get_path_to(sk))
		var names := []
		for i in sk.get_bone_count():
			names.append(sk.get_bone_name(i))
		var mapped := 0
		for i in bonemap.profile.bone_size:
			if str(bonemap.get_skeleton_bone_name(bonemap.profile.get_bone_name(i))) in names:
				mapped += 1
		print(glb, " skeleton=", skel_path, " bones=", sk.get_bone_count(), " profile bones found in skeleton=", mapped)
		inst.free()
	var cf := ConfigFile.new()
	var ip := glb + ".import"
	assert(cf.load(ip) == OK)
	var opts := {
		"retarget/bone_map": bonemap,
		"retarget/bone_renamer/rename_bones": true,
		"retarget/bone_renamer/unique_node/make_unique": true,
		"retarget/bone_renamer/unique_node/skeleton_name": "GeneralSkeleton",
		"retarget/rest_fixer/apply_node_transforms": true,
		"retarget/rest_fixer/normalize_position_tracks": true,
		"retarget/rest_fixer/reset_all_bone_poses_after_import": true,
		"retarget/rest_fixer/retarget_method": 1,
		"retarget/rest_fixer/fix_silhouette/enable": true,
		"retarget/rest_fixer/fix_silhouette/threshold": 15.0,
		"retarget/remove_tracks/unmapped_bones": true,
	}
	cf.set_value("params", "_subresources", {"nodes": {"PATH:" + skel_path: opts}})
	if as_library:
		cf.set_value("remap", "importer", "animation_library")
		cf.set_value("remap", "type", "AnimationLibrary")
	assert(cf.save(ip) == OK)

func _init() -> void:
	var mpfb := make_bonemap(mpfb_map(), "res://bonemaps/mpfb_game_engine.tres")
	var ual := make_bonemap(ual_map(), "res://bonemaps/ual_rigify_def.tres")
	for c in ["bouncer", "coat_woman", "old_civilian", "random_civilian"]:
		patch("res://chars/%s.glb" % c, mpfb, false)
	patch("res://anims/ual.glb", ual, true)
	quit()
