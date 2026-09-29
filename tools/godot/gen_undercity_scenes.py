#!/usr/bin/env python3
"""Generate Undercity's entity scenes and its player scene.

    python3 tools/godot/gen_undercity_scenes.py

Writes game/scenes/undercity/*.tscn. Each scene composes a thin script
(game/scripts/Undercity/...) with a prop model built in Blender
(tools/blender/build_undercity_props.py -> game/models/undercity/props/*.glb) and the collision
the interactor's ray hits. The importer (game/addons/brushfire_tools/blender_level_import.gd)
places these scenes at a level's ENT_ empties. Re-running overwrites them (CLAUDE.md 11).

Conventions: a node's forward is -Z, the side the player uses. Collision layers are Brushfire's
(game/scripts/Core/Damage.cs, Layers): World 1, Player 2, Enemy 4, Pickup 8. Props collide on
World; NPCs on Enemy, so the player bumps into them; small pickups and the bed on Pickup, which the
interactor's ray hits and the player's body doesn't. Areas sit on no layer and watch the Player.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tscn import Raw, Scene, hexcolor, path, v2, v3  # noqa: E402

GAME = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "game")
PROPS = "res://models/undercity/props/"
WORLD, PLAYER, ENEMY, PICKUP = 1, 2, 4, 8


def out(name):
    return os.path.join(GAME, "scenes", "undercity", name)


def script(s, path):
    return s.ext_res("Script", "res://scripts/Undercity/" + path)


def player():
    """Brushfire's controller without its weapons or HUD, plus the use key (Undercity's HUD is ui/undercity)."""
    s = Scene("Player", "CharacterBody3D")
    s.nodes[0][3].update(collision_layer=PLAYER, collision_mask=WORLD | ENEMY,
                         script=s.ext_res("Script", "res://scripts/Player/PlayerController.cs"))
    s.node("CollisionShape3D", "CollisionShape3D", ".", position=v3(0, 0.9, 0),
           shape=s.sub_res("CylinderShape3D", height=1.8, radius=0.4))
    s.node("CameraRig", "Node3D", ".")
    # far 1,500 m: the hub's skyline stands up to 1.2 km out (openspec/changes/hub-skyline, section 3)
    s.node("Camera3D", "Camera3D", "CameraRig", current=True, fov=67.0, near=0.02, far=1500.0)
    wm = s.node("WeaponManager", "Node3D", "CameraRig/Camera3D",
                script=s.ext_res("Script", "res://scripts/Player/WeaponManager.cs"))
    s.node("ViewmodelRoot", "Node3D", wm)
    s.node("Flashlight", "SpotLight3D", "CameraRig/Camera3D", visible=False, position=v3(0.15, -0.1, 0),
           light_color=hexcolor("#fff1d6"), light_energy=4.0, light_bake_mode=0, shadow_enabled=True,
           spot_range=32.0, spot_angle=26.0, spot_angle_attenuation=0.6)
    # the underwater view: a 2 x 2 quad the shader stretches over the screen, never culled
    s.node("Underwater", "MeshInstance3D", "CameraRig/Camera3D", visible=False, cast_shadow=0,
           extra_cull_margin=16384.0, script=script(s, "Player/UnderwaterView.cs"),
           mesh=s.sub_res("QuadMesh", size=v2(2, 2)),
           material_override=s.ext_res("Material", "res://materials/underwater.tres"))
    s.node("Interactor", "Node", ".", script=script(s, "Player/Interactor.cs"))
    s.node("Water", "Node", ".", script=script(s, "Player/PlayerWater.cs"))
    # draws the belt's firearm into the WeaponManager and feeds it (openspec/changes/archive/2026-09-28-hub-combat)
    s.node("Weapons", "Node", ".", script=script(s, "Player/WeaponAdapter.cs"))
    # the wrist-deck glow, characters only; WristLight.cs sets it from data/character_lighting.json
    s.node("Wrist", "OmniLight3D", "CameraRig/Camera3D", light_bake_mode=0, shadow_enabled=False,
           script=script(s, "Lighting/WristLight.cs"))
    s.save(out("player.tscn"))


NPC_RADIUS_M = 0.35
NPC_HEIGHT_M = 1.8


def kerb_floor_angle():
    """The steepest contact a person's capsule still stands on, radians: where the capsule's
    rounded bottom meets the edge of a kerb as high as the level's paving (city_plan.PAVED_Z),
    plus 3 degrees. The navmesh runs over kerbs; without this a fleeing person stops at the first
    one, its edge a wall to CharacterBody3D's default 45 degrees (openspec/changes/archive/2026-09-28-hub-combat)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "levels"))
    from city_plan import PAVED_Z  # noqa: E402  (the one source of the kerb height)
    return math.acos((NPC_RADIUS_M - PAVED_Z) / NPC_RADIUS_M) + math.radians(3)


