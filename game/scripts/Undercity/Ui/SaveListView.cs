// The save list (save_list.tscn) that both the title's Load and the pause menu show: one row per
// slot (save_row.tscn), the saves newest first and the empty slots after them.
//
// It lives in the UI layer as a thin view: which slots exist, their order and what each save
// says about itself are SaveStore's and SavesTable's (CLAUDE.md 5.1, 6.2). Each row is named
// after its slot so a scripted run can click it.

#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using Godot;
using Undercity.Core;

namespace Undercity.Client;

/// <summary>A list of save slots with one selected.</summary>
public partial class SaveListView : VBoxContainer
{
    /// <summary>One slot (save_row.tscn).</summary>
    [Export] public PackedScene RowScene { get; set; } = null!;

    private readonly Dictionary<string, SaveRowView> _rows = new(StringComparer.Ordinal);
    private IReadOnlyList<SaveSummary> _summaries = Array.Empty<SaveSummary>();

    /// <summary>Raised when the player picks a row.</summary>
    public event Action? SelectionChanged;

    /// <summary>The selected slot's summary, or null before the first <see cref="Show"/>.</summary>
    public SaveSummary? Selected { get; private set; }

    /// <summary>
    /// Lists <paramref name="saves"/>' slots and keeps <paramref name="keep"/> selected when it's
    /// one of them; otherwise selects the first row.
    /// </summary>
    public void Show(SaveStore saves, GameData data, string? keep = null)
    {
        _summaries = saves.Summaries(data.Saves.Slots);
        var now = DateTime.UtcNow;
        for (var i = 0; i < _summaries.Count; i++)
        {
            var s = _summaries[i];
            if (!_rows.TryGetValue(s.Slot, out var row))
            {
                row = RowScene.Instantiate<SaveRowView>();
                row.Name = s.Slot;
                row.Picked += Pick;
                AddChild(row);
                _rows[s.Slot] = row;
            }
            MoveChild(row, i);
            row.Bind(s, data, now);
        }
        Selected = _summaries.FirstOrDefault(s => s.Slot == keep) ?? _summaries.FirstOrDefault();
        Highlight();
    }

    private void Pick(string slot)
    {
        Selected = _summaries.FirstOrDefault(s => s.Slot == slot) ?? Selected;
        Highlight();
        SelectionChanged?.Invoke();
    }

    private void Highlight()
    {
        foreach (var (slot, row) in _rows)
        {
            row.SetSelected(slot == Selected?.Slot);
        }
    }
}
