// The hub's parked vehicles in the level data (openspec/changes/street-vehicles): one per car
// spot of the plan, each with a model, a place and a heading, and what validation refuses. The
// placement test finds each of them in the built level.

using Undercity.Core.World;

namespace Undercity.Core.Tests.World;

public sealed class ParkedCarsTests
{
    [Fact]
    public void Every_car_spot_of_the_hub_holds_a_parked_car()
    {
        var hub = TestData.Data.Levels["hub"];
        // 14 spots on the streets and the Kings' Garage bay (design section 4).
        Assert.Equal(15, hub.Cars.Count);
        Assert.Equal(10, hub.Cars.Select(c => c.Model).Distinct().Count());
        var errors = new List<string>();
        hub.Validate(errors);
        Assert.Empty(errors);
    }

    [Fact]
    public void A_car_with_no_place_is_refused()
    {
        var errors = new List<string>();
        new ParkedCarDef { Id = "001", Model = "taxi", At = [double.NaN, 3.0], HeadingDeg = 90.0 }.Validate("hub", errors);
        Assert.Contains(errors, e => e.Contains("cars.001: at", StringComparison.Ordinal));
    }
}
