// One objective in the journal (objective_row.tscn): ticked when done, marked when optional.
//
// It lives in the UI layer as a thin view: whether an objective shows and whether it's done are
// QuestLog.IsVisible and QuestLog.IsDone.

#nullable enable
using Godot;
using Undercity.Core.Quests;

namespace Undercity.Client;

/// <summary>A journal objective row.</summary>
public partial class ObjectiveRowView : HBoxContainer
{
    private Label _tick = null!;
    private Label _text = null!;
    private Label _optional = null!;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _tick = GetNode<Label>("%Tick");
        _text = GetNode<Label>("%Text");
        _optional = GetNode<Label>("%Optional");
    }

    /// <summary>Shows <paramref name="objective"/>, done or not.</summary>
    public void Bind(ObjectiveDef objective, bool done)
    {
        _tick.Text = done ? "[x]" : "[ ]";
        _text.Text = objective.Text;
        _text.ThemeTypeVariation = done ? "ObjectiveDone" : "ScreenText";
        _optional.Visible = objective.Optional;
    }
}
