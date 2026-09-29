// How NPC bodies move and fall (data/npc_bodies.json): which clip of the shared animation library
// plays for each NPC state, the cross-fade, and the ragdoll profile the NPC scene generator
// builds (openspec/changes/archive/2026-09-28-npc-characters, design sections 6 and 7), and where
// a civilian's accessories hang (openspec/changes/archive/2026-09-29-crowd-variety).
//
// It lives in the core because it is tuning in a data file, and every data file loads, validates
// and cross-checks here (CLAUDE.md 5.5, 5.6): a state an NPC names but the table lacks, or a
// ragdoll bone with no mass, must fail `dotnet test`, not a playtest.

using Undercity.Core.Data;

namespace Undercity.Core.World;

/// <summary>One simulated bone of the ragdoll.</summary>
public sealed class RagdollBodyDef
{
    /// <summary>The humanoid-profile bone the body follows, such as "LeftUpperLeg".</summary>
    public required string Bone { get; init; }

    /// <summary>The bone whose head ends the capsule; empty for a bone with no child (the head), which uses <see cref="LengthM"/>.</summary>
    public string To { get; init; } = "";

    /// <summary>The capsule length when <see cref="To"/> is empty, metres.</summary>
    public double LengthM { get; init; }

    /// <summary>The capsule radius, metres.</summary>
    public required double RadiusM { get; init; }

    /// <summary>The body's mass, kilograms.</summary>
    public required double MassKg { get; init; }

    /// <summary>The joint to the parent body: "none" (the root), "cone" or "hinge".</summary>
    public required string Joint { get; init; }

    /// <summary>A cone's swing span, or a hinge's lower limit, degrees.</summary>
    public double ADeg { get; init; }

    /// <summary>A cone's twist span, or a hinge's upper limit, degrees.</summary>
    public double BDeg { get; init; }

    /// <summary>A hinge's flexion direction at rest, in skeleton space: [x, y, z].</summary>
    public IReadOnlyList<double> Flex { get; init; } = Array.Empty<double>();
}

/// <summary>The ragdoll: its bodies and how long it simulates before it freezes.</summary>
public sealed class RagdollDef
{
    /// <summary>Seconds a ragdoll simulates before it freezes in its pose.</summary>
    public required double SettleS { get; init; }

    /// <summary>Surface friction of every body, 0 to 1.</summary>
    public required double Friction { get; init; }

    /// <summary>Linear damping of every body, per second.</summary>
    public required double LinearDampPerS { get; init; }

    /// <summary>Angular damping of every body, per second.</summary>
    public required double AngularDampPerS { get; init; }

    /// <summary>The simulated bones, root first.</summary>
    public required IReadOnlyList<RagdollBodyDef> Bodies { get; init; }
}

/// <summary>
/// Where an accessory hangs on a body (openspec/changes/archive/2026-09-29-crowd-variety, design section 5): a point on
/// a bone, fitted in the pose the accessory is used in. The NPC scene generator puts a node there
/// whose axes are the body's (forward, up and right) in that pose, or the bone's own, and a prop
/// built at that node's origin sits right on every body.
/// </summary>
public sealed class MountDef
{
    /// <summary>The humanoid-profile bone it follows, such as "Head" or "RightHand".</summary>
    public required string Bone { get; init; }

    /// <summary>The state whose clip's last frame it is fitted in; empty for the rest pose.</summary>
    public string Pose { get; init; } = "";

    /// <summary>How far along the bone from its head the point is, metres (a hand's palm).</summary>
    public double AlongM { get; init; }

    /// <summary>
    /// "body" (the default): the node's axes are the body's in the pose. "bone": they are the
    /// bone's own, +Y along it, for a prop that wraps the bone (a sleeve on a forearm).
    /// </summary>
    public string Axes { get; init; } = "body";
}

/// <summary>data/npc_bodies.json.</summary>
public sealed class NpcBodyTable : IValidated
{
    private static readonly string[] Joints = { "none", "cone", "hinge" };

