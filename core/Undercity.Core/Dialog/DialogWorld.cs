// The dialog world: how each kind of condition is tested and each kind of effect applied,
// against the run's state, as registries of small rules.
//
// It lives in the core because dialog, terminals and triggers share these rules (CLAUDE.md 5.1),
// and a new condition or effect is added as a rule here, never as a branch in the runner
// (CLAUDE.md 5.3).

using System.Globalization;
using Undercity.Core.Data;
using Undercity.Core.Progression;
using Undercity.Core.World;

namespace Undercity.Core.Dialog;

/// <summary>Who the runner is talking to.</summary>
/// <param name="StableId">The speaker's stable id, which seeds civilian small talk.</param>
/// <param name="NpcId">The named NPC's id, or null for a civilian or a device.</param>
/// <param name="DisguiseAccepted">True when the speaker accepts the runner's disguise.</param>
/// <param name="CoverBonus">Extra Cover in this conversation (Mimic).</param>
public sealed record Speaker(string StableId, string? NpcId, bool DisguiseAccepted = false, int CoverBonus = 0)
{
    /// <summary>No one: terminals and triggers.</summary>
    public static readonly Speaker Nobody = new("", null);
}

/// <summary>The dialog world backed by a <see cref="GameState"/>.</summary>
public sealed class DialogWorld : IDialogWorld
{
    /// <summary>An empty tree, for effects run outside a conversation.</summary>
    public static readonly DialogTree NoTree = new()
    {
        Id = "none",
        Name = "",
        Starts = new[] { new DialogStart { Node = "end" } },
        Nodes = new Dictionary<string, DialogNode> { ["end"] = new DialogNode { Exit = true } },
    };

    private readonly GameState _s;
    private readonly Speaker _speaker;

    /// <summary>Creates the world for one conversation.</summary>
    public DialogWorld(GameState state, Speaker speaker)
    {
        _s = state;
        _speaker = speaker;
    }

    /// <inheritdoc/>
    public int ConversationCover => _speaker.DisguiseAccepted
        ? Perception.DisguiseRules.Cover(_s.Character, _s.Inventory, _speaker.CoverBonus)
        : 0;

    /// <inheritdoc/>
    public bool DisguiseAccepted => _speaker.DisguiseAccepted;

    /// <inheritdoc/>
    public int XpPerDc => _s.Data.Progression.Xp.DialogCheckPerDc;

    /// <inheritdoc/>
    public int CheckValue(Skill skill) => _s.CheckValue(skill);

    /// <inheritdoc/>
    public bool Flag(string flag) => _s.World.Flag(flag);

    /// <inheritdoc/>
    public void SetFlag(string flag) => _s.World.SetFlag(flag);

    /// <inheritdoc/>
    public void PayXp(int xp, string sourceId, string reason) => _s.Character.AddXp(xp, sourceId, reason);

    // ------------------------------------------------------------------ conditions

    /// <summary>A kind of condition: which ones it handles, whether it holds, and its requirement text.</summary>
    private sealed record CondRule(
        Func<DialogCond, bool> Handles,
        Func<DialogCond, DialogWorld, DialogTree, bool> Holds,
        Func<DialogCond, DialogWorld, DialogTree, string>? Requirement = null);

