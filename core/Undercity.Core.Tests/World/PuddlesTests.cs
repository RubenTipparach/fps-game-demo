// The hub's puddles (openspec/changes/archive/2026-09-30-street-puddles, "Puddles lie where water gathers"): every one
// lies in the rain by the core's own wetness rule, the same rule that dries a character under a
// roof, and a level's puddle data is refused when it is malformed.

using Undercity.Core.Data;
using Undercity.Core.World;

namespace Undercity.Core.Tests.World;

public sealed class PuddlesTests
{
    private static LevelDef Hub => TestData.Data.Levels["hub"];

    private static WetnessDef Rates => TestData.Data.CharacterLighting.Wetness;

    private static PuddleDef At(double x, double y, string kind = "gutter") => new()
    {
        Id = "forced_001",
        Kind = kind,
        At = [x, y],
        GroundM = 0,
        Poly = [[x - 1, y - 0.3], [x + 1, y - 0.3], [x + 1, y + 0.3], [x - 1, y + 0.3]],
    };

    private static List<string> Errors(PuddlesDef puddles)
    {
        var errors = new List<string>();
        puddles.Validate("hub", errors);
        return errors;
    }

    [Fact]
    public void Every_puddle_of_the_hub_lies_in_the_rain()
    {
        var puddles = Hub.Puddles!.List;
        // Survey L2: about 2.6 % of the ground, which the plan's rules make about 250 puddles.
        Assert.InRange(puddles.Count, 200, 320);
        var dry = puddles.Where(p => !p.InTheRain(Hub.Shelters, Rates)).Select(p => p.Id).ToList();
        Assert.True(dry.Count == 0, $"no rain falls under a roof, so no water stands there: {string.Join(", ", dry)}");
    }

    [Fact]
    public void A_puddle_under_the_skyway_is_under_a_roof()
    {
        var deck = Hub.Shelters.Single(s => s.Label == "Skyway deck");
        var (x, y) = (deck.Poly.Average(p => p[0]), deck.Poly.Average(p => p[1]));
        Assert.True(deck.Covers(x, y, 0, Rates.HeadroomM), "the deck's middle is under the deck");
        Assert.False(At(x, y).InTheRain(Hub.Shelters, Rates));
    }

    [Fact]
    public void The_mask_is_read_with_the_numbers_it_was_written_with()
    {
        var p = Hub.Puddles!;
        Assert.Equal("res://levels/undercity/hub/hub_puddles.png", p.Mask);
        // The whole hub, 240 x 170 m: tools/levels/puddle_mask.py writes a texel every 0.125 m over it.
        Assert.Equal((0.0, 0.0, 240.0, 170.0), (p.RectM[0], p.RectM[1], p.RectM[2], p.RectM[3]));
        Assert.Empty(Errors(p));
    }

    [Fact]
    public void A_puddle_of_an_unknown_kind_or_a_mask_over_nothing_is_refused()
    {
        var bad = new PuddlesDef
        {
            Mask = "res://levels/undercity/hub/hub_puddles.png",
            RectM = [0, 0, 0, 170],
            RangeM = 0.5,
            HeightM = [-1, 3],
            List = [At(10, 10, "pothole")],
        };
        var errors = Errors(bad);
        Assert.Contains(errors, e => e.Contains("puddles.rect_m", StringComparison.Ordinal));
        Assert.Contains(errors, e => e.Contains("forced_001: kind 'pothole'", StringComparison.Ordinal));
    }

    [Fact]
    public void A_misspelt_key_in_a_puddle_is_refused()
    {
        const string json = """{"id": "g", "kind": "gutter", "at": [1, 1], "ground": 0, "poly": [[0, 0], [2, 0], [2, 2]]}""";
        Assert.Throws<DataException>(() => JsonData.Parse<PuddleDef>(json, "hub.json"));
    }
}
