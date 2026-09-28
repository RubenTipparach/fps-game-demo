// The ragdoll check (scenes/undercity/tests/ragdoll_test.tscn): stands each listed NPC scene on a
// 0.45 m step with its back to the edge, collapses it with a shove to the chest, and checks the
// spec (openspec/changes/npc-characters, "Deaths and knockouts are ragdolls that come to rest"):
// the body falls off the step without exploding, and it is frozen once data/npc_bodies.json's
// settle time is up. Prints PASS or FAIL per body and quits with 1 on any failure.
//
//   flock /tmp/undercity-godot.lock timeout 600 godot --headless --path game res://scenes/undercity/tests/ragdoll_test.tscn
//
// It lives beside the entity scripts because it loads the real generated NPC scenes and the real
// data, not a copy of either (CLAUDE.md 5.6). The numbers it checks against are the
// measurement's (docs/spikes/npc-pipeline): Jolt peaked at 6.9-7.7 m/s; GodotPhysics3D exploded
// past 2,000 m/s.

#nullable enable
using System;
using System.Linq;
using System.Threading.Tasks;
using Godot;
using Undercity.Core;

namespace Undercity.Client;

/// <summary>The headless ragdoll check.</summary>
public partial class RagdollTest : Node3D
{
    /// <summary>The NPC scenes to drop, one after another.</summary>
    [Export] public string[] Bodies { get; set; } = Array.Empty<string>();

    /// <summary>The step's top, metres.</summary>
    [Export] public float StepTopM { get; set; } = 0.45f;

    /// <summary>A body faster than this has exploded, m/s.</summary>
    [Export] public float ExplodedMps { get; set; } = 20f;

    /// <summary>The shove to the chest, newton-seconds, toward the edge (+Z).</summary>
    [Export] public float PushNs { get; set; } = 40f;

    private int _fail;

    /// <inheritdoc/>
    public override async void _Ready()
    {
        try
        {
            var data = GameData.Load(new GodotDataSource());
            foreach (var path in Bodies)
            {
                await Drop(path, data.NpcBodies.Ragdoll.SettleS);
            }
        }
        catch (Exception e)
        {
            GD.PrintErr($"FAIL [ragdoll_test] {e}");
            _fail++;
        }
        GD.Print($"[ragdoll_test] {Bodies.Length - Math.Min(_fail, Bodies.Length)} of {Bodies.Length} passed");
        GetTree().Quit(_fail > 0 ? 1 : 0);
    }

    private async Task Drop(string path, double settleS)
    {
        var body = GD.Load<PackedScene>(path).Instantiate<Node3D>();
        // Standing on the step 0.28 m from its edge (z = 0), facing away from it.
        body.Position = new Vector3(0, StepTopM, -0.28f);
        body.RotationDegrees = new Vector3(0, 180, 0);
        AddChild(body);
        var ragdoll = body.FindChildren("Ragdoll", "", true, false).OfType<NpcRagdoll>().First();
        var anim = body.GetNode<AnimationPlayer>("Anim");
        while (!ragdoll.Prepared)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
        }
        anim.Play("Idle");
        for (var i = 0; i < 20; i++)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
        }
        anim.Stop(keepState: true);
        ragdoll.Collapse(settleS, new Vector3(0, 0, PushNs));
        var bodies = ragdoll.GetChildren().OfType<PhysicalBone3D>().ToList();
        var peak = 0f;
        var elapsed = 0.0;
        while (!ragdoll.Frozen && elapsed < settleS + 1.0)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
            elapsed += GetPhysicsProcessDeltaTime();
            peak = Math.Max(peak, bodies.Max(b => PhysicsServer3D.BodyGetState(b.GetRid(), PhysicsServer3D.BodyState.LinearVelocity).AsVector3().Length()));
        }
        var sk = ragdoll.GetSkeleton();
        var hips = sk.FindBone("Hips");
        var before = (sk.GlobalTransform * sk.GetBoneGlobalPose(hips)).Origin;
        for (var i = 0; i < 30; i++)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
        }
        var after = (sk.GlobalTransform * sk.GetBoneGlobalPose(hips)).Origin;
        var problems = new System.Collections.Generic.List<string>();
        if (!ragdoll.Frozen || Math.Abs(elapsed - settleS) > 0.1)
        {
            problems.Add(UiText.Invariant($"not frozen at {settleS:0.0} s (frozen {ragdoll.Frozen}, {elapsed:0.00} s)"));
        }
        if (peak > ExplodedMps)
        {
            problems.Add(UiText.Invariant($"peak speed {peak:0.0} m/s, over {ExplodedMps:0} m/s"));
        }
        if (before.DistanceTo(after) > 0.001f)
        {
            problems.Add(UiText.Invariant($"the hips moved {before.DistanceTo(after) * 100:0.0} cm after freezing"));
        }
        if (after.Y > StepTopM || after.Z < 0)
        {
            problems.Add(UiText.Invariant($"the body didn't fall off the step (hips at y {after.Y:0.00} m, z {after.Z:0.00} m)"));
        }
        var line = UiText.Invariant($"{path}: peak {peak:0.0} m/s, frozen at {elapsed:0.00} s, hips at y {after.Y:0.00} m z {after.Z:0.00} m");
        if (problems.Count == 0)
        {
            GD.Print("PASS " + line);
        }
        else
        {
            _fail++;
            GD.PrintErr("FAIL " + line + ": " + string.Join("; ", problems));
        }
        body.QueueFree();
        await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
    }
}
