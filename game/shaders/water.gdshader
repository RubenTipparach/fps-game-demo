// Canal water (openspec/changes/archive/2026-09-29-water-and-swimming, design section 6): a dark surface that
// reflects the lit city. Two scrolling normal maps and rain ripples (the hub always rains) break
// the screen-space reflections of the windows, neon and lamps into streaks, with a glassy
// roughness. Both faces draw, so the surface shows from below.
//
// It is opaque on purpose. Godot's screen-space reflections skip transparent materials, and the
// first version read the screen and depth textures (for refraction and a colour by the water's
// thickness), which made it transparent: from swimming height it reflected nothing and read as
// a black void (docs/validation/2026-09-28-water-and-swimming.md). The canal is 2.3-4.5 m of
// murky water at night, so its deep colour is what the eye would see through it anyway.
//
// Its numbers are the material's parameters (game/materials/materials.json "water", written into
// materials/water.tres by tools/material_maker/postprocess.py); nothing here is tuned inline. The
// rain's rings are rain_ripples.gdshaderinc's, which the street's puddles draw too.
shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform vec3 color : source_color = vec3(0.043, 0.137, 0.153);
uniform sampler2D normal_map : hint_normal, filter_linear_mipmap, repeat_enable;
uniform float tile_m = 6.0;             // the normal map repeats every this many metres
uniform vec2 flow_a_mps = vec2(0.035, 0.012);
uniform vec2 flow_b_mps = vec2(-0.022, 0.028);
uniform float normal_strength = 0.6;
uniform float ripple_cell_m = 0.9;      // one rain drop at a time per cell this wide, metres
uniform float ripple_rate_hz = 0.7;     // drops per cell per second
uniform float ripple_strength = 0.35;
uniform float ripple_wave_per_m = 40.0;    // a ring's crests per metre, times 2 pi
uniform float ripple_falloff_per_m = 18.0; // how sharply a ring fades either side of its crest
uniform float surface_roughness : hint_range(0.0, 1.0) = 0.05;

varying vec3 world_pos;

#include "res://shaders/rain_ripples.gdshaderinc"

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 uv = world_pos.xz / tile_m;
	vec3 n1 = texture(normal_map, uv + TIME * flow_a_mps / tile_m).rgb * 2.0 - 1.0;
	vec3 n2 = texture(normal_map, uv * 1.7 + TIME * flow_b_mps / tile_m).rgb * 2.0 - 1.0;
	vec2 slope = (n1.xy + n2.xy) * 0.5 + rain_ripples(world_pos.xz, TIME, ripple_cell_m, ripple_rate_hz, ripple_strength,
			ripple_wave_per_m, ripple_falloff_per_m);
	vec3 n = normalize(vec3(slope, 1.0));
	NORMAL_MAP = n * 0.5 + 0.5;
	NORMAL_MAP_DEPTH = normal_strength;
	ROUGHNESS = surface_roughness;
	METALLIC = 0.0;
	SPECULAR = 0.5;
	ALBEDO = color;
}
