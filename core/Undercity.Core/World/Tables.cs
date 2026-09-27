// NPC and level tables (data/npcs.json, data/levels/*.json): who stands where and says what, and
// every lock, container, terminal, trigger and exit a level places.
//
// It lives in the core because stable ids, contents and conditions must be readable in a test
// without loading a scene (CLAUDE.md 5.2, openspec/changes/undercity-architecture). The level
// files are generated from the layout (tools/levels/export_level_data.py).

using Undercity.Core.Data;
using Undercity.Core.Dialog;
using Undercity.Core.Locks;

namespace Undercity.Core.World;

/// <summary>One named NPC.</summary>
public sealed class NpcDef
{
    /// <summary>The id, such as <c>silk</c>.</summary>
    public required string Id { get; init; }

    /// <summary>The display name.</summary>
    public required string Name { get; init; }

    /// <summary>What they do, in a few words, for the journal and the map.</summary>
    public required string Role { get; init; }

    /// <summary>Their faction id.</summary>
    public required string Faction { get; init; }

    /// <summary>Intelligence, 1 to 5.</summary>
    public required int Intelligence { get; init; }

    /// <summary>Their dialog tree id.</summary>
    public required string Dialog { get; init; }

    /// <summary>Their character model id (game/models/characters/&lt;id&gt;.glb).</summary>
    public required string Model { get; init; }

    /// <summary>The animation they idle in: idle, guard, sit or talk.</summary>
    public string Idle { get; init; } = "idle";

    /// <summary>True for MerSec troopers who enforce the hub's law.</summary>
    public bool Law { get; init; }
}

/// <summary>The civilian pool: models, and lines chosen with a seeded stream per civilian.</summary>
public sealed class CivilianPool
{
    /// <summary>The dialog tree civilians use.</summary>
    public required string Dialog { get; init; }

    /// <summary>The model ids civilians are drawn from.</summary>
    public required IReadOnlyList<string> Models { get; init; }

    /// <summary>Small-talk lines.</summary>
    public required IReadOnlyList<string> SmallTalk { get; init; }

    /// <summary>Rumours: hints about routes.</summary>
    public required IReadOnlyList<string> Rumours { get; init; }
}

/// <summary>data/npcs.json.</summary>
public sealed class NpcTable : IValidated
{
    /// <summary>The named NPCs.</summary>
    public required IReadOnlyList<NpcDef> Npcs { get; init; }

    /// <summary>The civilian pool.</summary>
    public required CivilianPool Civilians { get; init; }

    /// <summary>The NPC with this id, or null.</summary>
    public NpcDef? Find(string id) => Npcs.FirstOrDefault(n => n.Id == id);

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        foreach (var dup in Npcs.GroupBy(n => n.Id).Where(g => g.Count() > 1))
        {
            errors.Add($"npcs: '{dup.Key}' appears twice");
        }
        foreach (var n in Npcs.Where(n => n.Intelligence is < 1 or > 5))
        {
            errors.Add($"npcs.{n.Id}: intelligence must be 1 to 5");
        }
        if (Civilians.SmallTalk.Count == 0 || Civilians.Rumours.Count == 0 || Civilians.Models.Count == 0)
        {
            errors.Add("civilians need models, small_talk and rumours");
        }
    }
}

/// <summary>A container placed in a level.</summary>
public sealed class ContainerDef
{
    /// <summary>What it is called in prompts: locker, safe, crate, box.</summary>
    public required string Noun { get; init; }

    /// <summary>Contents as "item" or "item:count".</summary>
    public IReadOnlyList<string> Items { get; init; } = Array.Empty<string>();

    /// <summary>The owning faction: what's taken is stolen from them.</summary>
    public string? Owner { get; init; }

    /// <summary>Its lock, or null.</summary>
    public LockDef? Lock { get; init; }
}

/// <summary>A page of a terminal.</summary>
public sealed class TerminalPage
{
    /// <summary>Who wrote it.</summary>
    public required string From { get; init; }

    /// <summary>The subject line.</summary>
    public required string Subject { get; init; }

    /// <summary>The text.</summary>
    public required string Body { get; init; }
}

/// <summary>An action a terminal offers once logged in.</summary>
public sealed class TerminalAction
{
    /// <summary>The button label.</summary>
    public required string Label { get; init; }

    /// <summary>What it does.</summary>
    public IReadOnlyList<DialogEffect> Do { get; init; } = Array.Empty<DialogEffect>();
}

/// <summary>A terminal placed in a level.</summary>
public sealed class TerminalDef
{
    /// <summary>The title bar.</summary>
    public required string Title { get; init; }

    /// <summary>Its login lock (a device lock), or null for an open terminal.</summary>
    public LockDef? Lock { get; init; }

    /// <summary>The owning faction: hacking it in view is a crime.</summary>
    public string? Owner { get; init; }

    /// <summary>Its pages.</summary>
    public IReadOnlyList<TerminalPage> Pages { get; init; } = Array.Empty<TerminalPage>();

    /// <summary>Its actions.</summary>
    public IReadOnlyList<TerminalAction> Actions { get; init; } = Array.Empty<TerminalAction>();

    /// <summary>Effects on first login (codes learned, objectives).</summary>
    public IReadOnlyList<DialogEffect> OnRead { get; init; } = Array.Empty<DialogEffect>();
}

