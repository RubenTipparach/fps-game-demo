// Running a conversation: which start applies, which choices show and whether they're enabled,
// what a pick does, and the text with prices filled in.
//
// It lives in the core because the greyed-out choice the screen shows and the outcome of picking
// it must come from the same code (CLAUDE.md 5.1). Conditions and effects are small rules in a
// registry, so a new kind is a new rule, not an edit to the runner (CLAUDE.md 5.3).

using System.Globalization;
using System.Text.RegularExpressions;
using Undercity.Core.Progression;

namespace Undercity.Core.Dialog;

/// <summary>What the conversation needs from the game: state to read, effects to apply.</summary>
public interface IDialogWorld
{
    /// <summary>A skill's check value: rank plus gear.</summary>
    int CheckValue(Skill skill);

    /// <summary>The runner's Cover in this conversation, including a Mimic bonus; 0 when not disguised.</summary>
    int ConversationCover { get; }

    /// <summary>True when the speaker accepts the runner's disguise in this conversation.</summary>
    bool DisguiseAccepted { get; }

    /// <summary>Tests a story or build condition. Returns null for a condition kind it doesn't know.</summary>
    bool Holds(DialogCond cond, DialogTree tree);

    /// <summary>The requirement text for a build condition, such as "[200 cr]", or "" for a story condition.</summary>
    string Requirement(DialogCond cond, DialogTree tree);

    /// <summary>Applies an effect.</summary>
    void Apply(DialogEffect effect, DialogTree tree, string choiceId);

    /// <summary>Fills {price:item}, {sell:item}, {small_talk} and {rumour} in a line.</summary>
    string Fill(string text, DialogTree tree);

    /// <summary>True when a flag is set.</summary>
    bool Flag(string flag);

    /// <summary>Sets a flag.</summary>
    void SetFlag(string flag);

    /// <summary>Pays XP once per source.</summary>
    void PayXp(int xp, string sourceId, string reason);

    /// <summary>XP per point of DC for a passed check.</summary>
    int XpPerDc { get; }
}

/// <summary>A choice as the screen shows it.</summary>
/// <param name="Index">Its index in the node's choices.</param>
/// <param name="Text">The line, with prices filled in.</param>
/// <param name="Requirement">"[Deception 2]", "[200 cr]", or "" when it needs nothing.</param>
/// <param name="Enabled">False when a build requirement isn't met: shown greyed.</param>
/// <param name="Passed">True when its check was passed before.</param>
public sealed record ChoiceView(int Index, string Text, string Requirement, bool Enabled, bool Passed);

/// <summary>One conversation with one speaker.</summary>
public sealed class DialogSession
{
    private readonly DialogTree _tree;
    private readonly IDialogWorld _world;
    private DialogNode _node;
    private string _nodeId;
    private int _line;

    /// <summary>Starts at the first entry whose conditions hold, running its node's effects.</summary>
    public DialogSession(DialogTree tree, IDialogWorld world)
    {
        _tree = tree;
        _world = world;
        var start = tree.Starts.FirstOrDefault(s => s.If.All(c => world.Holds(c, tree))) ?? tree.Starts[^1];
        _nodeId = start.Node;
        _node = tree.Nodes[_nodeId];
        Enter(_nodeId);
    }

    /// <summary>The tree.</summary>
    public DialogTree Tree => _tree;

    /// <summary>True once the conversation is over.</summary>
    public bool Over { get; private set; }

    /// <summary>The current node's id.</summary>
    public string NodeId => _nodeId;

    /// <summary>The line being shown, with placeholders filled.</summary>
    public string Line => _node.Say.Count == 0 ? "" : _world.Fill(_node.Say[Math.Min(_line, _node.Say.Count - 1)], _tree);

    /// <summary>True when more lines follow the current one before the choices.</summary>
    public bool MoreLines => _line < _node.Say.Count - 1;

