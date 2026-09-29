// Vendor prices: Haggler, reputation, and stolen goods (openspec/changes/inventory-and-equipment,
// design section 6).

namespace Undercity.Core.Tests.Economy;

public class PricingTests
{
    [Fact]
    public void Kessler_sells_the_Kestrel_for_300_and_255_with_Haggler()
    {
        var s = TestData.NewGame();
        Assert.Equal(300, s.BuyPrice("kessler", "pistol"));
        s.Character.Raise(Undercity.Core.Progression.Skill.Persuasion);
        s.Character.Raise(Undercity.Core.Progression.Skill.Persuasion);
        Assert.True(s.BuyPrice("kessler", "pistol") == 255, "Haggler (Persuasion 2) takes 15 % off");
    }

    [Fact]
    public void A_liked_faction_takes_ten_percent_off_its_vendors()
    {
        var s = TestData.NewGame();
        s.Reputation.Change("residents", 20, 1.0);
        Assert.Equal(270, s.BuyPrice("kessler", "pistol"));
    }

    [Fact]
    public void A_stolen_data_shard_sells_for_18_on_the_black_market_and_not_at_all_to_Kessler()
    {
        var s = TestData.NewGame();
        Assert.Equal(18, s.SellPrice("oracle", "data_shard", stolen: true));
        Assert.Null(s.SellPrice("kessler", "data_shard", stolen: true));
        Assert.Equal(24, s.SellPrice("kessler", "data_shard"));
    }

    [Fact]
    public void Selling_to_the_black_market_takes_clean_and_stolen_at_their_own_rates()
    {
        var s = TestData.NewGame();
        s.PickUp("data_shard", 1);
        s.PickUp("data_shard", 2, stolenFrom: "residents");
        var before = s.Inventory.Credits;
        Assert.Equal(24 + 2 * 18, s.SellAll("oracle", "data_shard"));
        Assert.Equal(before + 60, s.Inventory.Credits);
        Assert.False(s.Inventory.Pack.Has("data_shard"));
    }

    [Fact]
    public void A_vendor_sells_no_more_than_its_stock_until_a_restock()
    {
        var s = TestData.NewGame();
        s.Inventory.Earn(10_000);
        Assert.True(s.Buy("kessler", "pistol"));
        Assert.Equal(0, s.InStock("kessler", "pistol"));
        Assert.False(s.Buy("kessler", "pistol"));
    }

    [Fact]
    public void Stock_behind_a_mission_flag_is_not_for_sale_before_it()
    {
        var s = TestData.NewGame();
        Assert.Equal(0, s.InStock("kessler", "whisper"));
        s.World.SetFlag("m1_done");
        Assert.Equal(1, s.InStock("kessler", "whisper"));
    }

    [Fact]
    public void A_box_is_bought_whole_with_one_line_in_the_feed()
    {
        var s = TestData.NewGame();
        var lines = new List<string>();
        s.Feed += lines.Add;
        var rounds = s.Inventory.Pack.Count("ammo_10mm");
        Assert.True(s.Buy("kessler", "ammo_10mm", 12));
        Assert.Equal(rounds + 12, s.Inventory.Pack.Count("ammo_10mm"));
        Assert.Equal("10mm rounds x12: -24 cr", Assert.Single(lines));
    }

    [Fact]
    public void A_box_the_runner_cant_pay_for_in_full_changes_nothing()
    {
        var s = TestData.NewGame();
        s.Inventory.Spend(s.Inventory.Credits - 20);
        var rounds = s.Inventory.Pack.Count("ammo_10mm");
        Assert.False(s.Buy("kessler", "ammo_10mm", 12));
        Assert.Equal(20, s.Inventory.Credits);
        Assert.Equal(rounds, s.Inventory.Pack.Count("ammo_10mm"));
    }
}