/// <summary>A door with a lock, placed in a level.</summary>
public sealed class DoorDef
{
    /// <summary>The door's lock.</summary>
    public required LockDef Lock { get; init; }

    /// <summary>The owning faction: picking it in view is a crime.</summary>
    public string? Owner { get; init; }
}

/// <summary>A walk-in trigger: secrets, discoveries, objectives.</summary>
public sealed class TriggerDef
{
    /// <summary>Conditions that must hold for it to fire.</summary>
    public IReadOnlyList<DialogCond> If { get; init; } = Array.Empty<DialogCond>();

    /// <summary>What it does.</summary>
    public IReadOnlyList<DialogEffect> Do { get; init; } = Array.Empty<DialogEffect>();

    /// <summary>Fires once per save.</summary>
    public bool Once { get; init; } = true;
}

/// <summary>A level exit.</summary>
public sealed class ExitDef
{
    /// <summary>The prompt, such as "Go down the storm drain".</summary>
    public required string Label { get; init; }

    /// <summary>The level it leads to.</summary>
    public required string Target { get; init; }

    /// <summary>The spawn in the target level.</summary>
    public string Spawn { get; init; } = "";

    /// <summary>A gate on the way through (a grate, a keypad, a lift panel), or null. Opened once, it stays open.</summary>
    public LockDef? Lock { get; init; }

    /// <summary>Conditions for it to open.</summary>
    public IReadOnlyList<DialogCond> If { get; init; } = Array.Empty<DialogCond>();

    /// <summary>The prompt while it's closed.</summary>
    public string LockedText { get; init; } = "It won't open.";
}

/// <summary>A restricted zone: a faction keeps even its own out.</summary>
public sealed class ZoneDef
{
    /// <summary>The faction.</summary>
    public required string Faction { get; init; }

    /// <summary>Its name, for the warning bark.</summary>
    public required string Name { get; init; }

    /// <summary>Conditions under which the runner may be here (Dace waved them through). All must hold.</summary>
    public IReadOnlyList<DialogCond> Allow { get; init; } = Array.Empty<DialogCond>();
}

/// <summary>data/levels/&lt;id&gt;.json: everything a level places, by stable id.</summary>
public sealed class LevelDef : IValidated
{
    /// <summary>The level id.</summary>
    public required string Id { get; init; }

    /// <summary>The level's title.</summary>
    public required string Title { get; init; }

    /// <summary>Spawn point ids.</summary>
    public IReadOnlyList<string> Spawns { get; init; } = Array.Empty<string>();

    /// <summary>Containers by stable id.</summary>
    public IReadOnlyDictionary<string, ContainerDef> Containers { get; init; } = new Dictionary<string, ContainerDef>();

    /// <summary>Terminals by stable id.</summary>
    public IReadOnlyDictionary<string, TerminalDef> Terminals { get; init; } = new Dictionary<string, TerminalDef>();

    /// <summary>Locked doors by stable id.</summary>
    public IReadOnlyDictionary<string, DoorDef> Doors { get; init; } = new Dictionary<string, DoorDef>();

    /// <summary>Triggers by stable id.</summary>
    public IReadOnlyDictionary<string, TriggerDef> Triggers { get; init; } = new Dictionary<string, TriggerDef>();

    /// <summary>Exits by stable id.</summary>
    public IReadOnlyDictionary<string, ExitDef> Exits { get; init; } = new Dictionary<string, ExitDef>();

    /// <summary>Restricted zones by stable id.</summary>
    public IReadOnlyDictionary<string, ZoneDef> Zones { get; init; } = new Dictionary<string, ZoneDef>();

    /// <summary>World items by stable id: "item" or "item:count".</summary>
    public IReadOnlyDictionary<string, string> Items { get; init; } = new Dictionary<string, string>();

    /// <summary>NPC placements by stable id: the NPC id (named) or "civ" (a civilian).</summary>
    public IReadOnlyDictionary<string, string> Npcs { get; init; } = new Dictionary<string, string>();

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        var ids = Containers.Keys.Concat(Terminals.Keys).Concat(Doors.Keys).Concat(Triggers.Keys)
            .Concat(Exits.Keys).Concat(Zones.Keys).Concat(Items.Keys).Concat(Npcs.Keys);
        foreach (var dup in ids.GroupBy(i => i).Where(g => g.Count() > 1))
        {
            errors.Add($"levels.{Id}: stable id '{dup.Key}' is used twice");
        }
        foreach (var id in ids.Where(i => !i.StartsWith(Id + ":", StringComparison.Ordinal)))
        {
            errors.Add($"levels.{Id}: stable id '{id}' must start with '{Id}:'");
        }
        foreach (var (id, lk) in Containers.Where(c => c.Value.Lock is not null).Select(c => (c.Key, c.Value.Lock!))
            .Concat(Doors.Select(d => (d.Key, d.Value.Lock)))
            .Concat(Terminals.Where(t => t.Value.Lock is not null).Select(t => (t.Key, t.Value.Lock!)))
            .Concat(Exits.Where(e => e.Value.Lock is not null).Select(e => (e.Key, e.Value.Lock!))))
        {
            if (lk.Tier is < 1 or > 3)
            {
                errors.Add($"levels.{Id}.{id}: lock tier must be 1 to 3");
            }
        }
    }
}