    /// <summary>
    /// The choices to show now: none while more lines follow. Story conditions that fail hide a
    /// choice; build conditions and unmet skill checks show it greyed, with the requirement.
    /// </summary>
    public IReadOnlyList<ChoiceView> Choices()
    {
        if (Over || MoreLines)
        {
            return Array.Empty<ChoiceView>();
        }
        var views = new List<ChoiceView>();
        for (var i = 0; i < _node.Choices.Count; i++)
        {
            var c = _node.Choices[i];
            if (c.Once && _world.Flag(OnceFlag(i)))
            {
                continue;
            }
            var hidden = false;
            var enabled = true;
            var reqs = new List<string>();
            foreach (var cond in c.If)
            {
                var holds = _world.Holds(cond, _tree);
                var req = _world.Requirement(cond, _tree);
                if (req.Length == 0)
                {
                    hidden |= !holds;
                }
                else
                {
                    reqs.Add(req);
                    enabled &= holds;
                }
            }
            if (hidden)
            {
                continue;
            }
            var passed = false;
            if (c.Check is { Skill: { } skill } chk)
            {
                reqs.Insert(0, $"[{skill} {chk.Dc}]");
                enabled &= _world.CheckValue(skill) >= chk.Dc;
                passed = _world.Flag(PassFlag(i));
            }
            else if (c.Check is { Cover: { } cover })
            {
                reqs.Insert(0, $"[Cover {cover}]");
            }
            var requirement = string.Join(" ", reqs);
            if (passed)
            {
                requirement = requirement.Replace("]", ": passed]", StringComparison.Ordinal);
            }
            views.Add(new ChoiceView(i, _world.Fill(c.Text, _tree), requirement, enabled, passed));
        }
        if (views.Count == 0 && _node.Choices.Count > 0)
        {
            views.Add(new ChoiceView(-1, "(Leave.)", "", true, false));
        }
        return views;
    }

    /// <summary>Shows the next line, or moves on when the node has no choices. Returns false when nothing happened.</summary>
    public bool Advance()
    {
        if (Over)
        {
            return false;
        }
        if (MoreLines)
        {
            _line++;
            return true;
        }
        if (_node.Choices.Count > 0)
        {
            return false;
        }
        if (_node.Next is not null)
        {
            Enter(_node.Next);
        }
        else
        {
            Over = true;
        }
        return true;
    }

    /// <summary>Picks a choice by its index. Returns false, changing nothing, when it isn't shown or is disabled.</summary>
    public bool Choose(int index)
    {
        var view = Choices().FirstOrDefault(v => v.Index == index);
        if (view is null || !view.Enabled)
        {
            return false;
        }
        if (index < 0)
        {
            Over = true;
            return true;
        }
        var c = _node.Choices[index];
        var choiceId = $"dlg:{_tree.Id}:{_nodeId}:{index}";
        if (c.Once)
        {
            _world.SetFlag(OnceFlag(index));
        }
        foreach (var e in c.Do)
        {
            _world.Apply(e, _tree, choiceId);
        }
        string? next = c.Next;
        if (c.Check is { Skill: { } skill } chk)
        {
            // Enabled means the check value meets the DC: deterministic, so a pick always passes.
            _world.SetFlag(PassFlag(index));
            _world.PayXp(_world.XpPerDc * chk.Dc, choiceId, $"{skill} {chk.Dc}");
            next = c.Pass;
        }
        else if (c.Check is { Cover: { } cover })
        {
            var ok = _world.ConversationCover >= cover;
            if (ok)
            {
                _world.PayXp(_world.XpPerDc * cover, choiceId, $"Cover {cover}");
            }
            next = ok ? c.Pass : c.Fail;
        }
        if (c.Exit || next is null)
        {
            Over = true;
            return true;
        }
        Enter(next);
        return true;
    }

    private void Enter(string nodeId)
    {
        _nodeId = nodeId;
        _node = _tree.Nodes[nodeId];
        _line = 0;
        foreach (var e in _node.Do)
        {
            _world.Apply(e, _tree, $"dlg:{_tree.Id}:{nodeId}");
        }
        if (_node.Say.Count == 0 && _node.Choices.Count == 0)
        {
            if (_node.Next is not null && _node.Next != nodeId)
            {
                Enter(_node.Next);
            }
            else
            {
                Over = true;
            }
        }
    }

    private string OnceFlag(int index) => $"dlg:{_tree.Id}:{_nodeId}:{index}:once";

    private string PassFlag(int index) => $"dlg:{_tree.Id}:{_nodeId}:{index}:passed";
}

/// <summary>Placeholder filling shared by every dialog world.</summary>
public static partial class DialogText
{
    [GeneratedRegex(@"\{(price|sell):([a-z0-9_]+)\}")]
    private static partial Regex PricePattern();

    /// <summary>Replaces {price:item} and {sell:item} using <paramref name="price"/> and <paramref name="sell"/>.</summary>
    public static string FillPrices(string text, Func<string, int?> price, Func<string, int?> sell) =>
        PricePattern().Replace(text, m =>
        {
            var value = m.Groups[1].Value == "price" ? price(m.Groups[2].Value) : sell(m.Groups[2].Value);
            return value is { } v ? v.ToString(CultureInfo.InvariantCulture) + " cr" : "?";
        });
}
