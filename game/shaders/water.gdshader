// Canal water (openspec/changes/water-and-swimming, design section 6): a dark green-black surface
// whose colour deepens with the water's thickness behind it, two scrolling normal maps and rain
// ripples (the hub always rains), a glassy roughness that streaks the lamps, and the refracted
// scene through it. Both faces draw, so the surface shows from below.
//
// Its numbers are the material's parameters (game/materials/materials.json "water", written into
// materials/water.tres by tools/material_maker/postprocess.py); nothing here is tuned inline.
shader_type spatial;
render_mode blend_mix, depth_draw_always, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform vec3 shallow_color : source_color = vec3(0.122, 0.290, 0.290);
uniform vec3 deep_color : source_color = vec3(0.043, 0.137, 0.153);
uniform float deep_m = 2.3;             // water this thick behind the surface reads fully deep, metres
uniform float clarity = 0.55;           // how much of the scene behind shows through shallow water, 0-1
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
uniform float refraction = 0.025;       // screen offset of the scene behind, at full normal
uniform float surface_roughness : hint_range(0.0, 1.0) = 0.05;
uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

// A rain drop's ring in each cell: the slope it adds to the surface, in x and z.
vec2 ripples(vec2 p, float t) {
	vec2 cell = floor(p / ripple_cell_m);
	vec2 slope = vec2(0.0);
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			vec2 c = cell + vec2(float(i), float(j));
			float h = hash12(c);
			vec2 centre = (c + vec2(hash12(c + 17.1), hash12(c + 41.7))) * ripple_cell_m;
			float age = fract(t * ripple_rate_hz + h);
			vec2 d = p - centre;
			float r = length(d);
			float front = age * ripple_cell_m;
			float ring = sin((r - front) * ripple_wave_per_m) * exp(-abs(r - front) * ripple_falloff_per_m) * (1.0 - age);
			slope += (r > 1e-4 ? d / r : vec2(0.0)) * ring;
		}
	}
	return slope * ripple_strength;
}

void fragment() {
	vec2 uv = world_pos.xz / tile_m;
	vec3 n1 = texture(normal_map, uv + TIME * flow_a_mps / tile_m).rgb * 2.0 - 1.0;
	vec3 n2 = texture(normal_map, uv * 1.7 + TIME * flow_b_mps / tile_m).rgb * 2.0 - 1.0;
	vec2 slope = (n1.xy + n2.xy) * 0.5 + ripples(world_pos.xz, TIME);
	vec3 n = normalize(vec3(slope, 1.0));
	NORMAL_MAP = n * 0.5 + 0.5;
	NORMAL_MAP_DEPTH = normal_strength;
	ROUGHNESS = surface_roughness;
	METALLIC = 0.0;
	SPECULAR = 0.5;

	// How much water lies between the surface and what is behind it, along the view.
	vec2 suv = SCREEN_UV + slope * refraction;
	float raw = texture(depth_tex, suv).r;
	vec4 behind_view = INV_PROJECTION_MATRIX * vec4(suv * 2.0 - 1.0, raw, 1.0);
	behind_view.xyz /= behind_view.w;
	float thickness = max(-behind_view.z + VERTEX.z, 0.0);
	float deep = clamp(thickness / deep_m, 0.0, 1.0);

	vec3 behind = texture(screen_tex, suv).rgb;
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float fresnel = pow(1.0 - facing, 5.0);
	float see = FRONT_FACING ? clarity * (1.0 - deep) * (1.0 - fresnel) : 0.8;
	ALBEDO = mix(shallow_color, deep_color, deep) * (1.0 - see);
	EMISSION = behind * see;
	ALPHA = 1.0;
}
