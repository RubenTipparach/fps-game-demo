// One message in a terminal's list (page_row.tscn): who it's from and its subject.
//
// It lives in the UI layer as a thin view of a TerminalPage from the level's data.

#nullable enable
using System;
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>A terminal page row.</summary>
public partial class PageRowView : Button
{
    private Label _from = null!;
    private Label _subject = null!;
    private int _index;

    /// <summary>Raised with the page's index when the row is clicked.</summary>
    public event Action<int>? Picked;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _from = GetNode<Label>("%From");
        _subject = GetNode<Label>("%Subject");
        Pressed += () => Picked?.Invoke(_index);
    }

    /// <summary>Shows page <paramref name="index"/>, highlighted when it's the one open.</summary>
    public void Bind(int index, TerminalPage page, bool selected)
    {
        _index = index;
        _from.Text = page.From;
        _subject.Text = page.Subject;
        ThemeTypeVariation = selected ? "ListRowSelected" : "ListRow";
    }
}
