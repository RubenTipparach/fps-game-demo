// Every data table, loaded and cross-checked as one set (game/data/).
//
// It lives in the core because a dangling reference (an item id in a dialog tree, a vendor's
// stock, a level's container) must fail in `dotnet test`, not in play (CLAUDE.md 5.5, 5.6).
// Each file validates itself; this checks the references between files.

using Undercity.Core.Data;
using Undercity.Core.Dialog;
using Undercity.Core.Economy;
using Undercity.Core.Factions;
using Undercity.Core.Items;
using Undercity.Core.Locks;
using Undercity.Core.Perception;
using Undercity.Core.Progression;
using Undercity.Core.Quests;
using Undercity.Core.World;

namespace Undercity.Core;

/// <summary>One level in the campaign index (data/levels/index.json).</summary>
public sealed class LevelIndexEntry
{
    /// <summary>The level id.</summary>
    public required string Id { get; init; }

    /// <summary>The level's title.</summary>
    public required string Title { get; init; }

    /// <summary>True when the level is built and playable; false for a later slice.</summary>
    public required bool Built { get; init; }

    /// <summary>The level's scene path in the game, for built levels.</summary>
    public string Scene { get; init; } = "";
}

/// <summary>data/levels/index.json: every level of the campaign, built or planned.</summary>
public sealed class LevelIndex : IValidated
{
    /// <summary>The levels.</summary>
    public required IReadOnlyList<LevelIndexEntry> Levels { get; init; }

    /// <summary>The entry with this id, or null.</summary>
    public LevelIndexEntry? Find(string id) => Levels.FirstOrDefault(l => l.Id == id);

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        foreach (var l in Levels.Where(l => l.Built && string.IsNullOrEmpty(l.Scene)))
        {
            errors.Add($"levels.{l.Id}: a built level needs its scene");
        }
    }
}

/// <summary>Every data table.</summary>
public sealed class GameData
{
    /// <summary>data/skills.json.</summary>
    public required SkillTable Skills { get; init; }

    /// <summary>data/progression.json.</summary>
    public required ProgressionTable Progression { get; init; }

    /// <summary>data/items.json.</summary>
    public required ItemDb Items { get; init; }

    /// <summary>data/factions.json.</summary>
    public required FactionTable Factions { get; init; }

    /// <summary>data/vendors.json.</summary>
    public required VendorTable Vendors { get; init; }

    /// <summary>data/locks.json.</summary>
    public required LockTable Locks { get; init; }

    /// <summary>data/quests.json.</summary>
    public required QuestTable Quests { get; init; }

    /// <summary>data/perception.json.</summary>
    public required PerceptionTable Perception { get; init; }

    /// <summary>data/npcs.json.</summary>
    public required NpcTable Npcs { get; init; }

    /// <summary>data/saves.json.</summary>
    public required SavesTable Saves { get; init; }

    /// <summary>data/npc_bodies.json.</summary>
    public required NpcBodyTable NpcBodies { get; init; }

    /// <summary>data/water.json.</summary>
    public required Vitals.WaterTable Water { get; init; }

    /// <summary>data/weapons.json.</summary>
    public required Combat.WeaponTable Weapons { get; init; }

    /// <summary>data/combat.json.</summary>
    public required Combat.CombatTable Combat { get; init; }

    /// <summary>data/character_lighting.json.</summary>
    public required CharacterLightingTable CharacterLighting { get; init; }

    /// <summary>data/crowd.json.</summary>
    public required CrowdTable Crowd { get; init; }

    /// <summary>data/dialog/*.json by tree id.</summary>
    public required IReadOnlyDictionary<string, DialogTree> Dialogs { get; init; }

    /// <summary>data/levels/index.json.</summary>
    public required LevelIndex LevelIndex { get; init; }

    /// <summary>data/levels/&lt;id&gt;.json by level id, for built levels.</summary>
    public required IReadOnlyDictionary<string, LevelDef> Levels { get; init; }

