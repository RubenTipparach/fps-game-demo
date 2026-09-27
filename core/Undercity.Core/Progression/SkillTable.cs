// The skill and progression tables (data/skills.json, data/progression.json).
//
// It lives in the core because rank costs, perk effects, the XP curve and the XP awards are read
// by dialog, locks, disguise, the HUD and the skills screen, and each must read the same numbers
// (openspec/changes/character-progression).

using Undercity.Core.Data;
using Undercity.Core.Vitals;

namespace Undercity.Core.Progression;

/// <summary>The seven skills.</summary>
public enum Skill
{
    /// <summary>Spread, recoil, reloads.</summary>
    Firearms,

    /// <summary>Melee damage and takedowns.</summary>
    Melee,

    /// <summary>Noise and visibility.</summary>
    Stealth,

    /// <summary>Terminals, cameras, turrets.</summary>
    Hacking,

    /// <summary>Doors and safes.</summary>
    Lockpicking,

    /// <summary>Disguises and lies.</summary>
    Deception,

    /// <summary>Charm, threats and prices.</summary>
    Persuasion,
}

/// <summary>One numeric effect of a perk, applied to a named stat.</summary>
public sealed class StatEffect
{
    /// <summary>
    /// The stat. A name ending in <c>_mult</c> multiplies, <c>_add</c> adds, and anything else is a
    /// flag that is on when its value is non-zero.
    /// </summary>
    public required string Stat { get; init; }

    /// <summary>The multiplier, the amount added, or 1 for a flag.</summary>
    public required double Value { get; init; }
}

/// <summary>A cross-tree requirement: another skill's rank.</summary>
public sealed class PerkRequirement
{
    /// <summary>The other skill.</summary>
    public required Skill Skill { get; init; }

    /// <summary>The rank it must have.</summary>
    public required int Rank { get; init; }
}

/// <summary>The perk a rank grants.</summary>
public sealed class PerkDef
{
    /// <summary>The perk's name, such as "Steady Hands".</summary>
    public required string Name { get; init; }

    /// <summary>The short effect text shown on the skills screen.</summary>
    public required string Text { get; init; }

    /// <summary>The numeric effects, read by the systems that use them.</summary>
    public IReadOnlyList<StatEffect> Effects { get; init; } = Array.Empty<StatEffect>();

    /// <summary>A cross-tree requirement, or null.</summary>
    public PerkRequirement? Requires { get; init; }
}

/// <summary>One skill: its name, blurb and five perks.</summary>
public sealed class SkillDef
{
    /// <summary>The skill.</summary>
    public required Skill Id { get; init; }

    /// <summary>The display name.</summary>
    public required string Name { get; init; }

    /// <summary>What the skill governs, in a line.</summary>
    public required string Blurb { get; init; }

    /// <summary>The perks for ranks 1 to 5.</summary>
    public required IReadOnlyList<PerkDef> Perks { get; init; }
}

/// <summary>data/skills.json.</summary>
public sealed class SkillTable : IValidated
{
    /// <summary>Skill points for ranks 1 to 5.</summary>
    public required IReadOnlyList<int> RankCosts { get; init; }

    /// <summary>The highest check value, rank plus gear.</summary>
    public required int MaxCheckValue { get; init; }

    /// <summary>The most gear can add to a check.</summary>
    public required int MaxItemBonus { get; init; }

    /// <summary>The seven skills.</summary>
    public required IReadOnlyList<SkillDef> Skills { get; init; }

    /// <summary>The top rank.</summary>
    public int MaxRank => RankCosts.Count;

    /// <summary>The definition of a skill.</summary>
    public SkillDef Get(Skill skill) => Skills.First(s => s.Id == skill);

    /// <summary>The cost of buying <paramref name="rank"/> (1-based).</summary>
    public int CostOf(int rank) => RankCosts[rank - 1];

