# Generates one NPC scene per body glb: game/scenes/undercity/npcs/<id>.tscn, an inherited scene
# of game/models/characters/<id>.glb with the ragdoll (a PhysicalBoneSimulator3D of capsules and
# joints, from data/npc_bodies.json) and an AnimationPlayer holding the shared libraries
# (openspec/changes/npc-characters, design sections 6 and 7).
#
#   godot --headless --path game -s res://../tools/godot/gen_npc_scenes.gd
#
# Each scene is written as text, instancing the glb and adding only the Ragdoll and Anim nodes,
# so a rebuilt body needs no regenerated scene unless its skeleton changed.
# Run it after setup_npc_import.gd and a reimport, since it reads each body's retargeted
# skeleton. It lives in tools because it is authoring (CLAUDE.md 6.1: generators write files):
# the committed .tscn files are what the game loads, and re-running overwrites them. The ragdoll
# rules come from the measurement spike (docs/spikes/npc-pipeline/godot/tools/ragdoll.gd): a
# body per listed bone, capsules along the bone, cone joints except hinged knees and elbows.
# The joints are rebuilt at the rest pose at runtime by NpcRagdoll, and the collision
# exceptions between neighbouring bodies are added there too, because neither can be saved.
extends SceneTree

const BODIES_DIR := "res://models/characters"
const OUT_DIR := "res://scenes/undercity/npcs"
const DATA := "res://data/npc_bodies.json"
const LIBRARIES := {"": "res://animations/ual/ual_standard.glb", "undercity": "res://animations/undercity_clips.glb"}
const RAGDOLL_SCRIPT := "res://scripts/Undercity/Entities/NpcRagdoll.cs"
# Brushfire's physics layers (game/scripts/Core/Damage.cs, Layers): World 1, Debris 32.
const WORLD := 1
const DEBRIS := 32

var _failed := false


## data/npc_bodies.json, whose // comment lines JSON can't parse.
func load_data() -> Dictionary:
	var lines := []
	for line in FileAccess.get_file_as_string(DATA).split("\n"):
		if not line.strip_edges().begins_with("//"):
			lines.append(line)
	var parsed = JSON.parse_string("\n".join(lines))
	if parsed == null:
		fail("%s doesn't parse" % DATA)
		return {}
	return parsed


func find_skeleton(n: Node) -> Skeleton3D:
	if n is Skeleton3D:
		return n
	for c in n.get_children():
		var s := find_skeleton(c)
		if s:
			return s
	return null


## One ragdoll body worked out from the skeleton's rest pose: what its node and capsule hold.
func body_def(sk: Skeleton3D, b: Dictionary, id: String) -> Dictionary:
	var bone: String = b["bone"]
	var bi := sk.find_bone(bone)
	if bi < 0:
		fail("%s: the skeleton has no bone %s" % [id, bone])
		return {}
	var rest := sk.get_bone_global_rest(bi)
	var tip := Vector3(0, float(b.get("length_m", 0.2)), 0)
	if b.get("to", "") != "":
		var ti := sk.find_bone(b["to"])
		if ti < 0:
			fail("%s: the skeleton has no bone %s" % [id, b["to"]])
			return {}
		tip = rest.affine_inverse() * sk.get_bone_global_rest(ti).origin
	var length := tip.length()
	# The body's -Z runs along the bone, its origin mid-bone.
	var body := Transform3D(Basis.looking_at(tip, Vector3(0, 0, 1)), tip * 0.5)
	var radius := float(b["radius_m"])
	var props := {}
	var jb := Basis()
	match str(b["joint"]):
		"none":
			props["joint_type"] = PhysicalBone3D.JOINT_TYPE_NONE
		"cone":
			props["joint_type"] = PhysicalBone3D.JOINT_TYPE_CONE
			# A cone twists about the joint's X, so X runs down the bone.
			jb = Basis(Vector3(0, 0, -1), Vector3(0, 1, 0), Vector3(1, 0, 0))
		"hinge":
			props["joint_type"] = PhysicalBone3D.JOINT_TYPE_HINGE
			# The hinge axis is the joint's Z = cross(bone direction, flexion direction) at rest.
			var flex := Vector3(b["flex"][0], b["flex"][1], b["flex"][2])
			var bdir: Vector3 = (rest.basis * tip).normalized()
			var zax: Vector3 = bdir.cross(flex).normalized()
			jb = (rest.basis * body.basis).inverse() * Basis(bdir, zax.cross(bdir), zax)
	props["joint_offset"] = Transform3D(jb.orthonormalized(), Vector3(0, 0, length * 0.5))
	props["body_offset"] = body
	props["bone_name"] = bone
	props["mass"] = float(b["mass_kg"])
	match str(b["joint"]):
		"cone":
			props["joint_constraints/swing_span"] = float(b["a_deg"])
			props["joint_constraints/twist_span"] = float(b["b_deg"])
		"hinge":
			props["joint_constraints/angular_limit_enabled"] = true
			props["joint_constraints/angular_limit_lower"] = float(b["a_deg"])
			props["joint_constraints/angular_limit_upper"] = float(b["b_deg"])
	return {"bone": bone, "props": props, "radius": radius, "height": max(length, 2.0 * radius + 0.01)}


