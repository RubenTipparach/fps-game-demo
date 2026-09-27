// The run: the runner, what they carry, their health, the journal, reputation and the world's
// memory, plus the actions that touch more than one of them (using an item, buying, opening a
// lock, searching a container, completing objectives).
//
// It lives in the core because these actions cross systems, and each cross-system rule must
// exist once (CLAUDE.md 5.1). The Godot layer calls these methods; it never reimplements them.

using Undercity.Core.Data;
using Undercity.Core.Dialog;
using Undercity.Core.Economy;
using Undercity.Core.Factions;
using Undercity.Core.Items;
using Undercity.Core.Kit;
using Undercity.Core.Locks;
using Undercity.Core.Perception;
using Undercity.Core.Progression;
using Undercity.Core.Quests;
using Undercity.Core.Vitals;
using Undercity.Core.World;

namespace Undercity.Core;

/// <summary>The whole state of a run.</summary>
public sealed class GameState
{
    private readonly List<(double PerS, double LeftS)> _heals = new();

    private GameState(GameData data, ulong seed)
    {
        Data = data;
        Character = new Character(data.Skills, data.Progression);
        Inventory = new Kit.Inventory(data.Items);
        Health = new FloorPool(Character.MaxHealth, data.Progression.HealthRegen);
        Quests = new QuestLog(data.Quests);
        Reputation = new Reputation(data.Factions);
        World = new WorldState { Seed = seed };
        Law = new LawWatch(data.Perception.Law);
        Character.LeveledUp += level =>
        {
            Health.SetMax(Character.MaxHealth);
            Say($"Level {level}: +{data.Progression.PointsPerLevel} skill points");
        };
        Character.XpGained += (xp, why) => Say($"+{xp} XP  {why}");
        Quests.Updated += (q, line) => Say($"{q.Title}: {line}");
        Inventory.Changed += () =>
        {
            if (Drawn is { } id && !Inventory.Pack.Has(id))
            {
                Holster();
            }
        };
    }

    /// <summary>The data tables.</summary>
    public GameData Data { get; }

    /// <summary>Skills, XP and level.</summary>
    public Character Character { get; }

    /// <summary>The pack, equipment, belt and credits.</summary>
    public Kit.Inventory Inventory { get; }

    /// <summary>Health, regenerating only to its floor.</summary>
    public FloorPool Health { get; }

    /// <summary>The journal.</summary>
    public QuestLog Quests { get; }

    /// <summary>Reputation with every faction.</summary>
    public Reputation Reputation { get; }

    /// <summary>Flags, per-level memory, NPC status.</summary>
    public WorldState World { get; private set; }

    /// <summary>MerSec's patience in the hub.</summary>
    public LawWatch Law { get; }

    /// <summary>Raises with a line for the message feed.</summary>
    public event Action<string>? Feed;

    /// <summary>Raises when the runner asks the engine to do something (sleep, open, an NPC action).</summary>
    public event Action<string, string>? HostAction;

    /// <summary>Starts a new run: the start kit, worn clothes, credits and flags.</summary>
    public static GameState NewGame(GameData data, ulong seed)
    {
        var s = new GameState(data, seed);
        foreach (var item in data.Progression.StartKit)
        {
            s.Inventory.PickUp(data.Items.Get(item.Item), item.Count);
        }
        foreach (var id in data.Progression.StartWorn.Values)
        {
            s.Inventory.Wear(data.Items.Get(id));
        }
        s.Inventory.Earn(data.Progression.StartCredits);
        return s;
    }

    /// <summary>Adds a line to the message feed.</summary>
    public void Say(string line) => Feed?.Invoke(line);

    /// <summary>Asks the engine to do something by name, with an argument.</summary>
    public void Host(string action, string arg = "") => HostAction?.Invoke(action, arg);

    /// <summary>The weapon in the runner's hands (an item id), or null when holstered.</summary>
    public string? Drawn { get; private set; }

