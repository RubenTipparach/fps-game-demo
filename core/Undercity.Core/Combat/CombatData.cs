// Weapons and the combat numbers (data/weapons.json, data/combat.json).
//
// It lives in the core because damage, magazines, the NPCs' aim and what violence costs are rules
// a save, the HUD and the NPCs must agree on (CLAUDE.md 5.1; openspec/changes/archive/2026-09-28-hub-combat). The
// Godot layer fires and animates; it reads these numbers and asks the core what a hit does.

using Undercity.Core.Data;

namespace Undercity.Core.Combat;

/// <summary>A weapon: the runner's (named by an item's "weapon") or one only NPCs carry.</summary>
public sealed class WeaponDef
{
    /// <summary>The kinds of damage a weapon deals; resistances are per kind.</summary>
    public static readonly IReadOnlyList<string> DamageTypes = ["ballistic", "blunt", "shock", "tranq"];

    /// <summary>The display name.</summary>
    public required string Name { get; init; }

    /// <summary>Damage per hit, before zones and resistances.</summary>
    public required double Damage { get; init; }

    /// <summary>Hits per shot (a scattergun's pellets).</summary>
    public int Pellets { get; init; } = 1;

    /// <summary>The kind of damage: ballistic, blunt, shock or tranq.</summary>
    public required string Type { get; init; }

    /// <summary>Shots (or swings) per second.</summary>
    public required double RatePerS { get; init; }

    /// <summary>Shots per trigger pull.</summary>
    public int Burst { get; init; } = 1;

    /// <summary>Seconds between bursts.</summary>
    public double BurstGapS { get; init; }

    /// <summary>Rounds a full magazine holds; 0 for a melee weapon.</summary>
    public int Magazine { get; init; }

    /// <summary>Seconds a reload takes.</summary>
    public double ReloadS { get; init; }

    /// <summary>Spread of a shot, degrees either side of the aim.</summary>
    public double SpreadDeg { get; init; }

    /// <summary>A melee weapon's reach, metres.</summary>
    public double ReachM { get; init; }

    /// <summary>How far a shot or a swing is heard, metres.</summary>
    public required double NoiseM { get; init; }

    /// <summary>The item a reload takes from the pack, or null for a melee weapon.</summary>
    public string? Ammo { get; init; }

    /// <summary>The Godot scene that fires it, for the weapons built so far; null otherwise.</summary>
    public string? Scene { get; init; }

    /// <summary>True for a weapon only NPCs carry.</summary>
    public bool NpcOnly { get; init; }

    /// <summary>The sound of a shot or a swing (game/audio/sfx, without the variant number), or null.</summary>
    public string? FireSound { get; init; }

    /// <summary>The sound of a reload, or null.</summary>
    public string? ReloadSound { get; init; }

    /// <summary>The model an NPC holds it by (a res:// .glb), or null when nothing is drawn in their hand.</summary>
    public string? HandModel { get; init; }

    /// <summary>True for a weapon that swings rather than shoots.</summary>
    public bool Melee => Magazine == 0;
}

/// <summary>data/weapons.json.</summary>
public sealed class WeaponTable : IValidated
{
    /// <summary>The weapons by id.</summary>
    public required IReadOnlyDictionary<string, WeaponDef> Weapons { get; init; }

