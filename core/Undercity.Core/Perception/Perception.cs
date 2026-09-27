// Perception: the disguise verdict, the detection meter and awareness states, noise radii, and
// the hub's law (MerSec).
//
// It lives in the core because the AI, the HUD's disguise chip and detection arcs, and dialog
// with hostiles must all use the same verdict and the same meter (CLAUDE.md 5.1,
// openspec/changes/perception-and-disguise).

using Undercity.Core.Data;
using Undercity.Core.Progression;

namespace Undercity.Core.Perception;

/// <summary>Disguise tuning (perception.json "disguise").</summary>
public sealed class DisguiseTable
{
    /// <summary>Scrutiny range at intelligence 0, metres.</summary>
    public required double ScrutinyBaseM { get; init; }

    /// <summary>Scrutiny range added per point of intelligence, metres.</summary>
    public required double ScrutinyPerIntelligenceM { get; init; }

    /// <summary>Seconds a restricted zone warns before the disguise is blown.</summary>
    public required double RestrictedWarningS { get; init; }

    /// <summary>How fast a Suspicious verdict fills the meter, per second, times visibility.</summary>
    public required double SuspicionFillPerS { get; init; }
}

/// <summary>Detection tuning (perception.json "detection").</summary>
public sealed class DetectionTable
{
    /// <summary>The meter's fill rate at point-blank, full visibility, per second.</summary>
    public required double BaseRatePerS { get; init; }

    /// <summary>How fast the meter drains out of sight, per second.</summary>
    public required double DrainPerS { get; init; }

    /// <summary>The far cone's rate multiplier.</summary>
    public required double FarConeMult { get; init; }

    /// <summary>The meter value that makes an observer Suspicious.</summary>
    public required double SuspiciousAt { get; init; }

    /// <summary>Seconds without sight before Alerted turns to Searching.</summary>
    public required double LostAfterS { get; init; }

    /// <summary>Seconds a search lasts.</summary>
    public required double SearchS { get; init; }

    /// <summary>Seconds a Suspicious observer looks around.</summary>
    public required double SuspiciousLookS { get; init; }

    /// <summary>Seconds an observer stays Wary.</summary>
    public required double WaryS { get; init; }

    /// <summary>How much faster the meter fills while Wary.</summary>
    public required double WaryFillMult { get; init; }

    /// <summary>Visibility multiplier by stance.</summary>
    public required IReadOnlyDictionary<string, double> Stance { get; init; }

    /// <summary>Visibility multiplier by motion.</summary>
    public required IReadOnlyDictionary<string, double> Motion { get; init; }

    /// <summary>Below this light level, the Shadow perk applies.</summary>
    public required double ShadowLightBelow { get; init; }
}

/// <summary>The hub's law (perception.json "law").</summary>
public sealed class LawTable
{
    /// <summary>A second drawn weapon within this many seconds of a warning turns MerSec hostile.</summary>
    public required double WarningWindowS { get; init; }

    /// <summary>Seconds until MerSec backup arrives once they're hostile.</summary>
    public required double BackupDelayS { get; init; }

    /// <summary>Residents' reputation lost when a crime is seen.</summary>
    public required int CrimeRepPenalty { get; init; }

    /// <summary>The faction whose reputation a witnessed crime costs (the Sump's residents).</summary>
    public required string CrimeRepFaction { get; init; }
}

/// <summary>data/perception.json.</summary>
public sealed class PerceptionTable : IValidated
{
    private static readonly string[] StanceKeys = { "standing", "crouched" };
    private static readonly string[] MotionKeys = { "still", "walking", "sprinting" };

    /// <summary>Disguise tuning.</summary>
    public required DisguiseTable Disguise { get; init; }

    /// <summary>Detection tuning.</summary>
    public required DetectionTable Detection { get; init; }

    /// <summary>The hub's law.</summary>
    public required LawTable Law { get; init; }

    /// <summary>Noise radius by noise name, metres.</summary>
    public required IReadOnlyDictionary<string, double> NoiseM { get; init; }

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        var d = Detection;
        if (d.BaseRatePerS <= 0 || d.DrainPerS <= 0 || d.FarConeMult is <= 0 or > 1 || d.SuspiciousAt is <= 0 or >= 1)
        {
            errors.Add("detection rates out of range");
        }
        if (Disguise.ScrutinyBaseM < 0 || Disguise.ScrutinyPerIntelligenceM <= 0 || Disguise.SuspicionFillPerS <= 0)
        {
            errors.Add("disguise tuning out of range");
        }
        foreach (var key in StanceKeys.Where(k => !d.Stance.ContainsKey(k)))
        {
            errors.Add($"detection.stance needs '{key}'");
        }
        foreach (var key in MotionKeys.Where(k => !d.Motion.ContainsKey(k)))
        {
            errors.Add($"detection.motion needs '{key}'");
        }
        foreach (var (k, v) in NoiseM.Where(kv => kv.Value < 0 || !double.IsFinite(kv.Value)))
        {
            errors.Add($"noise_m.{k} must be finite and not negative (is {v})");
        }
    }
}

