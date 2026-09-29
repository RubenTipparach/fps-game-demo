// Meridian's towers around the hub (openspec/changes/archive/2026-09-29-hub-skyline, design section 3): dark masses
// with lit windows, neon crowns, blinking beacons and holo billboards, hazed by distance. Unshaded
// and out of the scene fog, which would wash them out; the haze here stands in for it.
//
// One material draws every part, so the skyline costs one draw call per ring. What a face is
// rides in its vertex colour (tools/levels/skyline.py, vertex_color): red the tower's lit share,
// green its window seed, blue (part * 8 + neon role) / 32. The parts are 0 facade, 1 neon band,
// 2 beacon, 3 billboard; the neon role indexes neon_palette (tools/godot/gen_skyline_materials.py
// fills it, linear, from data/character_lighting.json).
//
// A facade's windows are procedural from world position: 3.2 m floors, 2.4 m bays, the window
// 60 % x 55 % of its cell, lit when hash(cell, the tower's seed) is under the tower's lit share.

shader_type spatial;
render_mode unshaded, fog_disabled, cull_back;

const float CODE_SCALE = 32.0;                          // skyline.CODE_SCALE
const int ROLES = 8;                                    // len(skyline.NEON_ROLES)

uniform vec3 neon_palette[8];                           // linear
uniform vec3 facade_color : source_color = vec3(0.027, 0.031, 0.051);
uniform vec3 warm_color : source_color = vec3(1.0, 0.851, 0.627);
uniform vec3 cool_color : source_color = vec3(0.749, 0.890, 1.0);
uniform vec3 beacon_color : source_color = vec3(1.0, 0.12, 0.08);
uniform vec3 haze_color : source_color = vec3(0.082, 0.090, 0.2);
uniform float floor_m = 3.2;
uniform float bay_m = 2.4;
uniform vec2 window_frac = vec2(0.6, 0.55);
uniform float warm_share = 0.6;                         // of lit windows; cool takes the next 0.3
uniform float cool_share = 0.3;                         // ... and the tower's neon the rest
uniform float window_energy = 1.8;                      // over the glow threshold: lit windows bloom a little
uniform float neon_energy = 2.4;
uniform float billboard_energy = 1.4;
uniform float billboard_line_m = 0.8;                   // the holo panel's scan lines
uniform float billboard_scroll_mps = 0.6;
uniform float haze_per_m = 0.0018;
uniform float beacon_period_s = 1.6;
uniform float beacon_on = 0.2;

varying vec3 world;
varying flat vec3 tower;                                // (lit share, seed, code)

void vertex() {
	world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	tower = COLOR.rgb;
}

float hash(vec3 p) {
	p = fract(p * 0.3183099 + vec3(0.1, 0.2, 0.3));
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

void fragment() {
	int code = int(round(tower.z * CODE_SCALE));
	int part = code / ROLES;
	vec3 neon = neon_palette[clamp(code - part * ROLES, 0, ROLES - 1)];
	vec3 surface = facade_color;
	vec3 glow = vec3(0.0);
	if (part == 1) {
		glow = neon * neon_energy;
	} else if (part == 2) {
		float on = step(fract(TIME / beacon_period_s), beacon_on);
		glow = beacon_color * mix(0.15, 3.0, on);
	} else if (part == 3) {
		float line = fract((world.y + TIME * billboard_scroll_mps) / billboard_line_m);
		glow = neon * billboard_energy * mix(0.55, 1.0, step(0.35, line));
	} else {
		// Windows on the walls only: a face's horizontal axis is whichever world axis runs along it.
		vec3 n = abs(normalize(cross(dFdx(world), dFdy(world))));
		if (n.y < 0.5) {
			float along = n.x > n.z ? world.z : world.x;
			vec2 cell = vec2(along / bay_m, world.y / floor_m);
			vec2 f = fract(cell);
			vec2 inset = (1.0 - window_frac) * 0.5;
			bool pane = f.x > inset.x && f.x < 1.0 - inset.x && f.y > inset.y && f.y < 1.0 - inset.y;
			float h = hash(vec3(floor(cell), tower.y * 97.0 + (n.x > n.z ? 1.0 : 0.0)));
			if (pane && h < tower.x) {
				float pick = hash(vec3(floor(cell) + 7.0, tower.y * 31.0));
				vec3 c = pick < warm_share ? warm_color : (pick < warm_share + cool_share ? cool_color : neon);
				glow = c * window_energy;
			}
		}
	}
	// Distance haze: surfaces fully, light at half the rate, since it carries further.
	float d = length(world - CAMERA_POSITION_WORLD);
	float haze = 1.0 - exp(-haze_per_m * d);
	float haze_glow = 1.0 - exp(-haze_per_m * 0.5 * d);
	ALBEDO = mix(surface, haze_color, haze) + glow * (1.0 - haze_glow);
}
