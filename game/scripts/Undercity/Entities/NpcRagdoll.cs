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
// A body that falls into water floats: each bone is pushed up in proportion to how much of it
// is under the surface, and damped, and it isn't frozen while it's in the water
// (openspec/changes/water-and-swimming, design section 5).

#nullable enable
using System.Collections.Generic;
using System.Linq;
using Godot;

namespace Undercity.Client;

/// <summary>A body's ragdoll.</summary>
public partial class NpcRagdoll : PhysicalBoneSimulator3D
{
    private readonly List<PhysicalBone3D> _bodies = new();
    private readonly Dictionary<PhysicalBone3D, CollisionShape3D?> _shapes = new();
    private LevelWater? _water;

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
        foreach (var b in _bodies)
        {
            _shapes[b] = b.GetChildren().OfType<CollisionShape3D>().FirstOrDefault();
        }
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
    /// as a hit would. Where the level has <paramref name="water"/>, the body floats in it.
    /// </summary>
    public async void Collapse(double settleS, Vector3 pushNs = default, LevelWater? water = null)
    {
        if (Collapsed)
        {
            return;
        }
        Collapsed = true;
        _water = water;
        PhysicalBonesStartSimulation();
        if (pushNs != Vector3.Zero && _bodies.FirstOrDefault(b => BoneName(b) == "UpperChest") is { } chest)
        {
            chest.ApplyCentralImpulse(pushNs);
        }
        await ToSignal(GetTree().CreateTimer(settleS, processAlways: false, processInPhysics: true), SceneTreeTimer.SignalName.Timeout);
        if (!IsInstanceValid(this) || InWater())
        {
            return;     // a body in water floats on, damped, rather than freezing mid-rise
        }
        Freeze();
    }

    /// <inheritdoc/>
    public override void _PhysicsProcess(double delta)
    {
        if (!Collapsed || Frozen || _water is null)
        {
            return;
        }
        var t = _water.Table;
        var g = (float)ProjectSettings.GetSetting("physics/3d/default_gravity").AsDouble();
        foreach (var b in _bodies)
        {
            var f = _water.SubmergedFraction(b.GlobalPosition, HalfHeight(b));
            if (f <= 0)
            {
                continue;
            }
            b.ApplyCentralImpulse(Vector3.Up * ((float)t.BodyBuoyancyRatio * b.Mass * g * f * (float)delta));
            b.LinearDamp = (float)t.BodyLinearDampPerS;
            b.AngularDamp = (float)t.BodyAngularDampPerS;
        }
    }

    private bool InWater() => _water is not null && _bodies.Any(b => _water.SubmergedFraction(b.GlobalPosition, HalfHeight(b)) > 0);

    // How far a bone's collider reaches up and down from its centre, metres: a capsule's by how
    // upright it lies, a sphere's radius, a box's largest half side.
    private float HalfHeight(PhysicalBone3D b)
    {
        var node = _shapes.GetValueOrDefault(b);
        return node?.Shape switch
        {
            CapsuleShape3D c => c.Radius + (c.Height / 2 - c.Radius) * Mathf.Abs(node.GlobalBasis.Y.Normalized().Y),
            SphereShape3D sp => sp.Radius,
            BoxShape3D bx => Mathf.Max(bx.Size.X, Mathf.Max(bx.Size.Y, bx.Size.Z)) / 2,
            _ => 0.1f,
        };
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
