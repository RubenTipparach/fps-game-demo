// The combat rules: where a hit lands, what it does after zones and resistances, how likely an
// NPC's shot is to hit, and which defence a civilian takes (openspec/changes/hub-combat, design
// sections 3 to 5).
//
// It lives in the core because each is a rule the HUD, the NPCs, a save and a balance tool must
// agree on, and each exists once (CLAUDE.md 5.1): the runner's shots and the NPCs' shots resolve
// through the same damage rule.

using Undercity.Core.Data;
using Undercity.Core.World;

namespace Undercity.Core.Combat;

/// <summary>Where on a body a hit lands.</summary>
public enum HitZone
{
    /// <summary>The head: the top of the body.</summary>
    Head,

    /// <summary>Everything between the legs and the head.</summary>
    Torso,

    /// <summary>The legs (and, for melee and ranged alike, the limbs' multiplier).</summary>
    Limbs,
}

/// <summary>What a defender does when violence starts.</summary>
public enum Defence
{
    /// <summary>Fights back with their weapon.</summary>
    Fight,

    /// <summary>Runs away, then cowers.</summary>
    Flee,

    /// <summary>Drops and covers where they are.</summary>
    Cower,

    /// <summary>Puts their hands up.</summary>
    Surrender,
}

/// <summary>What sets a person off.</summary>
public enum Provocation
{
    /// <summary>A shot heard within the weapon's noise radius.</summary>
    ShotHeard,

    /// <summary>They were hurt.</summary>
    Hurt,

    /// <summary>They saw one of their own faction killed.</summary>
    MurderSeen,
}

/// <summary>The combat rules.</summary>
public static class CombatRules
{
    /// <summary>The zone a hit <paramref name="heightM"/> metres above a standing body's feet lands in.</summary>
    public static HitZone ZoneAt(ZoneTable zones, double heightM) =>
        heightM >= zones.HeadFromM ? HitZone.Head : heightM < zones.LegsBelowM ? HitZone.Limbs : HitZone.Torso;

    /// <summary>A zone's multiplier; the head's is multiplied by <paramref name="headshotMult"/> (the Headhunter perk).</summary>
    public static double ZoneMult(ZoneTable zones, HitZone zone, double headshotMult = 1.0) => zone switch
    {
        HitZone.Head => zones.Head * headshotMult,
        HitZone.Limbs => zones.Limbs,
        _ => zones.Torso,
    };

    /// <summary>
    /// The damage one hit (one pellet) of <paramref name="weapon"/> does: its damage times the zone's
    /// multiplier, less the target's resistance to its type, which is capped for NPCs and the
    /// runner alike (combat.json "resist_cap_pct"). The one damage rule.
    /// </summary>
    public static double Damage(CombatTable table, WeaponDef weapon, HitZone zone, double resistPct, bool targetIsPlayer,
        double headshotMult = 1.0)
    {
        var cap = targetIsPlayer ? table.ResistCapPct.Player : table.ResistCapPct.Npc;
        var resist = double.IsFinite(resistPct) ? Math.Clamp(resistPct, 0, cap) : 0;
        return weapon.Damage * ZoneMult(table.Zones, zone, headshotMult) * (1 - resist / 100.0);
    }

    /// <summary>
    /// The chance an NPC's shot hits the runner at <paramref name="distanceM"/> metres:
    /// base, less per metre, less for moving and crouching, clamped (combat.json "hit_chance").
    /// </summary>
    public static double HitChance(HitChanceTable t, double distanceM, bool moving, bool crouched)
    {
        var d = double.IsFinite(distanceM) ? Math.Max(0, distanceM) : double.MaxValue;
        var p = t.Base - t.PerM * d - (moving ? t.Moving : 0) - (crouched ? t.Crouched : 0);
        return Math.Clamp(p, t.Min, t.Max);
    }

    /// <summary>
    /// The defence a civilian takes, drawn from the pool's weights with a stream seeded by the
    /// run's seed and the civilian's stable id, so a save and a replay agree (CLAUDE.md 5.4).
    /// </summary>
    public static Defence CivilianDefence(IReadOnlyDictionary<string, int> weights, ulong seed, string stableId)
    {
        var ordered = weights.Where(p => p.Value > 0).OrderBy(p => p.Key, StringComparer.Ordinal).ToList();
        var total = ordered.Sum(p => p.Value);
        if (total <= 0)
        {
            return Defence.Cower;
        }
        var roll = SeededRandom.For(seed, stableId, "defence").Next(total);
        foreach (var (name, w) in ordered)
        {
            if (roll < w)
            {
                return ParseDefence(name) ?? Defence.Cower;
            }
            roll -= w;
        }
        return Defence.Cower;
    }

    /// <summary>
    /// The defence a person takes: a named NPC's from data/npcs.json, a civilian's drawn from the
    /// pool (<see cref="CivilianDefence"/>). The one rule for who does what when violence starts.
    /// </summary>
    public static Defence DefenceOf(NpcDef? named, CivilianPool pool, ulong seed, string stableId) =>
        named is not null ? ParseDefence(named.Defence) ?? Defence.Cower : CivilianDefence(pool.Defences, seed, stableId);

    /// <summary>
    /// What a person whose defence is <paramref name="defence"/> does when <paramref name="what"/>
    /// happens, or null when they carry on. A fighter fights when hurt or when they see one of
    /// their own killed; a shot they only hear doesn't start their fight (the law's own rule turns
    /// MerSec). Everyone else takes their defence at once.
    /// </summary>
    public static Defence? Respond(Defence defence, Provocation what) =>
        defence != Defence.Fight ? defence : what == Provocation.ShotHeard ? null : Defence.Fight;

    /// <summary>
    /// Whether an NPC's shot hits the runner: <see cref="HitChance"/> against a roll from a stream
    /// seeded by the run, the shooter's key and the shot's number, so a replay hits the same
    /// shots (CLAUDE.md 5.4).
    /// </summary>
    public static bool NpcShotHits(HitChanceTable t, ulong seed, string shooterKey, long shot, double distanceM,
        bool moving, bool crouched) =>
        SeededRandom.For(seed, shooterKey, $"shot:{shot}").NextDouble() < HitChance(t, distanceM, moving, crouched);

    /// <summary>A defence by its data name (fight, flee, cower, surrender), or null.</summary>
    public static Defence? ParseDefence(string name) => name switch
    {
        "fight" => Defence.Fight,
        "flee" => Defence.Flee,
        "cower" => Defence.Cower,
        "surrender" => Defence.Surrender,
        _ => null,
    };
}
