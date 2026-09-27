using System;
using System.Collections.Generic;
using System.Linq;
using Godot;

namespace Brushfire;

/// <summary>A stack of one item type occupying a W x H footprint at (X, Y) in the grid.</summary>
public class ItemStack
{
    public ItemDef Def;
    public int Count;
    public int X, Y;
    public string Id => Def.Id;
    public Rect2I Rect => new(X, Y, Def.W, Def.H);
}

/// <summary>
/// Deus Ex-style grid inventory (10 x 6), five equipment slots and a ten-slot belt (keys 1-0).
/// Equipped items leave the grid. The belt stores item ids; a belt slot is live while the
/// inventory holds that item. Weapons read their ammo straight from the grid (see
/// WeaponManager.AmmoProvider).
/// </summary>
public class Inventory
{
    public const int Cols = 10, Rows = 6, BeltSize = 10;

    readonly List<ItemStack> _stacks = new();
    readonly Dictionary<EquipSlot, ItemDef> _equipped = new();
    public readonly string[] Belt = new string[BeltSize];

    public event Action Changed;
    public IReadOnlyList<ItemStack> Stacks => _stacks;

    public void NotifyChanged() => Changed?.Invoke();

    // ------------------------------------------------------------------ queries

    public int Count(string id) => _stacks.Where(s => s.Id == id).Sum(s => s.Count);
    public bool Has(string id) => Count(id) > 0 || _equipped.Values.Any(d => d.Id == id);
    public ItemDef Equipped(EquipSlot slot) => _equipped.TryGetValue(slot, out var d) ? d : null;
    public ItemStack StackAt(int x, int y) => _stacks.FirstOrDefault(s => s.Rect.HasPoint(new Vector2I(x, y)));

    public bool CanPlace(ItemDef def, int x, int y, ItemStack ignore = null)
    {
        if (x < 0 || y < 0 || x + def.W > Cols || y + def.H > Rows)
            return false;
        var r = new Rect2I(x, y, def.W, def.H);
        return !_stacks.Any(s => s != ignore && s.Rect.Intersects(r));
    }

    bool FindSpot(ItemDef def, out int x, out int y)
    {
        // Row-major scan from the top left, like Deus Ex.
        for (y = 0; y <= Rows - def.H; y++)
            for (x = 0; x <= Cols - def.W; x++)
                if (CanPlace(def, x, y))
                    return true;
        x = y = -1;
        return false;
    }

    /// <summary>How many of `count` would fit (without adding anything).</summary>
    public int RoomFor(ItemDef def, int count)
    {
        int room = _stacks.Where(s => s.Id == def.Id).Sum(s => def.Stack - s.Count);
        if (room >= count)
            return count;
        // Free cells, packed greedily with a scratch copy of the grid.
        var scratch = new Inventory();
        foreach (var s in _stacks)
            scratch._stacks.Add(new ItemStack { Def = s.Def, Count = s.Count, X = s.X, Y = s.Y });
        while (room < count && scratch.FindSpot(def, out int x, out int y))
        {
            scratch._stacks.Add(new ItemStack { Def = def, Count = def.Stack, X = x, Y = y });
            room += def.Stack;
        }
        return Math.Min(room, count);
    }

    // ------------------------------------------------------------------ changes

    /// <summary>Adds up to `count`, merging stacks first. Returns how many did NOT fit.</summary>
    public int Add(ItemDef def, int count = 1)
    {
        if (def == null || count <= 0)
            return count;
        foreach (var s in _stacks.Where(s => s.Id == def.Id && s.Count < def.Stack))
        {
            int take = Math.Min(count, def.Stack - s.Count);
            s.Count += take;
            count -= take;
            if (count == 0)
                break;
        }
        while (count > 0 && FindSpot(def, out int x, out int y))
        {
            int take = Math.Min(count, def.Stack);
            _stacks.Add(new ItemStack { Def = def, Count = take, X = x, Y = y });
            count -= take;
        }
        AutoBelt(def);
        Changed?.Invoke();
        return count;
    }

    public int Add(string id, int count = 1) => Add(ItemDb.Get(id), count);

    /// <summary>Removes up to `count` of an item (smallest stacks first). Returns how many were removed.</summary>
    public int Remove(string id, int count = 1)
    {
        int removed = 0;
        foreach (var s in _stacks.Where(s => s.Id == id).OrderBy(s => s.Count).ToList())
        {
            int take = Math.Min(count - removed, s.Count);
            s.Count -= take;
            removed += take;
            if (s.Count == 0)
                _stacks.Remove(s);
            if (removed == count)
                break;
        }
        if (removed > 0)
        {
            CleanBelt();
            Changed?.Invoke();
        }
        return removed;
    }