/// <summary>What an observer makes of a disguise.</summary>
public enum Verdict
{
    /// <summary>Not wearing this observer's colours: normal stealth rules.</summary>
    NotDisguised,

    /// <summary>Taken for one of their own.</summary>
    Accepted,

    /// <summary>Something's off: the meter fills slowly.</summary>
    Suspicious,

    /// <summary>Seen through, or given away.</summary>
    Blown,
}

/// <summary>Who is looking.</summary>
/// <param name="Faction">Their faction id.</param>
/// <param name="Intelligence">1 to 5.</param>
/// <param name="Unfoolable">Sensors or scent: dogs, cameras, turrets.</param>
/// <param name="Remembers">They fought the runner or saw a change of clothes this mission.</param>
public sealed record Observer(string Faction, int Intelligence, bool Unfoolable = false, bool Remembers = false);

/// <summary>What the observer can see the runner doing.</summary>
/// <param name="DistanceM">Distance between them, metres.</param>
/// <param name="Talking">In conversation with this observer.</param>
/// <param name="WeaponDrawnS">Seconds a weapon has been drawn; 0 when holstered.</param>
/// <param name="Sneaking">Crouched or sprinting.</param>
/// <param name="RestrictedS">Seconds inside this faction's restricted zone; 0 when outside.</param>
/// <param name="SuspiciousAct">Attacking, picking or hacking their things, searching their containers, carrying a body.</param>
/// <param name="CoverBonus">Extra Cover for this moment (Mimic while talking).</param>
public sealed record Situation(double DistanceM, bool Talking = false, double WeaponDrawnS = 0, bool Sneaking = false,
    double RestrictedS = 0, bool SuspiciousAct = false, int CoverBonus = 0);

/// <summary>The verdict, with the numbers behind it for the HUD.</summary>
/// <param name="Verdict">The verdict.</param>
/// <param name="Quality">Disguise quality Q.</param>
/// <param name="Cover">Deception + Q (+ bonus).</param>
/// <param name="ScrutinyM">This observer's scrutiny range, metres.</param>
/// <param name="Reason">Why, in a few words.</param>
public sealed record Judgement(Verdict Verdict, int Quality, int Cover, double ScrutinyM, string Reason);

/// <summary>The one disguise rule.</summary>
public static class DisguiseRules
{
    /// <summary>Cover = Deception rank + disguise quality (+ bonus); 0 without an outfit or at Deception 0.</summary>
    public static int Cover(Character character, Kit.Inventory inventory, int bonus = 0)
    {
        var dec = character.Rank(Skill.Deception);
        var q = inventory.DisguiseQuality;
        return dec == 0 || q == 0 ? 0 : dec + q + bonus;
    }

    /// <summary>An observer's scrutiny range: base + per-I x intelligence, times the Doppelganger multiplier.</summary>
    public static double ScrutinyM(DisguiseTable table, Character character, int intelligence) =>
        (table.ScrutinyBaseM + table.ScrutinyPerIntelligenceM * intelligence) * character.Mult("scrutiny_mult");

