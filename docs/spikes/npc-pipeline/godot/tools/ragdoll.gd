extends SceneTree
## Measurement instrument (throwaway project): builds a PhysicalBoneSimulator3D ragdoll on an
## imported MPFB character by script (the editor's "Create Physical Skeleton" is not reachable
## headless), starts it from an animated pose on a step, shoves the chest, and records stills
## plus per-tick metrics (max body speed, max joint gap, knee/elbow flexion sign).
## Run: godot --path godot_proj --fixed-fps 60 --script res://tools/ragdoll.gd -- <label> [who] [ticks_per_s]

# bone, length-target bone ("" = along bone Y), capsule radius m, mass kg, joint, a, b
# cone: a = swing span deg, b = twist span deg. hinge: a = lower deg, b = upper deg; the hinge axis is
# cross(bone direction, flexion direction) at rest. Measured: with that axis the engine's positive
# hinge angle is extension, so flexion limits are [-140, 0]. Every bone between Hips and a
# simulated bone is simulated too, and joints are built at the rest pose (anatomical zero).
const BODIES := [
	["Hips", "Spine", 0.13, 12.0, "none", 0, 0],
	["Spine", "Chest", 0.12, 8.0, "cone", 15, 10],
	["Chest", "UpperChest", 0.12, 8.0, "cone", 15, 10],
	["UpperChest", "Neck", 0.14, 8.0, "cone", 15, 10],
	["Neck", "Head", 0.05, 1.0, "cone", 30, 30],
	["Head", "", 0.1, 4.5, "cone", 30, 30],
	["LeftShoulder", "LeftUpperArm", 0.045, 1.0, "cone", 10, 10],
	["LeftUpperArm", "LeftLowerArm", 0.055, 2.5, "cone", 70, 40],
	["LeftLowerArm", "LeftHand", 0.045, 1.5, "hinge", -140, 0, Vector3(0, 0, 1)],
	["LeftHand", "LeftMiddleProximal", 0.04, 0.5, "cone", 30, 20],
	["RightShoulder", "RightUpperArm", 0.045, 1.0, "cone", 10, 10],
	["RightUpperArm", "RightLowerArm", 0.055, 2.5, "cone", 70, 40],
	["RightLowerArm", "RightHand", 0.045, 1.5, "hinge", -140, 0, Vector3(0, 0, 1)],
	["RightHand", "RightMiddleProximal", 0.04, 0.5, "cone", 30, 20],
	["LeftUpperLeg", "LeftLowerLeg", 0.085, 9.0, "cone", 50, 15],
	["LeftLowerLeg", "LeftFoot", 0.065, 4.0, "hinge", -140, 0, Vector3(0, 0, -1)],
	["LeftFoot", "LeftToes", 0.05, 1.0, "cone", 20, 10],
	["RightUpperLeg", "RightLowerLeg", 0.085, 9.0, "cone", 50, 15],
	["RightLowerLeg", "RightFoot", 0.065, 4.0, "hinge", -140, 0, Vector3(0, 0, -1)],
	["RightFoot", "RightToes", 0.05, 1.0, "cone", 20, 10],
]
const SHOTS_S := [[0.0, "a_start"], [0.6, "b_falling"], [3.3, "c_rest"]]
const TOTAL_S := 5.0
var RELOAD_JOINTS := false
var REBUILD_AT_REST := true
var SIBLING_EXCEPTIONS := true
var body_rest := {}  # bone -> body basis at rest, skeleton space

var label := "jolt"
var who := "bouncer"
var out_dir := ProjectSettings.globalize_path("res://").path_join("../stills/ragdoll")
var sk: Skeleton3D
var sim: PhysicalBoneSimulator3D
var pbs := {}
var anchors := {}  # child bone -> [parent pb, point in parent body space]
var rest_info := {}
var csv := []

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		label = args[0]
	if args.size() > 1:
		who = args[1]
	if args.size() > 2:
		Engine.physics_ticks_per_second = int(args[2])
	if args.size() > 3:
		RELOAD_JOINTS = args[3] == "reload"
	if args.size() > 4:
		SIBLING_EXCEPTIONS = args[4] == "exc"
	if args.size() > 5:
		REBUILD_AT_REST = args[5] == "rebuild"
	DirAccess.make_dir_recursive_absolute(out_dir)
	print("engine setting=", ProjectSettings.get_setting("physics/3d/physics_engine"), " ticks=", Engine.physics_ticks_per_second)
	var world := Node3D.new()
	root.add_child(world)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.09, 0.1, 0.13)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.45, 0.5, 0.6)
	env.environment.ambient_light_energy = 0.6
	world.add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-45, 60, 0)
	sun.shadow_enabled = true
	world.add_child(sun)
	box(world, Vector3(20, 1, 20), Vector3(0, -0.5, 0), Color(0.3, 0.3, 0.32))      # floor, top y=0
	box(world, Vector3(3, 0.45, 2), Vector3(0, 0.225, -1.0), Color(0.45, 0.4, 0.35))  # step, top y=0.45, edge z=0
	var ch: Node3D = load("res://chars/%s.glb" % who).instantiate()
	ch.position = Vector3(0, 0.45, -0.28)
	ch.rotation_degrees.y = 180.0  # faces -Z, back to the edge
	world.add_child(ch)
	sk = ch.find_children("*", "Skeleton3D", true, false)[0]
	sk.reset_bone_poses()  # joints are built from the rest pose
	build_ragdoll()
	var cam := Camera3D.new()
	world.add_child(cam)
	cam.look_at_from_position(Vector3(4.2, 1.4, 0.6), Vector3(0, 0.6, 0.4))
	_run(ch)