    private static readonly CondRule[] CondRules =
    {
        new(c => c.Flag is not null, (c, w, _) => w._s.World.Flag(c.Flag!)),
        new(c => c.NotFlag is not null, (c, w, _) => !w._s.World.Flag(c.NotFlag!)),
        new(c => c.Item is not null, (c, w, _) => w._s.Inventory.Pack.Has(c.Item!, c.Count)),
        new(c => c.NoItem is not null, (c, w, _) => !w._s.Inventory.Pack.Has(c.NoItem!)),
        new(c => c.Credits is not null, (c, w, _) => w._s.Inventory.Credits >= c.Credits,
            (c, _, _) => $"[{c.Credits} cr]"),
        new(c => c.Skill is not null, (c, w, _) => w._s.CheckValue(c.Skill!.Value) >= (c.Min ?? 0),
            (c, _, _) => $"[{c.Skill} {c.Min}]"),
        new(c => c.Disguise is not null, (c, w, _) => w._speaker.DisguiseAccepted == c.Disguise),
        new(c => c.Quest is not null, (c, w, _) => w._s.Quests.State(c.Quest!) == (c.State ?? Quests.QuestState.Active)),
        new(c => c.Objective is not null, (c, w, _) => w._s.Quests.IsDone(c.Objective!)),
        new(c => c.NotObjective is not null, (c, w, _) => !w._s.Quests.IsDone(c.NotObjective!)),
        new(c => c.Npc is not null, (c, w, _) => w._s.World.Npc(c.Npc!) == (c.Status ?? NpcStatus.Alive)),
        new(c => c.Rep is not null,
            (c, w, _) => w._s.Reputation.Get(c.Rep!) >= (c.Min ?? -100) && w._s.Reputation.Get(c.Rep!) <= (c.Max ?? 100),
            (c, w, _) => $"[{w._s.Data.Factions.Factions.First(f => f.Id == c.Rep).Name} {(c.Min is { } m ? m.ToString(CultureInfo.InvariantCulture) + "+" : "")}]"),
        new(c => c.Parley is not null, (c, w, _) => w._s.World.Parleys.Contains(c.Parley!)),
        new(c => c.Outfit is not null, (c, w, _) => w._s.Inventory.OutfitFaction == c.Outfit),
        new(c => c.CanAfford is not null,
            (c, w, t) => t.Vendor is not null && w._s.InStock(t.Vendor, c.CanAfford!) >= c.Count
                && w._s.Inventory.Credits >= w._s.BuyPrice(t.Vendor, c.CanAfford!) * c.Count,
            (c, w, t) => t.Vendor is null ? "[not for sale]"
                : w._s.InStock(t.Vendor, c.CanAfford!) >= c.Count ? $"[{w._s.BuyPrice(t.Vendor, c.CanAfford!) * c.Count} cr]" : "[sold out]"),
    };

    private static CondRule RuleFor(DialogCond c) =>
        CondRules.FirstOrDefault(r => r.Handles(c))
        ?? throw new DataException("dialog", "a condition sets no known test");

    /// <inheritdoc/>
    public bool Holds(DialogCond cond, DialogTree tree) => RuleFor(cond).Holds(cond, this, tree);

    /// <inheritdoc/>
    public string Requirement(DialogCond cond, DialogTree tree) =>
        RuleFor(cond).Requirement?.Invoke(cond, this, tree) ?? "";

    // ------------------------------------------------------------------ effects

    /// <summary>A kind of effect: which ones it handles and what it does.</summary>
    private sealed record EffectRule(Func<DialogEffect, bool> Handles, Action<DialogEffect, DialogWorld, DialogTree, string> Apply);

