# Writes the NPC bone maps and the retarget import options of every NPC body glb and every shared
# animation library, so each body and each clip lands on Godot's SkeletonProfileHumanoid
# (openspec/changes/archive/2026-09-28-npc-characters, design section 5).
#
#   godot --headless --path game --import                                  # first sight of new glbs
#   godot --headless --path game -s res://../tools/godot/setup_npc_import.gd
#   godot --headless --path game --import                                  # reimport with the options
#
# It lives in tools because it is authoring: it writes the committed bone maps
# (game/animations/bonemaps/*.tres) and the committed .import files, which the editor would
# otherwise set by hand in its import dialog. Godot's auto-mapper (BoneMapper) isn't exposed to
# scripts, so the two maps are spelt out here. Borrowed from the measurement spike
# (docs/spikes/npc-pipeline/godot/tools/setup_import.gd).
extends SceneTree

const BODIES_DIR := "res://models/characters"
const LIBRARIES := {
	"res://animations/ual/ual_standard.glb": "ual",
	"res://animations/undercity_clips.glb": "ual",
}
const MPFB_MAP := "res://animations/bonemaps/mpfb_game_engine.tres"
const SKIN_DIR := "res://materials/characters"
const UAL_MAP := "res://animations/bonemaps/ual_rigify_def.tres"
const SIDES := {"Left": ["_l", ".L"], "Right": ["_r", ".R"]}

var _failed := false


## MPFB's game_engine rig (Unreal mannequin names) to the humanoid profile.
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


## UAL's Rigify deform bones to the humanoid profile.
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
	for i in bm.profile.bone_size:
		var pn: StringName = bm.profile.get_bone_name(i)
		if mapping.has(str(pn)):
			bm.set_skeleton_bone_name(pn, StringName(mapping[str(pn)]))
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(path.get_base_dir()))
	if ResourceSaver.save(bm, path) != OK:
		fail("can't write %s" % path)
	return load(path)


func find_skeleton(n: Node) -> Skeleton3D:
	if n is Skeleton3D:
		return n
	for c in n.get_children():
		var s := find_skeleton(c)
		if s:
			return s
	return null


## Writes the retarget options into a glb's .import. A library also switches importer.
func patch(glb: String, bonemap: BoneMap, as_library: bool) -> void:
	var cf := ConfigFile.new()
	var ip := glb + ".import"
	if cf.load(ip) != OK:
		fail("%s has no .import yet: run `godot --headless --path game --import` first" % glb)
		return
	# The skeleton's node path inside the imported scene, as the import dialog would name it: the
	# path before the retarget renames it. Once a pass has written it, keep it, since a retargeted
	# import (a body re-run, or a library) no longer shows the old name: options keyed by the new
	# name "GeneralSkeleton" would match nothing and the next clean import would lose the retarget.
	var skel_path := ""
	if cf.has_section_key("params", "_subresources"):
		var subs: Dictionary = cf.get_value("params", "_subresources")
		for key in subs.get("nodes", {}):
			skel_path = str(key).trim_prefix("PATH:")
	var imported = load(glb) if skel_path == "" else null
	if imported is PackedScene:
		var inst: Node = imported.instantiate()
		var sk := find_skeleton(inst)
		if sk:
			skel_path = str(inst.get_path_to(sk))
		inst.free()
	if skel_path == "":
		fail("%s: no Skeleton3D found" % glb)
		return
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
	var subs := {"nodes": {"PATH:" + skel_path: opts}}
	# A body's skin and outfit take their generated materials (tools/godot/gen_character_materials.py):
	# openspec/changes/archive/2026-09-29-character-lighting, design sections 1 and 8.
	if not as_library:
		var id := glb.get_file().get_basename()
		var mats := {}
		for part in ["skin", "outfit"]:
			var path := SKIN_DIR.path_join("%s_%s.tres" % [id, part])
			if FileAccess.file_exists(path):
				mats["%s_%s" % [id, part]] = {"use_external/enabled": true, "use_external/path": path}
		if not mats.is_empty():
			subs["materials"] = mats
	cf.set_value("params", "_subresources", subs)
	if as_library:
		cf.set_value("remap", "importer", "animation_library")
		cf.set_value("remap", "type", "AnimationLibrary")
	if cf.save(ip) != OK:
		fail("can't write %s" % ip)
		return
	print("[setup_npc_import] %s: skeleton %s%s" % [glb, skel_path, " (library)" if as_library else ""])


func fail(msg: String) -> void:
	printerr("[setup_npc_import] " + msg)
	_failed = true


func _init() -> void:
	var mpfb := make_bonemap(mpfb_map(), MPFB_MAP)
	var ual := make_bonemap(ual_map(), UAL_MAP)
	var bodies := DirAccess.get_files_at(BODIES_DIR)
	bodies.sort()
	for f in bodies:
		if f.ends_with(".glb"):
			patch(BODIES_DIR.path_join(f), mpfb, false)
	for glb in LIBRARIES:
		if FileAccess.file_exists(glb):
			patch(glb, ual, true)
		else:
			print("[setup_npc_import] %s: not built yet, skipped" % glb)
	for f in bodies:
		if f.ends_with("_normal.webp"):
			keep_alpha(BODIES_DIR.path_join(f))
	quit(1 if _failed else 0)


## A body's normal maps carry roughness in their alpha (openspec/changes/archive/2026-09-29-character-lighting,
## design sections 1 and 8). They stay lossless, and the editor's "detect 3D" is off: it would
## switch them to VRAM compression, whose normal-map format drops the alpha.
func keep_alpha(texture: String) -> void:
	var ip := texture + ".import"
	var cf := ConfigFile.new()
	if cf.load(ip) != OK:
		print("[setup_npc_import] %s: not imported yet, skipped" % texture)
		return
	cf.set_value("params", "compress/mode", 0)
	cf.set_value("params", "detect_3d/compress_to", 0)
	if cf.save(ip) != OK:
		fail("can't write %s" % ip)
		return
	print("[setup_npc_import] %s: lossless, alpha kept" % texture)
