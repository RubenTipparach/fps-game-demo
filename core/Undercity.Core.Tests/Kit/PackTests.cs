// The 10 x 6 pack grid: first fit, stacking, and all-or-nothing adds (openspec/changes/inventory-and-equipment).

using Undercity.Core.Kit;

namespace Undercity.Core.Tests.Kit;

public class PackTests
{
    private static Items.ItemDef Item(string id) => TestData.Data.Items.Get(id);

    [Fact]
    public void Items_go_to_the_first_free_cell_reading_row_by_row()
    {
        var pack = new Pack();
        pack.Add(Item("pistol"), 1);
        pack.Add(Item("pistol"), 1);
        var second = pack.Stacks[1];
        Assert.Equal((2, 0), (second.X, second.Y));
    }

    [Fact]
    public void Ammo_tops_up_a_stack_before_starting_another()
    {
        var pack = new Pack();
        pack.Add(Item("ammo_10mm"), 50);
        pack.Add(Item("ammo_10mm"), 20);
        Assert.Equal(60, pack.Stacks[0].Count);
        Assert.Equal(10, pack.Stacks[1].Count);
    }

    [Fact]
    public void Stolen_and_clean_items_never_share_a_stack()
    {
        var pack = new Pack();
        pack.Add(Item("data_shard"), 1);
        pack.Add(Item("data_shard"), 1, stolenFrom: "residents");
        Assert.Equal(2, pack.Stacks.Count);
    }

    [Fact]
    public void A_full_pack_refuses_the_rest_and_changes_nothing_it_cant_finish()
    {
        var pack = new Pack();
        Assert.Equal(0, pack.Add(Item("rat_jacket"), 15));
        var before = pack.Stacks.Count;
        Assert.Equal(1, pack.Add(Item("rat_jacket"), 1));
        Assert.Equal(before, pack.Stacks.Count);
    }

    [Fact]
    public void An_add_that_only_partly_fits_reports_what_is_left()
    {
        var pack = new Pack();
        pack.Add(Item("rat_jacket"), 14);
        Assert.True(pack.Add(Item("pistol"), 3) == 2, "one 2 x 2 hole left: one pistol fits, two don't");
    }
}
