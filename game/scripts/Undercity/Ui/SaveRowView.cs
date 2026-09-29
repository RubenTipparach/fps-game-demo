// One slot in the save list (save_row.tscn): its name, where the run was, how long it has been
// played and when it was written.
//
// It lives in the UI layer as a thin view: the summary is read from the save by SaveStore.

#nullable enable
using System;
using Godot;
using Undercity.Core;

namespace Undercity.Client;

/// <summary>A save list row.</summary>
public partial class SaveRowView : Button
{
    private Label _slot = null!;
    private Label _place = null!;
    private Label _time = null!;
    private Label _written = null!;
    private string _slotId = "";

    /// <summary>Raised with the slot when the row is clicked.</summary>
    public event Action<string>? Picked;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _slot = GetNode<Label>("%Slot");
        _place = GetNode<Label>("%Place");
        _time = GetNode<Label>("%Time");
        _written = GetNode<Label>("%Written");
        Pressed += () => Picked?.Invoke(_slotId);
    }

    /// <summary>Shows a slot: an empty one names only itself.</summary>
    public void Bind(SaveSummary save, GameData data, DateTime nowUtc)
    {
        _slotId = save.Slot;
        _slot.Text = UiText.Slot(save.Slot);
        _place.Text = !save.Exists ? "empty" : save.Damaged ? "damaged" : UiText.Place(data, save.LevelId);
        _time.Text = save.Loadable ? UiText.PlayTime(save.PlayTimeS) : "";
        _written.Text = save.Exists ? UiText.Written(save.WrittenUtc, nowUtc) : "";
    }

    /// <summary>Marks the row as the selected one.</summary>
    public void SetSelected(bool selected) => ThemeTypeVariation = selected ? "SaveRowOn" : "SaveRow";
}