    /// <summary>Loads every table from <paramref name="source"/> and cross-checks references. Throws <see cref="DataException"/>.</summary>
    public static GameData Load(IDataSource source)
    {
        var dialogs = new SortedDictionary<string, DialogTree>(StringComparer.Ordinal);
        foreach (var file in source.List("dialog").Where(f => f.EndsWith(".json", StringComparison.Ordinal)))
        {
            var tree = JsonData.Load<DialogTree>(source, file);
            var expected = Path.GetFileNameWithoutExtension(file);
            if (tree.Id != expected)
            {
                throw new DataException(file, $"id '{tree.Id}' must match the file name '{expected}'");
            }
            dialogs[tree.Id] = tree;
        }
        var index = JsonData.Load<LevelIndex>(source, "levels/index.json");
        var levels = new SortedDictionary<string, LevelDef>(StringComparer.Ordinal);
        foreach (var entry in index.Levels.Where(l => l.Built))
        {
            levels[entry.Id] = JsonData.Load<LevelDef>(source, $"levels/{entry.Id}.json");
        }
        var data = new GameData
        {
            Skills = JsonData.Load<SkillTable>(source, "skills.json"),
            Progression = JsonData.Load<ProgressionTable>(source, "progression.json"),
            Items = JsonData.Load<ItemDb>(source, "items.json"),
            Factions = JsonData.Load<FactionTable>(source, "factions.json"),
            Vendors = JsonData.Load<VendorTable>(source, "vendors.json"),
            Locks = JsonData.Load<LockTable>(source, "locks.json"),
            Quests = JsonData.Load<QuestTable>(source, "quests.json"),
            Perception = JsonData.Load<PerceptionTable>(source, "perception.json"),
            Npcs = JsonData.Load<NpcTable>(source, "npcs.json"),
            Saves = JsonData.Load<SavesTable>(source, "saves.json"),
            NpcBodies = JsonData.Load<NpcBodyTable>(source, "npc_bodies.json"),
            Water = JsonData.Load<Vitals.WaterTable>(source, "water.json"),
            Weapons = JsonData.Load<Combat.WeaponTable>(source, "weapons.json"),
            Combat = JsonData.Load<Combat.CombatTable>(source, "combat.json"),
            CharacterLighting = JsonData.Load<CharacterLightingTable>(source, "character_lighting.json"),
            Crowd = JsonData.Load<CrowdTable>(source, "crowd.json"),
            Dialogs = dialogs,
            LevelIndex = index,
            Levels = levels,
        };
        var errors = new List<string>();
        data.CrossCheck(errors);
        if (errors.Count > 0)
        {
            throw new DataException("game/data", string.Join("\n  ", errors.Prepend("cross-references:")));
        }
        return data;
    }

