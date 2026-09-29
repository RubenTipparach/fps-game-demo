// Under the water (openspec/changes/archive/2026-09-29-water-and-swimming, design section 6): drawn over the whole
// view while the camera is below a surface, it tints the scene and fogs it with distance (63 %
// hidden at visibility_m, 86 % at twice that), and wobbles it a little. A 2 x 2 quad in front
// of the camera (scenes/undercity/player.tscn, "Underwater") covers the screen; its numbers are
// the material's (materials/underwater.tres).
shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, fog_disabled, skip_vertex_transform;

uniform vec3 fog_color : source_color = vec3(0.039, 0.133, 0.149);
uniform vec3 tint : source_color = vec3(0.7, 0.95, 0.9);
uniform float visibility_m = 8.0;       // at this distance the fog hides 63 % of what is behind it
uniform float wobble = 0.004;           // screen offset of the waver
uniform float wobble_hz = 0.6;
uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec2 w = vec2(sin(SCREEN_UV.y * 40.0 + TIME * 6.2832 * wobble_hz), cos(SCREEN_UV.x * 36.0 + TIME * 6.2832 * wobble_hz * 0.8));
	vec2 uv = SCREEN_UV + w * wobble;
	float raw = texture(depth_tex, uv).r;
	vec4 view = INV_PROJECTION_MATRIX * vec4(uv * 2.0 - 1.0, raw, 1.0);
	float dist = length(view.xyz / view.w);
	float fog = 1.0 - exp(-dist / visibility_m);
	ALBEDO = mix(texture(screen_tex, uv).rgb * tint, fog_color, fog);
}
