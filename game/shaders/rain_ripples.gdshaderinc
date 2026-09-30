// Rain drops on standing water (openspec/changes/archive/2026-09-30-street-puddles, design section 3.3): one drop at a
// time in each cell of a grid, its ring spreading and fading, summed over the nine cells round a
// point. The canal (water.gdshader) and the street's puddles (city_ground.gdshader) both include it,
// so a drop reads the same on either (CLAUDE.md 5.1: the same behaviour, the same code). Its numbers
// are arguments: each material passes its own uniforms, which tools/material_maker/postprocess.py
// copies from the water's entry in materials.json ("ripples_from"), so they can't drift apart.

float rain_hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

// The slope the rain adds to a flat surface at p (world x and z, metres) at time t (seconds).
vec2 rain_ripples(vec2 p, float t, float cell_m, float rate_hz, float strength, float wave_per_m, float falloff_per_m) {
	vec2 cell = floor(p / cell_m);
	vec2 slope = vec2(0.0);
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			vec2 c = cell + vec2(float(i), float(j));
			float h = rain_hash12(c);
			vec2 centre = (c + vec2(rain_hash12(c + 17.1), rain_hash12(c + 41.7))) * cell_m;
			float age = fract(t * rate_hz + h);
			vec2 d = p - centre;
			float r = length(d);
			float front = age * cell_m;
			float ring = sin((r - front) * wave_per_m) * exp(-abs(r - front) * falloff_per_m) * (1.0 - age);
			slope += (r > 1e-4 ? d / r : vec2(0.0)) * ring;
		}
	}
	return slope * strength;
}
