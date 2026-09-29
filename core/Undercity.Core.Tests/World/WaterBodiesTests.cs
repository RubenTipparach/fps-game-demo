// Where water is and how deep a body is in it, against the hub's exported water
// (openspec/changes/archive/2026-09-29-water-and-swimming: "Water volumes come from the layout", "The player wades
// and swims").

using Undercity.Core.Vitals;
using Undercity.Core.World;

namespace Undercity.Core.Tests.World;

public class WaterBodiesTests
{
    private static IReadOnlyList<WaterBody> Hub => TestData.Data.Levels["hub"].Water;

    private static WaterTable Table => TestData.Data.Water;

    [Fact]
    public void The_hub_carries_the_cut_with_its_surface_and_bed_from_the_layout()
    {
        var cut = Hub.Single(w => w.Id == "the_cut");
        Assert.Equal(-2.2, cut.SurfaceM, 6);
        Assert.Equal(-4.5, cut.BedM, 6);
        Assert.Equal(3, Hub.Count);
    }

    [Fact]
    public void A_point_in_the_canal_is_in_the_cut_and_a_point_on_the_quay_is_not()
    {
        Assert.Equal("the_cut", WaterRules.At(Hub, 203, 100)?.Id);
        Assert.Null(WaterRules.At(Hub, 188, 100));
    }

    [Fact]
    public void A_floating_runner_swims()
    {
        var cut = WaterRules.At(Hub, 203, 100);
        // eyes 0.15 m above the surface, feet 1.62 m below the eyes
        Assert.Equal(WaterContact.Swimming, WaterRules.Contact(Table, cut, -2.05 - 1.62, -2.05));
    }

    [Fact]
    public void Eyes_under_the_surface_are_submerged()
    {
        var cut = WaterRules.At(Hub, 203, 100);
        Assert.Equal(WaterContact.Submerged, WaterRules.Contact(Table, cut, -4.5, -2.88));
    }

    [Fact]
    public void Chest_deep_water_is_wading_and_ankle_deep_is_dry()
    {
        var cut = WaterRules.At(Hub, 203, 100);
        Assert.Equal(WaterContact.Wading, WaterRules.Contact(Table, cut, -3.1, -1.48));
        Assert.Equal(WaterContact.Dry, WaterRules.Contact(Table, cut, -2.25, -0.63));
    }

    [Fact]
    public void Out_of_the_water_is_dry()
    {
        Assert.Equal(WaterContact.Dry, WaterRules.Contact(Table, null, -4.5, -2.88));
    }
}