    /// <summary>The states every NPC scene must be able to play.</summary>
    public static readonly IReadOnlyList<string> RequiredStates = new[] { "idle", "walk", "talk", "guard", "hostile" };

    /// <summary>The clip for each NPC state, by state name ("idle", "walk", "talk", "guard", "hostile", ...).</summary>
    public required IReadOnlyDictionary<string, string> Clips { get; init; }

    /// <summary>Seconds a clip change cross-fades over.</summary>
    public required double BlendS { get; init; }

    /// <summary>The ragdoll.</summary>
    public required RagdollDef Ragdoll { get; init; }

    /// <summary>Where accessories hang, by mount id.</summary>
    public IReadOnlyDictionary<string, MountDef> Mounts { get; init; } = new Dictionary<string, MountDef>();

    /// <summary>The clip for a state, or null when the table doesn't name one.</summary>
    public string? Clip(string state) => Clips.TryGetValue(state, out var c) ? c : null;

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        foreach (var s in RequiredStates.Where(s => !Clips.ContainsKey(s)))
        {
            errors.Add($"clips: the state '{s}' needs a clip");
        }
        foreach (var (state, clip) in Clips.Where(c => string.IsNullOrWhiteSpace(c.Value)))
        {
            errors.Add($"clips.{state}: empty clip name");
        }
        if (!double.IsFinite(BlendS) || BlendS < 0)
        {
            errors.Add("blend_s must be a finite number of seconds, zero or more");
        }
        var r = Ragdoll;
        if (!double.IsFinite(r.SettleS) || r.SettleS <= 0)
        {
            errors.Add("ragdoll.settle_s must be a finite number of seconds above zero");
        }
        if (r.Friction is < 0 or > 1 || !double.IsFinite(r.LinearDampPerS) || r.LinearDampPerS < 0
            || !double.IsFinite(r.AngularDampPerS) || r.AngularDampPerS < 0)
        {
            errors.Add("ragdoll: friction must be 0 to 1 and damping zero or more");
        }
        if (r.Bodies.Count == 0 || r.Bodies[0].Joint != "none")
        {
            errors.Add("ragdoll.bodies: the first body is the root, with joint 'none'");
        }
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var b in r.Bodies)
        {
            var at = $"ragdoll.bodies.{b.Bone}";
            if (!seen.Add(b.Bone))
            {
                errors.Add($"{at}: listed twice");
            }
            if (!Joints.Contains(b.Joint))
            {
                errors.Add($"{at}.joint: '{b.Joint}' isn't none, cone or hinge");
            }
            if (!double.IsFinite(b.RadiusM) || b.RadiusM <= 0 || !double.IsFinite(b.MassKg) || b.MassKg <= 0)
            {
                errors.Add($"{at}: radius_m and mass_kg must be above zero");
            }
            if (b.To.Length == 0 && (!double.IsFinite(b.LengthM) || b.LengthM <= 0))
            {
                errors.Add($"{at}: a body with no 'to' bone needs length_m above zero");
            }
            if (b.Joint == "hinge" && (b.Flex.Count != 3 || b.ADeg >= b.BDeg))
            {
                errors.Add($"{at}: a hinge needs flex [x, y, z] and a_deg below b_deg");
            }
        }
        foreach (var (id, m) in Mounts)
        {
            if (m.Pose.Length > 0 && !Clips.ContainsKey(m.Pose))
            {
                errors.Add($"mounts.{id}.pose: '{m.Pose}' is no state of clips");
            }
            if (!double.IsFinite(m.AlongM) || string.IsNullOrWhiteSpace(m.Bone))
            {
                errors.Add($"mounts.{id}: a bone and a finite along_m");
            }
            if (m.Axes is not ("body" or "bone"))
            {
                errors.Add($"mounts.{id}.axes: 'body' or 'bone', not '{m.Axes}'");
            }
        }
    }
}
