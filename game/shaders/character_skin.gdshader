// A body's skin (openspec/changes/character-lighting, design sections 1 and 9). It draws what
// the StandardMaterial3D skin drew, one for one: the skin atlas, the normal derived from it
// (tools/blender/build_npcs.py) with the roughness mask in its alpha (0.42 on the T-zone, 0.55 on
// the cheeks, 0.62 on the body), specular 0.42 (F0 0.028), and subsurface scattering in skin mode
// with transmittance, so ears glow against a rim gel. It adds wetness (owner J1: "he's not wet in
// doors"): the mask is the wet look, and dry skin is rougher by the data's dry add.
//
// "wetness" is per instance, 0 dry to 1 soaked, set by BodyWetness from the core's rule
// (Undercity.Core.World.Wetness). The dry add is a global the game sets from
// data/character_lighting.json at start (CharacterShading); project.godot declares it with a
// neutral 0. tools/godot/gen_character_materials.py writes the materials that use this shader;
// nothing here is tuned inline.
shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx, sss_mode_skin;

uniform sampler2D albedo_texture : source_color, filter_linear_mipmap;
uniform sampler2D normal_texture : hint_normal, filter_linear_mipmap;
uniform float specular = 0.42;
uniform float normal_strength = 1.0;
uniform float sss_strength = 0.3;
uniform vec3 transmittance_color : source_color = vec3(0.9, 0.35, 0.25);
uniform float transmittance_depth = 0.2;
uniform float transmittance_boost = 0.3;
global uniform float character_skin_dry_roughness_add;
// A body's skin and outfit are surfaces of one mesh instance, so an instance uniform they share
// must sit at the same index in both, or only one of them reads it (Godot warns).
instance uniform float wetness : instance_index(0) = 0.0;

void fragment() {
	vec4 n = texture(normal_texture, UV);
	ALBEDO = texture(albedo_texture, UV).rgb;
	NORMAL_MAP = n.rgb;
	NORMAL_MAP_DEPTH = normal_strength;
	float dry = min(n.a + character_skin_dry_roughness_add, 1.0);
	ROUGHNESS = mix(dry, n.a, clamp(wetness, 0.0, 1.0));
	SPECULAR = specular;
	METALLIC = 0.0;
	SSS_STRENGTH = sss_strength;
	SSS_TRANSMITTANCE_COLOR = vec4(transmittance_color, 1.0);
	SSS_TRANSMITTANCE_DEPTH = transmittance_depth;
	SSS_TRANSMITTANCE_BOOST = transmittance_boost;
}
