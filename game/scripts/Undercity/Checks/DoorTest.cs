// The sliding entrances' check (scenes/undercity/tests/door_test.tscn): loads the hub and walks
// up to its public entrances (openspec/changes/hub-doorways, "Public entrances open as you walk
// up"). Every public entrance has its sliding door, timed from data/doors.json. The Anchor's opens
// as the runner walks up and closes behind the runner after its wait. A person walking the navmesh
// through the Fish Hall's closed north entrance finds it open before reaching it and walks through
// without stopping. Prints PASS or FAIL per check and quits with 1 on any failure.
//
//   flock /tmp/undercity-godot.lock timeout 900 godot --headless --path game res://scenes/undercity/tests/door_test.tscn
//
// It lives beside the other level checks because it runs the level's own scene. The walker is the
// NPC scene's own capsule in the group the doors watch, driven along the level's navmesh, rather
// than a copy of its size (CLAUDE.md 5.6).

#nullable enable
using System;
using System.Linq;
using System.Threading.Tasks;
using Brushfire;
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>The headless sliding-door check.</summary>
public partial class DoorTest : Node3D
{
    /// <summary>The level the check runs in.</summary>
    [Export] public string LevelScene { get; set; } = "res://levels/undercity/hub/hub.tscn";

    /// <summary>The public entrances the hub has (design section 3.3: 15, and the three shells').</summary>
    [Export] public int Entrances { get; set; } = 18;

    /// <summary>A walker's pace, metres a second: an NPC's walk.</summary>
    [Export] public float WalkMps { get; set; } = 1.5f;

    private const string NpcScene = "res://scenes/undercity/npc.tscn";

    private UndercityLevel? _level;
    private int _checks;
    private int _fail;

    private UndercityLevel L => _level!;

    /// <inheritdoc/>
    public override async void _Ready()
    {
        try
        {
            AutoTest.Active = true;
            _level = GD.Load<PackedScene>(LevelScene).Instantiate<UndercityLevel>();
            AddChild(_level);
            await Frames(10);
            var d = L.AutoTestState!.Data.Doors.Sliding;
            var doors = GetTree().GetNodesInGroup("ent_sliding_door").OfType<SlidingDoorway>().ToList();
            Check("every public entrance has its sliding door", doors.Count == Entrances, $"{doors.Count} of {Entrances}");
            Check("every sliding door is timed from data/doors.json",
                doors.All(x => Mathf.IsEqualApprox(x.TriggerRadius, (float)d.TriggerRadiusM) && Mathf.IsEqualApprox(x.Wait, (float)d.WaitS)
                               && x.OpenForGroups.SequenceEqual(new[] { SlidingDoorway.PeopleGroup })),
                $"trigger {d.TriggerRadiusM} m, wait {d.WaitS} s, opens for '{SlidingDoorway.PeopleGroup}'");
            await TheRunnerWalksIn(doors, d);
            await APersonWalksThrough(doors);
        }
        catch (Exception e)
        {
            Check("the test ran", false, e.ToString());
        }
        GD.Print($"[door_test] {_checks - _fail} of {_checks} passed");
        GetTree().Quit(_fail > 0 ? 1 : 0);
    }

    private static Door[] LeavesOf(Node door) => door.GetChildren().OfType<Door>().ToArray();

    private static Vector3 Outward(Node3D door) => -door.GlobalBasis.Z with { Y = 0 };

    private async Task TheRunnerWalksIn(System.Collections.Generic.List<SlidingDoorway> doors, SlidingDoorDef d)
    {
        var anchor = doors.FirstOrDefault(x => x.Name == "sliding_door_rusty_anchor_0");
        Check("the Rusty Anchor's entrance has its sliding door", anchor != null, anchor?.Name ?? "missing");
        if (anchor == null)
        {
            return;
        }
        var leaves = LeavesOf(anchor);
        var outward = Outward(anchor).Normalized();
        async Task StandAt(float metres, float seconds)
        {
            L.Player.GlobalPosition = anchor.GlobalPosition + outward * metres + Vector3.Up * 0.05f;
            L.Player.Velocity = Vector3.Zero;
            await Seconds(seconds);
        }
        await StandAt(12f, (float)d.WaitS + 1.5f);
        Check("far from it, the Anchor's entrance is shut", leaves.Length == 2 && leaves.All(l => l.OpenAmount == 0),
            string.Join(", ", leaves.Select(l => $"{l.Name} {l.OpenAmount:0.00}")));
        await StandAt(2.5f, 1.0f);
        Check("walking up, its leaves slide apart", leaves.All(l => l.OpenAmount >= 0.999f),
            string.Join(", ", leaves.Select(l => $"{l.Name} {l.OpenAmount:0.00}")) + " a second after coming within 2.5 m");
        await StandAt(12f, (float)d.WaitS + 1.5f);
        Check("walking away, they close behind the runner after the wait", leaves.All(l => l.OpenAmount == 0),
            string.Join(", ", leaves.Select(l => $"{l.Name} {l.OpenAmount:0.00}")));
    }