def npc():
    """A person: the model is chosen from data/npcs.json when the level wires it."""
    s = Scene("Npc", "CharacterBody3D")
    s.nodes[0][3].update(collision_layer=ENEMY, collision_mask=WORLD, script=script(s, "Entities/NpcActor.cs"),
                         floor_max_angle=round(kerb_floor_angle(), 4), floor_snap_length=0.2)
    s.node("CollisionShape3D", "CollisionShape3D", ".", position=v3(0, NPC_HEIGHT_M / 2, 0),
           shape=s.sub_res("CapsuleShape3D", radius=NPC_RADIUS_M, height=NPC_HEIGHT_M))
    # how they flee and close in, on the level's baked navmesh (openspec/changes/archive/2026-09-28-hub-combat). The
    # navmesh lies 0.3 m above the street (level_common.add_navigation's cells), and the agent
    # measures in 3D, so the path is lowered to the feet; a waypoint then counts as reached within
    # 0.35 m, and a sprinter (0.09 m a physics tick) turns late enough not to clip the corner the
    # path bends around
    s.node("Nav", "NavigationAgent3D", ".", radius=NPC_RADIUS_M, height=NPC_HEIGHT_M, path_height_offset=0.3,
           path_desired_distance=0.35, target_desired_distance=0.8, avoidance_enabled=False)
    s.save(out("npc.tscn"))


def door():
    """A swinging leaf for a 1.4 x 2.4 m opening: the hinge on the left jamb, 2 cm clear of it."""
    s = Scene("Door", "Node3D")
    s.nodes[0][3].update(script=script(s, "Entities/LockedDoor.cs"))
    s.node("Hinge", "Node3D", ".", position=v3(-0.68, 0.01, 0))
    s.instance("Leaf", PROPS + "door_leaf.glb", "Hinge")
    s.save(out("door.tscn"))


def barrier():
    """The checkpoint boom: its arm lifts about Z from the left post."""
    s = Scene("Barrier", "Node3D")
    s.nodes[0][3].update(script=script(s, "Entities/LockedDoor.cs"), Moving=path("Model/arm"),
                         OpenRotationDeg=v3(0, 0, 80), OpenTimeS=1.6)
    s.instance("Model", PROPS + "barrier.glb")
    s.save(out("barrier.tscn"))


def loot(model):
    s = Scene("Container", "Node3D")
    s.nodes[0][3].update(script=script(s, "Entities/LootContainer.cs"))
    s.instance("Model", PROPS + f"{model}.glb")
    s.save(out(f"loot_{model}.tscn"))


def terminal():
    s = Scene("Terminal", "Node3D")
    s.nodes[0][3].update(script=script(s, "Entities/TerminalActor.cs"))
    s.instance("Model", PROPS + "terminal.glb")
    s.save(out("terminal.tscn"))


def exits():
    # A gate stands at the entity; a grate and a wall panel mount on the wall 0.55 m behind it.
    for style, model, pos in (("gate", "gate", (0, 0, 0)), ("grate", "grate", (0, 0.1, 0.55)),
                              ("panel", "wall_panel", (0, 1.3, 0.55))):
        s = Scene("Exit", "Node3D")
        s.nodes[0][3].update(script=script(s, "Entities/LevelExit.cs"))
        s.instance("Model", PROPS + f"{model}.glb", position=v3(*pos))
        s.save(out(f"exit_{style}.tscn"))
    s = Scene("Exit", "Node3D")
    s.nodes[0][3].update(script=script(s, "Entities/LevelExit.cs"), WalkIn=True)
    s.node("Area", "Area3D", ".", collision_layer=0, collision_mask=PLAYER)
    s.node("Shape", "CollisionShape3D", "Area", position=v3(0, 1.5, 0),
           shape=s.sub_res("BoxShape3D", size=v3(4, 3, 1.5)))
    s.save(out("exit_none.tscn"))


def world_item():
    s = Scene("WorldItem", "Node3D")
    s.nodes[0][3].update(script=script(s, "Entities/WorldItem.cs"))
    s.instance("Model", PROPS + "item_pouch.glb")
    s.node("Body", "StaticBody3D", ".", collision_layer=PICKUP, collision_mask=0)
    s.node("CollisionShape3D", "CollisionShape3D", "Body", position=v3(0, 0.12, 0),
           shape=s.sub_res("BoxShape3D", size=v3(0.5, 0.24, 0.4)))
    s.save(out("world_item.tscn"))