    /// <summary>Seconds the current weapon has been out; the disguise rule's grace period reads it.</summary>
    public double DrawnS { get; private set; }

    /// <summary>Raised when a weapon is drawn or holstered.</summary>
    public event Action? LoadoutChanged;

    /// <summary>
    /// Uses belt slot <paramref name="slot"/> (0-9, keys 1 to 0): a weapon is drawn, or holstered
    /// if it's already out; a consumable is used. The one belt rule, for the keys and the HUD alike.
    /// </summary>
    public BeltResult UseBelt(int slot)
    {
        if (slot < 0 || slot >= Inventory.Belt.Count || Inventory.Belt[slot] is not { } id)
        {
            return BeltResult.Empty;
        }
        var def = Data.Items.Get(id);
        if (def.Category == Items.ItemCategory.Weapon)
        {
            if (Drawn == id)
            {
                Holster();
                return BeltResult.Holstered;
            }
            Drawn = id;
            DrawnS = 0;
            LoadoutChanged?.Invoke();
            return BeltResult.Drawn;
        }
        var stack = Inventory.Pack.Stacks.FirstOrDefault(x => x.Def.Id == id);
        return stack is not null && Use(stack) ? BeltResult.Used : BeltResult.Refused;
    }

    /// <summary>Puts the weapon away.</summary>
    public void Holster()
    {
        if (Drawn is null)
        {
            return;
        }
        Drawn = null;
        DrawnS = 0;
        LoadoutChanged?.Invoke();
    }

    /// <summary>
    /// A crime (theft, a picked lock) seen by <paramref name="witness"/>: it costs reputation with
    /// the Sump's residents and is reported to the law. The one crime rule.
    /// </summary>
    public LawResponse ReportCrime(string witness)
    {
        var law = Data.Perception.Law;
        Reputation.Change(law.CrimeRepFaction, -law.CrimeRepPenalty, 1.0);
        Say($"{witness} saw that.");
        return Law.CrimeSeen();
    }

    /// <summary>Sleeps: health back to full.</summary>
    public void Rest()
    {
        Health.Set(Health.Max);
        Say("Rested.");
    }

    /// <summary>Advances time: health regeneration, heals over time, the law's clock, play time.</summary>
    public void Tick(double dt)
    {
        if (!double.IsFinite(dt) || dt <= 0)
        {
            return;
        }
        Health.Tick(dt);
        for (var i = _heals.Count - 1; i >= 0; i--)
        {
            var (perS, left) = _heals[i];
            var step = Math.Min(dt, left);
            Health.Restore(perS * step);
            left -= step;
            if (left <= 0)
            {
                _heals.RemoveAt(i);
            }
            else
            {
                _heals[i] = (perS, left);
            }
        }
        Law.Tick(dt);
        if (Drawn is not null)
        {
            DrawnS += dt;
        }
        World.PlayTimeS += dt;
    }

    // ------------------------------------------------------------------ checks

    /// <summary>A skill's check value: rank plus carried gear, capped. The one check rule.</summary>
    public int CheckValue(Skill skill) => Character.CheckValue(skill, Inventory.SkillBonus(skill));

    /// <summary>Judges the disguise for an observer.</summary>
    public Judgement Judge(Observer observer, Situation situation) =>
        DisguiseRules.Judge(Data.Perception.Disguise, Character, Inventory, observer, situation);

    // ------------------------------------------------------------------ items

    /// <summary>Picks up an item. Returns how many were left behind for lack of room.</summary>
    public int PickUp(string itemId, int count, string? stolenFrom = null)
    {
        var def = Data.Items.Get(itemId);
        var left = Inventory.PickUp(def, count, stolenFrom);
        var got = count - left;
        if (got > 0)
        {
            Say(def.CreditsOnPickup ? $"+{def.Value * got} credits" : got > 1 ? $"{def.Name} x{got}" : def.Name);
        }
        return left;
    }

