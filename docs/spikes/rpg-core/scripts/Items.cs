using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;
using Godot;

namespace Brushfire;

public enum ItemCategory { Weapon, Ammo, Consumable, Gadget, Clothing, Armor, Key, Quest, Valuable }

public enum EquipSlot { None, Head, Face, Body, Armor, Boots }

/// <summary>
/// One item type, loaded from res://data/items.json (written and validated by
/// tools/rpg/build_items.py). Sizes are grid cells; clothing carries a faction tag and a cover
/// value for disguises.
/// </summary>
public class ItemDef
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public string Desc { get; set; } = "";
    public ItemCategory Cat { get; set; }
    public int W { get; set; } = 1;
    public int H { get; set; } = 1;
    public int Stack { get; set; } = 1;
    public int Value { get; set; }
    public string Icon { get; set; } = "";
    public string Model { get; set; } = "";
    public EquipSlot Slot { get; set; }
    public string Faction { get; set; } = "";
    public int Cover { get; set; }
    public int Armor { get; set; }
    public float Noise { get; set; } = 1f;
    /// <summary>Weapon node name in the viewmodel (Weapon.ItemId matches the item id).</summary>
    public string Weapon { get; set; } = "";
    /// <summary>For ammo items: the AmmoType they feed.</summary>
    public string AmmoType { get; set; } = "";
    public int Heal { get; set; }
    /// <summary>"lockpick", "multitool" or a throwable kind ("emp", "frag", "noise").</summary>
    public string Tool { get; set; } = "";
    public bool Droppable { get; set; } = true;

    [JsonIgnore] public bool Stackable => Stack > 1;
    [JsonIgnore] public bool Equippable => Slot != EquipSlot.None;
    [JsonIgnore] public bool Beltable => Cat is ItemCategory.Weapon or ItemCategory.Gadget or ItemCategory.Consumable;

    Texture2D _icon;
    [JsonIgnore]
    public Texture2D IconTexture
    {
        get
        {
            if (_icon == null && !string.IsNullOrEmpty(Icon) && ResourceLoader.Exists(Icon))
                _icon = GD.Load<Texture2D>(Icon);
            return _icon;
        }
    }

    public Brushfire.AmmoType? AmmoKind =>
        System.Enum.TryParse<Brushfire.AmmoType>(AmmoType, true, out var t) ? t : null;
}

public static class ItemDb
{
    static Dictionary<string, ItemDef> _items;

    public static readonly JsonSerializerOptions Json = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        PropertyNameCaseInsensitive = true,
        Converters = { new JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseLower) },
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
    };

    public static IReadOnlyDictionary<string, ItemDef> All
    {
        get
        {
            Load();
            return _items;
        }
    }

    public static ItemDef Get(string id)
    {
        Load();
        if (id != null && _items.TryGetValue(id, out var def))
            return def;
        GD.PushWarning($"[ItemDb] unknown item '{id}'");
        return null;
    }

    public static bool Exists(string id)
    {
        Load();
        return id != null && _items.ContainsKey(id);
    }

    static void Load()
    {
        if (_items != null)
            return;
        _items = new Dictionary<string, ItemDef>();
        string text = FileAccess.GetFileAsString("res://data/items.json");
        if (string.IsNullOrEmpty(text))
        {
            GD.PushError("[ItemDb] res://data/items.json missing");
            return;
        }
        var list = JsonSerializer.Deserialize<List<ItemDef>>(text, Json);
        foreach (var d in list)
            _items[d.Id] = d;
    }
}
