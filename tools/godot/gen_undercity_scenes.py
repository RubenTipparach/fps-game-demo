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
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tscn import Scene, hexcolor, path, v3  # noqa: E402

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
    s.node("Camera3D", "Camera3D", "CameraRig", current=True, fov=67.0, near=0.02, far=400.0)
    wm = s.node("WeaponManager", "Node3D", "CameraRig/Camera3D",
                script=s.ext_res("Script", "res://scripts/Player/WeaponManager.cs"))
    s.node("ViewmodelRoot", "Node3D", wm)
    s.node("Flashlight", "SpotLight3D", "CameraRig/Camera3D", visible=False, position=v3(0.15, -0.1, 0),
           light_color=hexcolor("#fff1d6"), light_energy=4.0, light_bake_mode=0, shadow_enabled=True,
           spot_range=32.0, spot_angle=26.0, spot_angle_attenuation=0.6)
    s.node("Interactor", "Node", ".", script=script(s, "Player/Interactor.cs"))
    s.save(out("player.tscn"))


def npc():
    """A person: the model is chosen from data/npcs.json when the level wires it."""
    s = Scene("Npc", "CharacterBody3D")
    s.nodes[0][3].update(collision_layer=ENEMY, collision_mask=WORLD, script=script(s, "Entities/NpcActor.cs"))
    s.node("CollisionShape3D", "CollisionShape3D", ".", position=v3(0, 0.9, 0),
           shape=s.sub_res("CapsuleShape3D", radius=0.35, height=1.8))
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
    print("wrote", len(os.listdir(os.path.join(GAME, "scenes", "undercity"))), "scenes to game/scenes/undercity")


if __name__ == "__main__":
    main()
