// Health regenerates only up to a floor (owner B1: a 25 % floor).

using Undercity.Core.Vitals;

namespace Undercity.Core.Tests.Vitals;

public class FloorPoolTests
{
    private static FloorPool Health() => new(100, new FloorRegen(25, 2, 5));

    [Fact]
    public void Health_below_the_floor_climbs_back_to_it_after_the_delay()
    {
        var h = Health();
        h.Lose(90);
        h.Tick(4.9);
        Assert.Equal(10, h.Value, 6);
        for (var i = 0; i < 200; i++)
        {
            h.Tick(0.1);
        }
        Assert.True(h.Value == 25, "regeneration stops at the floor, 25 % of 100");
    }

    [Fact]
    public void Health_above_the_floor_does_not_regenerate()
    {
        var h = Health();
        h.Lose(60);
        h.Tick(60);
        Assert.Equal(40, h.Value, 6);
    }

    [Fact]
    public void Damage_restarts_the_delay()
    {
        var h = Health();
        h.Lose(95);
        h.Tick(4);
        h.Lose(1);
        h.Tick(4);
        Assert.Equal(4, h.Value, 6);
    }
}