def areas():
    for name, cs, height in (("zone", "Entities/RestrictedZone.cs", 6.0), ("trigger", "Entities/StoryTrigger.cs", 3.0)):
        s = Scene(name.title(), "Area3D")
        s.nodes[0][3].update(script=script(s, cs), collision_layer=0, collision_mask=PLAYER, monitorable=False)
        s.node("Shape", "CollisionShape3D", ".", position=v3(0, height / 2, 0),
               shape=s.sub_res("BoxShape3D", size=v3(4, height, 4)))
        s.save(out(f"{name}.tscn"))


def bed():
    """Capsule 12: a use box a little larger than the capsule and as tall as a standing eye line
    (2.2 m), so the ray meets it before the capsule's shell from anywhere in the corridor."""
    s = Scene("Bed", "Node3D")
    s.nodes[0][3].update(script=script(s, "Entities/Bed.cs"))
    s.node("Body", "StaticBody3D", ".", collision_layer=PICKUP, collision_mask=0)
    s.node("CollisionShape3D", "CollisionShape3D", "Body", position=v3(0, 1.1, 0),
           shape=s.sub_res("BoxShape3D", size=v3(2.6, 2.2, 3.8)))
    s.save(out("bed.tscn"))


def ladder():
    """A ladder out of the water. The level plan builds its stiles and rungs with the quay and
    writes its size into the entity (tools/levels/city_plan.py ladder()); the scene holds the use
    box over its top, where "Climb down" is offered: from the grab hoops (1 m above the floor, 0.5 m
    in) to 0.3 m out over the water."""
    s = Scene("Ladder", "Node3D")
    s.nodes[0][3].update(script=script(s, "Entities/Ladder.cs"))
    s.node("Body", "StaticBody3D", ".", collision_layer=PICKUP, collision_mask=0)
    s.node("CollisionShape3D", "CollisionShape3D", "Body", position=v3(0, 0.4, -0.15),
           shape=s.sub_res("BoxShape3D", size=v3(1.0, 1.2, 0.9)))
    s.save(out("ladder.tscn"))


def splash():
    """Water thrown up where something falls in (ParticleBurst.cs frees it once it has played). One
    shot of droplets thrown up and out, falling back under gravity; the thrower sets how many."""
    s = Scene("Splash", "GPUParticles3D")
    drops = s.sub_res("ParticleProcessMaterial", direction=v3(0, 1, 0), spread=38.0,
                      initial_velocity_min=2.2, initial_velocity_max=4.8, gravity=v3(0, -9.8, 0),
                      scale_min=0.5, scale_max=1.3, emission_shape=1, emission_sphere_radius=0.35)
    look = s.sub_res("StandardMaterial3D", transparency=1, shading_mode=1, vertex_color_use_as_albedo=True,
                     albedo_color=hexcolor("#a9c9c6", 0.7), billboard_mode=3, billboard_keep_scale=True)
    s.nodes[0][3].update(script=script(s, "Player/ParticleBurst.cs"), emitting=False, amount=48, lifetime=0.9,
                         one_shot=True, explosiveness=0.92, cast_shadow=0, process_material=drops,
                         draw_pass_1=s.sub_res("QuadMesh", size=v2(0.09, 0.09), material=look))
    s.save(out("splash.tscn"))


def kestrel():
    """The Kestrel 10mm in the runner's hand (openspec/changes/archive/2026-09-28-hub-combat, design section 8):
    Brushfire's Weapon with the prop kit's model, its muzzle and flash. WeaponAdapter sets its
    numbers from data/weapons.json when it is drawn; the scene holds only its parts. Viewmodel
    space, as Brushfire's weapons (WeaponManager draws them at 1/4 scale): the model is full size,
    its barrel along -Z, and the muzzle sits where the model's barrel ends
    (build_undercity_props.kestrel: (0, 0.155, 0.095) in Blender, (0, 0.095, -0.155) here)."""
    s = Scene("Kestrel", "Node3D")
    s.nodes[0][3].update(script=s.ext_res("Script", "res://scripts/Player/Weapon.cs"), WeaponId="kestrel",
                         DisplayName="Kestrel 10mm", Slot=0, Owned=True)
    at = (0.15, -0.19, -0.34)
    s.instance("Model", PROPS + "kestrel.glb", ".", position=v3(*at))
    muzzle = s.node("Muzzle", "Marker3D", ".", position=v3(at[0], at[1] + 0.095, at[2] - 0.155))
    s.node("Flash", "MeshInstance3D", muzzle, cast_shadow=0, gi_mode=2,
           mesh=s.sub_res("QuadMesh", size=v2(0.14, 0.14)),
           material_override=s.ext_res("Material", "res://materials/fx/muzzle_flash.tres"))
    os.makedirs(out("weapons"), exist_ok=True)
    s.save(out("weapons/kestrel.tscn"))


