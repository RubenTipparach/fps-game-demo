// What the runner carries and wears: the pack, five equipment slots, the ten-slot belt and the
// wallet.
//
// It lives in the core because equipping, the belt and the disguise pieces are rules the
// inventory screen, the disguise verdict and the save must agree about
// (openspec/changes/inventory-and-equipment).

using Undercity.Core.Items;
using Undercity.Core.Progression;

namespace Undercity.Core.Kit;

/// <summary>A worn item.</summary>
/// <param name="Def">The item.</param>
/// <param name="StolenFrom">The faction it was stolen from, or null.</param>
public sealed record Worn(ItemDef Def, string? StolenFrom);

/// <summary>The pack, the equipment slots, the belt and the credits.</summary>
public sealed class Inventory
{
    private readonly Dictionary<EquipSlot, Worn> _worn = new();
    private readonly string?[] _belt;
    private readonly ItemDb _items;

    /// <summary>Creates an empty inventory with a 10 x 6 pack and a ten-slot belt.</summary>
    public Inventory(ItemDb items, int beltSize = 10)
    {
        _items = items;
        _belt = new string?[beltSize];
        Pack = new Pack();
        Pack.Changed += OnPackChanged;
    }

    /// <summary>The grid pack.</summary>
    public Pack Pack { get; }

    /// <summary>Credits carried.</summary>
    public int Credits { get; private set; }

    /// <summary>The item catalogue.</summary>
    public ItemDb Items => _items;

    /// <summary>Raises when anything changes: pack, slots, belt or credits.</summary>
    public event Action? Changed;

    // ------------------------------------------------------------------ credits

    /// <summary>Adds credits.</summary>
    public void Earn(int credits)
    {
        if (credits <= 0)
        {
            return;
        }
        Credits += credits;
        Changed?.Invoke();
    }

    /// <summary>Spends credits. Returns false, spending nothing, when there aren't enough.</summary>
    public bool Spend(int credits)
    {
        if (credits < 0 || credits > Credits)
        {
            return false;
        }
        Credits -= credits;
        Changed?.Invoke();
        return true;
    }

    // ------------------------------------------------------------------ picking up

    /// <summary>
    /// Takes up to <paramref name="count"/> of an item: credit chips become credits, anything
    /// else goes into the pack, and a new weapon or gadget goes on the belt. Returns how many
    /// were left behind for lack of room.
    /// </summary>
    public int PickUp(ItemDef def, int count, string? stolenFrom = null)
    {
        if (def.CreditsOnPickup)
        {
            Earn(def.Value * count);
            return 0;
        }
        var hadIt = Pack.Has(def.Id);
        var left = Pack.Add(def, count, stolenFrom);
        if (left < count && !hadIt && def.AutoBelt)
        {
            AutoBelt(def.Id);
        }
        return left;
    }

    // ------------------------------------------------------------------ equipment

    /// <summary>The item worn in a slot, or null.</summary>
    public Worn? WornIn(EquipSlot slot) => _worn.TryGetValue(slot, out var w) ? w : null;

    /// <summary>Everything worn, by slot.</summary>
    public IReadOnlyDictionary<EquipSlot, Worn> AllWorn => _worn;

    /// <summary>
    /// Wears a stack from the pack. Whatever was in the slot goes back into the pack; if it can't
    /// fit, nothing changes and this returns false.
    /// </summary>
    public bool Equip(PackItem stack)
    {
        if (stack.Def.Slot is not { } slot || !Pack.Stacks.Contains(stack))
        {
            return false;
        }
        var (x, y, stolen) = (stack.X, stack.Y, stack.StolenFrom);
        Pack.RemoveStack(stack);
        if (_worn.TryGetValue(slot, out var old) && !Pack.PlaceStack(old.Def, 1, old.StolenFrom))
        {
            Pack.Restore(stack.Def, stack.Count, x, y, stolen);
            return false;
        }
        if (stack.Count > 1)
        {
            Pack.Restore(stack.Def, stack.Count - 1, x, y, stolen);
        }
        _worn[slot] = new Worn(stack.Def, stolen);
        Changed?.Invoke();
        return true;
    }

    /// <summary>Wears an item straight from the catalogue (a new game, a save), replacing the slot.</summary>
    public void Wear(ItemDef def, string? stolenFrom = null)
    {
        if (def.Slot is not { } slot)
        {
            return;
        }
        _worn[slot] = new Worn(def, stolenFrom);
        Changed?.Invoke();
    }

    /// <summary>Takes off a slot's item into the pack. Returns false, changing nothing, when there's no room.</summary>
    public bool Unequip(EquipSlot slot)
    {
        if (!_worn.TryGetValue(slot, out var w) || !Pack.PlaceStack(w.Def, 1, w.StolenFrom))
        {
            return false;
        }
        _worn.Remove(slot);
        Changed?.Invoke();
        return true;
    }

    /// <summary>The faction of the worn outfit (BODY), or null: a disguise needs the outfit.</summary>
    public string? OutfitFaction => WornIn(EquipSlot.Body)?.Def.Faction;

    /// <summary>
    /// Disguise quality: the disguise weights of worn pieces that match the outfit's faction
    /// (BODY 2, HEAD 1, FACE 1). 0 without a faction outfit.
    /// </summary>
    public int DisguiseQuality
    {
        get
        {
            var faction = OutfitFaction;
            if (faction is null)
            {
                return 0;
            }
            return _worn.Values.Where(w => w.Def.Faction == faction).Sum(w => w.Def.Disguise);
        }
    }