    /// <summary>Checks the references between files, adding a message per dangling id.</summary>
    public void CrossCheck(ICollection<string> errors)
    {
        // Every district the gels name is one a level has (openspec/changes/character-lighting).
        var districts = Levels.Values.SelectMany(l => l.Districts).Select(d => d.Id).ToHashSet(StringComparer.Ordinal);
        foreach (var d in CharacterLighting.Gels.Keys.Where(d => !districts.Contains(d)))
        {
            errors.Add($"character_lighting.json gels: no level has a district '{d}'");
        }
        foreach (var d in Crowd.DistrictRoles.Keys.Where(d => !districts.Contains(d)))
        {
            errors.Add($"crowd.json district_roles: no level has a district '{d}'");
        }
        foreach (var (name, role) in Crowd.Roles)
        {
            foreach (var idle in role.Idles.Where(i => NpcBodies.Clip(i) is null))
            {
                errors.Add($"crowd.json roles.{name}.idles: '{idle}' is no state of npc_bodies.json");
            }
        }
        foreach (var (id, a) in Crowd.Accessories.Where(a => a.Value.Idle is { } i && NpcBodies.Clip(i) is null))
        {
            errors.Add($"crowd.json accessories.{id}.idle: '{a.Idle}' is no state of npc_bodies.json");
        }
        foreach (var (id, a) in Crowd.Accessories.Where(a => !NpcBodies.Mounts.ContainsKey(a.Value.Mount)))
        {
            errors.Add($"crowd.json accessories.{id}.mount: '{a.Mount}' is no mount of npc_bodies.json");
        }
        void Item(string? id, string where)
        {
            if (id is not null && !Items.Exists(id))
            {
                errors.Add($"{where}: unknown item '{id}'");
            }
        }
        void Faction(string? id, string where)
        {
            if (id is not null && !Factions.Exists(id))
            {
                errors.Add($"{where}: unknown faction '{id}'");
            }
        }
        Faction(Perception.Law.CrimeRepFaction, "perception.law.crime_rep_faction");
        foreach (var s in Progression.StartKit)
        {
            Item(s.Item, "progression.start_kit");
        }
        foreach (var (slot, id) in Progression.StartWorn)
        {
            Item(id, $"progression.start_worn.{slot}");
            if (Items.Exists(id) && !string.Equals(Items.Get(id).Slot?.ToString(), slot, StringComparison.OrdinalIgnoreCase))
            {
                errors.Add($"progression.start_worn.{slot}: '{id}' isn't worn in {slot}");
            }
        }
        foreach (var v in Vendors.Vendors)
        {
            Faction(v.Faction, $"vendors.{v.Id}");
            foreach (var s in v.Stock)
            {
                Item(s.Item, $"vendors.{v.Id}.stock");
            }
        }
        foreach (var n in Npcs.Npcs)
        {
            Faction(n.Faction, $"npcs.{n.Id}");
            if (!Dialogs.ContainsKey(n.Dialog))
            {
                errors.Add($"npcs.{n.Id}: unknown dialog '{n.Dialog}'");
            }
        }
        foreach (var n in Npcs.Npcs.Where(n => n.Weapon is not null && Weapons.Find(n.Weapon) is null))
        {
            errors.Add($"npcs.{n.Id}: unknown weapon '{n.Weapon}'");
        }
        foreach (var i in Items.Items.Where(i => i.Weapon is not null))
        {
            if (Weapons.Find(i.Weapon!) is not { } w)
            {
                errors.Add($"items.{i.Id}: unknown weapon '{i.Weapon}'");
            }
            else if (w.NpcOnly)
            {
                errors.Add($"items.{i.Id}: '{i.Weapon}' is a weapon only NPCs carry");
            }
        }
        foreach (var (id, w) in Weapons.Weapons)
        {
            Item(w.Ammo, $"weapons.{id}.ammo");
        }
        foreach (var n in Npcs.Npcs.Where(n => NpcBodies.Clip(n.Idle) is null))
        {
            errors.Add($"npcs.{n.Id}.idle: '{n.Idle}' isn't a state in npc_bodies.clips");
        }
        if (!Dialogs.ContainsKey(Npcs.Civilians.Dialog))
        {
            errors.Add($"npcs.civilians: unknown dialog '{Npcs.Civilians.Dialog}'");
        }
        foreach (var t in Dialogs.Values)
        {
            if (t.Vendor is not null && !Vendors.Exists(t.Vendor))
            {
                errors.Add($"dialog.{t.Id}: unknown vendor '{t.Vendor}'");
            }
            var conds = t.Starts.SelectMany(s => s.If)
                .Concat(t.Nodes.Values.SelectMany(n => n.Choices).SelectMany(c => c.If));
            var effects = t.Nodes.Values.SelectMany(n => n.Do)
                .Concat(t.Nodes.Values.SelectMany(n => n.Choices).SelectMany(c => c.Do));
            CheckConds(conds, $"dialog.{t.Id}", errors, Item, Faction);
            CheckEffects(effects, $"dialog.{t.Id}", errors, Item, Faction);
            foreach (var e in effects.Where(e => e.Buy is not null || e.Sell is not null))
            {
                if (t.Vendor is null)
                {
                    errors.Add($"dialog.{t.Id}: buy or sell needs the tree's vendor");
                }
                else if (e.Buy is not null && Vendors.Get(t.Vendor).Stock.All(s => s.Item != e.Buy))
                {
                    errors.Add($"dialog.{t.Id}: '{e.Buy}' isn't in {t.Vendor}'s stock");
                }
            }
        }
        foreach (var (id, level) in Levels)
        {
            var where = $"levels.{id}";
            foreach (var (cid, c) in level.Containers)
            {
                Faction(c.Owner, $"{where}.{cid}");
                foreach (var spec in c.Items)
                {
                    Item(spec.Split(':')[0], $"{where}.{cid}");
                }
                Item(c.Lock?.Key, $"{where}.{cid}.lock");
            }
            foreach (var (did, d) in level.Doors)
            {
                Item(d.Lock.Key, $"{where}.{did}.lock");
                Faction(d.Owner, $"{where}.{did}");
            }
            foreach (var (tid, term) in level.Terminals)
            {
                CheckEffects(term.OnRead.Concat(term.Actions.SelectMany(a => a.Do)), $"{where}.{tid}", errors, Item, Faction);
            }
            foreach (var (tid, trig) in level.Triggers)
            {
                CheckConds(trig.If, $"{where}.{tid}", errors, Item, Faction);
                CheckEffects(trig.Do, $"{where}.{tid}", errors, Item, Faction);
            }
            foreach (var (eid, exit) in level.Exits)
            {
                if (LevelIndex.Find(exit.Target) is null)
                {
                    errors.Add($"{where}.{eid}: unknown target level '{exit.Target}'");
                }
                Item(exit.Lock?.Key, $"{where}.{eid}.lock");
                CheckConds(exit.If, $"{where}.{eid}", errors, Item, Faction);
            }
            foreach (var (zid, z) in level.Zones)
            {
                Faction(z.Faction, $"{where}.{zid}");
                CheckConds(z.Allow, $"{where}.{zid}", errors, Item, Faction);
            }
            foreach (var (iid, spec) in level.Items)
            {
                Item(spec.Split(':')[0], $"{where}.{iid}");
            }
            foreach (var (nid, npc) in level.Npcs.Where(n => n.Value != "civ" && Npcs.Find(n.Value) is null))
            {
                errors.Add($"{where}.{nid}: unknown npc '{npc}'");
            }
        }
    }

