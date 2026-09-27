// Quake/Unreal-style sky surface: put this material on a brush face (CSG box face, TrenchBroom
// texture "sky_*", Blender material "sky_*") and the face becomes a window onto the sky.
// Like Quake's sky it ignores the face's UVs and projects two tileable layers onto a squashed
// dome around the viewer; the back layer and the clouds scroll at different speeds, and an
// optional moon/planet is drawn analytically. Unshaded and fog-free, so the sky stays bright
// even though the lightmap on this face is black.
shader_type spatial;
render_mode unshaded, fog_disabled, shadows_disabled, ambient_light_disabled;

uniform sampler2D back_layer : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D cloud_layer : source_color, filter_linear_mipmap, repeat_enable;
uniform float layer_scale = 0.55;
uniform vec2 back_speed = vec2(0.002, 0.001);
uniform vec2 cloud_speed = vec2(0.012, 0.006);
uniform float dome_squash = 3.0;          // Quake used 3: flattens the dome so layers read as sky, not a ball
uniform vec3 tint : source_color = vec3(1.0);
uniform float energy = 1.0;
uniform vec3 moon_direction = vec3(0.3, 0.8, -0.5);
uniform float moon_size = 0.0;            // angular radius in radians; 0 = no moon
uniform vec3 moon_color : source_color = vec3(0.9, 0.92, 1.0);
uniform float moon_phase = 0.35;          // 0 = full, 1 = new
uniform vec3 glow_color : source_color = vec3(0.0);   // haze towards the horizon (e.g. furnace glow)

void fragment() {
	vec3 d = normalize(mat3(INV_VIEW_MATRIX) * VERTEX);
	vec3 q = normalize(vec3(d.x, max(d.y, 0.02) * dome_squash, d.z));
	vec2 uv = q.xz * layer_scale / max(q.y, 0.2);
	vec3 col = texture(back_layer, uv + TIME * back_speed).rgb;

	if (moon_size > 0.0) {
		vec3 md = normalize(moon_direction);
		float c = dot(d, md);
		float r = acos(clamp(c, -1.0, 1.0)) / moon_size;
		if (r < 1.0) {
			// disc with limb darkening and a phase terminator
			vec3 side = normalize(cross(md, vec3(0.0, 1.0, 0.0)));
			vec3 up = cross(side, md);
			vec2 p = vec2(dot(d - md * c, side), dot(d - md * c, up)) / sin(moon_size);
			float z = sqrt(max(1.0 - dot(p, p), 0.0));
			float lit = smoothstep(-0.1, 0.1, dot(vec3(p, z), normalize(vec3(-1.0 + 2.0 * moon_phase, 0.2, 1.0 - moon_phase))));
			float craters = texture(cloud_layer, p * 0.35 + 0.5).a;
			col = mix(col, moon_color * (0.55 + 0.45 * z) * (1.0 - 0.35 * craters), lit * smoothstep(1.0, 0.96, r));
		}
		col += moon_color * 0.25 * exp(-max(r - 1.0, 0.0) * 1.5) * step(1.0, r);
	}

	vec4 clouds = texture(cloud_layer, uv * 1.6 + TIME * cloud_speed);
	col = mix(col, clouds.rgb, clouds.a);
	col += glow_color * pow(1.0 - clamp(d.y, 0.0, 1.0), 3.0);
	ALBEDO = col * tint * energy;
}
