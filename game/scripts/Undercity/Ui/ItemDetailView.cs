// The deck's detail panel for the selected stack: its icon, name, category and footprint, count,
// value, what it does, and the Use, Equip and Drop buttons.
//
// It lives in the UI layer as a thin view: it prints the item's data and raises a request per
// button; the inventory page calls the core for each (GameState.Use, Inventory.Equip, Pack).

#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using Godot;
using Undercity.Core;
using Undercity.Core.Items;
using Undercity.Core.Kit;

namespace Undercity.Client;

/// <summary>The item detail panel.</summary>
public partial class ItemDetailView : PanelContainer
{
    private Control _body = null!;
    private Label _empty = null!;
    private TextureRect _icon = null!;
    private Label _name = null!;
    private Label _category = null!;
    private Label _count = null!;
    private Label _value = null!;
    private Label _worn = null!;
    private Label _effect = null!;
    private Label _stolen = null!;
    private Label _desc = null!;
    private Button _use = null!;
    private Button _equip = null!;
    private Button _drop = null!;

    /// <summary>Raised when Use is pressed.</summary>
    public event Action? UseRequested;

    /// <summary>Raised when Equip is pressed.</summary>
    public event Action? EquipRequested;

    /// <summary>Raised when Drop is pressed.</summary>
    public event Action? DropRequested;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _body = GetNode<Control>("%DetailBody");
        _empty = GetNode<Label>("%DetailEmpty");
        _icon = GetNode<TextureRect>("%DetailIcon");
        _name = GetNode<Label>("%DetailName");
        _category = GetNode<Label>("%DetailCategory");
        _count = GetNode<Label>("%CountValue");
        _value = GetNode<Label>("%ValueValue");
        _worn = GetNode<Label>("%WornValue");
        _effect = GetNode<Label>("%EffectValue");
        _stolen = GetNode<Label>("%StolenValue");
        _desc = GetNode<Label>("%DetailDesc");
        _use = GetNode<Button>("%Use");
        _equip = GetNode<Button>("%Equip");
        _drop = GetNode<Button>("%Drop");
        _use.Pressed += () => UseRequested?.Invoke();
        _equip.Pressed += () => EquipRequested?.Invoke();
        _drop.Pressed += () => DropRequested?.Invoke();
    }

    /// <summary>Shows <paramref name="stack"/>, or the empty line when null.</summary>
    public void Bind(PackItem? stack, GameData data)
    {
        _body.Visible = stack is not null;
        _empty.Visible = stack is null;
        if (stack is null)
        {
            return;
        }
        var def = stack.Def;
        _icon.Texture = ItemIcons.For(def);
        _name.Text = def.Name;
        _category.Text = UiText.Invariant($"{def.Category} · {def.W} x {def.H}");
        _count.Text = def.Stackable ? UiText.Invariant($"{stack.Count} / {def.Stack}") : "1";
        _value.Text = UiText.Invariant($"{def.Value} cr");
        Row(_worn, def.Slot is { } slot
            ? string.Join(" · ", new[] { slot.ToString(), UiText.Faction(data, def.Faction), def.Disguise > 0 ? UiText.Invariant($"Q {def.Disguise}") : "" }
                .Where(s => s.Length > 0))
            : "");
        Row(_effect, string.Join(", ", Effects(def, data)));
        Row(_stolen, UiText.Faction(data, stack.StolenFrom));
        _desc.Text = def.Desc;
        _use.Visible = def.Use is not null;
        _equip.Visible = def.Slot is not null;
    }

    private static void Row(Label value, string text)
    {
        value.Text = text;
        value.Visible = text.Length > 0;
        value.GetParent().GetNode<Control>(value.Name.ToString().Replace("Value", "Key", StringComparison.Ordinal)).Visible = text.Length > 0;
    }

    private static IEnumerable<string> Effects(ItemDef def, GameData data)
    {
        if (def.Use is { } use)
        {
            if (use.Heal > 0)
            {
                yield return use.HealTimeS > 0 ? UiText.Invariant($"+{use.Heal} health over {use.HealTimeS:0.#} s") : UiText.Invariant($"+{use.Heal} health");
            }
            if (use.Energy > 0)
            {
                yield return UiText.Invariant($"+{use.Energy} energy");
            }
            if (use.SkillPoints > 0)
            {
                yield return use.SkillPoints == 1 ? "+1 skill point" : UiText.Invariant($"+{use.SkillPoints} skill points");
            }
        }
        foreach (var (skill, bonus) in def.SkillBonus.OrderBy(kv => kv.Key))
        {
            yield return UiText.Invariant($"+{bonus} {data.Skills.Get(skill).Name}");
        }
        foreach (var (type, pct) in def.ResistPct.OrderBy(kv => kv.Key, StringComparer.Ordinal))
        {
            yield return UiText.Invariant($"{type} {pct:0} %");
        }
        if (def.FootstepMult != 1)
        {
            yield return UiText.Invariant($"footsteps x{def.FootstepMult:0.##}");
        }
    }

}