    /// <summary>The total cost of ranks 1 to <paramref name="rank"/>.</summary>
    public int CostTo(int rank) => RankCosts.Take(rank).Sum();

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        if (RankCosts.Count != 5 || RankCosts.Any(c => c < 1))
        {
            errors.Add("rank_costs must be five positive numbers");
        }
        foreach (var skill in Enum.GetValues<Skill>())
        {
            if (Skills.Count(s => s.Id == skill) != 1)
            {
                errors.Add($"skills: {skill} must appear exactly once");
            }
        }
        foreach (var s in Skills)
        {
            if (s.Perks.Count != RankCosts.Count)
            {
                errors.Add($"skills.{s.Id}: needs {RankCosts.Count} perks, has {s.Perks.Count}");
            }
            foreach (var p in s.Perks.Where(p => p.Requires is not null))
            {
                if (p.Requires!.Skill == s.Id || p.Requires.Rank is < 1 or > 5)
                {
                    errors.Add($"skills.{s.Id}.{p.Name}: bad requirement");
                }
            }
        }
        if (MaxCheckValue < RankCosts.Count || MaxItemBonus < 0)
        {
            errors.Add("max_check_value or max_item_bonus out of range");
        }
    }
}

/// <summary>XP paid for each kind of deed (data/progression.json "xp").</summary>
public sealed class XpAwards
{
    /// <summary>A passed dialog check pays this times its DC.</summary>
    public required int DialogCheckPerDc { get; init; }

    /// <summary>A lock or device pays this times its tier.</summary>
    public required int LockPerTier { get; init; }

    /// <summary>A non-lethal takedown or knock-out.</summary>
    public required int Takedown { get; init; }

    /// <summary>A kill.</summary>
    public required int Kill { get; init; }

    /// <summary>A secret area found.</summary>
    public required int Secret { get; init; }

    /// <summary>A clue that opens a route.</summary>
    public required int Clue { get; init; }

    /// <summary>Mission bonus: never in combat.</summary>
    public required int Ghost { get; init; }

    /// <summary>Mission bonus: no kills.</summary>
    public required int Merciful { get; init; }

    /// <summary>Mission bonus: no alarm raised.</summary>
    public required int SmoothOperator { get; init; }
}

/// <summary>One item of the starting kit.</summary>
public sealed class StartItem
{
    /// <summary>The item id.</summary>
    public required string Item { get; init; }

    /// <summary>How many.</summary>
    public int Count { get; init; } = 1;
}

/// <summary>data/progression.json: the XP curve, health, and the new runner.</summary>
public sealed class ProgressionTable : IValidated
{
    /// <summary>XP to the next level is this times the current level.</summary>
    public required int XpPerLevel { get; init; }

    /// <summary>The highest level.</summary>
    public required int LevelCap { get; init; }

    /// <summary>Skill points per level gained.</summary>
    public required int PointsPerLevel { get; init; }

    /// <summary>Unspent points a new runner has.</summary>
    public required int StartPoints { get; init; }

    /// <summary>Ranks a new runner has for free.</summary>
    public required IReadOnlyDictionary<Skill, int> StartRanks { get; init; }

    /// <summary>Maximum health at level 1.</summary>
    public required int BaseHealth { get; init; }

    /// <summary>Maximum health added per level.</summary>
    public required int HealthPerLevel { get; init; }

    /// <summary>Health regeneration: only up to a floor (owner B1).</summary>
    public required FloorRegen HealthRegen { get; init; }

    /// <summary>The XP awards.</summary>
    public required XpAwards Xp { get; init; }

    /// <summary>A new runner's credits.</summary>
    public required int StartCredits { get; init; }

    /// <summary>A new runner's pack.</summary>
    public required IReadOnlyList<StartItem> StartKit { get; init; }

    /// <summary>What a new runner wears, by slot name.</summary>
    public required IReadOnlyDictionary<string, string> StartWorn { get; init; }

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        if (XpPerLevel <= 0 || LevelCap < 1 || PointsPerLevel < 0 || StartPoints < 0)
        {
            errors.Add("xp_per_level, level_cap, points_per_level and start_points must be positive");
        }
        if (BaseHealth <= 0 || HealthPerLevel < 0)
        {
            errors.Add("base_health must be positive and health_per_level not negative");
        }
        if (HealthRegen.FloorPct is < 0 or > 100 || HealthRegen.RatePerS < 0 || HealthRegen.DelayS < 0)
        {
            errors.Add("health_regen out of range");
        }
        if (StartRanks.Values.Any(r => r is < 0 or > 5))
        {
            errors.Add("start_ranks must be 0 to 5");
        }
    }
}
