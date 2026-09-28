extends SceneTree
func _init():
	for c in ["BoneMapper", "BoneMap", "SkeletonProfileHumanoid", "PhysicalBoneSimulator3D", "PhysicalBone3D", "SkeletonModifier3D", "ModifierBoneTarget3D", "RetargetModifier3D", "SpringBoneSimulator3D"]:
		print(c, " exists=", ClassDB.class_exists(c), " can_instantiate=", ClassDB.can_instantiate(c) if ClassDB.class_exists(c) else false)
	if ClassDB.class_exists("BoneMapper"):
		for m in ClassDB.class_get_method_list("BoneMapper", true):
			print("  BoneMapper.", m.name)
	for m in ClassDB.class_get_method_list("BoneMap", true):
		print("  BoneMap.", m.name)
	var p := SkeletonProfileHumanoid.new()
	var names := []
	for i in p.bone_size:
		names.append(str(p.get_bone_name(i)))
	print("humanoid bones ", p.bone_size, ": ", ", ".join(names))
	quit()