    /// <summary>
    /// Uses a consumable from the pack: heals (over its heal time), restores energy, or grants
    /// skill points. Returns false, using nothing, when it would do nothing (full health).
    /// </summary>
    public bool Use(PackItem stack)
    {
        var use = stack.Def.Use;
        if (use is null)
        {
            return false;
        }
        if (use.Heal > 0 && use.SkillPoints == 0 && Health.Value >= Health.Max)
        {
            Say("Already at full health");
            return false;
        }
        if (!Inventory.Pack.TakeOne(stack))
        {
            return false;
        }
        if (use.Heal > 0)
        {
            if (use.HealTimeS > 0)
            {
                _heals.Add((use.Heal / use.HealTimeS, use.HealTimeS));
            }
            else
            {
                Health.Restore(use.Heal);
            }
        }
        if (use.SkillPoints > 0)
        {
            Character.AddSkillPoints(use.SkillPoints);
            Say($"+{use.SkillPoints} skill point");
        }
        return true;
    }

    // ------------------------------------------------------------------ vendors

    /// <summary>The price the runner pays for an item at a vendor. The one price rule.</summary>
    public int BuyPrice(string vendorId, string itemId) =>
        Pricing.Buy(Data.Items.Get(itemId), Data.Vendors.Get(vendorId), Character.Mult("buy_price_mult"), Reputation);

    /// <summary>What a vendor pays for one clean item, or null when they won't buy it.</summary>
    public int? SellPrice(string vendorId, string itemId, bool stolen = false) =>
        Pricing.Sell(Data.Items.Get(itemId), stolen, Data.Vendors.Get(vendorId), Data.Vendors, Character.Mult("sell_price_mult"));

    /// <summary>How many of an item a vendor has left until the next restock (0 when it needs a flag not set).</summary>
    public int InStock(string vendorId, string itemId)
    {
        var line = Data.Vendors.Get(vendorId).Stock.FirstOrDefault(s => s.Item == itemId);
        if (line is null || line.RequiresFlag is not null && !World.Flag(line.RequiresFlag))
        {
            return 0;
        }
        return Math.Max(0, line.Count - World.SoldCount(vendorId, itemId));
    }

    /// <summary>Buys one item. Returns false, changing nothing, when it's out of stock, too dear, or won't fit.</summary>
    public bool Buy(string vendorId, string itemId)
    {
        var price = BuyPrice(vendorId, itemId);
        var def = Data.Items.Get(itemId);
        if (InStock(vendorId, itemId) < 1 || Inventory.Credits < price)
        {
            return false;
        }
        if (!def.CreditsOnPickup && Inventory.Pack.RoomFor(def, 1) < 1)
        {
            Say($"{def.Name}: no room");
            return false;
        }
        Inventory.Spend(price);
        PickUp(itemId, 1);
        World.RecordSale(vendorId, itemId);
        return true;
    }

    /// <summary>
    /// Sells every one of an item the vendor will take: clean ones at the clean price, stolen ones
    /// at the stolen price where the vendor buys stolen goods. Returns the credits earned.
    /// </summary>
    public int SellAll(string vendorId, string itemId)
    {
        var total = 0;
        var sold = 0;
        foreach (var s in Inventory.Pack.Stacks.Where(s => s.Def.Id == itemId).ToList())
        {
            if (SellPrice(vendorId, itemId, s.StolenFrom is not null) is not { } each)
            {
                continue;
            }
            total += each * s.Count;
            sold += s.Count;
            Inventory.Pack.RemoveStack(s);
        }
        if (sold == 0)
        {
            Say($"{Data.Vendors.Get(vendorId).Name} won't take it.");
            return 0;
        }
        Inventory.Earn(total);
        Say($"Sold {Data.Items.Get(itemId).Name} x{sold}: +{total} cr");
        return total;
    }