    /// <summary>Total resistance to a damage type from worn items, capped at <paramref name="capPct"/>.</summary>
    public double ResistPct(string damageType, double capPct) =>
        Math.Min(capPct, _worn.Values.Sum(w => w.Def.ResistPct.TryGetValue(damageType, out var v) ? v : 0));

    /// <summary>The footstep noise multiplier of worn items.</summary>
    public double FootstepMult => _worn.Values.Aggregate(1.0, (acc, w) => acc * w.Def.FootstepMult);

    /// <summary>The largest skill bonus from any carried item (the check rule caps it).</summary>
    public int SkillBonus(Skill skill) => Pack.Stacks
        .Select(s => s.Def.SkillBonus.TryGetValue(skill, out var b) ? b : 0)
        .DefaultIfEmpty(0).Max();

    // ------------------------------------------------------------------ belt

    /// <summary>The belt: item ids by slot 0-9 (keys 1 to 0), or null for an empty slot.</summary>
    public IReadOnlyList<string?> Belt => _belt;

    /// <summary>Puts an item on a belt slot, removing it from any other slot. Returns false for a bad slot or an item not carried.</summary>
    public bool SetBelt(int slot, string? itemId)
    {
        if (slot < 0 || slot >= _belt.Length || itemId is not null && !Pack.Has(itemId))
        {
            return false;
        }
        if (itemId is not null)
        {
            for (var i = 0; i < _belt.Length; i++)
            {
                if (_belt[i] == itemId)
                {
                    _belt[i] = null;
                }
            }
        }
        _belt[slot] = itemId;
        Changed?.Invoke();
        return true;
    }

    /// <summary>Puts an item on the first free belt slot, if it isn't already on the belt.</summary>
    public void AutoBelt(string itemId)
    {
        if (Array.IndexOf(_belt, itemId) >= 0)
        {
            return;
        }
        var free = Array.IndexOf(_belt, null);
        if (free >= 0)
        {
            _belt[free] = itemId;
            Changed?.Invoke();
        }
    }

    private void OnPackChanged()
    {
        // A belt slot never points at nothing: it empties when its item is used up.
        for (var i = 0; i < _belt.Length; i++)
        {
            if (_belt[i] is { } id && !Pack.Has(id))
            {
                _belt[i] = null;
            }
        }
        Changed?.Invoke();
    }

    // ------------------------------------------------------------------ saves

    /// <summary>A copy of the state for a save.</summary>
    public InventorySave Save() => new()
    {
        Credits = Credits,
        Stacks = Pack.Stacks.Select(s => new StackSave { Item = s.Def.Id, Count = s.Count, X = s.X, Y = s.Y, StolenFrom = s.StolenFrom }).ToList(),
        Worn = new SortedDictionary<EquipSlot, string>(_worn.ToDictionary(kv => kv.Key, kv => kv.Value.Def.Id)),
        Belt = _belt.ToList(),
    };

    /// <summary>
    /// Restores a save, repairing what's damaged (CLAUDE.md 5.6): unknown items are dropped, stacks
    /// are clamped to their limit, and items that no longer fit go to the first free cell.
    /// Returns a message per repair.
    /// </summary>
    public IReadOnlyList<string> Load(InventorySave save)
    {
        var repairs = new List<string>();
        Pack.Clear();
        _worn.Clear();
        Array.Fill(_belt, null);
        Credits = Math.Max(0, save.Credits);
        foreach (var s in save.Stacks)
        {
            if (!_items.Exists(s.Item))
            {
                repairs.Add($"unknown item '{s.Item}' dropped");
                continue;
            }
            var def = _items.Get(s.Item);
            if (s.Count > def.Stack)
            {
                repairs.Add($"{s.Item} x{s.Count} clamped to its stack of {def.Stack}");
            }
            if (!Pack.Restore(def, s.Count, s.X, s.Y, s.StolenFrom))
            {
                repairs.Add($"{s.Item} didn't fit and was dropped");
            }
        }
        foreach (var (slot, id) in save.Worn)
        {
            if (_items.Exists(id) && _items.Get(id).Slot == slot)
            {
                _worn[slot] = new Worn(_items.Get(id), null);
            }
            else
            {
                repairs.Add($"worn '{id}' in {slot} dropped");
            }
        }
        for (var i = 0; i < Math.Min(_belt.Length, save.Belt.Count); i++)
        {
            _belt[i] = save.Belt[i] is { } id && Pack.Has(id) ? id : null;
        }
        Changed?.Invoke();
        return repairs;
    }
}

/// <summary>The saved form of an <see cref="Inventory"/>.</summary>
public sealed class InventorySave
{
    /// <summary>Credits.</summary>
    public int Credits { get; set; }

    /// <summary>Pack stacks.</summary>
    public List<StackSave> Stacks { get; set; } = new();

    /// <summary>Worn item ids by slot.</summary>
    public SortedDictionary<EquipSlot, string> Worn { get; set; } = new();

    /// <summary>Belt item ids, slot 0 first.</summary>
    public List<string?> Belt { get; set; } = new();
}

/// <summary>A saved pack stack.</summary>
public sealed class StackSave
{
    /// <summary>The item id.</summary>
    public string Item { get; set; } = "";

    /// <summary>How many.</summary>
    public int Count { get; set; } = 1;

    /// <summary>Column.</summary>
    public int X { get; set; }

    /// <summary>Row.</summary>
    public int Y { get; set; }

    /// <summary>The faction it was stolen from.</summary>
    public string? StolenFrom { get; set; }
}
