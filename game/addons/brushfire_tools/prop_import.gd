@tool
extends EditorScenePostImport
## Post-import for Blender-made props (doorway kit): parts that change at runtime (the door
## status lights swap colour) are excluded from lightmap baking and lit by probes instead.


func _post_import(scene: Node) -> Object:
	for n in scene.find_children("*", "MeshInstance3D", true, false):
		if n.name.begins_with("Status"):
			(n as MeshInstance3D).gi_mode = GeometryInstance3D.GI_MODE_DYNAMIC
			(n as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return scene
