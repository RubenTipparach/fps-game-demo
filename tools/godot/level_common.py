"""Shared pieces for building level scenes: environment, lightmapping, probes, entities.

Every level uses the same recipe:
  * LevelRoot script on the root node (spawns the player, tracks stats).
  * Static geometry with GI mode "Static" (baked into lightmaps). Level lights use bake mode
    "Static": their direct AND indirect light is baked, nothing is computed at runtime.
  * LightmapGI with directional lightmaps (so normal maps still read under baked light),
    automatic probe generation plus hand-placed LightmapProbe nodes where dynamic objects go
    (enemies, pickups, the viewmodel are lit by those probes).
  * Box-projected ReflectionProbes (update once) so metals and glossy PBR surfaces reflect
    the baked lighting.
"""
from tscn import Raw, color, hexcolor, v3

ENTITY_SCENES = {
    "player_start": "res://scenes/props/player_start.tscn",
    "grunt": "res://scenes/enemies/grunt.tscn",
    "brute": "res://scenes/enemies/brute.tscn",
    "drone": "res://scenes/enemies/drone.tscn",
    "health": "res://scenes/pickups/health.tscn",
    "megahealth": "res://scenes/pickups/megahealth.tscn",
    "armor": "res://scenes/pickups/armor.tscn",
    "armor_heavy": "res://scenes/pickups/armor_heavy.tscn",
    "shells": "res://scenes/pickups/shells.tscn",
    "bullets": "res://scenes/pickups/bullets.tscn",
    "rockets": "res://scenes/pickups/rockets.tscn",
    "chaingun": "res://scenes/pickups/weapon_chaingun.tscn",
    "rocket_launcher": "res://scenes/pickups/weapon_rocket_launcher.tscn",
    "barrel": "res://scenes/props/explosive_barrel.tscn",
    "exit": "res://scenes/props/exit.tscn",
    "door": "res://scenes/props/door.tscn",
    "doorway": "res://scenes/props/doorway.tscn",
    "archway_400x350": "res://scenes/props/archway_400x350.tscn",
    "archway_400x400": "res://scenes/props/archway_400x400.tscn",
    "ceiling_light": "res://scenes/props/ceiling_light.tscn",
    "wall_lamp": "res://scenes/props/wall_lamp.tscn",
}


def setup_root(scene, title):
    scene.nodes[0][3].update(script=scene.ext_res("Script", "res://scripts/World/LevelRoot.cs"), LevelTitle=title)


def add_environment(scene, fog_color="#20232a", fog_density=0.006, exposure=1.15, sky_color="#0a0b0e"):
    env = scene.sub_res(
        "Environment",
        background_mode=1,                       # clear colour; interiors don't see the sky
        background_color=hexcolor(sky_color),
        ambient_light_source=1,                   # disabled: lightmaps + probes provide ambient
        reflected_light_source=0,
        tonemap_mode=4,                           # AgX
        tonemap_exposure=exposure,
        ssao_enabled=True,
        ssao_radius=1.2,
        ssao_intensity=1.6,
        ssao_light_affect=0.15,
        glow_enabled=True,
        glow_intensity=0.55,
        glow_bloom=0.04,
        glow_hdr_threshold=1.1,
        glow_blend_mode=1,
        fog_enabled=True,
        fog_light_color=hexcolor(fog_color),
        fog_density=fog_density,
        fog_sky_affect=0.0,
    )
    scene.node("WorldEnvironment", "WorldEnvironment", ".", environment=env)


def add_lightmap(scene, texel_scale=1.0, quality=1, bounces=3, probes_subdiv=2):
    scene.node("LightmapGI", "LightmapGI", ".",
               quality=quality, bounces=bounces, directional=True, interior=True,
               use_denoiser=True, denoiser_strength=0.12, texel_scale=texel_scale,
               generate_probes_subdiv=probes_subdiv, environment_mode=0)


def add_probes(scene, points, parent="LightProbes"):
    scene.node(parent, "Node3D", ".")
    for i, p in enumerate(points):
        scene.node(f"Probe{i}", "LightmapProbe", parent, position=v3(*p))


def add_reflection_probes(scene, boxes, parent="ReflectionProbes"):
    """boxes: (name, (x0, x1), (y0, y1), (z0, z1))."""
    scene.node(parent, "Node3D", ".")
    for name, (x0, x1), (y0, y1), (z0, z1) in boxes:
        cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
        # capture from eye height
        eye = y0 + 1.7
        scene.node(name, "ReflectionProbe", parent, position=v3(cx, eye, cz),
                   size=v3(x1 - x0, y1 - y0, z1 - z0), origin_offset=v3(0, cy - eye, 0),
                   box_projection=True, interior=True, update_mode=0, ambient_mode=0,
                   max_distance=max(x1 - x0, y1 - y0, z1 - z0) * 1.5, intensity=1.0)


def add_entities(scene, entities, parent="Entities"):
    """entities: (kind, (x, y, z), yaw_degrees[, extra props dict])."""
    scene.node(parent, "Node3D", ".")
    counts = {}
    for e in entities:
        kind, pos, yaw = e[0], e[1], e[2]
        extra = e[3] if len(e) > 3 else {}
        counts[kind] = counts.get(kind, 0) + 1
        name = f"{kind.title().replace('_', '')}{counts[kind]}"
        props = dict(position=v3(*pos))
        if yaw:
            props["rotation_degrees"] = v3(0, yaw, 0)
        props.update(extra)
        scene.instance(name, ENTITY_SCENES[kind], parent, **props)


def add_trigger(scene, name, kind, box_min, box_max, parent="Triggers", **props):
    x0, y0, z0 = box_min
    x1, y1, z1 = box_max
    if not any(n[0] == parent for n in scene.nodes):
        scene.node(parent, "Node3D", ".")
    t = scene.node(name, "Area3D", parent, position=v3((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                   script=scene.ext_res("Script", "res://scripts/World/Trigger.cs"), Kind=kind, **props)
    scene.node("Shape", "CollisionShape3D", t,
               shape=scene.sub_res("BoxShape3D", size=v3(x1 - x0, y1 - y0, z1 - z0)))


def add_fill_lights(scene, lights, parent="FillLights"):
    """Big, soft coloured fills (UT99-style warm/cool contrast). lights: (pos, hex, energy, range)."""
    scene.node(parent, "Node3D", ".")
    for i, (pos, hexc, energy, rng) in enumerate(lights):
        scene.node(f"Fill{i}", "OmniLight3D", parent, position=v3(*pos), light_color=hexcolor(hexc),
                   light_energy=energy, light_indirect_energy=1.2, omni_range=rng, omni_attenuation=0.8,
                   light_size=1.5, light_bake_mode=1, shadow_enabled=True)


def add_navigation(scene, parent_name="Navigation"):
    nav = scene.sub_res("NavigationMesh", agent_height=1.8, agent_radius=0.4, agent_max_climb=0.5,
                        agent_max_slope=46.0, cell_size=0.2, cell_height=0.1,
                        geometry_parsed_geometry_type=1, geometry_collision_mask=1)
    return scene.node(parent_name, "NavigationRegion3D", ".", navigation_mesh=nav)
