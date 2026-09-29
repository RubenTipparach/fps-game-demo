// Factions and reputation (data/factions.json): who likes you, and what that changes.
//
// It lives in the core because stance decides prices, dialog conditions and who attacks you in
// the hub, and all three must read the same number (openspec/changes/dialog-and-social).

using Undercity.Core.Data;

namespace Undercity.Core.Factions;

/// <summary>How a faction treats the runner, from reputation.</summary>
public enum Stance
{
    /// <summary>Hostile everywhere, the hub too.</summary>
    Hated,

    /// <summary>Higher prices; some doors stay shut.</summary>
    Disliked,

    /// <summary>Normal.</summary>
    Neutral,

    /// <summary>Lower prices; extra dialog.</summary>
    Liked,

    /// <summary>Faction doors open; members warn you of alarms.</summary>
    Trusted,
}

/// <summary>One faction.</summary>
public sealed class FactionDef
{
    /// <summary>The id, such as <c>drain_rats</c>.</summary>
    public required string Id { get; init; }

    /// <summary>The display name.</summary>
    public required string Name { get; init; }

    /// <summary>Reputation at the start of a new game, -100 to 100.</summary>
    public required int StartRep { get; init; }
}

/// <summary>data/factions.json.</summary>
public sealed class FactionTable : IValidated
{
    /// <summary>Reputation at or below this is Hated.</summary>
    public required int HatedAtMost { get; init; }

    /// <summary>Reputation at or below this (and above Hated) is Disliked.</summary>
    public required int DislikedAtMost { get; init; }

    /// <summary>Reputation at or above this (and below Trusted) is Liked.</summary>
    public required int LikedAtLeast { get; init; }

    /// <summary>Reputation at or above this is Trusted.</summary>
    public required int TrustedAtLeast { get; init; }

    /// <summary>Price multipliers by stance; a stance not listed pays 1.</summary>
    public required IReadOnlyDictionary<Stance, double> PriceMult { get; init; }

    /// <summary>The factions.</summary>
    public required IReadOnlyList<FactionDef> Factions { get; init; }

    /// <summary>True when the faction id exists.</summary>
    public bool Exists(string id) => Factions.Any(f => f.Id == id);

    /// <summary>The stance for a reputation value.</summary>
    public Stance StanceFor(int rep) => rep <= HatedAtMost ? Stance.Hated
        : rep <= DislikedAtMost ? Stance.Disliked
        : rep >= TrustedAtLeast ? Stance.Trusted
        : rep >= LikedAtLeast ? Stance.Liked
        : Stance.Neutral;

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        if (!(HatedAtMost < DislikedAtMost && DislikedAtMost < LikedAtLeast && LikedAtLeast < TrustedAtLeast))
        {
            errors.Add("stance thresholds must rise: hated < disliked < liked < trusted");
        }
        foreach (var f in Factions.Where(f => f.StartRep is < -100 or > 100))
        {
            errors.Add($"factions.{f.Id}: start_rep must be -100 to 100");
        }
        foreach (var dup in Factions.GroupBy(f => f.Id).Where(g => g.Count() > 1))
        {
            errors.Add($"factions: '{dup.Key}' appears twice");
        }
    }
}

/// <summary>The runner's reputation with every faction, -100 to 100.</summary>
public sealed class Reputation
{
    private readonly FactionTable _table;
    private readonly SortedDictionary<string, int> _rep = new(StringComparer.Ordinal);

    /// <summary>Starts every faction at its start reputation.</summary>
    public Reputation(FactionTable table)
    {
        _table = table;
        foreach (var f in table.Factions)
        {
            _rep[f.Id] = f.StartRep;
        }
    }

    /// <summary>Raises with the faction id when a reputation changes.</summary>
    public event Action<string>? Changed;

    /// <summary>Reputation with a faction; 0 for an unknown one.</summary>
    public int Get(string faction) => _rep.TryGetValue(faction, out var r) ? r : 0;

    /// <summary>The stance of a faction.</summary>
    public Stance StanceOf(string faction) => _table.StanceFor(Get(faction));

    /// <summary>The price multiplier a faction's vendor charges.</summary>
    public double PriceMult(string? faction) =>
        faction is not null && _table.PriceMult.TryGetValue(StanceOf(faction), out var m) ? m : 1.0;

    /// <summary>Changes reputation, scaling gains by <paramref name="gainMult"/> (Friendly), clamped to -100..100.</summary>
    public void Change(string faction, int delta, double gainMult = 1.0)
    {
        if (delta == 0 || !_rep.TryGetValue(faction, out var current))
        {
            return;
        }
        var scaled = delta > 0 ? (int)Math.Round(delta * gainMult, MidpointRounding.AwayFromZero) : delta;
        _rep[faction] = Math.Clamp(current + scaled, -100, 100);
        Changed?.Invoke(faction);
    }

    /// <summary>A copy for a save.</summary>
    public SortedDictionary<string, int> Save() => new(_rep, StringComparer.Ordinal);

    /// <summary>Restores a save, clamping values and ignoring unknown factions.</summary>
    public void Load(IReadOnlyDictionary<string, int> saved)
    {
        foreach (var (id, v) in saved)
        {
            if (_rep.ContainsKey(id))
            {
                _rep[id] = Math.Clamp(v, -100, 100);
            }
        }
    }
}