    public void RemoveStack(ItemStack s)
    {
        if (_stacks.Remove(s))
        {
            CleanBelt();
            Changed?.Invoke();
        }
    }

    public bool Move(ItemStack s, int x, int y)
    {
        if (!CanPlace(s.Def, x, y, s))
        {
            // Dropping onto a stack of the same item merges into it.
            var target = StackAt(x, y);
            if (target != null && target != s && target.Id == s.Id && target.Count < s.Def.Stack)
            {
                int take = Math.Min(s.Count, s.Def.Stack - target.Count);
                target.Count += take;
                s.Count -= take;
                if (s.Count == 0)
                    _stacks.Remove(s);
                Changed?.Invoke();
                return true;
            }
            return false;
        }
        s.X = x;
        s.Y = y;
        Changed?.Invoke();
        return true;
    }

    /// <summary>Wear a grid item. The previously worn item goes back to the grid (fails if it doesn't fit).</summary>
    public bool Equip(ItemStack s)
    {
        if (s == null || !s.Def.Equippable)
            return false;
        var slot = s.Def.Slot;
        var old = Equipped(slot);
        // Take one out of the grid first so the old item can use the freed cells.
        s.Count--;
        if (s.Count == 0)
            _stacks.Remove(s);
        if (old != null && Add(old) > 0)
        {
            // No room for the old item: undo.
            Add(s.Def);
            return false;
        }
        _equipped[slot] = s.Def;
        Changed?.Invoke();
        return true;
    }

    public bool Unequip(EquipSlot slot)
    {
        var d = Equipped(slot);
        if (d == null || RoomFor(d, 1) < 1)
            return false;
        _equipped.Remove(slot);
        Add(d);
        return true;
    }

    /// <summary>Directly wear an item without it passing through the grid (new-game setup, dialog gifts).</summary>
    public void Wear(ItemDef def)
    {
        if (def?.Equippable == true)
        {
            _equipped[def.Slot] = def;
            Changed?.Invoke();
        }
    }

    // ------------------------------------------------------------------ belt

    public void AutoBelt(ItemDef def)
    {
        if (def == null || !def.Beltable || Belt.Contains(def.Id))
            return;
        // Weapons and gadgets always get a slot; consumables only medkits and stims.
        if (def.Cat == ItemCategory.Consumable && def.Heal < 25)
            return;
        for (int i = 0; i < BeltSize; i++)
            if (Belt[i] == null)
            {
                Belt[i] = def.Id;
                return;
            }
    }

    public void SetBelt(int index, string id)
    {
        if (index < 0 || index >= BeltSize)
            return;
        for (int i = 0; i < BeltSize; i++)
            if (Belt[i] == id)
                Belt[i] = null;
        Belt[index] = id;
        Changed?.Invoke();
    }

    void CleanBelt()
    {
        for (int i = 0; i < BeltSize; i++)
            if (Belt[i] != null && !Has(Belt[i]))
                Belt[i] = null;
    }

    // ------------------------------------------------------------------ derived stats

    /// <summary>The faction the body outfit claims, or "" for street clothes.</summary>
    public string DisguiseFaction => Equipped(EquipSlot.Body)?.Faction ?? "";

    /// <summary>Disguise quality Q: body 2, head 1, face 1 for pieces matching the outfit's faction.</summary>
    public int DisguiseQuality
    {
        get
        {
            string f = DisguiseFaction;
            if (string.IsNullOrEmpty(f))
                return 0;
            int q = 0;
            foreach (var slot in new[] { EquipSlot.Body, EquipSlot.Head, EquipSlot.Face })
            {
                var d = Equipped(slot);
                if (d != null && d.Faction == f)
                    q += d.Cover;
            }
            return q;
        }
    }

    /// <summary>Armour that doesn't belong to the disguise faction makes observers suspicious.</summary>
    public bool ArmorClashes
    {
        get
        {
            var a = Equipped(EquipSlot.Armor);
            return a != null && !string.IsNullOrEmpty(DisguiseFaction) && a.Faction != DisguiseFaction;
        }
    }

    /// <summary>Damage absorbed per hit, in percent (armour + helmet), capped at 60 %.</summary>
    public int ArmorPercent => Math.Min(60, (Equipped(EquipSlot.Armor)?.Armor ?? 0) + (Equipped(EquipSlot.Head)?.Armor ?? 0));

    public float FootstepNoise => Equipped(EquipSlot.Boots)?.Noise ?? 1f;
}