def blood():
    """Blood where a shot hits a person (ParticleBurst.cs plays it along the hit's normal and frees
    it). A short spray of dark drops that falls away under gravity."""
    s = Scene("Blood", "GPUParticles3D")
    drops = s.sub_res("ParticleProcessMaterial", direction=v3(0, 1, 0), spread=35.0,
                      initial_velocity_min=1.0, initial_velocity_max=3.0, gravity=v3(0, -9.8, 0),
                      scale_min=0.6, scale_max=1.4, emission_shape=1, emission_sphere_radius=0.04)
    look = s.sub_res("StandardMaterial3D", transparency=1, shading_mode=1, vertex_color_use_as_albedo=True,
                     albedo_color=hexcolor("#5a0a0c", 0.9), billboard_mode=3, billboard_keep_scale=True)
    s.nodes[0][3].update(script=script(s, "Player/ParticleBurst.cs"), emitting=False, amount=24, lifetime=0.6,
                         one_shot=True, explosiveness=0.95, cast_shadow=0, process_material=drops,
                         draw_pass_1=s.sub_res("QuadMesh", size=v2(0.035, 0.035), material=look))
    s.save(out("blood.tscn"))


def conversation_rig():
    """The conversation rig (openspec/changes/character-lighting, design section 4): a spot key and
    two omni gels. ConversationRig.cs places them around the speaker's head and sets their colour,
    energy and reach from data/character_lighting.json; here they are dark and unbaked."""
    s = Scene("ConversationRig", "Node3D")
    s.nodes[0][3].update(script=script(s, "Lighting/ConversationRig.cs"))
    s.node("Key", "SpotLight3D", ".", light_energy=0.0, light_bake_mode=0, shadow_enabled=True)
    s.node("Rim", "OmniLight3D", ".", light_energy=0.0, light_bake_mode=0)
    s.node("Accent", "OmniLight3D", ".", light_energy=0.0, light_bake_mode=0)
    s.save(out("conversation_rig.tscn"))


# A searchlight's cone (openspec/changes/hub-skyline, design section 3a): 900 m long, 3 degrees
# wide, off a lamp 0.8 m across. The shader stands it on its base and sweeps it, so the node's box
# is set to hold every place the sweep can reach (up to 35 degrees from vertical).
BEAM_LENGTH_M = 900.0
BEAM_WIDTH_DEG = 3.0
BEAM_LAMP_RADIUS_M = 0.8
BEAM_MAX_TILT_DEG = 35.0


def searchlight():
    """One searchlight beam: an open cone drawn by shaders/searchlight.gdshader, which casts no
    light and no shadow. The level sets each beam's period, phase and tilt from the layout
    (tools/levels/skyline.py searchlights) as instance shader parameters."""
    top = BEAM_LAMP_RADIUS_M + BEAM_LENGTH_M * math.tan(math.radians(BEAM_WIDTH_DEG / 2))
    reach = BEAM_LENGTH_M * math.sin(math.radians(BEAM_MAX_TILT_DEG)) + top
    s = Scene("Searchlight", "MeshInstance3D")
    beam = s.sub_res("ShaderMaterial", shader=s.ext_res("Shader", "res://shaders/searchlight.gdshader"),
                      **{"shader_parameter/length_m": BEAM_LENGTH_M})
    cone = s.sub_res("CylinderMesh", material=beam, top_radius=top, bottom_radius=BEAM_LAMP_RADIUS_M,
                     height=BEAM_LENGTH_M, radial_segments=24, rings=1, cap_top=False, cap_bottom=False)
    s.nodes[0][3].update(mesh=cone, cast_shadow=0, gi_mode=0,
                         custom_aabb=Raw(f"AABB({-reach:.1f}, -1, {-reach:.1f}, {2 * reach:.1f}, "
                                         f"{BEAM_LENGTH_M + 2:.1f}, {2 * reach:.1f})"))
    s.save(out("searchlight.tscn"))


def main():
    player()
    npc()
    door()
    barrier()
    for m in ("locker", "safe", "crate", "tool_box", "shelf", "offering_box", "stash_box"):
        loot(m)
    terminal()
    exits()
    world_item()
    areas()
    bed()
    ladder()
    splash()
    kestrel()
    blood()
    conversation_rig()
    searchlight()
    print("wrote", len(os.listdir(os.path.join(GAME, "scenes", "undercity"))), "scenes to game/scenes/undercity")


if __name__ == "__main__":
    main()