func line(key: String, value) -> String:
	return "%s = %s\n" % [key, var_to_str(value)]


## Writes the scene as text: the glb as an instance, and only the nodes this adds. (Packing an
## instanced glb from a script embeds the whole body instead of inheriting it.)
func write_scene(id: String, glb: String, skel_path: String, bodies: Array, profile: Dictionary) -> bool:
	var libs := {}
	for lib_name in LIBRARIES:
		var path: String = LIBRARIES[lib_name]
		if not ResourceLoader.exists(path):
			if lib_name == "":
				fail("%s isn't imported" % path)
				return false
			continue
		if not load(path) is AnimationLibrary:
			fail("%s isn't imported as an AnimationLibrary: run setup_npc_import.gd" % path)
			return false
		libs[lib_name] = path
	var t := "[gd_scene format=3]\n\n"
	t += '[ext_resource type="PackedScene" path="%s" id="1_body"]\n' % glb
	t += '[ext_resource type="Script" path="%s" id="2_ragdoll"]\n' % RAGDOLL_SCRIPT
	var lib_ids := {}
	var n := 3
	for lib_name in libs:
		var rid := "%d_%s" % [n, "ual" if lib_name == "" else lib_name]
		t += '[ext_resource type="AnimationLibrary" path="%s" id="%s"]\n' % [libs[lib_name], rid]
		lib_ids[lib_name] = rid
		n += 1
	t += "\n"
	for b in bodies:
		t += '[sub_resource type="CapsuleShape3D" id="Capsule_%s"]\n' % b["bone"]
		t += line("radius", b["radius"]) + line("height", b["height"]) + "\n"
	t += '[node name="%s" instance=ExtResource("1_body")]\n\n' % id
	t += '[node name="Ragdoll" type="PhysicalBoneSimulator3D" parent="%s"]\n' % skel_path
	t += 'script = ExtResource("2_ragdoll")\n\n'
	for b in bodies:
		t += '[node name="PB_%s" type="PhysicalBone3D" parent="%s/Ragdoll"]\n' % [b["bone"], skel_path]
		t += line("collision_layer", DEBRIS) + line("collision_mask", WORLD | DEBRIS)
		for key in b["props"]:
			t += line(key, b["props"][key])
		t += line("friction", float(profile["friction"]))
		t += line("linear_damp", float(profile["linear_damp_per_s"]))
		t += line("angular_damp", float(profile["angular_damp_per_s"])) + "\n"
		t += '[node name="Capsule" type="CollisionShape3D" parent="%s/Ragdoll/PB_%s"]\n' % [skel_path, b["bone"]]
		# The capsule's Y onto the body's Z.
		t += line("transform", Transform3D(Basis(Vector3.RIGHT, PI * 0.5), Vector3.ZERO))
		t += 'shape = SubResource("Capsule_%s")\n\n' % b["bone"]
	t += '[node name="Anim" type="AnimationPlayer" parent="."]\n'
	for lib_name in lib_ids:
		t += 'libraries/%s = ExtResource("%s")\n' % [lib_name, lib_ids[lib_name]]
	var f := FileAccess.open(OUT_DIR.path_join(id + ".tscn"), FileAccess.WRITE)
	if f == null:
		fail("%s: can't write its scene" % id)
		return false
	f.store_string(t)
	f.close()
	return true


func generate(glb: String, profile: Dictionary) -> void:
	var id := glb.get_file().get_basename()
	var ps = load(glb)
	if not ps is PackedScene:
		fail("%s doesn't import as a scene" % glb)
		return
	var root: Node = ps.instantiate()
	var sk := find_skeleton(root)
	if sk == null or sk.name != "GeneralSkeleton":
		fail("%s: no retargeted GeneralSkeleton; run setup_npc_import.gd and reimport" % glb)
		root.free()
		return
	sk.reset_bone_poses()
	var bodies := []
	for b in profile["bodies"]:
		var d := body_def(sk, b, id)
		if not d.is_empty():
			bodies.append(d)
	var skel_path := str(root.get_path_to(sk))
	root.free()
	if bodies.size() == profile["bodies"].size() and write_scene(id, glb, skel_path, bodies, profile):
		print("[gen_npc_scenes] %s: ragdoll of %d bodies under %s" % [id, bodies.size(), skel_path])


func fail(msg: String) -> void:
	printerr("[gen_npc_scenes] " + msg)
	_failed = true


func _init() -> void:
	var data := load_data()
	if data.is_empty():
		quit(1)
		return
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	var files := DirAccess.get_files_at(BODIES_DIR)
	files.sort()
	for f in files:
		if f.ends_with(".glb"):
			generate(BODIES_DIR.path_join(f), data["ragdoll"])
	quit(1 if _failed else 0)