    /// <summary>The weapon with this id, or null.</summary>
    public WeaponDef? Find(string id) => Weapons.TryGetValue(id, out var w) ? w : null;

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        foreach (var (id, w) in Weapons.OrderBy(p => p.Key, StringComparer.Ordinal))
        {
            void Positive(string key, double v)
            {
                if (!double.IsFinite(v) || v <= 0)
                {
                    errors.Add($"weapons.{id}.{key} must be a finite number above zero");
                }
            }
            Positive("damage", w.Damage);
            Positive("rate_per_s", w.RatePerS);
            Positive("noise_m", w.NoiseM);
            if (!WeaponDef.DamageTypes.Contains(w.Type))
            {
                errors.Add($"weapons.{id}.type '{w.Type}' isn't one of {string.Join(", ", WeaponDef.DamageTypes)}");
            }
            if (w.Pellets < 1 || w.Burst < 1)
            {
                errors.Add($"weapons.{id}: pellets and burst must be 1 or more");
            }
            if (!double.IsFinite(w.BurstGapS) || w.BurstGapS < 0 || (w.Burst > 1 && w.BurstGapS <= 0))
            {
                errors.Add($"weapons.{id}.burst_gap_s must be above zero for a burst weapon, and never negative");
            }
            if (w.Magazine < 0)
            {
                errors.Add($"weapons.{id}.magazine can't be negative");
            }
            else if (w.Magazine == 0)
            {
                Positive("reach_m", w.ReachM);
                if (w.Ammo is not null)
                {
                    errors.Add($"weapons.{id}: a melee weapon takes no ammo");
                }
            }
            else
            {
                Positive("reload_s", w.ReloadS);
                if (!double.IsFinite(w.SpreadDeg) || w.SpreadDeg < 0 || w.SpreadDeg >= 45)
                {
                    errors.Add($"weapons.{id}.spread_deg must be 0 to under 45");
                }
                if (w.Ammo is null && !w.NpcOnly)
                {
                    errors.Add($"weapons.{id}: the runner's firearm needs its ammo item");
                }
            }
        }
    }
}

/// <summary>data/combat.json "zones": where on a 1.8 m body a hit lands, and what each zone multiplies.</summary>
public sealed class ZoneTable
{
    /// <summary>A hit this high above the feet or higher is to the head, metres.</summary>
    public required double HeadFromM { get; init; }

    /// <summary>A hit lower than this above the feet is to the legs, metres.</summary>
    public required double LegsBelowM { get; init; }

    /// <summary>The head's multiplier (the Headhunter perk's headshot_mult multiplies it).</summary>
    public required double Head { get; init; }

    /// <summary>The torso's multiplier.</summary>
    public required double Torso { get; init; }

    /// <summary>The limbs' multiplier.</summary>
    public required double Limbs { get; init; }
}

/// <summary>data/combat.json "resist_cap_pct": the most a resistance can take off, percent.</summary>
public sealed class ResistCaps
{
    /// <summary>For an NPC.</summary>
    public required double Npc { get; init; }

    /// <summary>For the runner.</summary>
    public required double Player { get; init; }
}

/// <summary>data/combat.json "hit_chance": how likely an NPC's shot is to hit the runner.</summary>
public sealed class HitChanceTable
{
    /// <summary>The chance at point blank, standing still.</summary>
    public required double Base { get; init; }

    /// <summary>Taken off per metre of range.</summary>
    public required double PerM { get; init; }

    /// <summary>Taken off while the runner moves.</summary>
    public required double Moving { get; init; }

    /// <summary>Taken off while the runner crouches.</summary>
    public required double Crouched { get; init; }

    /// <summary>The runner counts as moving above this speed, m/s.</summary>
    public required double MovingMps { get; init; }

    /// <summary>The least chance.</summary>
    public required double Min { get; init; }

    /// <summary>The most chance.</summary>
    public required double Max { get; init; }
}

/// <summary>data/combat.json "fight": the ranges a gunfighter keeps.</summary>
public sealed class FightTable
{
    /// <summary>A gunfighter closes to this range, metres.</summary>
    public required double CloseToM { get; init; }

    /// <summary>And backs off inside this range, metres.</summary>
    public required double BackOffM { get; init; }

    /// <summary>A fighter sees the runner in a clear line within this range, metres.</summary>
    public required double SightM { get; init; }

    /// <summary>A fighter who can't see the runner keeps after them this long after the last shot or hit, seconds.</summary>
    public required double PursueS { get; init; }
}