    private static readonly EffectRule[] EffectRules =
    {
        new(e => e.Flag is not null, (e, w, _, _) => w._s.World.SetFlag(e.Flag!)),
        new(e => e.Unflag is not null, (e, w, _, _) => w._s.World.ClearFlag(e.Unflag!)),
        new(e => e.Give is not null, (e, w, _, _) =>
        {
            var left = w._s.PickUp(e.Give!, e.Count);
            if (left > 0)
            {
                w._s.Host("drop", $"{e.Give}:{left}");
            }
        }),
        new(e => e.Take is not null, (e, w, _, _) => w._s.Inventory.Pack.Remove(e.Take!, e.Count)),
        new(e => e.Credits is not null, (e, w, _, _) =>
        {
            if (e.Credits > 0)
            {
                w._s.Inventory.Earn(e.Credits.Value);
                w._s.Say($"+{e.Credits} credits");
            }
            else
            {
                w._s.Inventory.Spend(Math.Min(-e.Credits!.Value, w._s.Inventory.Credits));
            }
        }),
        new(e => e.Xp is not null, (e, w, _, id) => w._s.Character.AddXp(e.Xp!.Value, e.Source ?? id, "")),
        new(e => e.Rep is not null, (e, w, _, _) =>
            w._s.Reputation.Change(e.Rep!, e.Delta, w._s.Character.Mult("rep_gain_mult"))),
        new(e => e.StartQuest is not null, (e, w, _, _) => w._s.Quests.Start(e.StartQuest!)),
        new(e => e.Objective is not null, (e, w, _, _) => w._s.CompleteObjective(e.Objective!)),
        new(e => e.Reveal is not null, (e, w, _, _) => w._s.Quests.Reveal(e.Reveal!)),
        new(e => e.CompleteQuest is not null, (e, w, _, _) => w._s.CompleteQuest(e.CompleteQuest!)),
        new(e => e.FailQuest is not null, (e, w, _, _) => w._s.Quests.Fail(e.FailQuest!)),
        new(e => e.Buy is not null, (e, w, t, _) =>
        {
            for (var i = 0; t.Vendor is not null && i < e.Count && w._s.Buy(t.Vendor, e.Buy!); i++)
            {
            }
        }),
        new(e => e.Sell is not null, (e, w, t, _) =>
        {
            if (t.Vendor is not null)
            {
                w._s.SellAll(t.Vendor, e.Sell!);
            }
        }),
        new(e => e.HealPerPointCr is not null, (e, w, _, _) => w._s.PaidHeal(e.HealPerPointCr!.Value)),
        new(e => e.Open is not null, (e, w, _, _) => w._s.Host("open", e.Open!)),
        new(e => e.Npc is not null, (e, w, _, _) =>
        {
            var status = e.Do switch
            {
                "hostile" => NpcStatus.Hostile,
                "gone" or "flee" => NpcStatus.Gone,
                "calm" => NpcStatus.Alive,
                _ => w._s.World.Npc(e.Npc!),
            };
            w._s.World.SetNpc(e.Npc!, status);
            w._s.Host("npc", $"{e.Npc}:{e.Do}");
        }),
        new(e => e.Parley is not null, (e, w, _, _) => w._s.World.Parleys.Add(e.Parley!)),
        new(e => e.Say is not null, (e, w, _, _) => w._s.Say(e.Say!)),
        new(e => e.Host is not null, (e, w, _, _) => w._s.Host(e.Host!)),
    };

    /// <inheritdoc/>
    public void Apply(DialogEffect effect, DialogTree tree, string choiceId)
    {
        var rule = EffectRules.FirstOrDefault(r => r.Handles(effect))
            ?? throw new DataException("dialog", "an effect sets no known action");
        rule.Apply(effect, this, tree, choiceId);
    }

    // ------------------------------------------------------------------ text

    /// <inheritdoc/>
    public string Fill(string text, DialogTree tree)
    {
        if (text.Contains("{small_talk}", StringComparison.Ordinal) || text.Contains("{rumour}", StringComparison.Ordinal))
        {
            var pool = _s.Data.Npcs.Civilians;
            var rng = SeededRandom.For(_s.World.Seed, _speaker.StableId, "civilian");
            text = text.Replace("{small_talk}", pool.SmallTalk[rng.Next(pool.SmallTalk.Count)], StringComparison.Ordinal)
                .Replace("{rumour}", pool.Rumours[rng.Next(pool.Rumours.Count)], StringComparison.Ordinal);
        }
        if (tree.Vendor is not { } vendor)
        {
            return text;
        }
        return DialogText.FillPrices(text,
            item => _s.Data.Items.Exists(item) ? _s.BuyPrice(vendor, item) : null,
            item => _s.Data.Items.Exists(item) ? _s.SellPrice(vendor, item) : null);
    }
}
