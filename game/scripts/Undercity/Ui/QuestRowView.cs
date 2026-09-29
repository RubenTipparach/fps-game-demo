// One quest in the journal's list (quest_row.tscn).
//
// It lives in the UI layer as a thin view: which quests are active or finished is the QuestLog's.

#nullable enable
using System;
using Godot;
using Undercity.Core.Quests;

namespace Undercity.Client;

/// <summary>A journal list row.</summary>
public partial class QuestRowView : Button
{
    private string _questId = "";

    /// <summary>Raised with the quest id when the row is clicked.</summary>
    public event Action<string>? Picked;

    /// <inheritdoc/>
    public override void _Ready() => Pressed += () => Picked?.Invoke(_questId);

    /// <summary>Shows <paramref name="quest"/>, highlighted when it's the one open.</summary>
    public void Bind(QuestDef quest, bool selected)
    {
        _questId = quest.Id;
        Text = quest.Title;
        ThemeTypeVariation = selected ? "ListRowSelected" : "ListRow";
    }
}
