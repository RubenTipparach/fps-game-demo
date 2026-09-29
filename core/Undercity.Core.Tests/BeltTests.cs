// The belt keys: draw and holster weapons, use consumables (openspec/changes/inventory-and-equipment).

namespace Undercity.Core.Tests;

public class BeltTests
{
    private static int SlotOf(GameState s, string id) => s.Inventory.Belt.ToList().IndexOf(id);

    [Fact]
    public void The_start_kit_puts_weapons_and_the_medkit_on_the_belt()
    {
        var s = TestData.NewGame();
        Assert.True(SlotOf(s, "pistol") >= 0);
        Assert.True(SlotOf(s, "medkit") >= 0);
    }

    [Fact]
    public void A_weapon_key_draws_and_the_same_key_holsters()
    {
        var s = TestData.NewGame();
        var slot = SlotOf(s, "pistol");
        Assert.Equal(BeltResult.Drawn, s.UseBelt(slot));
        Assert.Equal("pistol", s.Drawn);
        s.Tick(1.5);
        Assert.Equal(1.5, s.DrawnS, 6);
        Assert.Equal(BeltResult.Holstered, s.UseBelt(slot));
        Assert.Null(s.Drawn);
    }

    [Fact]
    public void A_medkit_at_full_health_is_refused_and_kept()
    {
        var s = TestData.NewGame();
        Assert.Equal(BeltResult.Refused, s.UseBelt(SlotOf(s, "medkit")));
        Assert.True(s.Inventory.Pack.Has("medkit"));
    }

    [Fact]
    public void A_medkit_heals_over_its_heal_time()
    {
        var s = TestData.NewGame();
        s.Health.Lose(60);
        Assert.Equal(BeltResult.Used, s.UseBelt(SlotOf(s, "medkit")));
        s.Tick(1);
        Assert.Equal(80, s.Health.Value, 6);
    }

    [Fact]
    public void A_bad_slot_does_nothing()
    {
        Assert.Equal(BeltResult.Empty, TestData.NewGame().UseBelt(12));
    }

    [Fact]
    public void Selling_the_drawn_weapon_holsters_it()
    {
        var s = TestData.NewGame();
        s.UseBelt(SlotOf(s, "pistol"));
        s.Inventory.Pack.Remove("pistol");
        Assert.Null(s.Drawn);
    }
}
