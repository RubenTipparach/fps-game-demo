// The city's ground, asphalt and wet paving (openspec/changes/street-puddles, design section 3.2):
// the ORMMaterial3D it replaces, drawn the same way, and the puddles the level plan placed, read
// from the level's puddle mask. Inside a puddle the ground darkens, turns to a mirror for the
// screen-space reflections and the probes, flattens, and the rain's rings cross it
// (rain_ripples.gdshaderinc, the canal's own rings).
//
// The mask (tools/levels/puddle_mask.py) arrives in four shader globals the level sets when it
// loads (PuddleShading.cs): the texture, the rect it covers in world x and z, and the numbers its
// two channels decode with, from the level data, so the writer and the shader can't disagree.
// project.godot declares an empty rect, so the editor, the lightmap bake and any level without
// puddles draw none. A puddle lies only where the ground faces up and stands within
// puddle_height_tol_m of the puddle's own height: a kerb top or a deck over the same x and z stays
// dry where the mask's soft edge reaches it.
//
// Its numbers are the materials' parameters (game/materials/materials.json, written into the .tres
// by tools/material_maker/postprocess.py, the ripples copied from the water's); nothing here is
// tuned inline.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

#include "res://shaders/rain_ripples.gdshaderinc"

// The material as it was: ORMMaterial3D's maps and numbers.
uniform sampler2D albedo_map : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D orm_map : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normal_map : hint_roughness_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float normal_strength = 1.0;
uniform float ao_light_affect = 0.2;
uniform float specular = 0.5;

// The puddles.
global uniform sampler2D puddle_mask;      // lossless, mipmapped: grey the distance to the edge, alpha the ground height
global uniform vec4 puddle_rect_m;         // x, z, width, depth of the mask, metres; width 0: no puddles
global uniform float puddle_range_m;       // grey 0..1 is a distance of -range..+range to the edge, inside negative
global uniform vec2 puddle_height_m;       // alpha 0..1 is a ground height of low..high
uniform float puddle_darken = 0.65;        // the albedo inside, over the albedo outside
uniform float puddle_roughness = 0.04;
uniform float puddle_edge_m = 0.04;        // the wet edge's width
uniform float puddle_noise_m = 0.05;       // how far the noise moves the edge
uniform float puddle_noise_wavelength_m = 0.3;
uniform float puddle_height_tol_m = 0.03;  // a fragment this far above or below the puddle's ground is dry
uniform float puddle_up_min = 0.9;         // the world normal's y a puddle's surface needs
uniform float ripple_cell_m = 0.9;
uniform float ripple_rate_hz = 0.7;
uniform float ripple_strength = 0.35;
uniform float ripple_wave_per_m = 40.0;
uniform float ripple_falloff_per_m = 18.0;
uniform float ripple_normal_depth = 0.6;   // the ripples' normal depth: the water's own

float value_noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	float a = rain_hash12(i);
	float b = rain_hash12(i + vec2(1.0, 0.0));
	float c = rain_hash12(i + vec2(0.0, 1.0));
	float d = rain_hash12(i + vec2(1.0, 1.0));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y) * 2.0 - 1.0;
}

// How wet the ground is at a world point on a surface with this world normal: 0 dry, 1 in a puddle.
float puddle_wet(vec3 world, vec3 world_normal) {
	if (puddle_rect_m.z <= 0.0 || world_normal.y < puddle_up_min) {
		return 0.0;
	}
	vec2 uv = (world.xz - puddle_rect_m.xy) / puddle_rect_m.zw;
	if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) {
		return 0.0;
	}
	vec4 m = texture(puddle_mask, uv);
	float ground = mix(puddle_height_m.x, puddle_height_m.y, m.a);
	if (abs(world.y - ground) > puddle_height_tol_m) {
		return 0.0;
	}
	float d = (m.r - 0.5) * 2.0 * puddle_range_m + value_noise(world.xz / puddle_noise_wavelength_m) * puddle_noise_m;
	return 1.0 - smoothstep(-puddle_edge_m * 0.5, puddle_edge_m * 0.5, d);
}

void fragment() {
	vec3 albedo = texture(albedo_map, UV).rgb;
	vec4 orm = texture(orm_map, UV);
	vec3 normal_tex = texture(normal_map, UV).rgb;
	vec3 world = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec3 world_normal = normalize((INV_VIEW_MATRIX * vec4(NORMAL, 0.0)).xyz);
	float wet = puddle_wet(world, world_normal);
	float rough = orm.g;
	float depth = normal_strength;
	if (wet > 0.0) {
		vec2 slope = rain_ripples(world.xz, TIME, ripple_cell_m, ripple_rate_hz, ripple_strength,
				ripple_wave_per_m, ripple_falloff_per_m);
		vec3 ripple_n = normalize(vec3(slope, 1.0)) * 0.5 + 0.5;
		albedo *= mix(1.0, puddle_darken, wet);
		rough = mix(rough, puddle_roughness, wet);
		normal_tex = mix(normal_tex, ripple_n, wet);
		depth = mix(normal_strength, ripple_normal_depth, wet);
	}
	ALBEDO = albedo;
	AO = orm.r;
	AO_LIGHT_AFFECT = ao_light_affect;
	ROUGHNESS = rough;
	METALLIC = orm.b;
	SPECULAR = specular;
	NORMAL_MAP = normal_tex;
	NORMAL_MAP_DEPTH = depth;
}
