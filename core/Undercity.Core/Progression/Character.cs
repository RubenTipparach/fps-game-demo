// The runner: level, XP, skill points, ranks and the perks they grant.
//
// It lives in the core because the skill-check value, the XP curve and what a perk does are
// single rules (CLAUDE.md 5.1) that dialog, locks, disguise and the screens all ask.

namespace Undercity.Core.Progression;

/// <summary>Whether a rank can be bought, and why not.</summary>
/// <param name="Ok">True when it can be bought now.</param>
/// <param name="Reason">What's missing, such as "needs 2 points" or "needs Stealth 2"; empty when ok.</param>
public sealed record RaiseCheck(bool Ok, string Reason);

/// <summary>The runner's progression.</summary>
public sealed class Character
{
    private readonly SkillTable _skills;
    private readonly ProgressionTable _progression;
    private readonly Dictionary<Skill, int> _ranks = new();
    private readonly HashSet<string> _paidSources = new(StringComparer.Ordinal);

    /// <summary>Creates a new runner: level 1, the start ranks and points.</summary>
    public Character(SkillTable skills, ProgressionTable progression)
    {
        _skills = skills;
        _progression = progression;
        foreach (var s in Enum.GetValues<Skill>())
        {
            _ranks[s] = progression.StartRanks.TryGetValue(s, out var r) ? r : 0;
        }
        Level = 1;
        SkillPoints = progression.StartPoints;
    }

    /// <summary>The current level, 1 to the cap.</summary>
    public int Level { get; private set; }

    /// <summary>XP gained toward the next level.</summary>
    public int Xp { get; private set; }

    /// <summary>All XP ever gained.</summary>
    public int TotalXp { get; private set; }

    /// <summary>Unspent skill points.</summary>
    public int SkillPoints { get; private set; }

    /// <summary>XP needed from the start of this level to the next, or 0 at the cap.</summary>
    public int XpToNext => Level >= _progression.LevelCap ? 0 : Level * _progression.XpPerLevel;

    /// <summary>Maximum health at this level.</summary>
    public int MaxHealth => _progression.BaseHealth + (Level - 1) * _progression.HealthPerLevel;

    /// <summary>The skill table this runner uses.</summary>
    public SkillTable Skills => _skills;

    /// <summary>Raises after XP is gained: the amount and the source's name.</summary>
    public event Action<int, string>? XpGained;

    /// <summary>Raises for each level gained, with the new level.</summary>
    public event Action<int>? LeveledUp;

    /// <summary>Raises when a rank or the points change.</summary>
    public event Action? Changed;

    /// <summary>The rank of a skill, 0 to 5.</summary>
    public int Rank(Skill skill) => _ranks[skill];

    /// <summary>
    /// The value a check compares against its DC: the rank plus at most the table's item bonus,
    /// capped at the table's maximum. The one skill-check rule.
    /// </summary>
    public int CheckValue(Skill skill, int itemBonus) =>
        Math.Min(_skills.MaxCheckValue, Rank(skill) + Math.Clamp(itemBonus, 0, _skills.MaxItemBonus));

    /// <summary>Whether the next rank of <paramref name="skill"/> can be bought now.</summary>
    public RaiseCheck CanRaise(Skill skill)
    {
        var next = Rank(skill) + 1;
        if (next > _skills.MaxRank)
        {
            return new RaiseCheck(false, "at the top rank");
        }
        var req = _skills.Get(skill).Perks[next - 1].Requires;
        if (req is not null && Rank(req.Skill) < req.Rank)
        {
            return new RaiseCheck(false, $"needs {_skills.Get(req.Skill).Name} {req.Rank}");
        }
        var cost = _skills.CostOf(next);
        if (SkillPoints < cost)
        {
            return new RaiseCheck(false, cost == 1 ? "needs 1 point" : $"needs {cost} points");
        }
        return new RaiseCheck(true, "");
    }

    /// <summary>Buys the next rank. Returns false, changing nothing, when <see cref="CanRaise"/> says no.</summary>
    public bool Raise(Skill skill)
    {
        if (!CanRaise(skill).Ok)
        {
            return false;
        }
        var next = Rank(skill) + 1;
        SkillPoints -= _skills.CostOf(next);
        _ranks[skill] = next;
        Changed?.Invoke();
        return true;
    }

    /// <summary>Adds skill points (a neural chip).</summary>
    public void AddSkillPoints(int points)
    {
        if (points <= 0)
        {
            return;
        }
        SkillPoints += points;
        Changed?.Invoke();
    }

