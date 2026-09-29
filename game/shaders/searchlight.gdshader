// A searchlight beam over the skyline (openspec/changes/archive/2026-09-29-hub-skyline, design section 3a; owner I8):
// sky decoration that casts no light. The mesh is an open cone standing on +Y, centred as Godot's
// CylinderMesh is (scenes/undercity/searchlight.tscn); the vertex stage stands it on its base,
// tilts it from vertical and turns it about the vertical, so the sweep costs no script and no CPU.
//
// Additive and unshaded. The beam fades toward its far end, is brightest through its middle (a
// face seen head-on has the most beam behind it) and fades when seen end-on, so it doesn't blow
// out when it points at the camera. Hazed like the towers (skyline_tower.gdshader), at the rate
// light hazes there.

shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled;

uniform float length_m = 900.0;                         // the cone's height, as the scene's mesh
uniform vec3 beam_color : source_color = vec3(0.78, 0.9, 1.0);
uniform float energy = 0.35;
uniform float core_power = 2.0;                         // how sharply the middle outshines the edges
uniform float end_on_power = 8.0;                       // how narrow the end-on fade is
uniform float base_fade = 0.02;                         // of the length, fading in off the lamp
uniform float haze_per_m = 0.0009;                      // half the towers' surface haze: light carries
uniform float tilt_cycles_per_turn = 1.618;             // the tilt's swing, out of step with the turn
instance uniform float period_s = 47.0;                 // one turn; negative turns the other way
instance uniform float phase_deg = 0.0;
instance uniform vec2 tilt_deg = vec2(20.0, 35.0);      // from vertical, least and most

varying float along;
varying vec3 world;
varying vec3 axis;

vec3 place(vec3 v, float tilt, float turn) {
	// tilt about X, then turn about Y
	v = vec3(v.x, v.y * cos(tilt) - v.z * sin(tilt), v.y * sin(tilt) + v.z * cos(tilt));
	return vec3(v.x * cos(turn) + v.z * sin(turn), v.y, -v.x * sin(turn) + v.z * cos(turn));
}

void vertex() {
	float turn = radians(phase_deg) + TAU * TIME / period_s;
	float swing = 0.5 + 0.5 * sin(TAU * TIME * tilt_cycles_per_turn / abs(period_s));
	float tilt = radians(mix(tilt_deg.x, tilt_deg.y, swing));
	vec3 v = VERTEX + vec3(0.0, length_m * 0.5, 0.0);
	along = clamp(v.y / length_m, 0.0, 1.0);
	VERTEX = place(v, tilt, turn);
	NORMAL = place(NORMAL, tilt, turn);
	world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	axis = normalize((MODEL_MATRIX * vec4(place(vec3(0.0, 1.0, 0.0), tilt, turn), 0.0)).xyz);
}

void fragment() {
	vec3 ray = world - CAMERA_POSITION_WORLD;
	float d = length(ray);
	float fade = pow(1.0 - along, 1.5) * smoothstep(0.0, base_fade, along);
	float core = pow(abs(dot(normalize(NORMAL), VIEW)), core_power);
	float end_on = 1.0 - pow(abs(dot(axis, ray / d)), end_on_power);
	ALBEDO = beam_color * energy * fade * core * end_on * exp(-haze_per_m * d);
}
