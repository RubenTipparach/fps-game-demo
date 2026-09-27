// Dialog tree data (data/dialog/*.json): nodes, lines, choices, conditions, checks and effects.
//
// It lives in the core because what a choice needs, whether it shows, and what it does are rules
// the dialog screen and the tests must read the same way (openspec/changes/dialog-and-social).
// Writers work in data; nothing in a tree needs code.

using Undercity.Core.Data;
using Undercity.Core.Progression;
using Undercity.Core.Quests;
using Undercity.Core.World;

namespace Undercity.Core.Dialog;

/// <summary>A condition. Exactly one kind of test is set per object; all conditions in a list must hold.</summary>
public sealed class DialogCond
{
    /// <summary>A story flag that must be set.</summary>
    public string? Flag { get; init; }

    /// <summary>A story flag that must not be set.</summary>
    public string? NotFlag { get; init; }

    /// <summary>An item that must be carried (<see cref="Count"/> of it).</summary>
    public string? Item { get; init; }

    /// <summary>An item that must not be carried.</summary>
    public string? NoItem { get; init; }

    /// <summary>How many of <see cref="Item"/>.</summary>
    public int Count { get; init; } = 1;

    /// <summary>At least this many credits (a build condition).</summary>
    public int? Credits { get; init; }

    /// <summary>A skill whose check value must be at least <see cref="Min"/> (a build condition).</summary>
    public Skill? Skill { get; init; }

    /// <summary>The minimum for <see cref="Skill"/> or <see cref="Rep"/>.</summary>
    public int? Min { get; init; }

    /// <summary>The maximum for <see cref="Rep"/>.</summary>
    public int? Max { get; init; }

    /// <summary>True: must be talking in an accepted disguise; false: must not be.</summary>
    public bool? Disguise { get; init; }

    /// <summary>A quest whose state must be <see cref="State"/>.</summary>
    public string? Quest { get; init; }

    /// <summary>The state <see cref="Quest"/> must be in.</summary>
    public QuestState? State { get; init; }

    /// <summary>An objective, "quest/objective", that must be done.</summary>
    public string? Objective { get; init; }

    /// <summary>An objective that must not be done.</summary>
    public string? NotObjective { get; init; }

    /// <summary>An NPC whose status must be <see cref="Status"/>.</summary>
    public string? Npc { get; init; }

    /// <summary>The status <see cref="Npc"/> must have.</summary>
    public NpcStatus? Status { get; init; }

    /// <summary>A faction whose reputation must be within <see cref="Min"/> and <see cref="Max"/> (a build condition).</summary>
    public string? Rep { get; init; }

    /// <summary>A faction whose truce must be in force.</summary>
    public string? Parley { get; init; }

    /// <summary>An item the tree's vendor has in stock and the runner can afford (a build condition).</summary>
    public string? CanAfford { get; init; }
}

/// <summary>A deterministic check on a choice.</summary>
public sealed class DialogCheck
{
    /// <summary>The skill checked, or null for a cover check.</summary>
    public Skill? Skill { get; init; }

    /// <summary>The DC for a skill check.</summary>
    public int Dc { get; init; }

    /// <summary>The Cover needed, for a cover check (bosses): Deception + disguise quality.</summary>
    public int? Cover { get; init; }
}

/// <summary>An effect. Exactly one kind of action is set per object; a list runs in order.</summary>
public sealed class DialogEffect
{
    /// <summary>Sets a flag.</summary>
    public string? Flag { get; init; }

    /// <summary>Clears a flag.</summary>
    public string? Unflag { get; init; }

    /// <summary>Gives <see cref="Count"/> of an item; what doesn't fit drops at the runner's feet.</summary>
    public string? Give { get; init; }

    /// <summary>Takes <see cref="Count"/> of an item.</summary>
    public string? Take { get; init; }

    /// <summary>How many for give and take.</summary>
    public int Count { get; init; } = 1;

    /// <summary>Credits paid (positive) or charged (negative).</summary>
    public int? Credits { get; init; }

    /// <summary>XP awarded, once per <see cref="Source"/>.</summary>
    public int? Xp { get; init; }

    /// <summary>The XP source id; defaults to the choice's id.</summary>
    public string? Source { get; init; }

    /// <summary>A faction whose reputation changes by <see cref="Delta"/>.</summary>
    public string? Rep { get; init; }

    /// <summary>The change for <see cref="Rep"/>.</summary>
    public int Delta { get; init; }

    /// <summary>Starts a quest.</summary>
    public string? StartQuest { get; init; }

    /// <summary>Completes an objective, "quest/objective".</summary>
    public string? Objective { get; init; }

    /// <summary>Reveals a hidden objective.</summary>
    public string? Reveal { get; init; }

    /// <summary>Completes a quest and pays its reward.</summary>
    public string? CompleteQuest { get; init; }

    /// <summary>Fails a quest.</summary>
    public string? FailQuest { get; init; }

    /// <summary>Buys one of an item from the tree's vendor at the price rule's price.</summary>
    public string? Buy { get; init; }

    /// <summary>Sells every clean (not stolen) one of an item to the tree's vendor.</summary>
    public string? Sell { get; init; }

    /// <summary>Heals to full at this many credits per point (as much as the runner can pay).</summary>
    public int? HealPerPointCr { get; init; }

    /// <summary>Opens a door or container by stable id.</summary>
    public string? Open { get; init; }