    /// <summary>Judges the runner's disguise for one observer in one situation.</summary>
    public static Judgement Judge(DisguiseTable table, Character character, Kit.Inventory inventory, Observer o, Situation s)
    {
        var q = inventory.DisguiseQuality;
        var cover = Cover(character, inventory, s.CoverBonus);
        var scrutiny = ScrutinyM(table, character, o.Intelligence);
        Judgement J(Verdict v, string why) => new(v, q, cover, scrutiny, why);

        if (o.Unfoolable)
        {
            return J(Verdict.NotDisguised, "can't be fooled");
        }
        if (inventory.OutfitFaction != o.Faction || q == 0)
        {
            return J(Verdict.NotDisguised, "not in their colours");
        }
        if (character.Rank(Skill.Deception) == 0)
        {
            return J(Verdict.NotDisguised, "Deception 0: worn like a costume");
        }
        if (o.Remembers)
        {
            return J(Verdict.Blown, "they remember you");
        }
        var grace = character.Sum("weapon_grace_s_add");
        if (s.WeaponDrawnS > grace)
        {
            return J(Verdict.Blown, "weapon drawn");
        }
        if (s.SuspiciousAct)
        {
            return J(Verdict.Blown, "seen doing something they won't allow");
        }
        if (s.RestrictedS > table.RestrictedWarningS)
        {
            return J(Verdict.Blown, "stayed in a restricted area");
        }
        var close = s.Talking || s.DistanceM <= scrutiny;
        if (close && cover < o.Intelligence)
        {
            return J(Verdict.Blown, $"Cover {cover} is less than I {o.Intelligence}");
        }
        if (s.RestrictedS > 0)
        {
            return J(Verdict.Suspicious, "in a restricted area");
        }
        if (ArmorClashes(character, inventory))
        {
            return J(Verdict.Suspicious, "wrong armour");
        }
        if (close && s.Sneaking)
        {
            return J(Verdict.Suspicious, "moving like an intruder");
        }
        return J(Verdict.Accepted, close ? $"Cover {cover} holds against I {o.Intelligence}" : "passes at a glance");
    }

    /// <summary>
    /// True when worn armour belongs to another faction (or none), unless it's light armour and the
    /// runner has Master of Disguise.
    /// </summary>
    public static bool ArmorClashes(Character character, Kit.Inventory inventory)
    {
        var armor = inventory.WornIn(Items.EquipSlot.Armor)?.Def;
        if (armor is null || armor.Faction == inventory.OutfitFaction)
        {
            return false;
        }
        return !(armor.LightArmor && character.Has("light_armor_ok"));
    }
}

/// <summary>An observer's awareness of the runner.</summary>
public enum AwarenessState
{
    /// <summary>Going about their business.</summary>
    Unaware,

    /// <summary>"?": looking into something.</summary>
    Suspicious,

    /// <summary>"!": fighting.</summary>
    Alerted,

    /// <summary>Lost the runner; searching the last known position.</summary>
    Searching,

    /// <summary>Back to routine, but on edge.</summary>
    Wary,
}

/// <summary>The one visibility and detection rule.</summary>
public static class Detection
{
    /// <summary>
    /// Visibility V = light x stance x motion, with Low Profile on the crouch and Shadow in the dark.
    /// Light is 0 to 1 at the runner.
    /// </summary>
    public static double Visibility(DetectionTable t, Character character, double light, bool crouched, string motion)
    {
        var stance = crouched ? t.Stance["crouched"] * character.Mult("crouch_visibility_mult") : t.Stance["standing"];
        var move = t.Motion.TryGetValue(motion, out var m) ? m : 1.0;
        var shadow = light < t.ShadowLightBelow ? character.Mult("shadow_mult") : 1.0;
        return Math.Clamp(light, 0, 1) * stance * move * shadow;
    }

    /// <summary>
    /// How fast the meter fills: V x base rate x (1 - distance / range) x the cone factor
    /// (1 near, the far multiplier otherwise). 0 at or beyond range.
    /// </summary>
    public static double FillRate(DetectionTable t, double visibility, double distanceM, double rangeM, bool nearCone) =>
        distanceM >= rangeM || rangeM <= 0 ? 0
            : visibility * t.BaseRatePerS * (1 - distanceM / rangeM) * (nearCone ? 1 : t.FarConeMult);
}

/// <summary>One observer's meter and state machine.</summary>
public sealed class Awareness
{
    private readonly DetectionTable _t;
    private double _timer;
    private double _unseenS;

    /// <summary>Creates an unaware observer.</summary>
    public Awareness(DetectionTable table) => _t = table;

    /// <summary>The detection meter, 0 to 1.</summary>
    public double Meter { get; private set; }

    /// <summary>The state.</summary>
    public AwarenessState State { get; private set; } = AwarenessState.Unaware;

    /// <summary>Raises when the state changes.</summary>
    public event Action<AwarenessState>? StateChanged;

    /// <summary>Makes the observer Alerted at once (combat noise, a body, the alarm, a blown disguise).</summary>
    public void Alert()
    {
        Meter = 1;
        _unseenS = 0;
        Set(AwarenessState.Alerted);
    }

    /// <summary>A quiet noise: an unaware or wary observer turns Suspicious and looks.</summary>
    public void HearQuiet()
    {
        if (State is AwarenessState.Unaware or AwarenessState.Wary)
        {
            Meter = Math.Max(Meter, _t.SuspiciousAt);
            _timer = _t.SuspiciousLookS;
            Set(AwarenessState.Suspicious);
        }
    }