func box(parent: Node3D, size: Vector3, pos: Vector3, col: Color) -> void:
	var sb := StaticBody3D.new()
	sb.position = pos
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	sb.add_child(cs)
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	var m := StandardMaterial3D.new()
	m.albedo_color = col
	bm.material = m
	mi.mesh = bm
	sb.add_child(mi)
	parent.add_child(sb)

func build_ragdoll() -> void:
	sim = PhysicalBoneSimulator3D.new()
	sim.name = "PhysicalBoneSimulator3D"
	sk.add_child(sim)
	for b in BODIES:
		var bi := sk.find_bone(b[0])
		var rest := sk.get_bone_global_rest(bi)
		var tip: Vector3
		if b[1] != "":
			tip = rest.affine_inverse() * sk.get_bone_global_rest(sk.find_bone(b[1])).origin
		else:
			tip = Vector3(0, 0.2, 0)
		var length := tip.length()
		var body := Transform3D(Basis.looking_at(tip, Vector3(0, 0, 1)), tip * 0.5)  # -Z along the bone, origin mid-bone
		var pb := PhysicalBone3D.new()
		pb.name = "PB_" + b[0]
		pb.bone_name = b[0]
		pb.mass = b[3]
		pb.body_offset = body
		pb.friction = 0.8
		pb.linear_damp = 0.05
		pb.angular_damp = 0.8
		pb.collision_layer = 2
		pb.collision_mask = 3
		var cs := CollisionShape3D.new()
		var cap := CapsuleShape3D.new()
		cap.radius = b[2]
		cap.height = max(length, 2.0 * b[2] + 0.01)
		cs.shape = cap
		cs.basis = Basis(Vector3.RIGHT, PI * 0.5)  # capsule Y -> body Z
		pb.add_child(cs)
		# joint at the bone head (body +Z by half length)
		var body_rest_basis := rest.basis * body.basis
		var jb: Basis
		match b[4]:
			"none":
				pb.joint_type = PhysicalBone3D.JOINT_TYPE_NONE
				jb = Basis()
			"cone":
				pb.joint_type = PhysicalBone3D.JOINT_TYPE_CONE
				# ConeTwist twists about joint X: point X down the bone (body -Z)
				jb = Basis(Vector3(0, 0, -1), Vector3(0, 1, 0), Vector3(1, 0, 0))
			"hinge":
				pb.joint_type = PhysicalBone3D.JOINT_TYPE_HINGE
				# Hinge axis is joint Z = cross(bone dir, flexion dir), both in skeleton space at rest
				var bdir: Vector3 = (rest.basis * tip).normalized()
				var zax: Vector3 = bdir.cross(b[7]).normalized()
				var xax: Vector3 = bdir
				jb = body_rest_basis.inverse() * Basis(xax, zax.cross(xax), zax)
		pb.joint_offset = Transform3D(jb.orthonormalized(), Vector3(0, 0, length * 0.5))
		sim.add_child(pb)
		if b[4] == "cone":
			pb.set("joint_constraints/swing_span", float(b[5]))
			pb.set("joint_constraints/twist_span", float(b[6]))
		elif b[4] == "hinge":
			pb.set("joint_constraints/angular_limit_enabled", true)
			pb.set("joint_constraints/angular_limit_lower", float(b[5]))
			pb.set("joint_constraints/angular_limit_upper", float(b[6]))
		pbs[b[0]] = pb
		body_rest[b[0]] = body_rest_basis
	# Overlapping capsules fight forever: the joint does NOT exclude its own pair (measured, see
	# notes), so exclude parent-child, siblings and grandparents in the physical-bone tree.
	var n_exc := 0
	if SIBLING_EXCEPTIONS:
		for a in pbs:
			for c in pbs:
				if a < c:
					var pa := parent_pb(a)
					var pc := parent_pb(c)
					var sib: bool = pa != null and pa == pc
					var grand: bool = (pa != null and parent_pb(str(pa.bone_name)) == pbs[c]) or (pc != null and parent_pb(str(pc.bone_name)) == pbs[a])
					var direct: bool = pa == pbs[c] or pc == pbs[a]
					if direct or sib or grand:
						(pbs[a] as PhysicalBone3D).add_collision_exception_with(pbs[c])
						n_exc += 1
	print("collision exception pairs=", n_exc)
	print("physical bones=", pbs.size(), " total mass=", BODIES.reduce(func(a, x): return a + x[3], 0.0))

