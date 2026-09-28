// An NPC's ragdoll (the "Ragdoll" node that tools/godot/gen_npc_scenes.gd puts under each body's
// skeleton): it readies the joints at the rest pose, keeps neighbouring bodies from colliding,
// and on a death or knockout simulates for the data's settle time, then freezes the body in the
// pose it reached (openspec/changes/archive/2026-09-28-npc-characters, design section 7).
//
// It lives in the Godot layer because it only drives the physics engine: whether an NPC dies is
// the game's rule, and how long a body settles is data (data/npc_bodies.json, ragdoll.settle_s).
// Two things can't be saved in the generated scene, so they happen here: the joints must be
// built while the skeleton is at rest (anatomical zero for the limits), and collision
// exceptions are runtime-only. Both follow the measurement (docs/spikes/npc-pipeline).

#nullable enable
using System.Collections.Generic;
using System.Linq;
using Godot;

namespace Undercity.Client;

/// <summary>A body's ragdoll.</summary>
public partial class NpcRagdoll : PhysicalBoneSimulator3D
{
    private readonly List<PhysicalBone3D> _bodies = new();

    /// <summary>True once the joints are built at rest; the body may animate from then on.</summary>
    public bool Prepared { get; private set; }

    /// <summary>True from the moment the body collapses.</summary>
    public bool Collapsed { get; private set; }

    /// <summary>True once the collapsed body has frozen.</summary>
    public bool Frozen { get; private set; }

    // PhysicalBone3D's bone_name isn't bound as a C# property in 4.7.
    private static string BoneName(PhysicalBone3D b) => b.Get("bone_name").AsString();

    /// <inheritdoc/>
    public override void _Ready()
    {
        _bodies.AddRange(GetChildren().OfType<PhysicalBone3D>());
        AddExceptions();
        Prepare();
    }

    // The bodies follow the skeleton once the simulator has run; then each joint is rebuilt from
    // the rest pose by setting its offset again.
    private async void Prepare()
    {
        for (var i = 0; i < 2; i++)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
        }
        foreach (var pb in _bodies)
        {
            pb.JointOffset = pb.JointOffset;
        }
        Prepared = true;
    }

    // A joint doesn't keep its own two bodies apart from colliding (measured: the spine opened by
    // 8.5 cm), so parents, siblings and grandparents are excepted.
    private void AddExceptions()
    {
        var sk = GetSkeleton();
        if (sk is null)
        {
            return;
        }
        var byBone = _bodies.ToDictionary(b => b.GetBoneId(), b => b);
        PhysicalBone3D? ParentOf(PhysicalBone3D b)
        {
            for (var p = sk.GetBoneParent(b.GetBoneId()); p >= 0; p = sk.GetBoneParent(p))
            {
                if (byBone.TryGetValue(p, out var found))
                {
                    return found;
                }
            }
            return null;
        }
        for (var i = 0; i < _bodies.Count; i++)
        {
            for (var j = i + 1; j < _bodies.Count; j++)
            {
                var a = _bodies[i];
                var c = _bodies[j];
                var pa = ParentOf(a);
                var pc = ParentOf(c);
                var near = pa == c || pc == a
                    || (pa is not null && pa == pc)
                    || (pa is not null && ParentOf(pa) == c)
                    || (pc is not null && ParentOf(pc) == a);
                if (near)
                {
                    a.AddCollisionExceptionWith(c);
                }
            }
        }
    }

    /// <summary>
    /// Hands the body to physics, and freezes it <paramref name="settleS"/> seconds later. A
    /// non-zero <paramref name="pushNs"/> (newton-seconds, world space) shoves the upper chest,
    /// as a hit would.
    /// </summary>
    public async void Collapse(double settleS, Vector3 pushNs = default)
    {
        if (Collapsed)
        {
            return;
        }
        Collapsed = true;
        PhysicalBonesStartSimulation();
        if (pushNs != Vector3.Zero && _bodies.FirstOrDefault(b => BoneName(b) == "UpperChest") is { } chest)
        {
            chest.ApplyCentralImpulse(pushNs);
        }
        await ToSignal(GetTree().CreateTimer(settleS, processAlways: false, processInPhysics: true), SceneTreeTimer.SignalName.Timeout);
        Freeze();
    }

    // Reads each simulated bone's pose from its body, stops the simulation, and writes the poses
    // back root first, so the skeleton keeps them and nothing simulates any more.
    private void Freeze()
    {
        var sk = GetSkeleton();
        if (sk is null || !IsInstanceValid(this))
        {
            return;
        }
        var toSkeleton = sk.GlobalTransform.AffineInverse();
        var poses = _bodies
            .Select(b => (Bone: b.GetBoneId(), Pose: toSkeleton * b.GlobalTransform * b.BodyOffset.AffineInverse()))
            .Where(p => p.Bone >= 0)
            .ToList();
        PhysicalBonesStopSimulation();
        foreach (var (bone, pose) in poses)
        {
            sk.SetBoneGlobalPose(bone, pose);
        }
        Frozen = true;
    }
}
