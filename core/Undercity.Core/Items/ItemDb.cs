// The item catalogue (data/items.json): every item's footprint, stack, value and effects.
//
// It lives in the core because the pack, equipment, vendors, dialog and saves all resolve item
// ids against it, and a dangling id must fail in a test, not in play
// (openspec/changes/inventory-and-equipment).

using Undercity.Core.Data;
using Undercity.Core.Progression;

namespace Undercity.Core.Items;

/// <summary>What kind of thing an item is.</summary>
public enum ItemCategory
{
    /// <summary>Drawn and used on the belt.</summary>
    Weapon,

    /// <summary>Loaded into weapons.</summary>
    Ammo,

    /// <summary>Grenades and throwables.</summary>
    Gadget,

    /// <summary>Lockpicks and multitools.</summary>
    Tool,

    /// <summary>Used up for an effect.</summary>
    Consumable,

    /// <summary>Worn in HEAD, FACE or BODY; may carry a faction.</summary>
    Clothing,

    /// <summary>Worn in ARMOR.</summary>
    Armor,

    /// <summary>Worn in BOOTS.</summary>
    Boots,

    /// <summary>Carried for a passive bonus.</summary>
    Trinket,

    /// <summary>Opens a lock.</summary>
    Key,

    /// <summary>A mission object.</summary>
    Quest,

    /// <summary>Sold for credits.</summary>
    Valuable,
}

/// <summary>An equipment slot.</summary>
public enum EquipSlot
{
    /// <summary>Hats, helmets, goggles.</summary>
    Head,

    /// <summary>Masks and respirators.</summary>
    Face,

    /// <summary>Outfits: the disguise base.</summary>
    Body,

    /// <summary>Vests and plates.</summary>
    Armor,

    /// <summary>Footwear.</summary>
    Boots,
}

/// <summary>What using an item does.</summary>
public sealed class UseEffect
{
    /// <summary>Health restored.</summary>
    public int Heal { get; init; }

    /// <summary>Seconds the heal takes; 0 is instant.</summary>
    public double HealTimeS { get; init; }

    /// <summary>Augmentation energy restored.</summary>
    public int Energy { get; init; }

    /// <summary>Skill points granted (a neural chip).</summary>
    public int SkillPoints { get; init; }
}

/// <summary>One item.</summary>
public sealed class ItemDef
{
    /// <summary>The stable id, snake_case.</summary>
    public required string Id { get; init; }

    /// <summary>The display name.</summary>
    public required string Name { get; init; }

    /// <summary>A line of description for the detail panel.</summary>
    public string Desc { get; init; } = "";

    /// <summary>The category.</summary>
    public required ItemCategory Category { get; init; }

    /// <summary>Footprint width in pack cells, 1 to 4 (0 for items that never enter the pack).</summary>
    public required int W { get; init; }

    /// <summary>Footprint height in pack cells, 1 to 3 (0 for items that never enter the pack).</summary>
    public required int H { get; init; }

    /// <summary>How many fit in one stack.</summary>
    public int Stack { get; init; } = 1;

    /// <summary>Base value in credits.</summary>
    public required int Value { get; init; }

    /// <summary>The slot it's worn in, for clothing, armour and boots.</summary>
    public EquipSlot? Slot { get; init; }

    /// <summary>The faction whose disguise it belongs to, or null.</summary>
    public string? Faction { get; init; }

    /// <summary>Its weight in disguise quality: BODY 2, HEAD 1, FACE 1.</summary>
    public int Disguise { get; init; }

    /// <summary>Damage resistance by damage type, in percent.</summary>
    public IReadOnlyDictionary<string, double> ResistPct { get; init; } = new Dictionary<string, double>();

    /// <summary>Whether this armour counts as light (Master of Disguise ignores the clash).</summary>
    public bool LightArmor { get; init; }

    /// <summary>Multiplier on footstep noise while worn.</summary>
    public double FootstepMult { get; init; } = 1;

    /// <summary>What using it does, for consumables.</summary>
    public UseEffect? Use { get; init; }

    /// <summary>The weapon it is, for weapons (a data/weapons.json id).</summary>
    public string? Weapon { get; init; }

    /// <summary>Skill bonuses while carried, such as +1 Persuasion.</summary>
    public IReadOnlyDictionary<Skill, int> SkillBonus { get; init; } = new Dictionary<Skill, int>();

    /// <summary>Picked up as credits instead of entering the pack.</summary>
    public bool CreditsOnPickup { get; init; }

    /// <summary>Which tool it is: <c>lockpick</c> or <c>multitool</c>, or null.</summary>
    public string? Tool { get; init; }

    /// <summary>True for items that stack.</summary>
    public bool Stackable => Stack > 1;

    /// <summary>True for items worn in a slot.</summary>
    public bool Wearable => Slot is not null;

    /// <summary>True for items that go on the belt when picked up.</summary>
    public bool AutoBelt => Category is ItemCategory.Weapon or ItemCategory.Gadget
        || Category == ItemCategory.Consumable && Use is { Heal: >= 25 };
}

/// <summary>data/items.json.</summary>
public sealed class ItemDb : IValidated
{
    private Dictionary<string, ItemDef>? _byId;

    /// <summary>Every item.</summary>
    public required IReadOnlyList<ItemDef> Items { get; init; }

    private Dictionary<string, ItemDef> ById => _byId ??= Items.ToDictionary(i => i.Id, StringComparer.Ordinal);

    /// <summary>The item with this id. Throws for an unknown id: data tests make that impossible.</summary>
    public ItemDef Get(string id) => ById.TryGetValue(id, out var d) ? d
        : throw new KeyNotFoundException($"unknown item '{id}'");

    /// <summary>True when the id exists.</summary>
    public bool Exists(string id) => ById.ContainsKey(id);

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        foreach (var dup in Items.GroupBy(i => i.Id).Where(g => g.Count() > 1))
        {
            errors.Add($"items: '{dup.Key}' appears {dup.Count()} times");
        }
        foreach (var i in Items)
        {
            var where = $"items.{i.Id}";
            if (i.CreditsOnPickup)
            {
                if (i.Value <= 0)
                {
                    errors.Add($"{where}: credits_on_pickup needs a value");
                }
                continue;
            }
            if (i.W is < 1 or > 4 || i.H is < 1 or > 3)
            {
                errors.Add($"{where}: footprint {i.W}x{i.H} is outside 1-4 x 1-3");
            }
            if (i.Stack < 1 || i.Value < 0)
            {
                errors.Add($"{where}: stack must be at least 1 and value not negative");
            }
            var wearable = i.Category is ItemCategory.Clothing or ItemCategory.Armor or ItemCategory.Boots;
            if (wearable != i.Slot.HasValue)
            {
                errors.Add($"{where}: clothing, armour and boots need a slot, and nothing else has one");
            }
            if (i.Category == ItemCategory.Armor && i.Slot != EquipSlot.Armor
                || i.Category == ItemCategory.Boots && i.Slot != EquipSlot.Boots)
            {
                errors.Add($"{where}: slot doesn't match the category");
            }
            if (i.Disguise != 0 && i.Faction is null)
            {
                errors.Add($"{where}: a disguise weight needs a faction");
            }
            if (i.Category == ItemCategory.Weapon && string.IsNullOrEmpty(i.Weapon))
            {
                errors.Add($"{where}: a weapon needs a weapon id");
            }
            if (i.ResistPct.Values.Any(v => v is < 0 or > 100) || !double.IsFinite(i.FootstepMult) || i.FootstepMult < 0)
            {
                errors.Add($"{where}: resist_pct or footstep_mult out of range");
            }
        }
    }
}
