// The deck's Inventory tab: the 10 x 6 pack grid, the five equipment slots with the disguise
// summary, the selected item's detail panel and the belt row.
//
// It lives in the UI layer as a thin view: every change it makes is a core call (GameState.Use,
// Inventory.Equip, Unequip and SetBelt, Pack.Move and RemoveStack), and every number it shows is
// the core's, including Cover and the disguise verdict (CLAUDE.md 5.1, 6.2).

#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using Godot;
using Undercity.Core.Items;
using Undercity.Core.Kit;
using Undercity.Core.Perception;

namespace Undercity.Client;

/// <summary>The Inventory tab.</summary>
public partial class InventoryPage : VBoxContainer, IWired
{
    private const string DragKind = "undercity_pack_stack";

    private static readonly EquipSlot[] Slots = { EquipSlot.Head, EquipSlot.Face, EquipSlot.Body, EquipSlot.Armor, EquipSlot.Boots };

    /// <summary>One cell of the grid's background (pack_cell.tscn).</summary>
    [Export] public PackedScene CellScene { get; set; } = null!;

    /// <summary>One stack in the grid (pack_item.tscn).</summary>
    [Export] public PackedScene ItemScene { get; set; } = null!;

    /// <summary>Pixels per pack cell. The grid panel in deck.tscn is sized for it: 10 x 6 cells plus a 1 px border.</summary>
    [Export] public int CellPx { get; set; } = 48;

