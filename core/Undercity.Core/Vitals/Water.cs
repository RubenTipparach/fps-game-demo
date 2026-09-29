// Water: the swimming numbers (data/water.json), and the runner's breath and stamina in water.
//
// It lives in the core because breath and stamina are saved, because every water body (the hub's
// canal, the dry dock, the Drains' flooded bypass) must share one rule, and because the belt's
// refusal to draw while swimming must agree with the keys and the HUD (CLAUDE.md 5.1;
// openspec/changes/archive/2026-09-29-water-and-swimming). How the body moves in water (buoyancy, strokes, ladders)
// is the Godot layer's job; it reads the same table.

using Undercity.Core.Data;

namespace Undercity.Core.Vitals;

/// <summary>data/water.json: wading, swimming, breath, stamina, exits and water physics.</summary>
public sealed class WaterTable : IValidated
{
    /// <summary>Water deeper than this at the feet makes the runner wade, metres.</summary>
    public required double WadeDepthM { get; init; }

    /// <summary>Water deeper than this at the feet makes the runner swim, metres.</summary>
    public required double SwimDepthM { get; init; }

    /// <summary>Ground speed is multiplied by this while wading.</summary>
    public required double WadeSpeedFactor { get; init; }

    /// <summary>Swimming speed along the look direction, metres per second.</summary>
    public required double SwimSpeedMps { get; init; }

    /// <summary>Diving speed (crouch held), metres per second.</summary>
    public required double DiveSpeedMps { get; init; }

    /// <summary>Rising speed (jump held), metres per second.</summary>
    public required double RiseSpeedMps { get; init; }

    /// <summary>How fast swimming velocity approaches the wanted velocity, per second.</summary>
    public required double AccelPerS { get; init; }

    /// <summary>How fast velocity decays with no input, per second.</summary>
    public required double DragPerS { get; init; }

    /// <summary>At the surface, looking within this pitch of level swims flat rather than diving, degrees.</summary>
    public required double SurfacePitchDeadZoneDeg { get; init; }

    /// <summary>A floating runner's eyes rest this far above the surface, metres.</summary>
    public required double FloatEyeAboveM { get; init; }

    /// <summary>The spring that holds a floating runner at the surface, per second squared.</summary>
    public required double FloatStiffnessPerS2 { get; init; }

    /// <summary>The damping on that spring, per second.</summary>
    public required double FloatDampingPerS { get; init; }

    /// <summary>The share of vertical speed kept on falling into water.</summary>
    public required double EntryKeepFraction { get; init; }

    /// <summary>Breath held under water, seconds.</summary>
    public required double BreathS { get; init; }

    /// <summary>Time for breath to refill from empty at the surface, seconds.</summary>
    public required double BreathRefillS { get; init; }

    /// <summary>Damage per second once breath runs out.</summary>
    public required double DrownDamagePerS { get; init; }

    /// <summary>Stamina when fresh (owner, survey I3: "swimming consumes stamina but slowly").</summary>
    public required double StaminaMax { get; init; }

    /// <summary>Stamina used per second while swimming.</summary>
    public required double SwimStaminaPerS { get; init; }

    /// <summary>Stamina regained per second while wading or dry.</summary>
    public required double StaminaRegenPerS { get; init; }

    /// <summary>Swimming speeds are multiplied by this with no stamina left.</summary>
    public required double TiredSpeedFactor { get; init; }

    /// <summary>Below this share of stamina, breathing gets heavier and strokes slower.</summary>
    public required double StaminaLowFraction { get; init; }

    /// <summary>A stroke sounds this often while swimming, seconds.</summary>
    public required double StrokeS { get; init; }

    /// <summary>And this often while stamina is low, seconds.</summary>
    public required double TiredStrokeS { get; init; }

    /// <summary>Below this share of breath the AIR bar turns red (mockup D8).</summary>
    public required double BreathLowFraction { get; init; }

    /// <summary>The AIR bar fades out over this long once breath is full again, seconds.</summary>
    public required double AirBarFadeS { get; init; }

    /// <summary>Surfacing with less than this share of breath gasps.</summary>
    public required double GaspBelowBreathFraction { get; init; }

    /// <summary>A ledge this far ahead of a swimmer can be climbed onto, metres.</summary>
    public required double MantleReachM { get; init; }

    /// <summary>The lowest ledge top above the surface that counts as a ledge, metres.</summary>
    public required double MantleMinRiseM { get; init; }