    /// <summary>Heals to full at <paramref name="perPointCr"/> credits a point, as far as the runner can pay. Returns points healed.</summary>
    public int PaidHeal(int perPointCr)
    {
        var missing = (int)Math.Ceiling(Health.Max - Health.Value);
        var affordable = perPointCr <= 0 ? missing : Math.Min(missing, Inventory.Credits / perPointCr);
        if (affordable <= 0)
        {
            return 0;
        }
        Inventory.Spend(affordable * perPointCr);
        Health.Restore(affordable);
        Say($"Healed {affordable} for {affordable * perPointCr} cr");
        return affordable;
    }

    // ------------------------------------------------------------------ quests

    /// <summary>Completes an objective and pays its XP.</summary>
    public void CompleteObjective(string path)
    {
        var xp = Quests.CompleteObjective(path);
        Character.AddXp(xp, $"obj:{path}", "objective");
    }

    /// <summary>Completes a quest and pays its XP and credits.</summary>
    public void CompleteQuest(string quest)
    {
        var (xp, credits) = Quests.Complete(quest);
        Character.AddXp(xp, $"quest:{quest}", "quest complete");
        if (credits > 0)
        {
            Inventory.Earn(credits);
            Say($"+{credits} credits");
        }
    }

    // ------------------------------------------------------------------ locks and containers

    /// <summary>The plan for opening a lock now. The one lock rule, for the prompt and the outcome alike.</summary>
    public LockPlan PlanLock(LockDef lk) =>
        LockRules.Best(lk, Data.Locks, Character, Inventory, World.Flag,
            id => Data.Items.Exists(id) ? Data.Items.Get(id).Name : id, Data.Progression.Xp.LockPerTier);

    /// <summary>True when the lock with this stable id was opened before.</summary>
    public bool IsOpened(string levelId, string stableId) => World.Level(levelId).Opened.Contains(stableId);

    /// <summary>Opens a lock by its plan: uses up the tool, pays XP once, remembers it. Returns false when it can't open now.</summary>
    public bool OpenLock(LockDef lk, string levelId, string stableId)
    {
        var plan = PlanLock(lk);
        if (!plan.CanOpen)
        {
            return false;
        }
        if (plan.Consumes is not null)
        {
            Inventory.Pack.Remove(plan.Consumes);
        }
        Character.AddXp(plan.Xp, $"lock:{stableId}", plan.Way == LockWay.Hack ? "system hacked" : "lock picked");
        World.Level(levelId).Opened.Add(stableId);
        return true;
    }

    /// <summary>
    /// Searches a container: takes everything that fits, remembers what's left, marks what's taken
    /// as stolen when it has an owner. Returns true when anything was taken.
    /// </summary>
    public bool Search(string levelId, string stableId, ContainerDef container)
    {
        var level = World.Level(levelId);
        if (level.Taken.Contains(stableId))
        {
            return false;
        }
        var contents = ContentsOf(levelId, stableId, container);
        var left = new SortedDictionary<string, int>(StringComparer.Ordinal);
        var took = false;
        foreach (var (id, n) in contents)
        {
            var remaining = PickUp(id, n, container.Owner);
            took |= remaining < n;
            if (remaining > 0)
            {
                left[id] = remaining;
            }
        }
        if (left.Count == 0)
        {
            level.Taken.Add(stableId);
            level.Leftovers.Remove(stableId);
        }
        else
        {
            level.Leftovers[stableId] = left;
            Say("No room for everything");
        }
        return took;
    }

    /// <summary>What a container holds now: its data contents, or what's left after a partial search.</summary>
    public IReadOnlyList<(string Item, int Count)> ContentsOf(string levelId, string stableId, ContainerDef container)
    {
        var level = World.Level(levelId);
        if (level.Taken.Contains(stableId))
        {
            return Array.Empty<(string, int)>();
        }
        if (level.Leftovers.TryGetValue(stableId, out var left))
        {
            return left.Select(kv => (kv.Key, kv.Value)).ToList();
        }
        return container.Items.Select(ParseSpec).ToList();
    }

    /// <summary>Parses "item" or "item:count".</summary>
    public static (string Item, int Count) ParseSpec(string spec)
    {
        var parts = spec.Split(':');
        return (parts[0], parts.Length > 1 && int.TryParse(parts[1], out var n) ? n : 1);
    }