    private void CheckConds(IEnumerable<DialogCond> conds, string where, ICollection<string> errors,
        Action<string?, string> item, Action<string?, string> faction)
    {
        foreach (var c in conds)
        {
            item(c.Item, where);
            item(c.NoItem, where);
            item(c.CanAfford, where);
            faction(c.Rep, where);
            faction(c.Parley, where);
            faction(c.Outfit, where);
            if (c.Quest is not null && !Quests.Exists(c.Quest))
            {
                errors.Add($"{where}: unknown quest '{c.Quest}'");
            }
            foreach (var o in new[] { c.Objective, c.NotObjective }.Where(o => o is not null && !Quests.ObjectiveExists(o)))
            {
                errors.Add($"{where}: unknown objective '{o}'");
            }
            if (c.Npc is not null && Npcs.Find(c.Npc) is null)
            {
                errors.Add($"{where}: unknown npc '{c.Npc}'");
            }
        }
    }

    private void CheckEffects(IEnumerable<DialogEffect> effects, string where, ICollection<string> errors,
        Action<string?, string> item, Action<string?, string> faction)
    {
        foreach (var e in effects)
        {
            item(e.Give, where);
            item(e.Take, where);
            item(e.Buy, where);
            item(e.Sell, where);
            faction(e.Rep, where);
            faction(e.Parley, where);
            foreach (var q in new[] { e.StartQuest, e.CompleteQuest, e.FailQuest }.Where(q => q is not null && !Quests.Exists(q)))
            {
                errors.Add($"{where}: unknown quest '{q}'");
            }
            foreach (var o in new[] { e.Objective, e.Reveal }.Where(o => o is not null && !Quests.ObjectiveExists(o)))
            {
                errors.Add($"{where}: unknown objective '{o}'");
            }
            if (e.Npc is not null && Npcs.Find(e.Npc) is null)
            {
                errors.Add($"{where}: unknown npc '{e.Npc}'");
            }
        }
    }
}
