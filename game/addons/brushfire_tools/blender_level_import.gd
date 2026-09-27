@tool
extends EditorScenePostImport
## Post-import for levels modelled in Blender (see tools/blender/build_cistern.py).
##
## Empties named ENT_<kind>_<n> become instances of the game's scenes (enemies, pickups,
## lights, doors...). Custom properties set on the empty in Blender arrive as glTF "extras":
##   ENT_light:   energy, range, color          -> a baked OmniLight3D
##   ENT_secret / ENT_message: size (x, y, z), text -> trigger volumes

const SCENES := {
	"player_start": "res://scenes/props/player_start.tscn",
	"grunt": "res://scenes/enemies/grunt.tscn",
	"brute": "res://scenes/enemies/brute.tscn",
	"drone": "res://scenes/enemies/drone.tscn",
	"health": "res://scenes/pickups/health.tscn",
	"megahealth": "res://scenes/pickups/megahealth.tscn",
	"armor_heavy": "res://scenes/pickups/armor_heavy.tscn",
	"armor": "res://scenes/pickups/armor.tscn",
	"shells": "res://scenes/pickups/shells.tscn",
	"bullets": "res://scenes/pickups/bullets.tscn",
	"rockets": "res://scenes/pickups/rockets.tscn",
	"rocket_launcher": "res://scenes/pickups/weapon_rocket_launcher.tscn",
	"chaingun": "res://scenes/pickups/weapon_chaingun.tscn",
	"barrel": "res://scenes/props/explosive_barrel.tscn",
	"exit": "res://scenes/props/exit.tscn",
	"doorway": "res://scenes/props/doorway.tscn",
	"door": "res://scenes/props/doorway.tscn",
	"archway_400x350": "res://scenes/props/archway_400x350.tscn",
	"archway_400x400": "res://scenes/props/archway_400x400.tscn",
	"ceiling_light": "res://scenes/props/ceiling_light.tscn",
	"wall_lamp": "res://scenes/props/wall_lamp.tscn",
}
const TRIGGER_SCRIPT := "res://scripts/World/Trigger.cs"


func _kind_of(node_name: String) -> String:
	if not node_name.begins_with("ENT_"):
		return ""
	var rest := node_name.substr(4)
	# strip the trailing _<number> Blender naming added
	var re := RegEx.new()
	re.compile("_\\d+$")
	return re.sub(rest, "")


func _post_import(scene: Node) -> Object:
	var entities := Node3D.new()
	entities.name = "Entities"
	scene.add_child(entities)
	entities.owner = scene
	for n in scene.find_children("ENT_*", "", true, false):
		var kind := _kind_of(n.name)
		var extras: Dictionary = n.get_meta("extras", {})
		var node: Node3D = null
		if SCENES.has(kind):
			node = (load(SCENES[kind]) as PackedScene).instantiate()
		elif kind == "light":
			var l := OmniLight3D.new()
			l.light_energy = float(extras.get("energy", 1.0))
			l.omni_range = float(extras.get("range", 8.0))
			var c = extras.get("color", [1.0, 0.85, 0.65])
			l.light_color = Color(c[0], c[1], c[2])
			l.light_bake_mode = Light3D.BAKE_STATIC
			l.shadow_enabled = true
			l.light_size = 0.2
			node = l
		elif kind == "secret" or kind == "message":
			var area := Area3D.new()
			area.set_script(load(TRIGGER_SCRIPT))
			area.set("Kind", 3 if kind == "secret" else 4)
			if kind == "message":
				area.set("Message", str(extras.get("text", "")))
			var shape := CollisionShape3D.new()
			var box := BoxShape3D.new()
			var sz = extras.get("size", [2.0, 2.0, 2.0])
			box.size = Vector3(sz[0], sz[2], sz[1]) # Blender (x, y, z) -> Godot (x, z, y)
			shape.shape = box
			shape.position = Vector3(0, box.size.y * 0.5, 0)
			area.add_child(shape)
			node = area
		else:
			push_warning("[Brushfire] unknown entity '%s' in %s" % [n.name, scene.name])
			continue
		node.name = n.name.trim_prefix("ENT_")
		entities.add_child(node)
		node.transform = _transform_in(n as Node3D, scene)
		_own(node, scene)
		n.get_parent().remove_child(n)
		n.free()
	return scene


## The imported scene isn't inside the tree yet, so accumulate transforms by hand.
func _transform_in(n: Node3D, root: Node) -> Transform3D:
	var t := n.transform
	var p := n.get_parent()
	while p != null and p != root:
		if p is Node3D:
			t = (p as Node3D).transform * t
		p = p.get_parent()
	return t


func _own(node: Node, owner: Node) -> void:
	node.owner = owner
	if node.scene_file_path.is_empty():
		for c in node.get_children():
			_own(c, owner)