    // ------------------------------------------------------------------ dialog

    /// <summary>Starts a conversation.</summary>
    public DialogSession Talk(DialogTree tree, Speaker speaker) => new(tree, new DialogWorld(this, speaker));

    /// <summary>Runs effects outside a conversation (a terminal action, a trigger).</summary>
    public void Apply(IEnumerable<DialogEffect> effects, string sourceId)
    {
        var world = new DialogWorld(this, Speaker.Nobody);
        foreach (var e in effects)
        {
            world.Apply(e, DialogWorld.NoTree, sourceId);
        }
    }

    /// <summary>Tests conditions outside a conversation (a trigger, an exit).</summary>
    public bool Holds(IEnumerable<DialogCond> conds)
    {
        var world = new DialogWorld(this, Speaker.Nobody);
        return conds.All(c => world.Holds(c, DialogWorld.NoTree));
    }

    // ------------------------------------------------------------------ saves

    /// <summary>The saved form of this run.</summary>
    public SaveGame Save() => new()
    {
        Version = SaveGame.CurrentVersion,
        Character = Character.Save(),
        Inventory = Inventory.Save(),
        Health = Health.Value,
        Quests = Quests.Save(),
        Reputation = Reputation.Save(),
        World = World,
    };

    /// <summary>
    /// Restores a run from a save, repairing damage (CLAUDE.md 5.6). Refuses a save from a newer
    /// version. Returns the state and a message per repair.
    /// </summary>
    public static (GameState State, IReadOnlyList<string> Repairs) Load(GameData data, SaveGame save)
    {
        if (save.Version > SaveGame.CurrentVersion || save.Version < 1)
        {
            throw new DataException("save", $"version {save.Version} isn't supported (this build reads 1 to {SaveGame.CurrentVersion})");
        }
        var s = new GameState(data, save.World.Seed);
        var repairs = new List<string>();
        repairs.AddRange(s.Character.Load(save.Character));
        s.Health.SetMax(s.Character.MaxHealth);
        repairs.AddRange(s.Inventory.Load(save.Inventory));
        s.Health.Set(save.Health);
        repairs.AddRange(s.Quests.Load(save.Quests));
        s.Reputation.Load(save.Reputation);
        s.World = save.World;
        return (s, repairs);
    }
}

/// <summary>What a belt key did.</summary>
public enum BeltResult
{
    /// <summary>Nothing on that slot.</summary>
    Empty,

    /// <summary>A weapon came out.</summary>
    Drawn,

    /// <summary>The weapon went away.</summary>
    Holstered,

    /// <summary>A consumable was used.</summary>
    Used,

    /// <summary>It would do nothing (a medkit at full health, a lockpick).</summary>
    Refused,
}

/// <summary>A saved run (user://saves/&lt;slot&gt;.json).</summary>
public sealed class SaveGame
{
    /// <summary>The version this build writes.</summary>
    public const int CurrentVersion = 1;

    /// <summary>The save's version.</summary>
    public int Version { get; set; } = CurrentVersion;

    /// <summary>The runner.</summary>
    public CharacterSave Character { get; set; } = new();

    /// <summary>What they carry.</summary>
    public InventorySave Inventory { get; set; } = new();

    /// <summary>Health.</summary>
    public double Health { get; set; }

    /// <summary>The journal.</summary>
    public QuestSave Quests { get; set; } = new();

    /// <summary>Reputation by faction.</summary>
    public SortedDictionary<string, int> Reputation { get; set; } = new(StringComparer.Ordinal);

    /// <summary>The world's memory.</summary>
    public WorldState World { get; set; } = new();

    /// <summary>Serializes a save.</summary>
    public string ToJson() => JsonData.Write(this);

    /// <summary>Parses a save. Unknown keys are refused, as in every data file.</summary>
    public static SaveGame FromJson(string json) => JsonData.Parse<SaveGame>(json, "save");
}
