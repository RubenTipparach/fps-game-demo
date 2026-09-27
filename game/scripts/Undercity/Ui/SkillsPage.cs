// The deck's Skills tab: one card per skill in data/skills.json, refreshed when the character
// changes. Raise buys the next rank through Character.Raise.
//
// It lives in the UI layer as a thin view: ranks, perks and whether a rank can be bought come from
// Character, the same code that buys it (CLAUDE.md 5.1).

#nullable enable
using System.Collections.Generic;
using Godot;

namespace Undercity.Client;

/// <summary>The Skills tab.</summary>
public partial class SkillsPage : HBoxContainer, IWired
{
    /// <summary>One skill's card (skill_card.tscn).</summary>
    [Export] public PackedScene CardScene { get; set; } = null!;

    private Services? _services;
    private readonly List<SkillCardView> _cards = new();

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _services = services;
        foreach (var skill in services.Data.Skills.Skills)
        {
            var card = CardScene.Instantiate<SkillCardView>();
            AddChild(card);
            card.RaiseRequested += s => services.State.Character.Raise(s);
            _cards.Add(card);
        }
        services.State.Character.Changed += Refresh;
        Refresh();
    }

    /// <inheritdoc/>
    public override void _ExitTree()
    {
        if (_services is not null)
        {
            _services.State.Character.Changed -= Refresh;
        }
    }

    private void Refresh()
    {
        if (_services is null)
        {
            return;
        }
        var skills = _services.Data.Skills.Skills;
        for (var i = 0; i < _cards.Count; i++)
        {
            _cards[i].Bind(skills[i], _services.State.Character);
        }
    }
}