    private Services? _services;
    private GridContainer _cells = null!;
    private Control _items = null!;
    private ItemDetailView _detail = null!;
    private Label _disguiseMain = null!;
    private Label _disguiseSub = null!;
    private readonly List<Label> _worn = new();
    private BeltSlotView[] _belt = Array.Empty<BeltSlotView>();
    private PackItem? _selected;
    private PackItem? _dragging;
    private bool _dirty = true;
    private bool _queued;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _cells = GetNode<GridContainer>("%Cells");
        _items = GetNode<Control>("%Items");
        _detail = GetNode<ItemDetailView>("%Detail");
        _disguiseMain = GetNode<Label>("%DisguiseMain");
        _disguiseSub = GetNode<Label>("%DisguiseSub");
        _belt = GetNode<Control>("%DeckBelt").GetChildren().OfType<BeltSlotView>().ToArray();
        foreach (var slot in Slots)
        {
            var button = GetNode<Button>($"%Slot{slot}");
            button.Pressed += () => Unequip(slot);
            _worn.Add(button.GetNode<Label>("Row/Worn"));
        }
        _detail.UseRequested += UseSelected;
        _detail.EquipRequested += EquipSelected;
        _detail.DropRequested += DropSelected;
        _items.SetDragForwarding(new Callable(), Callable.From<Vector2, Variant, bool>(CanDrop), Callable.From<Vector2, Variant>(Drop));
        VisibilityChanged += () =>
        {
            if (_dirty && IsVisibleInTree())
            {
                Refresh();
            }
        };
    }

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _services = services;
        var pack = services.State.Inventory.Pack;
        _cells.Columns = pack.Cols;
        for (var i = 0; i < pack.Cols * pack.Rows; i++)
        {
            _cells.AddChild(CellScene.Instantiate());
        }
        services.State.Inventory.Changed += MarkDirty;
        services.State.LoadoutChanged += MarkDirty;
        services.State.Character.Changed += MarkDirty;
        MarkDirty();
    }

    /// <inheritdoc/>
    public override void _ExitTree()
    {
        if (_services is not null)
        {
            _services.State.Inventory.Changed -= MarkDirty;
            _services.State.LoadoutChanged -= MarkDirty;
            _services.State.Character.Changed -= MarkDirty;
        }
    }

    /// <inheritdoc/>
    public override void _UnhandledInput(InputEvent e)
    {
        if (_services is null || _selected is null || !IsVisibleInTree() || UiKeys.Row(e) is not { } slot)
        {
            return;
        }
        _services.State.Inventory.SetBelt(slot, _selected.Def.Id);
        GetViewport().SetInputAsHandled();
    }

    // Deferred to the end of the frame: a change can come from inside a tile's own click or drop,
    // and the tiles are rebuilt by the refresh.
    private void MarkDirty()
    {
        _dirty = true;
        if (!_queued)
        {
            _queued = true;
            Callable.From(() =>
            {
                _queued = false;
                if (_dirty && IsInstanceValid(this) && IsVisibleInTree())
                {
                    Refresh();
                }
            }).CallDeferred();
        }
    }

    /// <summary>Redraws the grid, the slots, the disguise summary, the detail and the belt from the state.</summary>
    public void Refresh()
    {
        if (_services is null)
        {
            return;
        }
        _dirty = false;
        var s = _services.State;
        var inv = s.Inventory;
        if (_selected is not null && !inv.Pack.Stacks.Contains(_selected))
        {
            _selected = null;
        }
        foreach (var old in _items.GetChildren())
        {
            _items.RemoveChild(old);
            old.QueueFree();
        }
        foreach (var stack in inv.Pack.Stacks)
        {
            var tile = ItemScene.Instantiate<PackItemView>();
            _items.AddChild(tile);
            tile.Bind(stack, CellPx, stack == _selected);
            tile.Pressed += () => Select(stack);
            tile.SetDragForwarding(
                Callable.From<Vector2, Variant>(_ => StartDrag(tile)),
                Callable.From<Vector2, Variant, bool>((at, data) => CanDrop(tile.Position + at, data)),
                Callable.From<Vector2, Variant>((at, data) => Drop(tile.Position + at, data)));
        }
        for (var i = 0; i < Slots.Length; i++)
        {
            _worn[i].Text = inv.WornIn(Slots[i])?.Def.Name ?? "-";
        }
        RefreshDisguise();
        _detail.Bind(_selected, s.Data);
        for (var i = 0; i < _belt.Length; i++)
        {
            var id = i < inv.Belt.Count ? inv.Belt[i] : null;
            _belt[i].Bind(i, id is null ? null : s.Data.Items.Get(id), id is null ? 0 : inv.Pack.Count(id), id is not null && id == s.Drawn);
        }
    }

    private void RefreshDisguise()
    {
        var s = _services!.State;
        var faction = s.Inventory.OutfitFaction;
        if (faction is null)
        {
            _disguiseMain.Text = "NOT DISGUISED";
            _disguiseSub.Text = s.Inventory.WornIn(EquipSlot.Body) is { } body ? $"{body.Def.Name}: no faction" : "No outfit";
            return;
        }
        var cover = DisguiseRules.Cover(s.Character, s.Inventory);
        _disguiseMain.Text = UiText.Invariant($"{UiText.Faction(s.Data, faction).ToUpperInvariant()}  Q {s.Inventory.DisguiseQuality}  COVER {cover}");
        // Up close: the sharpest observer the core's own verdict accepts in conversation.
        var best = Enumerable.Range(1, 5)
            .LastOrDefault(i => s.Judge(new Observer(faction, i), new Situation(0, Talking: true)).Verdict == Verdict.Accepted);
        _disguiseSub.Text = best > 0
            ? UiText.Invariant($"up close: up to I {best}")
            : s.Judge(new Observer(faction, 1), new Situation(0, Talking: true)).Reason;
    }

    private void Select(PackItem stack)
    {
        _selected = stack;
        foreach (var tile in _items.GetChildren().OfType<PackItemView>())
        {
            if (tile.Stack is { } shown)
            {
                tile.Bind(shown, CellPx, shown == stack);
            }
        }
        _detail.Bind(_selected, _services!.State.Data);
    }

    private void Unequip(EquipSlot slot)
    {
        if (_services is null || _services.State.Inventory.WornIn(slot) is null)
        {
            return;
        }
        if (!_services.State.Inventory.Unequip(slot))
        {
            _services.State.Say("No room in the pack.");
        }
    }

    private void UseSelected()
    {
        if (_services is not null && _selected is not null)
        {
            _services.State.Use(_selected);
        }
    }

    private void EquipSelected()
    {
        if (_services is not null && _selected is not null && !_services.State.Inventory.Equip(_selected))
        {
            _services.State.Say("No room in the pack.");
        }
    }

    private void DropSelected()
    {
        if (_services is null || _selected is not { } stack)
        {
            return;
        }
        if (_services.State.Inventory.Pack.RemoveStack(stack))
        {
            _services.Level.DropAtPlayer(stack.Def.Id, stack.Count, stack.StolenFrom);
        }
    }

    // ------------------------------------------------------------------ drag and drop (Pack.Move)

    private Variant StartDrag(PackItemView tile)
    {
        if (tile.Stack is null)
        {
            return default;
        }
        _dragging = tile.Stack;
        // The preview's top-left follows the pointer, so a drop puts the stack's top-left cell under it.
        var preview = ItemScene.Instantiate<PackItemView>();
        preview.Modulate = new Color(1, 1, 1, 0.75f);
        preview.MouseFilter = MouseFilterEnum.Ignore;
        tile.SetDragPreview(preview);
        preview.Bind(tile.Stack, CellPx, false);
        return DragKind;
    }

    private bool CanDrop(Vector2 at, Variant data) =>
        _dragging is not null && data.VariantType == Variant.Type.String && data.AsString() == DragKind;

    private void Drop(Vector2 at, Variant data)
    {
        if (_services is null || _dragging is not { } stack || !CanDrop(at, data))
        {
            return;
        }
        _dragging = null;
        var x = Mathf.FloorToInt(at.X / CellPx);
        var y = Mathf.FloorToInt(at.Y / CellPx);
        _services.State.Inventory.Pack.Move(stack, x, y);
    }
}
