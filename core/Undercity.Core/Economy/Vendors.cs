// Vendors and prices (data/vendors.json).
//
// It lives in the core because the price a dialog line shows and the price the wallet is charged
// must come from one rule (CLAUDE.md 5.1): value x vendor x Haggler x reputation.

using Undercity.Core.Data;
using Undercity.Core.Factions;
using Undercity.Core.Items;

namespace Undercity.Core.Economy;

/// <summary>One line of a vendor's stock.</summary>
public sealed class StockLine
{
    /// <summary>The item id.</summary>
    public required string Item { get; init; }

    /// <summary>How many until the next restock.</summary>
    public required int Count { get; init; }

    /// <summary>A story flag that must be set before it's for sale, or null.</summary>
    public string? RequiresFlag { get; init; }
}

/// <summary>One vendor.</summary>
public sealed class VendorDef
{
    /// <summary>The id, such as <c>kessler</c>.</summary>
    public required string Id { get; init; }

    /// <summary>The shop's name.</summary>
    public required string Name { get; init; }

    /// <summary>The faction whose reputation sets the price, or null.</summary>
    public string? Faction { get; init; }

    /// <summary>Multiplier on the item value when selling to the runner.</summary>
    public required double BuyMult { get; init; }

    /// <summary>True when the vendor buys the runner's loot.</summary>
    public bool Buys { get; init; }

    /// <summary>True when the vendor buys stolen goods (the black market).</summary>
    public bool BuysStolen { get; init; }

    /// <summary>What's for sale.</summary>
    public IReadOnlyList<StockLine> Stock { get; init; } = Array.Empty<StockLine>();
}

/// <summary>data/vendors.json.</summary>
public sealed class VendorTable : IValidated
{
    /// <summary>What a vendor pays, as a fraction of value.</summary>
    public required double SellMult { get; init; }

    /// <summary>What the black market pays for stolen goods, as a fraction of value.</summary>
    public required double StolenSellMult { get; init; }

    /// <summary>The vendors.</summary>
    public required IReadOnlyList<VendorDef> Vendors { get; init; }

    /// <summary>The vendor with this id.</summary>
    public VendorDef Get(string id) => Vendors.First(v => v.Id == id);

    /// <summary>True when the vendor exists.</summary>
    public bool Exists(string id) => Vendors.Any(v => v.Id == id);

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        if (SellMult is <= 0 or > 1 || StolenSellMult is <= 0 or > 1)
        {
            errors.Add("sell_mult and stolen_sell_mult must be between 0 and 1");
        }
        foreach (var v in Vendors)
        {
            if (v.BuyMult <= 0)
            {
                errors.Add($"vendors.{v.Id}: buy_mult must be positive");
            }
            foreach (var s in v.Stock.Where(s => s.Count < 1))
            {
                errors.Add($"vendors.{v.Id}.{s.Item}: count must be at least 1");
            }
        }
    }
}

/// <summary>The one price rule.</summary>
public static class Pricing
{
    /// <summary>
    /// What the runner pays: value x vendor multiplier x <paramref name="buyPerkMult"/> (Haggler)
    /// x the reputation multiplier, rounded half away from zero, at least 1 for a valued item.
    /// </summary>
    public static int Buy(ItemDef item, VendorDef vendor, double buyPerkMult, Reputation reputation)
    {
        var price = item.Value * vendor.BuyMult * buyPerkMult * reputation.PriceMult(vendor.Faction);
        return item.Value == 0 ? 0 : Math.Max(1, (int)Math.Round(price, MidpointRounding.AwayFromZero));
    }

    /// <summary>
    /// What the vendor pays for an item, or null when they won't buy it: they don't buy at all, or
    /// it's stolen and they aren't the black market. Stolen goods sell at the stolen rate; anything
    /// else at the sell rate x <paramref name="sellPerkMult"/> (Haggler). Rounded down.
    /// </summary>
    public static int? Sell(ItemDef item, bool stolen, VendorDef vendor, VendorTable table, double sellPerkMult)
    {
        if (!vendor.Buys || item.Value <= 0 || item.Category is ItemCategory.Quest or ItemCategory.Key)
        {
            return null;
        }
        if (stolen)
        {
            return vendor.BuysStolen ? (int)Math.Floor(item.Value * table.StolenSellMult) : null;
        }
        return (int)Math.Floor(item.Value * table.SellMult * sellPerkMult);
    }
}