    /// <summary>
    /// Advances time. <paramref name="fillPerS"/> is the fill rate while the runner is seen (0 when
    /// not seen).
    /// </summary>
    public void Update(double dt, double fillPerS)
    {
        if (!double.IsFinite(dt) || dt <= 0)
        {
            return;
        }
        var seen = fillPerS > 0;
        if (seen)
        {
            var mult = State == AwarenessState.Wary ? _t.WaryFillMult : 1.0;
            Meter = Math.Min(1, Meter + fillPerS * mult * dt);
            _unseenS = 0;
        }
        else
        {
            _unseenS += dt;
            if (State != AwarenessState.Alerted)
            {
                Meter = Math.Max(0, Meter - _t.DrainPerS * dt);
            }
        }
        switch (State)
        {
            case AwarenessState.Unaware:
            case AwarenessState.Wary:
                if (Meter >= 1)
                {
                    Set(AwarenessState.Alerted);
                }
                else if (Meter >= _t.SuspiciousAt)
                {
                    _timer = _t.SuspiciousLookS;
                    Set(AwarenessState.Suspicious);
                }
                else if (State == AwarenessState.Wary && (_timer -= dt) <= 0)
                {
                    Set(AwarenessState.Unaware);
                }
                break;
            case AwarenessState.Suspicious:
                if (Meter >= 1)
                {
                    Set(AwarenessState.Alerted);
                }
                else if (!seen && (_timer -= dt) <= 0)
                {
                    _timer = _t.WaryS;
                    Set(AwarenessState.Wary);
                }
                break;
            case AwarenessState.Alerted:
                if (_unseenS >= _t.LostAfterS)
                {
                    _timer = _t.SearchS;
                    Meter = _t.SuspiciousAt;
                    Set(AwarenessState.Searching);
                }
                break;
            case AwarenessState.Searching:
                if (Meter >= 1)
                {
                    Set(AwarenessState.Alerted);
                }
                else if ((_timer -= dt) <= 0)
                {
                    _timer = _t.WaryS;
                    Set(AwarenessState.Wary);
                }
                break;
        }
    }

    /// <summary>Shortens the current search (Vanish).</summary>
    public void ScaleSearch(double mult)
    {
        if (State == AwarenessState.Searching)
        {
            _timer *= mult;
        }
    }

    private void Set(AwarenessState s)
    {
        if (s == State)
        {
            return;
        }
        State = s;
        StateChanged?.Invoke(s);
    }
}

/// <summary>What the law does about something it saw.</summary>
public enum LawResponse
{
    /// <summary>Nothing.</summary>
    None,

    /// <summary>A warning: "Put it away."</summary>
    Warn,

    /// <summary>A crime was seen: reported.</summary>
    Report,

    /// <summary>They fight.</summary>
    Hostile,
}

/// <summary>MerSec's patience in the hub: one warning, then force.</summary>
public sealed class LawWatch
{
    private readonly LawTable _t;
    private double _now;
    private double _warnedAt = double.NegativeInfinity;

    /// <summary>Creates a calm watch.</summary>
    public LawWatch(LawTable table) => _t = table;

    /// <summary>True once MerSec is hostile.</summary>
    public bool Hostile { get; private set; }

    /// <summary>Seconds until backup arrives, or null.</summary>
    public double? BackupInS { get; private set; }

    /// <summary>Advances time.</summary>
    public void Tick(double dt)
    {
        if (!double.IsFinite(dt) || dt <= 0)
        {
            return;
        }
        _now += dt;
        if (BackupInS is { } b)
        {
            BackupInS = Math.Max(0, b - dt);
        }
    }

    /// <summary>MerSec sees a drawn weapon: a warning the first time, force within the window after one.</summary>
    public LawResponse WeaponSeen()
    {
        if (Hostile)
        {
            return LawResponse.Hostile;
        }
        if (_now - _warnedAt <= _t.WarningWindowS)
        {
            return TurnHostile();
        }
        _warnedAt = _now;
        return LawResponse.Warn;
    }

    /// <summary>A shot is fired where MerSec can hear it.</summary>
    public LawResponse ShotFired() => Hostile ? LawResponse.Hostile : TurnHostile();

    /// <summary>A theft or a pick is seen by a resident or MerSec.</summary>
    public LawResponse CrimeSeen() => Hostile ? LawResponse.Hostile : LawResponse.Report;

    private LawResponse TurnHostile()
    {
        Hostile = true;
        BackupInS = _t.BackupDelayS;
        return LawResponse.Hostile;
    }
}