    /// <summary>An NPC to act, with <see cref="Do"/>.</summary>
    public string? Npc { get; init; }

    /// <summary>What the NPC does: hostile, calm, flee, surrender, gone.</summary>
    public string? Do { get; init; }

    /// <summary>Starts a truce with a faction.</summary>
    public string? Parley { get; init; }

    /// <summary>A line for the message feed.</summary>
    public string? Say { get; init; }

    /// <summary>An engine action by name, such as "sleep" (save at the safehouse).</summary>
    public string? Host { get; init; }
}

/// <summary>A choice.</summary>
public sealed class DialogChoice
{
    /// <summary>The line the runner says. May use {price:item} and {sell:item}.</summary>
    public required string Text { get; init; }

    /// <summary>Conditions; all must hold.</summary>
    public IReadOnlyList<DialogCond> If { get; init; } = Array.Empty<DialogCond>();

    /// <summary>A check, or null.</summary>
    public DialogCheck? Check { get; init; }

    /// <summary>The next node, for a choice without a check.</summary>
    public string? Next { get; init; }

    /// <summary>The node when the check passes.</summary>
    public string? Pass { get; init; }

    /// <summary>The node when a cover check fails.</summary>
    public string? Fail { get; init; }

    /// <summary>Effects, run when the choice is picked (before the check).</summary>
    public IReadOnlyList<DialogEffect> Do { get; init; } = Array.Empty<DialogEffect>();

    /// <summary>Ends the conversation after its effects.</summary>
    public bool Exit { get; init; }

    /// <summary>Can be picked only once per save.</summary>
    public bool Once { get; init; }
}

/// <summary>A node: what the other person says, then choices, a next node, or the end.</summary>
public sealed class DialogNode
{
    /// <summary>The lines, shown one after another. May use {small_talk} and {rumour}.</summary>
    public IReadOnlyList<string> Say { get; init; } = Array.Empty<string>();

    /// <summary>Effects run when the node is entered.</summary>
    public IReadOnlyList<DialogEffect> Do { get; init; } = Array.Empty<DialogEffect>();

    /// <summary>The node after the last line, when there are no choices.</summary>
    public string? Next { get; init; }

    /// <summary>The choices, shown after the last line.</summary>
    public IReadOnlyList<DialogChoice> Choices { get; init; } = Array.Empty<DialogChoice>();

    /// <summary>Ends the conversation after the last line when there are no choices.</summary>
    public bool Exit { get; init; }
}

/// <summary>An entry point, tried in order; the first whose conditions hold is used.</summary>
public sealed class DialogStart
{
    /// <summary>Conditions.</summary>
    public IReadOnlyList<DialogCond> If { get; init; } = Array.Empty<DialogCond>();

    /// <summary>The node to start at.</summary>
    public required string Node { get; init; }
}

/// <summary>One NPC's dialog tree.</summary>
public sealed class DialogTree : IValidated
{
    /// <summary>The tree id, the file's name.</summary>
    public required string Id { get; init; }

    /// <summary>The speaker's display name.</summary>
    public required string Name { get; init; }

    /// <summary>The vendor this speaker sells for, or null.</summary>
    public string? Vendor { get; init; }

    /// <summary>Entry points, tried in order.</summary>
    public required IReadOnlyList<DialogStart> Starts { get; init; }

    /// <summary>The nodes by id.</summary>
    public required IReadOnlyDictionary<string, DialogNode> Nodes { get; init; }

    /// <summary>Short context lines by kind: greeting, spotted, lost, found_body, alarm.</summary>
    public IReadOnlyDictionary<string, IReadOnlyList<string>> Barks { get; init; } = new Dictionary<string, IReadOnlyList<string>>();

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        if (Starts.Count == 0)
        {
            errors.Add($"dialog.{Id}: needs at least one start");
        }
        foreach (var s in Starts.Where(s => !Nodes.ContainsKey(s.Node)))
        {
            errors.Add($"dialog.{Id}: start goes to unknown node '{s.Node}'");
        }
        foreach (var (id, n) in Nodes)
        {
            if (n.Next is not null && !Nodes.ContainsKey(n.Next))
            {
                errors.Add($"dialog.{Id}.{id}: next goes to unknown node '{n.Next}'");
            }
            if (n.Choices.Count == 0 && n.Next is null && !n.Exit)
            {
                errors.Add($"dialog.{Id}.{id}: a node without choices needs next or exit");
            }
            for (var i = 0; i < n.Choices.Count; i++)
            {
                var c = n.Choices[i];
                var where = $"dialog.{Id}.{id}.choice {i + 1}";
                foreach (var target in new[] { c.Next, c.Pass, c.Fail }.Where(t => t is not null && !Nodes.ContainsKey(t)))
                {
                    errors.Add($"{where}: goes to unknown node '{target}'");
                }
                if (c.Check is null && c.Next is null && !c.Exit)
                {
                    errors.Add($"{where}: needs next or exit");
                }
                if (c.Check is not null && c.Pass is null)
                {
                    errors.Add($"{where}: a check needs a pass node");
                }
                if (c.Check?.Cover is not null && c.Fail is null)
                {
                    errors.Add($"{where}: a cover check needs a fail node");
                }
                if (c.Check is { Skill: not null, Dc: < 1 or > 6 })
                {
                    errors.Add($"{where}: a skill check's dc must be 1 to 6");
                }
            }
        }
    }
}
