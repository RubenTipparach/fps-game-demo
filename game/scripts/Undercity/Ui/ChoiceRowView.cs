// One dialog choice (choice_row.tscn): its number, its requirement in mono and its line, greyed
// when the build can't take it.
//
// It lives in the UI layer as a thin view of the core's ChoiceView: whether a choice shows, is
// enabled and what it requires come from DialogSession.Choices(), the same code that resolves the
// pick (CLAUDE.md 5.1).

#nullable enable
using System;
using Godot;
using Undercity.Core.Dialog;

namespace Undercity.Client;

/// <summary>A dialog choice row.</summary>
public partial class ChoiceRowView : Button
{
    private const float MaxRequirementPx = 520;

    private Label _number = null!;
    private Label _requirement = null!;
    private Label _text = null!;
    private int _index;

    /// <summary>Raised with the choice's index in its node (-1 for "(Leave.)") when it's clicked.</summary>
    public event Action<int>? Chosen;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _number = GetNode<Label>("%Number");
        _requirement = GetNode<Label>("%Requirement");
        _text = GetNode<Label>("%Text");
        Pressed += () => Chosen?.Invoke(_index);
    }

    /// <summary>Shows <paramref name="view"/> as row <paramref name="row"/> (0-based; numbered from 1).</summary>
    public void Bind(int row, ChoiceView view)
    {
        _index = view.Index;
        _number.Text = UiKeys.RowLabel(row) + ".";
        _requirement.Text = view.Requirement;
        _requirement.Visible = view.Requirement.Length > 0;
        _requirement.ThemeTypeVariation = view.Enabled ? "ChoiceReq" : "ChoiceReqOff";
        UiText.FitWidth(_requirement, MaxRequirementPx);
        _text.Text = view.Text;
        _text.ThemeTypeVariation = view.Enabled ? "ChoiceText" : "ChoiceTextOff";
        Disabled = !view.Enabled;
    }
}