    /// <summary>
    /// Adds XP, raising as many levels as it covers. A non-empty <paramref name="sourceId"/> pays
    /// once only (a dialog choice, a lock). Returns true when XP was added.
    /// </summary>
    public bool AddXp(int amount, string sourceId, string reason = "")
    {
        if (amount <= 0)
        {
            return false;
        }
        if (!string.IsNullOrEmpty(sourceId) && !_paidSources.Add(sourceId))
        {
            return false;
        }
        TotalXp += amount;
        Xp += amount;
        XpGained?.Invoke(amount, string.IsNullOrEmpty(reason) ? sourceId : reason);
        while (XpToNext > 0 && Xp >= XpToNext)
        {
            Xp -= XpToNext;
            Level++;
            SkillPoints += _progression.PointsPerLevel;
            LeveledUp?.Invoke(Level);
        }
        if (XpToNext == 0)
        {
            Xp = 0;
        }
        Changed?.Invoke();
        return true;
    }

    /// <summary>True when XP from this source was already paid.</summary>
    public bool WasPaid(string sourceId) => _paidSources.Contains(sourceId);

    /// <summary>The product of every owned perk's multiplier for <paramref name="stat"/>; 1 when none.</summary>
    public double Mult(string stat) => OwnedEffects(stat).Aggregate(1.0, (acc, e) => acc * e.Value);

    /// <summary>The sum of every owned perk's amount for <paramref name="stat"/>; 0 when none.</summary>
    public double Sum(string stat) => OwnedEffects(stat).Sum(e => e.Value);

    /// <summary>True when an owned perk turns on the flag <paramref name="stat"/>.</summary>
    public bool Has(string stat) => OwnedEffects(stat).Any(e => e.Value != 0);

    private IEnumerable<StatEffect> OwnedEffects(string stat) =>
        _skills.Skills.SelectMany(s => s.Perks.Take(Rank(s.Id)))
            .SelectMany(p => p.Effects)
            .Where(e => e.Stat == stat);

    /// <summary>A copy of the state for a save.</summary>
    public CharacterSave Save() => new()
    {
        Level = Level,
        Xp = Xp,
        TotalXp = TotalXp,
        SkillPoints = SkillPoints,
        Ranks = new SortedDictionary<Skill, int>(_ranks),
        PaidSources = _paidSources.OrderBy(s => s, StringComparer.Ordinal).ToList(),
    };

    /// <summary>
    /// Restores a save, repairing anything out of range to the nearest legal value (CLAUDE.md 5.6).
    /// Returns a message per repair.
    /// </summary>
    public IReadOnlyList<string> Load(CharacterSave save)
    {
        var repairs = new List<string>();
        Level = Math.Clamp(save.Level, 1, _progression.LevelCap);
        if (Level != save.Level)
        {
            repairs.Add($"level {save.Level} clamped to {Level}");
        }
        Xp = Math.Clamp(save.Xp, 0, Math.Max(0, XpToNext - 1));
        TotalXp = Math.Max(0, save.TotalXp);
        SkillPoints = Math.Max(0, save.SkillPoints);
        foreach (var s in Enum.GetValues<Skill>())
        {
            var r = save.Ranks.TryGetValue(s, out var v) ? v : 0;
            _ranks[s] = Math.Clamp(r, 0, _skills.MaxRank);
            if (_ranks[s] != r)
            {
                repairs.Add($"{s} rank {r} clamped to {_ranks[s]}");
            }
        }
        _paidSources.Clear();
        foreach (var p in save.PaidSources)
        {
            _paidSources.Add(p);
        }
        Changed?.Invoke();
        return repairs;
    }
}

/// <summary>The saved form of a <see cref="Character"/>.</summary>
public sealed class CharacterSave
{
    /// <summary>The level.</summary>
    public int Level { get; set; } = 1;

    /// <summary>XP toward the next level.</summary>
    public int Xp { get; set; }

    /// <summary>All XP gained.</summary>
    public int TotalXp { get; set; }

    /// <summary>Unspent points.</summary>
    public int SkillPoints { get; set; }

    /// <summary>Ranks by skill.</summary>
    public SortedDictionary<Skill, int> Ranks { get; set; } = new();

    /// <summary>XP sources already paid.</summary>
    public List<string> PaidSources { get; set; } = new();
}
