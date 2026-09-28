// The placement check (scenes/undercity/tests/placement_test.tscn): loads a level's real sector
// glbs, with the NPCs, civilians and spawn points the importer placed in them, and tests every
// person with their own collider against the level's physics (openspec/specs/level-geometry,
// "People stand clear of the level"). A person passes when their capsule, lifted just off the
// floor, overlaps no world collider and no other person, and the floor is right under their feet.
// Every stop on an NPC's patrol is tested the same way. Every ladder out of the water is tested
// with the player's collider: its foot at least 0.5 m under the surface, room to climb its whole
// height, and room to stand on the floor at its top (openspec/changes/water-and-swimming). Prints
// PASS or FAIL per check and quits with 1 on any failure.
//
//   flock /tmp/undercity-godot.lock timeout 900 godot --headless --path game res://scenes/undercity/tests/placement_test.tscn
//
// It lives beside the entity scripts because it loads the real level, the real NPC scene and the
// real player scene rather than copies of their sizes (CLAUDE.md 5.6). The layout's own check
// (tools/levels/city_plan.py, check_standing_room) catches most of this before a build, against
// the plan's boxes; this one also covers what isn't a box: stalls, lamps, bollards, stairs, props.

#nullable enable
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Brushfire;
using Godot;
using GArray = Godot.Collections.Array<Godot.Rid>;

namespace Undercity.Client;

/// <summary>The headless placement check.</summary>
public partial class PlacementTest : Node3D
{
    /// <summary>The level folder whose sector glbs are loaded.</summary>
    [Export] public string LevelDir { get; set; } = "res://levels/undercity/hub";

    /// <summary>How far the body is lifted off the floor for the overlap test, metres: the floor
    /// itself touches the capsule's foot and isn't an overlap.</summary>
    [Export] public float LiftM { get; set; } = 0.03f;

    /// <summary>How far the floor may be from a person's feet, metres, above or below.</summary>
    [Export] public float FloorToleranceM { get; set; } = 0.05f;

    /// <summary>How high above a patrol stop the floor search starts, metres over the NPC's own
    /// floor (patrols walk the streets, under the canopies).</summary>
    [Export] public float PatrolProbeM { get; set; } = 1.5f;

    private const string PlayerScene = "res://scenes/undercity/player.tscn";

    private int _people;
    private int _fail;

    /// <inheritdoc/>
    public override async void _Ready()
    {
        try
        {
            var glbs = DirAccess.GetFilesAt(LevelDir).Where(f => f.EndsWith(".glb", StringComparison.Ordinal))
                .Order(StringComparer.Ordinal).ToArray();
            if (glbs.Length == 0)
            {
                throw new InvalidOperationException($"{LevelDir} has no sector glbs");
            }
            foreach (var f in glbs)
            {
                AddChild(GD.Load<PackedScene>($"{LevelDir}/{f}").Instantiate());
            }
            // The level's trimeshes are one-sided, and a query ignores a face it sees from
            // behind, so a body whose centre is inside a solid (a counter, a hull) would touch
            // nothing. In this test only, every face counts from both sides.
            foreach (var shape in FindChildren("*", nameof(CollisionShape3D), true, false).OfType<CollisionShape3D>()
                         .Select(c => c.Shape).OfType<ConcavePolygonShape3D>())
            {
                shape.BackfaceCollision = true;
            }
            // The colliders join the physics space on the next physics frames.
            for (var i = 0; i < 3; i++)
            {
                await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
            }
            var npcs = People("ent_npc").Concat(People("ent_civ")).ToList();
            foreach (var npc in npcs)
            {
                CheckNpc(npc);
            }
            CheckSpawns();
            CheckLadders();
        }
        catch (Exception e)
        {
            GD.PrintErr($"FAIL [placement_test] {e}");
            _fail++;
        }
        GD.Print($"[placement_test] {_people - _fail} of {_people} placements passed");
        GetTree().Quit(_fail > 0 ? 1 : 0);
    }