func parent_pb(bone: String) -> PhysicalBone3D:
	var p := sk.get_bone_parent(sk.find_bone(bone))
	while p >= 0:
		var n := str(sk.get_bone_name(p))
		if pbs.has(n):
			return pbs[n]
		p = sk.get_bone_parent(p)
	return null

func body_flex(upper: String, lower: String, toward: Vector3) -> Array:
	# Angle (deg) between the two segments, signed + when the distal segment bends toward
	# `toward` (skeleton space at rest): back for knees, front for elbows.
	var gu: Basis = (pbs[upper] as PhysicalBone3D).global_basis
	var gl: Basis = (pbs[lower] as PhysicalBone3D).global_basis
	var dl: Vector3 = gu.inverse() * (-gl.z)   # distal direction in the upper body's frame
	var t_local: Vector3 = (body_rest[upper] as Basis).inverse() * toward
	var ang := rad_to_deg(Vector3(0, 0, -1).angle_to(dl))
	return [snapped(ang, 0.1), signf((dl - Vector3(0, 0, -1)).dot(t_local))]

func flex_sign(upper: String, lower: String, tip: String, back: Vector3) -> float:
	# >0: the distal segment moved toward `back` (skeleton space) relative to the upper bone's rest frame
	var u0: Transform3D = rest_info[upper]
	var v0: Vector3 = u0.basis.inverse() * (rest_info[tip].origin - rest_info[lower].origin)
	var u := sk.get_bone_global_pose(sk.find_bone(upper))
	var v := u.basis.inverse() * (sk.get_bone_global_pose(sk.find_bone(tip)).origin - sk.get_bone_global_pose(sk.find_bone(lower)).origin)
	return (v - v0).dot(u0.basis.inverse() * back)

func joint_gaps() -> Dictionary:
	# world distance between each joint's point on the child body and on its parent body,
	# using the parent-space anchor recorded when the joints were (re)built at rest
	var out := {}
	for name in anchors:
		var a: Array = anchors[name]
		var pbw: PhysicalBone3D = pbs[name]
		out[name] = ((a[0] as PhysicalBone3D).global_transform * a[1]).distance_to(pbw.global_transform * pbw.joint_offset.origin)
	return out

