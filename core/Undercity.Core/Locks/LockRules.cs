// Locks: the four ways in (key, code, pick, hack), their hold times, tool costs, XP and noise.
//
// It lives in the core because the use prompt, the hold time and the outcome must come from one
// rule (CLAUDE.md 5.1, openspec/changes/world-interaction). The minigames (owner B2) will wrap
// this rule once their mockups are approved; until then the hold time is the stand-in.

using Undercity.Core.Data;
using Undercity.Core.Kit;
using Undercity.Core.Progression;

namespace Undercity.Core.Locks;

/// <summary>What kind of lock: it changes the prompt noun and the pick time.</summary>
public enum LockKind
{
    /// <summary>A door or gate.</summary>
    Door,

    /// <summary>A safe: picking takes longer.</summary>
    Safe,

    /// <summary>A container such as a locker or a box.</summary>
    Container,

    /// <summary>A terminal or electronic device: hacked, not picked.</summary>
    Device,
}

/// <summary>How a lock is opened.</summary>
public enum LockWay
{
    /// <summary>It can't be opened now.</summary>
    None,

    /// <summary>With its key item.</summary>
    Key,

    /// <summary>With a known code (a flag).</summary>
    Code,

    /// <summary>With a lockpick and Lockpicking.</summary>
    Pick,

    /// <summary>With a multitool and Hacking.</summary>
    Hack,
}

/// <summary>One lock, placed in a level's data.</summary>
public sealed class LockDef
{
    /// <summary>1 to 3; picking and hacking need at least this rank.</summary>
    public required int Tier { get; init; }

    /// <summary>What it's on.</summary>
    public LockKind Kind { get; init; } = LockKind.Door;

    /// <summary>The key item that opens it, or null.</summary>
    public string? Key { get; init; }

    /// <summary>The flag that means the code is known, or null.</summary>
    public string? CodeFlag { get; init; }

    /// <summary>True when it can be picked.</summary>
    public bool Pick { get; init; } = true;

    /// <summary>True when it can be hacked.</summary>
    public bool Hack { get; init; }
}

/// <summary>data/locks.json: timings, XP and noise for locks.</summary>
public sealed class LockTable : IValidated
{
    /// <summary>Picking time per tier, seconds.</summary>
    public required double PickTimePerTierS { get; init; }

    /// <summary>Hacking time per tier, seconds.</summary>
    public required double HackTimePerTierS { get; init; }

    /// <summary>Time to enter a known code, seconds.</summary>
    public required double CodeTimeS { get; init; }

    /// <summary>Safes take this many times longer to pick.</summary>
    public required double SafePickMult { get; init; }

    /// <summary>Noise radius of each way, metres.</summary>
    public required IReadOnlyDictionary<LockWay, double> NoiseM { get; init; }

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        if (PickTimePerTierS <= 0 || HackTimePerTierS <= 0 || CodeTimeS < 0 || SafePickMult < 1)
        {
            errors.Add("lock timings out of range");
        }
        if (NoiseM.Values.Any(v => v < 0 || !double.IsFinite(v)))
        {
            errors.Add("noise_m must be finite and not negative");
        }
    }
}

/// <summary>The plan for opening a lock now: the way, the time, the cost, and the prompt that says so.</summary>
/// <param name="Way">How it will open, or <see cref="LockWay.None"/>.</param>
/// <param name="HoldS">Seconds to hold use; 0 opens at once.</param>
/// <param name="Consumes">The item used up when it opens, or null.</param>
/// <param name="Xp">XP paid when it opens.</param>
/// <param name="NoiseM">The noise radius, metres.</param>
/// <param name="Prompt">The use prompt.</param>
public sealed record LockPlan(LockWay Way, double HoldS, string? Consumes, int Xp, double NoiseM, string Prompt)
{
    /// <summary>True when the lock can be opened now.</summary>
    public bool CanOpen => Way != LockWay.None;
}

/// <summary>The one lock rule.</summary>
public static class LockRules
{
    /// <summary>The noun for a lock kind in prompts.</summary>
    public static string Noun(LockKind kind) => kind switch
    {
        LockKind.Safe => "safe",
        LockKind.Container => "lock",
        LockKind.Device => "system",
        _ => "door",
    };

    /// <summary>
    /// The best way to open <paramref name="lk"/> now, tried in order: its key, a known code,
    /// picking (Lockpicking >= tier and a lockpick), hacking (Hacking >= tier and a multitool).
    /// </summary>
    public static LockPlan Best(LockDef lk, LockTable table, Character character, Kit.Inventory inventory,
        Func<string, bool> hasFlag, ItemNames names, int xpPerTier)
    {
        var noun = Noun(lk.Kind);
        if (lk.Key is not null && inventory.Pack.Has(lk.Key))
        {
            return new LockPlan(LockWay.Key, 0, null, 0, table.NoiseM.GetValueOrDefault(LockWay.Key),
                $"Unlock {noun} ({names(lk.Key)})");
        }
        if (lk.CodeFlag is not null && hasFlag(lk.CodeFlag))
        {
            return new LockPlan(LockWay.Code, table.CodeTimeS, null, 0, table.NoiseM.GetValueOrDefault(LockWay.Code),
                $"Enter code (hold {table.CodeTimeS:0.0} s)");
        }
        var lp = character.Rank(Skill.Lockpicking);
        var keepsPicks = character.Has("keeps_lockpicks");
        if (lk.Pick && lk.Kind != LockKind.Device && lp >= lk.Tier && (keepsPicks || inventory.Pack.Has("lockpick")))
        {
            var t = table.PickTimePerTierS * lk.Tier * character.Mult("pick_time_mult");
            if (lk.Kind == LockKind.Safe)
            {
                t *= table.SafePickMult * character.Mult("safe_time_mult");
            }
            return new LockPlan(LockWay.Pick, t, keepsPicks ? null : "lockpick", xpPerTier * lk.Tier,
                table.NoiseM.GetValueOrDefault(LockWay.Pick), $"Pick {noun}, tier {lk.Tier} (hold {t:0.0} s)");
        }
        var hk = character.Rank(Skill.Hacking);
        var keepsTools = character.Has("keeps_multitools");
        if (lk.Hack && hk >= lk.Tier && (keepsTools || inventory.Pack.Has("multitool")))
        {
            var t = table.HackTimePerTierS * lk.Tier * character.Mult("hack_time_mult");
            return new LockPlan(LockWay.Hack, t, keepsTools ? null : "multitool", xpPerTier * lk.Tier,
                table.NoiseM.GetValueOrDefault(LockWay.Hack), $"Hack {noun}, tier {lk.Tier} (hold {t:0.0} s)");
        }
        var needs = new List<string>();
        if (lk.Key is not null)
        {
            needs.Add(names(lk.Key));
        }
        if (lk.CodeFlag is not null)
        {
            needs.Add("the code");
        }
        if (lk.Pick && lk.Kind != LockKind.Device)
        {
            needs.Add(lp >= lk.Tier ? "a lockpick" : $"Lockpicking {lk.Tier}");
        }
        if (lk.Hack)
        {
            needs.Add(hk >= lk.Tier ? "a multitool" : $"Hacking {lk.Tier}");
        }
        var what = needs.Count == 0 ? "sealed" : "needs " + string.Join(", or ", needs);
        return new LockPlan(LockWay.None, 0, null, 0, 0, $"Locked {noun}: {what}");
    }
}

/// <summary>Looks up an item's display name, for prompts.</summary>
public delegate string ItemNames(string itemId);
