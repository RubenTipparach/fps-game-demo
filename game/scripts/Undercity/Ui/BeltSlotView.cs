// One belt slot (belt_slot.tscn): its key, the item's icon and the stack count, highlighted when
// it holds the drawn weapon. The HUD and the deck show the same slot.
//
// It lives in the UI layer as a thin view: which item sits on which slot is Inventory.Belt, and
// what is drawn is GameState.Drawn (CLAUDE.md 6.2).

#nullable enable
using System.Globalization;
using Godot;
using Undercity.Core.Items;

namespace Undercity.Client;

/// <summary>A belt slot.</summary>
public partial class BeltSlotView : PanelContainer
{
    /// <summary>The theme variation of an idle slot; a slot holding the drawn weapon uses this name plus "On".</summary>
    [Export] public string Style { get; set; } = "HudBeltSlot";

    private TextureRect _icon = null!;
    private Label _number = null!;
    private Label _count = null!;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _icon = GetNode<TextureRect>("%Icon");
        _number = GetNode<Label>("%Number");
        _count = GetNode<Label>("%Count");
    }

    /// <summary>Shows slot <paramref name="slot"/> (0-9) holding <paramref name="item"/> (null when empty), <paramref name="count"/> carried.</summary>
    public void Bind(int slot, ItemDef? item, int count, bool drawn)
    {
        _number.Text = UiKeys.RowLabel(slot);
        _number.ThemeTypeVariation = drawn ? "MonoSmallOn" : "MonoSmall";
        _icon.Texture = item is null ? null : ItemIcons.For(item);
        _count.Text = item is not null && count > 1 ? count.ToString(CultureInfo.InvariantCulture) : "";
        ThemeTypeVariation = drawn ? Style + "On" : Style;
    }
}