    private IEnumerable<CollisionObject3D> People(string group) =>
        GetTree().GetNodesInGroup(group).OfType<CollisionObject3D>().OrderBy(n => n.Name.ToString(), StringComparer.Ordinal);

    private static CollisionShape3D ColliderOf(Node body) =>
        body.GetChildren().OfType<CollisionShape3D>().FirstOrDefault()
        ?? throw new InvalidOperationException($"{body.Name} has no CollisionShape3D");

    private void CheckNpc(CollisionObject3D npc)
    {
        var col = ColliderOf(npc);
        var feet = npc.GlobalTransform;
        Check($"{npc.Name}", col.Shape, feet, col.Transform, new[] { npc.GetRid() }, Layers.World | Layers.Enemy);
        var patrol = npc.HasMeta("patrol") ? npc.GetMeta("patrol").AsString() : "";
        var stops = patrol.Split(';', StringSplitOptions.RemoveEmptyEntries);
        for (var i = 0; i < stops.Length; i++)
        {
            // Layout metres, x east and y south: Godot's x and z.
            var xy = stops[i].Split(',');
            var x = float.Parse(xy[0], CultureInfo.InvariantCulture);
            var z = float.Parse(xy[1], CultureInfo.InvariantCulture);
            var floor = FloorBelow(new Vector3(x, feet.Origin.Y + PatrolProbeM, z), PatrolProbeM * 2, Array.Empty<Rid>());
            if (floor is not { } y)
            {
                Fail($"{npc.Name} patrol stop {i} ({xy[0]}, {xy[1]}): no floor under it");
                continue;
            }
            // Against the world only: whoever stands on a stop now will have walked on.
            Check($"{npc.Name} patrol stop {i}", col.Shape, new Transform3D(feet.Basis, new Vector3(x, y, z)),
                col.Transform, new[] { npc.GetRid() }, Layers.World);
        }
    }

    // The player's own collider at every spawn marker (the game drops the player 0.05 m above it).
    private void CheckSpawns()
    {
        var player = GD.Load<PackedScene>(PlayerScene).Instantiate<Node3D>();
        var col = ColliderOf(player);
        foreach (var spawn in GetTree().GetNodesInGroup("ent_spawn").OfType<Node3D>()
                     .OrderBy(n => n.Name.ToString(), StringComparer.Ordinal))
        {
            Check($"{spawn.Name}", col.Shape, spawn.GlobalTransform, col.Transform, Array.Empty<Rid>(), Layers.World | Layers.Enemy);
        }
        player.Free();
    }

    /// <summary>How far under the water's surface a ladder's foot must reach, metres: a floating
    /// swimmer's hands are there (openspec/changes/water-and-swimming, task 4.2).</summary>
    private const float LadderUnderM = 0.5f;

    // Each ladder, with the player's own collider: its foot under the water, the climb clear from
    // a floating swimmer's feet to over the top, and the floor at the top where the climb ends.
    private void CheckLadders()
    {
        var player = GD.Load<PackedScene>(PlayerScene).Instantiate<Node3D>();
        var col = ColliderOf(player);
        var radius = col.Shape is CylinderShape3D c ? c.Radius : 0.4f;
        var data = Session.Data;
        var level = LevelDir.TrimEnd('/').Split('/').Last();
        var water = new LevelWater(data.Levels[level].Water, data.Water);
        var ladders = GetTree().GetNodesInGroup("ladders").OfType<Ladder>().OrderBy(n => n.Name.ToString(), StringComparer.Ordinal).ToList();
        if (ladders.Count == 0 && data.Levels[level].Water.Count > 0)
        {
            Fail($"{level} has water and no ladders");
        }
        foreach (var l in ladders)
        {
            var hold = l.HoldPoint(radius, 0);
            if (water.SurfaceAt(hold) is not { } surface)
            {
                Fail($"{l.Name}: no water under the ladder");
                continue;
            }
            _people++;
            if (l.BottomM > surface - LadderUnderM)
            {
                Fail($"{l.Name}: its foot is at {l.BottomM:0.00} m, less than {LadderUnderM} m under the surface ({surface:0.00} m)");
            }
            else
            {
                GD.Print($"PASS [placement_test] {l.Name} reaches {surface - l.BottomM:0.00} m under the surface");
            }
            var eye = 1.62f;
            for (var y = surface + (float)data.Water.FloatEyeAboveM - eye; y < l.TopM + 0.06f; y += 0.25f)
            {
                var feet = l.HoldPoint(radius, Math.Min(y, l.TopM + 0.05f));
                if (!Clear($"{l.Name} climb at {feet.Y:0.00} m", col.Shape, new Transform3D(Basis.Identity, feet), col.Transform))
                {
                    break;
                }
            }
            Clear($"{l.Name} step in over the top", col.Shape, new Transform3D(Basis.Identity,
                new Vector3(l.Landing.X, l.TopM + 0.02f, l.Landing.Z)), col.Transform);
            Check($"{l.Name} landing", col.Shape, new Transform3D(Basis.Identity, l.Landing), col.Transform, Array.Empty<Rid>(), Layers.World | Layers.Enemy);
        }
        player.Free();
    }

