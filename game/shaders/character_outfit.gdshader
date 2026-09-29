// A body's outfit: its clothes, gear and eyes, which share one atlas and material (tools/blender/
// build_npcs.py). The outfit normal map's alpha is its roughness: 0.08 on the eyes, 0.7 on cloth
// (openspec/changes/archive/2026-09-29-character-lighting, design section 8). A civilian's palette shifts the
// clothes' hue and saturation per instance (openspec/changes/archive/2026-09-29-crowd-variety, design section 2),
// set by NpcActor from the crowd rule; the eyes are left as they are, found by that same alpha,
// and the skin and hair are other materials. Wet cloth (owner J1, design section 9) is smoother
// and darker: "wetness" is per instance, 0 dry to 1 soaked, set by BodyWetness from the core's
// rule, and the soaked roughness and brightness are globals the game sets from
// data/character_lighting.json at start (CharacterShading); project.godot declares them with
// neutral values. The eyes stay as they are, wet or dry.
//
// tools/godot/gen_character_materials.py writes the materials that use it; nothing here is
// tuned inline.
shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler2D albedo_texture : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D normal_texture : hint_normal, filter_linear_mipmap_anisotropic, repeat_disable;
uniform float specular = 0.5;
uniform float normal_strength = 1.0;
uniform float eye_roughness_below = 0.3;     // alpha under this is an eye: never recoloured
global uniform float character_cloth_wet_roughness;
global uniform float character_cloth_wet_brightness;
// A body's skin and outfit are surfaces of one mesh instance, so an instance uniform they share
// must sit at the same index in both, or only one of them reads it (Godot warns).
instance uniform float wetness : instance_index(0) = 0.0;
instance uniform float hue_deg : instance_index(1) = 0.0;
instance uniform float sat : instance_index(2) = 1.0;

vec3 rgb_to_hsv(vec3 c) {
	vec4 k = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
	vec4 p = mix(vec4(c.bg, k.wz), vec4(c.gb, k.xy), step(c.b, c.g));
	vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
	float d = q.x - min(q.w, q.y);
	return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + 1e-10)), d / (q.x + 1e-10), q.x);
}

vec3 hsv_to_rgb(vec3 c) {
	vec3 p = abs(fract(c.xxx + vec3(1.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0);
	return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

void fragment() {
	vec4 n = texture(normal_texture, UV);
	vec3 albedo = texture(albedo_texture, UV).rgb;
	float roughness = n.a;
	if (n.a >= eye_roughness_below) {
		vec3 hsv = rgb_to_hsv(albedo);
		hsv.x = fract(hsv.x + hue_deg / 360.0);
		hsv.y = clamp(hsv.y * sat, 0.0, 1.0);
		float wet = clamp(wetness, 0.0, 1.0);
		albedo = hsv_to_rgb(hsv) * mix(1.0, character_cloth_wet_brightness, wet);
		roughness = mix(n.a, character_cloth_wet_roughness, wet);
	}
	ALBEDO = albedo;
	NORMAL_MAP = n.rgb;
	NORMAL_MAP_DEPTH = normal_strength;
	ROUGHNESS = roughness;
	SPECULAR = specular;
	METALLIC = 0.0;
}
