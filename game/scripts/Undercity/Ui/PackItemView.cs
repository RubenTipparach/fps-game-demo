// One stack in the pack grid (pack_item.tscn): drawn at its cell, at its footprint, with its icon
// and stack count.
//
// It lives in the UI layer as a thin view of a core PackItem: where a stack sits and how many it
// holds are the pack's rules (CLAUDE.md 5.1); this only draws them.

#nullable enable
using System.Globalization;
using Godot;
using Undercity.Core.Items;
using Undercity.Core.Kit;

namespace Undercity.Client;

/// <summary>A stack in the pack grid.</summary>
public partial class PackItemView : Button
{
    private TextureRect _icon = null!;
    private Label _count = null!;

    /// <summary>The stack shown.</summary>
    public PackItem? Stack { get; private set; }

    /// <inheritdoc/>
    public override void _Ready()
    {
        _icon = GetNode<TextureRect>("%Icon");
        _count = GetNode<Label>("%Count");
    }

    /// <summary>Shows <paramref name="stack"/> at its cell of a grid of <paramref name="cellPx"/>-pixel cells.</summary>
    public void Bind(PackItem stack, int cellPx, bool selected)
    {
        Stack = stack;
        Position = new Vector2(stack.X * cellPx, stack.Y * cellPx);
        Size = new Vector2(stack.Def.W * cellPx - 1, stack.Def.H * cellPx - 1);
        _icon.Texture = ItemIcons.For(stack.Def);
        _count.Text = stack.Count > 1 ? stack.Count.ToString(CultureInfo.InvariantCulture) : "";
        ThemeTypeVariation = selected ? "PackItemSelected"
            : stack.Def.Category is ItemCategory.Quest or ItemCategory.Key ? "PackItemQuest"
            : "PackItem";
    }
}