    // Overlap only: nothing in the level where the body is.
    private bool Clear(string who, Shape3D shape, Transform3D feet, Transform3D shapeLocal)
    {
        _people++;
        var q = new PhysicsShapeQueryParameters3D
        {
            Shape = shape,
            Transform = feet * shapeLocal,
            CollisionMask = Layers.World | Layers.Enemy,
        };
        var hits = GetWorld3D().DirectSpaceState.IntersectShape(q, 8).Select(h => h["collider"].As<Node>())
            .Where(n => n is not null).Select(n => $"{n.GetParent()?.Name}/{n.Name}").Distinct(StringComparer.Ordinal).ToList();
        if (hits.Count > 0)
        {
            Fail($"{who}: the body overlaps {string.Join(", ", hits)}");
            return false;
        }
        return true;
    }

    private void Check(string who, Shape3D shape, Transform3D feet, Transform3D shapeLocal, Rid[] exclude, uint mask)
    {
        _people++;
        var space = GetWorld3D().DirectSpaceState;
        var q = new PhysicsShapeQueryParameters3D
        {
            Shape = shape,
            Transform = new Transform3D(feet.Basis, feet.Origin + Vector3.Up * LiftM) * shapeLocal,
            CollisionMask = mask,
            Exclude = new GArray(exclude),
        };
        var hits = space.IntersectShape(q, 8)
            .Select(h => h["collider"].As<Node>())
            .Where(n => n is not null)
            .Select(n => $"{n.GetParent()?.Name}/{n.Name}")
            .Distinct(StringComparer.Ordinal)
            .ToList();
        var at = $"({feet.Origin.X:0.##}, {feet.Origin.Z:0.##}) at {feet.Origin.Y:0.##} m";
        if (hits.Count > 0)
        {
            Fail($"{who} {at}: the body overlaps {string.Join(", ", hits)}");
            return;
        }
        var floor = FloorBelow(feet.Origin + Vector3.Up * 0.5f, 1.0f, exclude);
        if (floor is not { } y)
        {
            Fail($"{who} {at}: no floor within 0.5 m under the feet");
            return;
        }
        var gap = feet.Origin.Y - y;
        if (Math.Abs(gap) > FloorToleranceM)
        {
            Fail($"{who} {at}: the floor is {gap:0.00} m {(gap > 0 ? "below" : "above")} the feet");
            return;
        }
        GD.Print($"PASS [placement_test] {who} {at}");
    }

    private float? FloorBelow(Vector3 from, float depth, Rid[] exclude)
    {
        var q = PhysicsRayQueryParameters3D.Create(from, from + Vector3.Down * depth, Layers.World, new GArray(exclude));
        var hit = GetWorld3D().DirectSpaceState.IntersectRay(q);
        return hit.Count > 0 ? hit["position"].AsVector3().Y : null;
    }

    private void Fail(string message)
    {
        GD.PrintErr($"FAIL [placement_test] {message}");
        _fail++;
    }
}
