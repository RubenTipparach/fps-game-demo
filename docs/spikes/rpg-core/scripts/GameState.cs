using System;
using System.Collections.Generic;
using Godot;

namespace Brushfire;

/// <summary>
/// Everything that survives a level change in the Undercity campaign: the character,
/// inventory, story flags, quests, which pickups were taken and which NPCs are down.
/// Owned by the Game autoload (Game.Instance.State).
/// </summary>
public class GameState
{
    public Character Character { get; } = new();
    public Inventory Inventory { get; } = new();
    public QuestLog Quests { get; } = new();
    public readonly HashSet<string> Flags = new();
    /// <summary>Pickups/containers already emptied, keyed "level/node".</summary>
    public readonly HashSet<string> Taken = new();
    /// <summary>NPC ids -> "dead", "ko", "hostile", "gone", "freed"...</summary>
    public readonly Dictionary<string, string> NpcStatus = new();

    /// <summary>Player health carried between levels (-1 = full).</summary>
    public float Health = -1f;
    public string CurrentLevel = "";
    /// <summary>Spawn marker id to use when the next level loads (set by LevelExit).</summary>
    public string PendingSpawn = "";

    /// <summary>Raised for anything the player should read in the feed ("+50 XP", "Picked up Medkit").</summary>
    public event Action<string> Notice;

    public GameState()
    {
        Character.XpGained += (xp, why) => Notice?.Invoke($"+{xp} XP  {why}");
        Character.LeveledUp += lvl => Notice?.Invoke($"LEVEL {lvl}!  +2 skill points (K)");
        Quests.Updated += (_, msg) => Notice?.Invoke(msg);
    }

    public void Say(string text) => Notice?.Invoke(text);

    public static GameState NewGame()
    {
        var s = new GameState();
        var inv = s.Inventory;
        // A runner's kit: non-lethal first, a quiet gun for emergencies.
        inv.Add("stun_baton");
        inv.Add("pistol");
        inv.Add("ammo_10mm", 24);
        inv.Add("lockpick", 2);
        inv.Add("multitool", 1);
        inv.Add("medkit", 1);
        inv.Wear(ItemDb.Get("street_jacket"));
        return s;
    }

    public bool Flag(string f) => Flags.Contains(f);
    public void SetFlag(string f) => Flags.Add(f);
    public void ClearFlag(string f) => Flags.Remove(f);

    public string Npc(string id) => id != null && NpcStatus.TryGetValue(id, out var s) ? s : "";

    /// <summary>Give an item with a feed message. Returns false when nothing fit.</summary>
    public bool Give(string id, int count = 1)
    {
        var def = ItemDb.Get(id);
        if (def == null)
            return false;
        int left = Inventory.Add(def, count);
        int got = count - left;
        if (got > 0)
            Say(got > 1 ? $"{def.Name} ×{got}" : def.Name);
        if (left > 0)
            Say("Inventory full");
        return got > 0;
    }

    public void CompleteObjective(string quest, string objective)
    {
        int xp = Quests.CompleteObjective(quest, objective);
        if (xp > 0)
            Character.AddXp(xp, "objective");
    }

    public void CompleteQuest(string quest)
    {
        var (xp, credits) = Quests.Complete(quest);
        if (credits > 0)
        {
            Character.Earn(credits);
            Say($"+{credits} credits");
        }
        if (xp > 0)
            Character.AddXp(xp, "contract");
    }
}
