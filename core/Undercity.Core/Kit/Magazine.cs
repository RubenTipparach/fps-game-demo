// The rounds loaded in each of the runner's firearms, and the one reload rule
// (openspec/changes/archive/2026-09-28-hub-combat, design section 2).
//
// It lives in the core because what a weapon holds is saved, the HUD shows it ("12 / 24"), and a
// reload takes rounds out of the pack, which is the pack's rule: whole or not at all (CLAUDE.md
// 5.6).

using Undercity.Core.Combat;

namespace Undercity.Core.Kit;

/// <summary>Loaded rounds per weapon item.</summary>
public sealed class Magazines
{
    private readonly SortedDictionary<string, int> _loaded = new(StringComparer.Ordinal);

    /// <summary>Raises when a weapon's loaded rounds change.</summary>
    public event Action? Changed;

    /// <summary>
    /// The rounds loaded in the runner's <paramref name="itemId"/>, a <paramref name="weapon"/>. A
    /// firearm never fired or reloaded comes loaded; a melee weapon holds none.
    /// </summary>
    public int Loaded(string itemId, WeaponDef weapon) =>
        weapon.Melee ? 0 : _loaded.TryGetValue(itemId, out var n) ? n : weapon.Magazine;

    /// <summary>Fires one round. Returns false with nothing loaded (a dry click); a melee weapon always swings.</summary>
    public bool Fire(string itemId, WeaponDef weapon)
    {
        if (weapon.Melee)
        {
            return true;
        }
        var n = Loaded(itemId, weapon);
        if (n <= 0)
        {
            return false;
        }
        _loaded[itemId] = n - 1;
        Changed?.Invoke();
        return true;
    }

    /// <summary>
    /// Reloads from <paramref name="pack"/>: takes the rounds that fit, up to what the pack holds,
    /// and loads exactly what it took. Returns how many it loaded (0 when full, melee or out of rounds).
    /// </summary>
    public int Reload(string itemId, WeaponDef weapon, Pack pack)
    {
        if (weapon.Melee || weapon.Ammo is null)
        {
            return 0;
        }
        var loaded = Loaded(itemId, weapon);
        var want = Math.Min(weapon.Magazine - loaded, pack.Count(weapon.Ammo));
        if (want <= 0)
        {
            return 0;
        }
        var took = pack.Remove(weapon.Ammo, want);
        _loaded[itemId] = loaded + took;
        Changed?.Invoke();
        return took;
    }

    /// <summary>A copy for a save: rounds loaded by item id, for weapons that have been fired or reloaded.</summary>
    public SortedDictionary<string, int> Save() => new(_loaded, StringComparer.Ordinal);

    /// <summary>
    /// Restores from a save, repairing damage (CLAUDE.md 5.6): an unknown weapon is dropped and a
    /// count outside 0 to the magazine is clamped, each with a message.
    /// </summary>
    public IReadOnlyList<string> Load(IReadOnlyDictionary<string, int>? saved, Items.ItemDb items, WeaponTable weapons)
    {
        _loaded.Clear();
        var repairs = new List<string>();
        foreach (var (itemId, n) in saved ?? new SortedDictionary<string, int>())
        {
            var w = items.Exists(itemId) && items.Get(itemId).Weapon is { } wid ? weapons.Find(wid) : null;
            if (w is null || w.Melee)
            {
                repairs.Add($"magazines: '{itemId}' isn't a firearm; dropped");
                continue;
            }
            var clamped = Math.Clamp(n, 0, w.Magazine);
            if (clamped != n)
            {
                repairs.Add($"magazines: '{itemId}' held {n} rounds of {w.Magazine}; now {clamped}");
            }
            _loaded[itemId] = clamped;
        }
        return repairs;
    }
}