/// <summary>data/combat.json "reputation": what violence costs with the victim's faction.</summary>
public sealed class ViolenceRep
{
    /// <summary>The first time someone is hurt (assault).</summary>
    public required int Assault { get; init; }

    /// <summary>When someone is killed (murder).</summary>
    public required int Murder { get; init; }
}

/// <summary>data/combat.json.</summary>
public sealed class CombatTable : IValidated
{
    /// <summary>Hit zones.</summary>
    public required ZoneTable Zones { get; init; }

    /// <summary>Resistance caps.</summary>
    public required ResistCaps ResistCapPct { get; init; }

    /// <summary>The NPCs' hit chance.</summary>
    public required HitChanceTable HitChance { get; init; }

    /// <summary>A gunfighter's ranges.</summary>
    public required FightTable Fight { get; init; }

    /// <summary>A fleeing person runs to a point at least this far from the shooter, metres.</summary>
    public required double FleeM { get; init; }

    /// <summary>A cowering person stays down until this long after the last shot heard, seconds.</summary>
    public required double CowerS { get; init; }

    /// <summary>A surrendered person stays put while the runner is within this range, metres.</summary>
    public required double SurrenderRadiusM { get; init; }

    /// <summary>What violence costs.</summary>
    public required ViolenceRep Reputation { get; init; }

    /// <summary>The screen fades to black over this long when the runner dies, seconds.</summary>
    public required double DeathFadeS { get; init; }

    /// <summary>How fast a fighter closes in, running, m/s.</summary>
    public required double RunMps { get; init; }

    /// <summary>How fast a person flees, sprinting, m/s.</summary>
    public required double SprintMps { get; init; }

    /// <summary>The shove a killing shot gives the body's chest along the shot, newton-seconds.</summary>
    public required double DeathPushNs { get; init; }

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
        if (!(Zones.LegsBelowM > 0 && Zones.LegsBelowM < Zones.HeadFromM))
        {
            errors.Add("zones: legs_below_m must be above 0 and below head_from_m");
        }
        Positive("zones.head", Zones.Head);
        Positive("zones.torso", Zones.Torso);
        Positive("zones.limbs", Zones.Limbs);
        foreach (var (key, v) in new[] { ("npc", ResistCapPct.Npc), ("player", ResistCapPct.Player) })
        {
            if (!double.IsFinite(v) || v < 0 || v > 100)
            {
                errors.Add($"resist_cap_pct.{key} must be 0 to 100");
            }
        }
        var h = HitChance;
        if (!(0 <= h.Min && h.Min <= h.Max && h.Max <= 1) || !double.IsFinite(h.Base) || h.PerM < 0 || h.Moving < 0 || h.Crouched < 0)
        {
            errors.Add("hit_chance: min and max must be 0 to 1 with min under max, and the penalties never negative");
        }
        if (!double.IsFinite(h.MovingMps) || h.MovingMps < 0)
        {
            errors.Add("hit_chance.moving_mps must be a finite speed, zero or more");
        }
        if (!(Fight.BackOffM > 0 && Fight.BackOffM < Fight.CloseToM && Fight.CloseToM <= Fight.SightM))
        {
            errors.Add("fight: back_off_m must be above 0 and below close_to_m, and close_to_m no more than sight_m");
        }
        Positive("fight.pursue_s", Fight.PursueS);
        Positive("flee_m", FleeM);
        Positive("cower_s", CowerS);
        Positive("surrender_radius_m", SurrenderRadiusM);
        Positive("death_fade_s", DeathFadeS);
        Positive("run_mps", RunMps);
        Positive("sprint_mps", SprintMps);
        if (!double.IsFinite(DeathPushNs) || DeathPushNs < 0)
        {
            errors.Add("death_push_ns must be a finite number, zero or more");
        }
        if (Reputation.Assault > 0 || Reputation.Murder > 0)
        {
            errors.Add("reputation: assault and murder cost reputation (zero or less)");
        }
    }
}
