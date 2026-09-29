// The pack: a 10 x 6 grid where each item takes its footprint, and stackable items stack.
//
// It lives in the core because placement and stacking decide what a pickup, a container, a
// vendor and a save may do, and each must get the same answer (CLAUDE.md 5.1). An add that
// doesn't fit changes nothing it can't finish and reports what's left (CLAUDE.md 5.6).

using Undercity.Core.Items;

namespace Undercity.Core.Kit;

/// <summary>A stack of one item at a cell of the pack.</summary>
public sealed class PackItem
{
    internal PackItem(ItemDef def, int count, int x, int y, string? stolenFrom)
    {
        Def = def;
        Count = count;
        X = x;
        Y = y;
        StolenFrom = stolenFrom;
    }

    /// <summary>The item.</summary>
    public ItemDef Def { get; }

    /// <summary>How many, 1 to the item's stack limit.</summary>
    public int Count { get; internal set; }

    /// <summary>The column of its top-left cell.</summary>
    public int X { get; internal set; }

    /// <summary>The row of its top-left cell.</summary>
    public int Y { get; internal set; }

    /// <summary>The faction it was stolen from, or null.</summary>
    public string? StolenFrom { get; }

    /// <summary>True when the stack covers the cell.</summary>
    public bool Covers(int x, int y) => x >= X && x < X + Def.W && y >= Y && y < Y + Def.H;
}

/// <summary>The grid pack.</summary>
public sealed class Pack
{
    private readonly List<PackItem> _stacks = new();

    /// <summary>Creates an empty pack of the given size.</summary>
    public Pack(int cols = 10, int rows = 6)
    {
        Cols = cols;
        Rows = rows;
    }

    /// <summary>Columns.</summary>
    public int Cols { get; }

    /// <summary>Rows.</summary>
    public int Rows { get; }

    /// <summary>The stacks, in the order they were placed.</summary>
    public IReadOnlyList<PackItem> Stacks => _stacks;

    /// <summary>Raises when anything in the pack changes.</summary>
    public event Action? Changed;

    /// <summary>The stack covering a cell, or null. Out-of-range cells return null.</summary>
    public PackItem? At(int x, int y) =>
        x < 0 || y < 0 || x >= Cols || y >= Rows ? null : _stacks.FirstOrDefault(s => s.Covers(x, y));

    /// <summary>How many of an item the pack holds.</summary>
    public int Count(string itemId) => _stacks.Where(s => s.Def.Id == itemId).Sum(s => s.Count);

    /// <summary>True when the pack holds at least <paramref name="count"/> of an item.</summary>
    public bool Has(string itemId, int count = 1) => Count(itemId) >= count;

    /// <summary>True when a <paramref name="def"/>-sized item fits at (x, y), ignoring <paramref name="ignore"/>.</summary>
    public bool Fits(ItemDef def, int x, int y, PackItem? ignore = null)
    {
        if (x < 0 || y < 0 || x + def.W > Cols || y + def.H > Rows)
        {
            return false;
        }
        return !_stacks.Any(s => s != ignore
            && x < s.X + s.Def.W && s.X < x + def.W && y < s.Y + s.Def.H && s.Y < y + def.H);
    }

    /// <summary>The first free position for an item, scanning rows then columns, or null.</summary>
    public (int X, int Y)? FirstFit(ItemDef def, PackItem? ignore = null)
    {
        for (var y = 0; y <= Rows - def.H; y++)
        {
            for (var x = 0; x <= Cols - def.W; x++)
            {
                if (Fits(def, x, y, ignore))
                {
                    return (x, y);
                }
            }
        }
        return null;
    }

    /// <summary>How many of <paramref name="count"/> would fit if added now, without adding them.</summary>
    public int RoomFor(ItemDef def, int count, string? stolenFrom = null)
    {
        var placed = Plan(def, count, stolenFrom, out _, out _);
        return placed;
    }

    /// <summary>
    /// Adds up to <paramref name="count"/>: tops up matching stacks first, then places new stacks
    /// at the first fit. Returns how many didn't fit; those stay wherever they came from.
    /// </summary>
    public int Add(ItemDef def, int count, string? stolenFrom = null)
    {
        if (count <= 0 || def.CreditsOnPickup)
        {
            return count;
        }
        var placed = Plan(def, count, stolenFrom, out var topUps, out var newStacks);
        foreach (var (stack, add) in topUps)
        {
            stack.Count += add;
        }
        _stacks.AddRange(newStacks);
        if (placed > 0)
        {
            Changed?.Invoke();
        }
        return count - placed;
    }