    /// <summary>The highest ledge top above the surface a swimmer can climb onto, metres.</summary>
    public required double MantleMaxRiseM { get; init; }

    /// <summary>How long climbing onto a ledge takes, seconds.</summary>
    public required double MantleTimeS { get; init; }

    /// <summary>Climbing speed on a ladder, metres per second.</summary>
    public required double LadderSpeedMps { get; init; }

    /// <summary>Facing a ladder means the look and the into-the-wall direction agree by at least this dot product.</summary>
    public required double LadderFacingDot { get; init; }

    /// <summary>A body this far out from a ladder's stiles can take hold, metres.</summary>
    public required double LadderReachM { get; init; }

    /// <summary>A climber's hands reach this far past either stile, metres.</summary>
    public required double LadderSideReachM { get; init; }

    /// <summary>Jumping off a ladder pushes away at this speed, metres per second.</summary>
    public required double LadderPushOffMps { get; init; }

    /// <summary>Topping out of a ladder steps this far onto the floor, metres.</summary>
    public required double LadderTopStepM { get; init; }

    /// <summary>That step takes this long, seconds (and so does taking hold from the top).</summary>
    public required double LadderTopStepS { get; init; }

    /// <summary>A body in water is pushed up by this multiple of its submerged weight.</summary>
    public required double BodyBuoyancyRatio { get; init; }

    /// <summary>Linear damping on a body's bones in water, per second.</summary>
    public required double BodyLinearDampPerS { get; init; }

    /// <summary>Angular damping on a body's bones in water, per second.</summary>
    public required double BodyAngularDampPerS { get; init; }

    /// <summary>A dropped item sinks at this speed, metres per second.</summary>
    public required double ItemSinkMps { get; init; }

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        void Positive(string key, double v)
        {
            if (!double.IsFinite(v) || v <= 0)
            {
                errors.Add($"{key} must be a finite number above zero");
            }
        }
        void Fraction(string key, double v)
        {
            if (!double.IsFinite(v) || v < 0 || v > 1)
            {
                errors.Add($"{key} must be between 0 and 1");
            }
        }
        Positive("wade_depth_m", WadeDepthM);
        Positive("swim_depth_m", SwimDepthM);
        if (SwimDepthM <= WadeDepthM)
        {
            errors.Add("swim_depth_m must be deeper than wade_depth_m");
        }
        Fraction("wade_speed_factor", WadeSpeedFactor);
        Positive("swim_speed_mps", SwimSpeedMps);
        Positive("dive_speed_mps", DiveSpeedMps);
        Positive("rise_speed_mps", RiseSpeedMps);
        Positive("accel_per_s", AccelPerS);
        Positive("drag_per_s", DragPerS);
        if (!double.IsFinite(SurfacePitchDeadZoneDeg) || SurfacePitchDeadZoneDeg < 0 || SurfacePitchDeadZoneDeg >= 90)
        {
            errors.Add("surface_pitch_dead_zone_deg must be 0 to under 90");
        }
        Positive("float_eye_above_m", FloatEyeAboveM);
        Positive("float_stiffness_per_s2", FloatStiffnessPerS2);
        Positive("float_damping_per_s", FloatDampingPerS);
        Fraction("entry_keep_fraction", EntryKeepFraction);
        Positive("breath_s", BreathS);
        Positive("breath_refill_s", BreathRefillS);
        if (!double.IsFinite(DrownDamagePerS) || DrownDamagePerS < 0)
        {
            errors.Add("drown_damage_per_s must be a finite number, zero or more");
        }
        Positive("stamina_max", StaminaMax);
        if (!double.IsFinite(SwimStaminaPerS) || SwimStaminaPerS < 0)
        {
            errors.Add("swim_stamina_per_s must be a finite number, zero or more");
        }
        Positive("stamina_regen_per_s", StaminaRegenPerS);
        Fraction("tired_speed_factor", TiredSpeedFactor);
        Fraction("stamina_low_fraction", StaminaLowFraction);
        Positive("stroke_s", StrokeS);
        Positive("tired_stroke_s", TiredStrokeS);
        Fraction("breath_low_fraction", BreathLowFraction);
        Positive("air_bar_fade_s", AirBarFadeS);
        Fraction("gasp_below_breath_fraction", GaspBelowBreathFraction);
        Positive("mantle_reach_m", MantleReachM);
        Positive("mantle_min_rise_m", MantleMinRiseM);
        Positive("mantle_max_rise_m", MantleMaxRiseM);
        if (MantleMaxRiseM <= MantleMinRiseM)
        {
            errors.Add("mantle_max_rise_m must be above mantle_min_rise_m");
        }
        Positive("mantle_time_s", MantleTimeS);
        Positive("ladder_speed_mps", LadderSpeedMps);
        Fraction("ladder_facing_dot", LadderFacingDot);
        Positive("ladder_reach_m", LadderReachM);
        Positive("ladder_side_reach_m", LadderSideReachM);
        Positive("ladder_push_off_mps", LadderPushOffMps);
        Positive("ladder_top_step_m", LadderTopStepM);
        Positive("ladder_top_step_s", LadderTopStepS);
        Positive("body_buoyancy_ratio", BodyBuoyancyRatio);
        Positive("body_linear_damp_per_s", BodyLinearDampPerS);
        Positive("body_angular_damp_per_s", BodyAngularDampPerS);
        Positive("item_sink_mps", ItemSinkMps);
    }
}

