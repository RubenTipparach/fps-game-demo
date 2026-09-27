// One skill on the deck's Skills tab (skill_card.tscn): its name, rank pips, blurb, five perks
// with the owned ones lit, and the Raise button with the reason it's greyed.
//
// It lives in the UI layer as a thin view: the rank, the perks owned and whether the next rank
// can be bought (and why not) all come from Character, the code that buys it (CLAUDE.md 5.1).

#nullable enable
using System;
using System.Globalization;
using Godot;
using Undercity.Core.Progression;

namespace Undercity.Client;

/// <summary>A skill card.</summary>
public partial class SkillCardView : PanelContainer
{
    private const int Ranks = 5;

    private Label _name = null!;
    private Label _blurb = null!;
    private Button _raise = null!;
    private Label _reason = null!;
    private readonly Panel[] _pips = new Panel[Ranks];
    private readonly PanelContainer[] _perks = new PanelContainer[Ranks];
    private Skill _skill;

    /// <summary>Raised with the skill when Raise is pressed.</summary>
    public event Action<Skill>? RaiseRequested;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _name = GetNode<Label>("%Name");
        _blurb = GetNode<Label>("%Blurb");
        _raise = GetNode<Button>("%Raise");
        _reason = GetNode<Label>("%Reason");
        for (var i = 0; i < Ranks; i++)
        {
            _pips[i] = GetNode<Panel>($"%Pip{i + 1}");
            _perks[i] = GetNode<PanelContainer>($"%Perk{i + 1}");
        }
        _raise.Pressed += () => RaiseRequested?.Invoke(_skill);
    }

    /// <summary>Shows <paramref name="skill"/> as <paramref name="character"/> has it now.</summary>
    public void Bind(SkillDef skill, Character character)
    {
        _skill = skill.Id;
        var rank = character.Rank(skill.Id);
        _name.Text = skill.Name;
        _blurb.Text = skill.Blurb;
        for (var i = 0; i < Ranks; i++)
        {
            _pips[i].ThemeTypeVariation = i < rank ? "PipOn" : "Pip";
            var owned = i < rank;
            var perk = i < skill.Perks.Count ? skill.Perks[i] : null;
            _perks[i].Visible = perk is not null;
            if (perk is null)
            {
                continue;
            }
            _perks[i].ThemeTypeVariation = owned ? "PerkNodeOwned" : i == rank ? "PerkNodeNext" : "PerkNode";
            var index = _perks[i].GetNode<Label>("Rows/Head/Index");
            index.Text = (i + 1).ToString(CultureInfo.InvariantCulture);
            index.ThemeTypeVariation = owned ? "PerkIndexOwned" : "PerkIndex";
            var name = _perks[i].GetNode<Label>("Rows/Head/Name");
            name.Text = perk.Name;
            name.ThemeTypeVariation = owned ? "PerkNameOwned" : "PerkName";
            var text = _perks[i].GetNode<Label>("Rows/Text");
            text.Text = perk.Text;
            text.ThemeTypeVariation = owned ? "PerkTextOwned" : "PerkText";
        }
        var check = character.CanRaise(skill.Id);
        _raise.Disabled = !check.Ok;
        _reason.Text = check.Ok ? CostText(character.Skills.CostOf(rank + 1)) : check.Reason;
        _reason.ThemeTypeVariation = check.Ok ? "ScreenMonoDim" : "ReasonLabel";
    }

    private static string CostText(int points) => points == 1 ? "1 point" : $"{points} points";
}
