@tool
extends OmniLight3D
## TrenchBroom "light" entity with Quake-style keys, turned into a baked OmniLight3D.
## Runs at map build time (in the editor) so the settings are in place before baking lightmaps.


func _func_godot_apply_properties(props: Dictionary) -> void:
	var brightness := float(props.get("light", 300))
	light_energy = brightness / 200.0
	var r := float(props.get("range", 0.0))
	omni_range = r if r > 0.0 else brightness / 30.0
	omni_attenuation = 1.2
	var c = props.get("_color", Color(1.0, 0.86, 0.7))
	if c is Color:
		light_color = c
	elif c is String:
		var parts: PackedFloat64Array = (c as String).split_floats(" ", false)
		if parts.size() >= 3:
			var scale := 255.0 if parts[0] > 1.0 or parts[1] > 1.0 or parts[2] > 1.0 else 1.0
			light_color = Color(parts[0] / scale, parts[1] / scale, parts[2] / scale)
	shadow_enabled = int(props.get("shadows", 1)) != 0
	light_size = 0.2
	light_bake_mode = Light3D.BAKE_STATIC