/// <summary>How much of the runner is in water. Each is deeper than the one before.</summary>
public enum WaterContact
{
    /// <summary>No water at the feet (or less than wading depth).</summary>
    Dry,

    /// <summary>Water between wading and swimming depth: slowed, but walking.</summary>
    Wading,

    /// <summary>Swimming with the eyes above the surface.</summary>
    Swimming,

    /// <summary>Swimming with the eyes under the surface: breath drains.</summary>
    Submerged,
}

/// <summary>Breath: drains under water, refills at the surface, and drowns when it runs out.</summary>
public sealed class Breath
{
    private readonly WaterTable _t;

    /// <summary>Creates a full breath.</summary>
    public Breath(WaterTable table)
    {
        _t = table;
        Value = table.BreathS;
    }

    /// <summary>Breath when full, seconds.</summary>
    public double Max => _t.BreathS;

    /// <summary>Breath left, seconds.</summary>
    public double Value { get; private set; }

    /// <summary>True when breath is full: the HUD hides the meter then.</summary>
    public bool Full => Value >= Max;

    /// <summary>
    /// Advances time. Returns the drowning damage for this step: <see cref="WaterTable.DrownDamagePerS"/>
    /// for each second spent under water with no breath left, and 0 otherwise.
    /// </summary>
    public double Tick(double dt, bool submerged)
    {
        if (!double.IsFinite(dt) || dt <= 0)
        {
            return 0;
        }
        if (!submerged)
        {
            Value = Math.Min(Max, Value + Max / _t.BreathRefillS * dt);
            return 0;
        }
        var before = Value;
        Value = Math.Max(0, Value - dt);
        var withoutAirS = dt - (before - Value);
        return withoutAirS * _t.DrownDamagePerS;
    }

    /// <summary>Sets breath (loading a save), clamped; a non-finite value loads as full.</summary>
    public void Set(double value) => Value = double.IsFinite(value) ? Math.Clamp(value, 0, Max) : Max;
}

/// <summary>Stamina: used only by swimming, slowly; with none left the runner swims slower.</summary>
public sealed class Stamina
{
    private readonly WaterTable _t;

    /// <summary>Creates full stamina.</summary>
    public Stamina(WaterTable table)
    {
        _t = table;
        Value = table.StaminaMax;
    }

    /// <summary>Stamina when fresh.</summary>
    public double Max => _t.StaminaMax;

    /// <summary>Stamina left.</summary>
    public double Value { get; private set; }

    /// <summary>True with no stamina left.</summary>
    public bool Tired => Value <= 0;

    /// <summary>The multiplier on swimming speeds: <see cref="WaterTable.TiredSpeedFactor"/> when tired, else 1.</summary>
    public double SpeedFactor => Tired ? _t.TiredSpeedFactor : 1.0;

    /// <summary>Advances time: swimming (at or under the surface) drains stamina; wading or dry refills it.</summary>
    public void Tick(double dt, WaterContact contact)
    {
        if (!double.IsFinite(dt) || dt <= 0)
        {
            return;
        }
        Value = contact >= WaterContact.Swimming
            ? Math.Max(0, Value - _t.SwimStaminaPerS * dt)
            : Math.Min(Max, Value + _t.StaminaRegenPerS * dt);
    }

    /// <summary>Sets stamina (loading a save), clamped; a non-finite value loads as full.</summary>
    public void Set(double value) => Value = double.IsFinite(value) ? Math.Clamp(value, 0, Max) : Max;
}
