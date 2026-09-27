// Equipment and the belt (openspec/changes/inventory-and-equipment).

using Undercity.Core.Items;
using Undercity.Core.Kit;

namespace Undercity.Core.Tests.Kit;

public class InventoryTests
{
    private static ItemDef Item(string id) => TestData.Data.Items.Get(id);

    [Fact]
    public void A_swap_is_refused_when_the_old_item_wont_fit_back()
    {
        var inv = new Inventory(TestData.Data.Items);
        inv.Wear(Item("kings_goggles"));
        inv.Pack.Add(Item("sanitation_cap"), 1);
        inv.Pack.Add(Item("silver_lighter"), 59);
        var cap = inv.Pack.Stacks.First(s => s.Def.Id == "sanitation_cap");
        Assert.False(inv.Equip(cap), "the goggles are 2 x 1 and the cap frees only one cell");
        Assert.Equal("kings_goggles", inv.WornIn(EquipSlot.Head)!.Def.Id);
        Assert.True(inv.Pack.Has("sanitation_cap"));
    }

    [Fact]
    public void Wearing_from_the_pack_puts_the_old_outfit_back_in_the_pack()
    {
        var inv = new Inventory(TestData.Data.Items);
        inv.Wear(Item("street_jacket"));
        inv.Pack.Add(Item("rat_jacket"), 1);
        Assert.True(inv.Equip(inv.Pack.Stacks[0]));
        Assert.Equal("drain_rats", inv.OutfitFaction);
        Assert.True(inv.Pack.Has("street_jacket"));
    }

    [Fact]
    public void Credit_chips_become_credits_and_take_no_cell()
    {
        var inv = new Inventory(TestData.Data.Items);
        inv.PickUp(Item("credit_chip"), 4);
        Assert.Equal(100, inv.Credits);
        Assert.Empty(inv.Pack.Stacks);
    }
}