    private async Task APersonWalksThrough(System.Collections.Generic.List<SlidingDoorway> doors)
    {
        var hall = doors.FirstOrDefault(x => x.Name == "sliding_door_fish_hall_0");
        Check("the Fish Hall's north entrance has its sliding door", hall != null, hall?.Name ?? "missing");
        if (hall == null)
        {
            return;
        }
        var leaves = LeavesOf(hall);
        var outward = Outward(hall).Normalized();
        // Nobody else near: the runner stands off, and the door shuts.
        L.Player.GlobalPosition = hall.GlobalPosition + outward * 14f + Vector3.Up * 0.05f;
        await Seconds(3.0f);
        Check("the Fish Hall's entrance is shut before the walk", leaves.All(l => l.OpenAmount == 0),
            string.Join(", ", leaves.Select(l => $"{l.Name} {l.OpenAmount:0.00}")));

        // The walker: the NPC scene's own capsule, in the group the doors open for.
        var npc = GD.Load<PackedScene>(NpcScene).Instantiate<Node3D>();
        var shape = npc.GetChildren().OfType<CollisionShape3D>().First();
        var walker = new CharacterBody3D { Name = "Walker", CollisionLayer = Layers.Enemy, CollisionMask = Layers.World };
        walker.AddChild(new CollisionShape3D { Shape = shape.Shape, Position = shape.Position });
        npc.Free();
        AddChild(walker);
        walker.AddToGroup(SlidingDoorway.PeopleGroup);
        var map = GetWorld3D().NavigationMap;
        var from = NavigationServer3D.MapGetClosestPoint(map, hall.GlobalPosition + outward * 7f);
        var to = NavigationServer3D.MapGetClosestPoint(map, hall.GlobalPosition - outward * 4f);
        var path = NavigationServer3D.MapGetPath(map, from, to, true);
        walker.GlobalPosition = from + Vector3.Up * 0.1f;
        await Frames(2);
        var openAtDoor = -1f;
        var stuckS = 0f;
        var last = walker.GlobalPosition;
        var k = 1;
        var limit = 40.0;
        while (k < path.Length && limit > 0)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
            var dt = (float)GetPhysicsProcessDeltaTime();
            limit -= dt;
            var to2 = path[k] - walker.GlobalPosition;
            to2.Y = 0;
            if (to2.Length() < 0.3f)
            {
                k++;
                continue;
            }
            walker.Velocity = to2.Normalized() * WalkMps + Vector3.Down * 2f;
            walker.MoveAndSlide();
            var plane = (walker.GlobalPosition - hall.GlobalPosition).Dot(outward);
            if (openAtDoor < 0 && plane < 0.6f)
            {
                openAtDoor = leaves.Min(l => l.OpenAmount);
            }
            var moved = (walker.GlobalPosition - last) with { Y = 0 };
            stuckS = moved.Length() < WalkMps * dt * 0.3f ? stuckS + dt : 0f;
            last = walker.GlobalPosition;
            if (stuckS > 1.0f)
            {
                break;
            }
        }
        var arrived = (walker.GlobalPosition - to) with { Y = 0 };
        Check("the entrance is open before the person reaches it", openAtDoor >= 0.999f,
            openAtDoor < 0 ? "never reached the doorway" : $"leaves {openAtDoor:0.00} open 0.6 m from the doorway");
        Check("the person walks through without stopping", stuckS <= 1.0f && arrived.Length() < 0.8f,
            $"{arrived.Length():0.00} m from the goal inside, stopped for {stuckS:0.0} s");
        walker.QueueFree();
    }

    private async Task Frames(int n)
    {
        for (var i = 0; i < n; i++)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        }
    }

    private async Task Seconds(float s)
    {
        await ToSignal(GetTree().CreateTimer(s), SceneTreeTimer.SignalName.Timeout);
    }

    private void Check(string what, bool ok, string detail)
    {
        _checks++;
        if (!ok)
        {
            _fail++;
        }
        GD.Print($"[door_test] {(ok ? "PASS" : "FAIL")} {what}: {detail}");
    }
}
