// What the world remembers: story flags, per-level state by stable id, NPC status, vendor
// stock sold, truces, and where the runner is.
//
// It lives in the core because dialog, triggers, containers, doors and the save all read and
// write it, and saved ids must be stable (openspec/changes/world-interaction, CLAUDE.md 5.4).

namespace Undercity.Core.World;

/// <summary>An NPC's lasting status.</summary>
public enum NpcStatus
{
    /// <summary>Alive and normal.</summary>
    Alive,

    /// <summary>Knocked out.</summary>
    Unconscious,

    /// <summary>Dead.</summary>
    Dead,

    /// <summary>Hostile to the runner.</summary>
    Hostile,

    /// <summary>Gone from the level (left, fled, arrested).</summary>
    Gone,
}

/// <summary>One level's memory, by stable id.</summary>
public sealed class LevelState
{
    /// <summary>World items taken and containers emptied.</summary>
    public SortedSet<string> Taken { get; set; } = new(StringComparer.Ordinal);

    /// <summary>Locks opened.</summary>
    public SortedSet<string> Opened { get; set; } = new(StringComparer.Ordinal);

    /// <summary>Doors left open (true) or shut (false).</summary>
    public SortedDictionary<string, bool> Doors { get; set; } = new(StringComparer.Ordinal);

    /// <summary>Device states, such as "looped" or "off".</summary>
    public SortedDictionary<string, string> Devices { get; set; } = new(StringComparer.Ordinal);

    /// <summary>What containers still hold after a partial search: item id to count.</summary>
    public SortedDictionary<string, SortedDictionary<string, int>> Leftovers { get; set; } = new(StringComparer.Ordinal);
}

/// <summary>Everything the world remembers between saves.</summary>
public sealed class WorldState
{
    /// <summary>Story flags, codes and passwords.</summary>
    public SortedSet<string> Flags { get; set; } = new(StringComparer.Ordinal);

    /// <summary>Per-level memory by level id.</summary>
    public SortedDictionary<string, LevelState> Levels { get; set; } = new(StringComparer.Ordinal);

    /// <summary>NPC status by NPC id (absent means alive).</summary>
    public SortedDictionary<string, NpcStatus> Npcs { get; set; } = new(StringComparer.Ordinal);

    /// <summary>Items sold since the last restock, by vendor then item.</summary>
    public SortedDictionary<string, SortedDictionary<string, int>> Sold { get; set; } = new(StringComparer.Ordinal);

    /// <summary>Factions with a truce in force.</summary>
    public SortedSet<string> Parleys { get; set; } = new(StringComparer.Ordinal);

    /// <summary>The seed every random stream derives from.</summary>
    public ulong Seed { get; set; }

    /// <summary>The level the runner is in.</summary>
    public string CurrentLevel { get; set; } = "hub";

    /// <summary>The spawn point to use when the level loads.</summary>
    public string Spawn { get; set; } = "";

    /// <summary>Seconds played.</summary>
    public double PlayTimeS { get; set; }

    /// <summary>Raises with the flag's name when a flag is set or cleared.</summary>
    public event Action<string>? FlagChanged;

    /// <summary>True when a flag is set.</summary>
    public bool Flag(string flag) => Flags.Contains(flag);

    /// <summary>Sets a flag. Returns true when it wasn't set before.</summary>
    public bool SetFlag(string flag)
    {
        if (!Flags.Add(flag))
        {
            return false;
        }
        FlagChanged?.Invoke(flag);
        return true;
    }

    /// <summary>Clears a flag.</summary>
    public void ClearFlag(string flag)
    {
        if (Flags.Remove(flag))
        {
            FlagChanged?.Invoke(flag);
        }
    }

    /// <summary>A level's memory, created on first use.</summary>
    public LevelState Level(string levelId)
    {
        if (!Levels.TryGetValue(levelId, out var s))
        {
            s = new LevelState();
            Levels[levelId] = s;
        }
        return s;
    }

    /// <summary>An NPC's status (alive when never set).</summary>
    public NpcStatus Npc(string npcId) => Npcs.TryGetValue(npcId, out var s) ? s : NpcStatus.Alive;

    /// <summary>Sets an NPC's status.</summary>
    public void SetNpc(string npcId, NpcStatus status) => Npcs[npcId] = status;

    /// <summary>How many of an item a vendor has sold since the last restock.</summary>
    public int SoldCount(string vendor, string item) =>
        Sold.TryGetValue(vendor, out var m) && m.TryGetValue(item, out var n) ? n : 0;

    /// <summary>Records a sale.</summary>
    public void RecordSale(string vendor, string item)
    {
        if (!Sold.TryGetValue(vendor, out var m))
        {
            m = new SortedDictionary<string, int>(StringComparer.Ordinal);
            Sold[vendor] = m;
        }
        m[item] = m.GetValueOrDefault(item) + 1;
    }

    /// <summary>Restocks every vendor (after a mission is completed).</summary>
    public void Restock() => Sold.Clear();
}
