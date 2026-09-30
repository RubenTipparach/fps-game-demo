@tool
extends EditorScenePostImport
## Post-import for levels modelled in Blender (see tools/blender/build_cistern.py).
##
## Empties named ENT_<kind>_<n> become instances of the game's scenes (enemies, pickups,
## lights, doors...). Custom properties set on the empty in Blender arrive as glTF "extras":
##   ENT_light:   energy, range, color          -> a baked OmniLight3D
##   ENT_secret / ENT_message: size (x, y, z), text -> trigger volumes
## Any other kind (Undercity's npc, civ, loot, poi, mission, exit_<id>...) becomes a Marker3D
## named <kind>_<id>, with every extra copied onto it as metadata and the node in the group
## "ent_<kind>". The kind is the "kind" extra when the empty has one, else the name's first word.
##
## Mesh objects may carry render settings as extras (tools/levels/city_plan.py writes them):
##   visibility_range_end_m -> visibility_range_end; lightmap_texel_scale -> gi_lightmap_texel_scale;
##   gi_mode, cast_shadow -> the GeometryInstance3D enums of the same name.

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

## Undercity entities (tools/levels/layouts/<level>_entities.py), by their "kind" extra. Loot picks
## its scene by "model", doors and exits by "style" (see _undercity_scene). A parked car is a static
## mesh of its sector (car_<id>, built by build_undercity.py), so its ENT_car is its contact shadow,
## a decal sized by the "size" extra (openspec/changes/vehicle-fixes, design sections 2.2 and 2.3).
const UNDERCITY := {
	"npc": "res://scenes/undercity/npc.tscn",
	"civ": "res://scenes/undercity/npc.tscn",
	"item": "res://scenes/undercity/world_item.tscn",
	"terminal": "res://scenes/undercity/terminal.tscn",
	"zone": "res://scenes/undercity/zone.tscn",
	"trigger": "res://scenes/undercity/trigger.tscn",
	"bed": "res://scenes/undercity/bed.tscn",
	"ladder": "res://scenes/undercity/ladder.tscn",
}


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
		var undercity := _undercity_scene(extras)
		if undercity != "":
			node = _undercity_entity(undercity, extras)
		elif SCENES.has(kind):
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
			node = _marker(n.name, extras)
		if not (node is Marker3D) and undercity == "":
			node.name = n.name.trim_prefix("ENT_")
		entities.add_child(node)
		node.transform = _transform_in(n as Node3D, scene)
		_own(node, scene)
		n.get_parent().remove_child(n)
		n.free()
	for g in scene.find_children("*", "GeometryInstance3D", true, false):
		_apply_render_extras(g as GeometryInstance3D)
	return scene


func _undercity_scene(extras: Dictionary) -> String:
	var kind := str(extras.get("kind", ""))
	match kind:
		"loot":
			return "res://scenes/undercity/loot_%s.tscn" % str(extras.get("model", "crate"))
		"door":
			return "res://scenes/undercity/%s.tscn" % ("barrier" if str(extras.get("style", "")) == "barrier" else "door")
		"exit":
			return "res://scenes/undercity/exit_%s.tscn" % str(extras.get("style", "none"))
		"sliding_door":
			# a public entrance, by its size and face (tools/godot/detailing.py, SLIDING_LEAVES)
			return "res://scenes/undercity/doors/sliding_%s.tscn" % str(extras.get("leaf", ""))
		"car":
			# a parked car's contact shadow; the car itself is a static mesh of its sector, car_<id>
			# (openspec/changes/vehicle-fixes, design section 2.3)
			return "res://scenes/undercity/car_shadow.tscn"
		"gully":
			# a kerb gully's grate over its puddle (openspec/changes/street-puddles, design section 3.2)
			return "res://scenes/undercity/gully.tscn"
	return UNDERCITY.get(kind, "")


## An Undercity entity: its scene, with every extra as metadata (the game reads "id" and the rest),
## in the group "ent_<kind>", and its trigger box, or its decal, sized from a "size" extra ("w,d" metres).
func _undercity_entity(scene_path: String, extras: Dictionary) -> Node3D:
	var node := (load(scene_path) as PackedScene).instantiate() as Node3D
	var kind := str(extras.get("kind", ""))
	var id := str(extras.get("id", ""))
	node.name = "%s_%s" % [kind, id]
	for key in extras.keys():
		node.set_meta(StringName(str(key)), extras[key])
	node.add_to_group(StringName("ent_" + kind), true)
	var shape := node.find_child("Shape", true, false) as CollisionShape3D
	if shape != null and shape.shape is BoxShape3D and extras.has("size"):
		var wd := str(extras["size"]).split(",")
		var box := (shape.shape as BoxShape3D).duplicate() as BoxShape3D
		box.size = Vector3(float(wd[0]), box.size.y, float(wd[1]))
		shape.shape = box
	if node is Decal and extras.has("size"):
		var wd := str(extras["size"]).split(",")
		(node as Decal).size = Vector3(float(wd[0]), (node as Decal).size.y, float(wd[1]))
	return node


## A kind this importer has no scene for: a marker the game (or a later mapping) resolves.
func _marker(node_name: String, extras: Dictionary) -> Marker3D:
	var rest := node_name.trim_prefix("ENT_")
	var kind := str(extras.get("kind", rest.get_slice("_", 0)))
	var id := str(extras.get("id", rest.trim_prefix(kind + "_")))
	var m := Marker3D.new()
	m.name = "%s_%s" % [kind, id]
	for key in extras.keys():
		m.set_meta(StringName(str(key)), extras[key])
	m.set_meta(&"id", id)
	m.set_meta(&"kind", kind)
	m.add_to_group(StringName("ent_" + kind), true)
	return m


func _apply_render_extras(g: GeometryInstance3D) -> void:
	var extras: Dictionary = g.get_meta("extras", {})
	if extras.has("visibility_range_end_m"):
		g.visibility_range_end = float(extras["visibility_range_end_m"])
	if extras.has("lightmap_texel_scale"):
		g.gi_lightmap_texel_scale = float(extras["lightmap_texel_scale"])
	if extras.has("gi_mode"):
		g.gi_mode = int(extras["gi_mode"]) as GeometryInstance3D.GIMode
	if extras.has("cast_shadow"):
		g.cast_shadow = int(extras["cast_shadow"]) as GeometryInstance3D.ShadowCastingSetting


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
