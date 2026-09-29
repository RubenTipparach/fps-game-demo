// A ladder out of the water: a quay ladder, the outfall's, or a ship's boarding ladder. It says
// where it can be climbed, and offers "Climb down" from its top.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): the level plan places, sizes and
// builds it (tools/levels/city_plan.py ladder(), whose ENT_ladder metadata this reads), and how it
// is climbed is the player's ladder motor, with its numbers in data/water.json
// (openspec/changes/archive/2026-09-29-water-and-swimming, design section 4).

#nullable enable
using Godot;

namespace Undercity.Client;

/// <summary>A climbable ladder against a wall, from under the water to the floor at its top.</summary>
public partial class Ladder : Node3D, IWired, IInteractable, IStable
{
    /// <summary>A climber holds this far clear of the stiles, metres.</summary>
    private const float HoldClearM = 0.02f;

    private Services? _s;

    /// <summary>The height a climber clears at the ladder's top (the quay's edge, or a kerb along it), metres.</summary>
    public float TopM { get; private set; }

    /// <summary>The climb ends this far in from the edge, metres (the level plan's landing).</summary>
    public float StepInM { get; private set; }

    /// <summary>The height of the floor there, metres.</summary>
    public float FloorM { get; private set; }

    /// <summary>The height of the ladder's foot, under the water, metres.</summary>
    public float BottomM { get; private set; }

    /// <summary>Between the stiles, metres.</summary>
    public float WidthM { get; private set; }

    /// <summary>The stiles' outer faces stand this far off the wall, metres.</summary>
    public float StandOffM { get; private set; }

    /// <inheritdoc/>
    public string StableId => Entity.StableIdOf(this);

    /// <summary>Level, unit: from the water into the wall, towards the floor at the top (the node's forward).</summary>
    public Vector3 Into
    {
        get
        {
            var f = -GlobalBasis.Z;
            f.Y = 0;
            return f.Normalized();
        }
    }

    /// <summary>Level, unit: along the wall, to the climber's right.</summary>
    public Vector3 Along => Into.Cross(Vector3.Up);

    public override void _Ready()
    {
        TopM = Number("top_m");
        BottomM = Number("bottom_m");
        WidthM = Number("width_m");
        StandOffM = Number("stand_off_m");
        StepInM = Number("step_in_m");
        FloorM = Number("floor_m");
        if (!(BottomM < TopM) || WidthM <= 0 || StandOffM < 0 || StepInM <= 0 || FloorM > TopM)
        {
            GD.PushError($"[Ladder] {Name}: bottom_m {BottomM} must be under top_m {TopM}, floor_m {FloorM} no higher, "
                + $"and width_m {WidthM}, stand_off_m {StandOffM} and step_in_m {StepInM} positive");
        }
        AddToGroup("ladders");
    }

    private float Number(string key)
    {
        if (!HasMeta(key))
        {
            GD.PushError($"[Ladder] {Name} has no {key}; the level plan writes it (city_plan.py ladder())");
            return 0;
        }
        var v = (float)GetMeta(key).AsDouble();
        if (!float.IsFinite(v))
        {
            GD.PushError($"[Ladder] {Name}: {key} is not a finite number");
            return 0;
        }
        return v;
    }

    /// <inheritdoc/>
    public void Wire(Services services) => _s = services;

    /// <summary>Where the climb ends: the climber's feet on the floor, <see cref="StepInM"/> in from the edge.</summary>
    public Vector3 Landing => new Vector3(GlobalPosition.X, FloorM, GlobalPosition.Z) + Into * StepInM;

    /// <summary>
    /// Where a climber of <paramref name="radius"/> metres holds on: against the stiles, centred on
    /// the ladder, with the feet at <paramref name="feetY"/>.
    /// </summary>
    public Vector3 HoldPoint(float radius, float feetY)
    {
        var p = GlobalPosition - Into * (StandOffM + radius + HoldClearM);
        return new Vector3(p.X, feetY, p.Z);
    }

    /// <summary>
    /// True when a body of <paramref name="radius"/> metres, with its feet at <paramref name="feet"/>
    /// and its eyes at <paramref name="eyeY"/>, is close enough to take hold: in front of the ladder,
    /// within <paramref name="sideReachM"/> past a stile and <paramref name="reachM"/> out from them
    /// (data/water.json), with its eyes (and hands) above the ladder's foot and its feet no higher
    /// than a step above the top.
    /// </summary>
    public bool InReach(Vector3 feet, float eyeY, float radius, float reachM, float sideReachM)
    {
        var rel = feet - GlobalPosition;
        var side = Mathf.Abs(rel.Dot(Along));
        var outM = -rel.Dot(Into);
        return side <= WidthM / 2 + sideReachM
            && outM >= StandOffM && outM <= StandOffM + radius + HoldClearM + reachM
            && eyeY >= BottomM && feet.Y <= TopM + 0.1f;
    }

    /// <inheritdoc/>
    public Interaction Describe()
    {
        var water = _s?.Level.Player?.GetNodeOrNull<PlayerWater>("Water");
        return water is not null && water.CanClimbDown(this) ? new Interaction("Climb down", true) : Interaction.None;
    }

    /// <inheritdoc/>
    public void Use() => _s?.Level.Player?.GetNodeOrNull<PlayerWater>("Water")?.ClimbDown(this);
}