func _run(ch: Node3D) -> void:
	# 1) still at rest: let the simulator register every bone, then rebuild each joint so the
	#    parent lookup and both frames come from the rest pose (anatomical zero for limits)
	await process_frame
	await process_frame
	if REBUILD_AT_REST:
		for name in pbs:
			var pbr: PhysicalBone3D = pbs[name]
			pbr.joint_offset = pbr.joint_offset
	for name in pbs:
		var par := parent_pb(name)
		if par:
			var pb0: PhysicalBone3D = pbs[name]
			anchors[name] = [par, par.global_transform.affine_inverse() * (pb0.global_transform * pb0.joint_offset.origin)]
	# 2) pose from the shared UAL library
	var ap := AnimationPlayer.new()
	ch.add_child(ap)
	ap.root_node = NodePath("..")
	ap.add_animation_library("", load("res://anims/ual.glb"))
	ap.play("Pistol_Idle")
	ap.seek(0.5, true)
	ap.pause()
	await process_frame
	await process_frame
	print("start pose knees[deg,sign]=", body_flex("LeftUpperLeg", "LeftLowerLeg", Vector3(0, 0, -1)), " elbows=", body_flex("LeftUpperArm", "LeftLowerArm", Vector3(0, 0, 1)), body_flex("RightUpperArm", "RightLowerArm", Vector3(0, 0, 1)), " (bodies not yet simulated)")
	for n in ["LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "LeftUpperArm", "LeftLowerArm", "LeftHand"]:
		rest_info[n] = sk.get_bone_global_rest(sk.find_bone(n))
	print("rest dirs: LeftLowerArm->Hand=", (rest_info["LeftHand"].origin - rest_info["LeftLowerArm"].origin).normalized(),
		" LeftLowerLeg->Foot=", (rest_info["LeftFoot"].origin - rest_info["LeftLowerLeg"].origin).normalized())
	sim.physical_bones_start_simulation()
	await physics_frame
	# Joints were built from the rest pose; non-simulated in-between bones (Shoulder, Chest, Neck)
	# are animated, so rebuild each joint from the current posed transforms.
	if RELOAD_JOINTS:
		for name in pbs:
			var pbj: PhysicalBone3D = pbs[name]
			pbj.joint_offset = pbj.joint_offset
		await physics_frame
	var g0 := joint_gaps()
	print("gaps at start (m): ", g0.keys().map(func(k): return "%s=%.3f" % [k, g0[k]]))
	# the "shot": chest impulse toward the edge (character's back) plus a little lift
	pbs["UpperChest"].apply_central_impulse(Vector3(0, 8, 45))
	pbs["Head"].apply_central_impulse(Vector3(0, 0, 6))
	var max_gap_all := 0.0
	var max_speed_all := 0.0
	var hz := Engine.physics_ticks_per_second
	var total := int(TOTAL_S * hz)
	var shots := {}
	for sh in SHOTS_S:
		shots[max(1, int(round(sh[0] * hz)))] = sh[1]
	for f in range(1, total + 1):
		await physics_frame
		var max_speed := 0.0
		var max_gap := 0.0
		var sleeping := 0
		for name in pbs:
			var pb: PhysicalBone3D = pbs[name]
			max_speed = max(max_speed, pb.linear_velocity.length())
			if PhysicsServer3D.body_get_state(pb.get_rid(), PhysicsServer3D.BODY_STATE_SLEEPING):
				sleeping += 1
			if anchors.has(name):
				var a: Array = anchors[name]
				var gap: float = ((a[0] as PhysicalBone3D).global_transform * a[1]).distance_to(pb.global_transform * pb.joint_offset.origin)
				max_gap = max(max_gap, gap)
		max_gap_all = max(max_gap_all, max_gap)
		max_speed_all = max(max_speed_all, max_speed)
		csv.append("%d,%.4f,%.4f,%d" % [f, max_speed, max_gap, sleeping])
		if shots.has(f):
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(out_dir.path_join("%s_%s_%s.png" % [label, who, shots[f]]))
			print("wrote ", label, " ", shots[f], " tick ", f)
	# settle metrics over the last second
	var tail_speed := 0.0
	var tail_gap := 0.0
	for line in csv.slice(total - hz):
		var p: PackedStringArray = line.split(",")
		tail_speed = max(tail_speed, float(p[1]))
		tail_gap = max(tail_gap, float(p[2]))
	var back := Vector3(0, 0, -1)   # character's back in skeleton space (faces +Z)
	var fwd := Vector3(0, 0, 1)
	var hips_y: float = (pbs["Hips"] as PhysicalBone3D).global_position.y
	var worst := ""
	var worst_gap := 0.0
	for name in anchors:
		var a: Array = anchors[name]
		var pbw: PhysicalBone3D = pbs[name]
		var g: float = ((a[0] as PhysicalBone3D).global_transform * a[1]).distance_to(pbw.global_transform * pbw.joint_offset.origin)
		if g > worst_gap:
			worst_gap = g
			worst = name
	var gend := joint_gaps()
	var top := gend.keys()
	top.sort_custom(func(x, y): return gend[x] > gend[y])
	print("gaps at end, worst 4: ", top.slice(0, 4).map(func(k): return "%s=%.3f" % [k, gend[k]]))
	print("RESULT label=", label, " who=", who, " rebuild_at_rest=", REBUILD_AT_REST, " reload_joints=", RELOAD_JOINTS, " worst_gap_bone_end=", worst, "(", snapped(worst_gap, 0.001), ")", " ticks=", Engine.physics_ticks_per_second,
		" max_speed=", snapped(max_speed_all, 0.01), " max_joint_gap_m=", snapped(max_gap_all, 0.001),
		" last1s_max_speed=", snapped(tail_speed, 0.001), " last1s_max_gap_m=", snapped(tail_gap, 0.001),
		" sleeping_at_end=", csv[-1].split(",")[3], "/", pbs.size(), " hips_y_end=", snapped(hips_y, 0.01),
		" exceptions=", SIBLING_EXCEPTIONS,
		" knees[deg,sign]=", body_flex("LeftUpperLeg", "LeftLowerLeg", back), body_flex("RightUpperLeg", "RightLowerLeg", back),
		" elbows[deg,sign]=", body_flex("LeftUpperArm", "LeftLowerArm", fwd), body_flex("RightUpperArm", "RightLowerArm", fwd))
	var fa := FileAccess.open(out_dir.path_join("%s_%s_metrics.csv" % [label, who]), FileAccess.WRITE)
	fa.store_string("frame,max_speed_mps,max_joint_gap_m,sleeping\n" + "\n".join(csv) + "\n")
	fa.close()
	quit()