    private int Plan(ItemDef def, int count, string? stolenFrom,
        out List<(PackItem Stack, int Add)> topUps, out List<PackItem> newStacks)
    {
        topUps = new();
        newStacks = new();
        var left = count;
        foreach (var s in _stacks.Where(s => s.Def == def && s.StolenFrom == stolenFrom && s.Count < def.Stack))
        {
            if (left == 0)
            {
                break;
            }
            var add = Math.Min(left, def.Stack - s.Count);
            topUps.Add((s, add));
            left -= add;
        }
        // Place new stacks in a scratch copy so a partial fit never writes half an operation.
        var scratch = new Pack(Cols, Rows);
        scratch._stacks.AddRange(_stacks);
        while (left > 0)
        {
            var at = scratch.FirstFit(def);
            if (at is null)
            {
                break;
            }
            var n = Math.Min(left, def.Stack);
            var stack = new PackItem(def, n, at.Value.X, at.Value.Y, stolenFrom);
            scratch._stacks.Add(stack);
            newStacks.Add(stack);
            left -= n;
        }
        return count - left;
    }

    /// <summary>Removes up to <paramref name="count"/> of an item, newest stacks last. Returns how many were removed.</summary>
    public int Remove(string itemId, int count = 1)
    {
        var removed = 0;
        foreach (var s in _stacks.Where(s => s.Def.Id == itemId).Reverse().ToList())
        {
            var take = Math.Min(count - removed, s.Count);
            s.Count -= take;
            removed += take;
            if (s.Count == 0)
            {
                _stacks.Remove(s);
            }
            if (removed == count)
            {
                break;
            }
        }
        if (removed > 0)
        {
            Changed?.Invoke();
        }
        return removed;
    }

    /// <summary>Removes one from a specific stack (using it). Returns false when the stack isn't in the pack.</summary>
    public bool TakeOne(PackItem stack)
    {
        if (!_stacks.Contains(stack))
        {
            return false;
        }
        stack.Count--;
        if (stack.Count <= 0)
        {
            _stacks.Remove(stack);
        }
        Changed?.Invoke();
        return true;
    }

    /// <summary>Removes a whole stack (dropping or equipping it). Returns false when it isn't in the pack.</summary>
    public bool RemoveStack(PackItem stack)
    {
        if (!_stacks.Remove(stack))
        {
            return false;
        }
        Changed?.Invoke();
        return true;
    }

    /// <summary>Puts a whole stack back at a free position, as when unequipping. Returns false when it can't fit.</summary>
    public bool PlaceStack(ItemDef def, int count, string? stolenFrom = null)
    {
        var at = FirstFit(def);
        if (at is null)
        {
            return false;
        }
        _stacks.Add(new PackItem(def, count, at.Value.X, at.Value.Y, stolenFrom));
        Changed?.Invoke();
        return true;
    }

    /// <summary>
    /// Moves a stack to (x, y). Dropped onto a matching stack, it merges as far as the limit
    /// allows. Returns false, changing nothing, when it can't go there.
    /// </summary>
    public bool Move(PackItem stack, int x, int y)
    {
        if (!_stacks.Contains(stack))
        {
            return false;
        }
        var target = At(x, y);
        if (target is not null && target != stack && target.Def == stack.Def
            && target.StolenFrom == stack.StolenFrom && target.Count < target.Def.Stack)
        {
            var add = Math.Min(stack.Count, target.Def.Stack - target.Count);
            target.Count += add;
            stack.Count -= add;
            if (stack.Count == 0)
            {
                _stacks.Remove(stack);
            }
            Changed?.Invoke();
            return true;
        }
        if (!Fits(stack.Def, x, y, stack))
        {
            return false;
        }
        stack.X = x;
        stack.Y = y;
        Changed?.Invoke();
        return true;
    }

    /// <summary>Splits <paramref name="count"/> off a stack into a new stack at the first fit. Returns false when there's no room.</summary>
    public bool Split(PackItem stack, int count)
    {
        if (!_stacks.Contains(stack) || count <= 0 || count >= stack.Count)
        {
            return false;
        }
        var at = FirstFit(stack.Def);
        if (at is null)
        {
            return false;
        }
        stack.Count -= count;
        _stacks.Add(new PackItem(stack.Def, count, at.Value.X, at.Value.Y, stack.StolenFrom));
        Changed?.Invoke();
        return true;
    }

    /// <summary>Empties the pack.</summary>
    public void Clear()
    {
        _stacks.Clear();
        Changed?.Invoke();
    }

    /// <summary>Restores a stack from a save exactly where it was, if it fits there; otherwise at the first fit. Returns false when it can't fit anywhere.</summary>
    public bool Restore(ItemDef def, int count, int x, int y, string? stolenFrom)
    {
        count = Math.Clamp(count, 1, def.Stack);
        if (!Fits(def, x, y))
        {
            var at = FirstFit(def);
            if (at is null)
            {
                return false;
            }
            (x, y) = at.Value;
        }
        _stacks.Add(new PackItem(def, count, x, y, stolenFrom));
        Changed?.Invoke();
        return true;
    }
}
