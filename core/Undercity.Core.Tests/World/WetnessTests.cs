// Dry indoors, wet in the rain (openspec/changes/character-lighting, design section 9; the owner,
// survey J1): the shelter rule on the hub's exported roofs, the wetness step's rates, and what
// validation refuses. The places are the hub's real ones: named NPCs from
// tools/levels/layouts/hub_entities.py, civilians from the level data's crowd block, ground
// heights from the plan (city_plan.py, ground_level).

using Undercity.Core.Data;
using Undercity.Core.World;

namespace Undercity.Core.Tests.World;

public sealed class WetnessTests
{
    private static LevelDef Hub => TestData.Data.Levels["hub"];

    private static WetnessDef Rates => TestData.Data.CharacterLighting.Wetness;

    private static bool Sheltered(double x, double y, double feetM) => Wetness.Sheltered(Hub.Shelters, x, y, feetM, Rates);

    [Fact]
    public void Tank_behind_the_Anchors_bar_is_under_a_roof_and_starts_dry()
    {
        // hub_entities.py: tank at (99.3, 55.5), between the counter and the back wall; the floor is 0.15.
        Assert.True(Sheltered(99.3, 55.5, 0.15), "the owner's case: Tank is indoors, so he is not wet");
        Assert.Equal(0, Wetness.Start(Sheltered(99.3, 55.5, 0.15)));
    }

    [Fact]
    public void Dace_at_the_checkpoint_gate_stands_in_the_rain_and_starts_soaked()
    {
        // hub_entities.py: dace at (169, 155.5), in front of the checkpoint on open ground at 0.
        Assert.False(Sheltered(169, 155.5, 0.0), "nothing is over the checkpoint's forecourt");
        Assert.Equal(1, Wetness.Start(Sheltered(169, 155.5, 0.0)));
    }

    [Fact]
    public void A_civilian_under_the_Skyway_is_dry()
    {
        var at = Hub.Crowd["hub:civ_16"].At;
        Assert.True(Sheltered(at[0], at[1], 0.05), "the Skyway's deck is a roof 13 m up");
        Assert.Contains(Hub.Shelters, s => s.Label == "Skyway deck" && s.Covers(at[0], at[1], 0.05, Rates.HeadroomM));
    }

    [Fact]
    public void Under_a_shop_awning_is_dry()
    {
        var awning = Hub.Shelters.First(s => s.Label == "shop awning");
        var x = awning.Poly.Average(p => p[0]);
        var y = awning.Poly.Average(p => p[1]);
        Assert.True(Sheltered(x, y, 0.0), $"the middle of the awning at ({x:0.0}, {y:0.0}) is under it");
    }

    [Fact]
    public void A_roof_never_shelters_the_people_standing_on_it()
    {
        // The Rusty Anchor's roof is 10 m up; the district's other roofs don't reach over it.
        Assert.True(Sheltered(90, 57, 0.15));
        Assert.False(Sheltered(90, 57, 10.0), "standing on the roof leaves no headroom under it");
    }

    [Fact]
    public void A_character_soaks_in_20_seconds_in_the_open()
    {
        Assert.Equal(0.5, Wetness.Step(0, sheltered: false, 10, Rates), 9);
        Assert.Equal(1, Wetness.Step(0, sheltered: false, 20, Rates), 9);
        Assert.Equal(1, Wetness.Step(0.9, sheltered: false, 100, Rates));
    }

    [Fact]
    public void A_civilian_who_runs_indoors_dries_over_240_seconds_not_at_once()
    {
        var w = 1.0;
        var t = 0.0;
        while (w > 0)
        {
            w = Wetness.Step(w, sheltered: true, Rates.UpdateS, Rates);
            t += Rates.UpdateS;
            Assert.True(t <= Rates.DryTimeS + Rates.UpdateS, "drying never runs past its time");
        }
        Assert.Equal(240, t, 6);
        Assert.Equal(0.5, Wetness.Step(1, sheltered: true, 120, Rates), 9);
    }

    [Fact]
    public void A_damaged_wetness_starts_again_from_the_place_and_time_never_runs_backwards()
    {
        Assert.Equal(0, Wetness.Step(double.NaN, sheltered: true, Rates.UpdateS, Rates));
        Assert.Equal(1, Wetness.Step(double.PositiveInfinity, sheltered: false, Rates.UpdateS, Rates));
        Assert.Equal(0.5, Wetness.Step(0.5, sheltered: true, -3, Rates));
        Assert.Equal(0.5, Wetness.Step(0.5, sheltered: false, double.NaN, Rates));
    }

    [Fact]
    public void Dry_skin_is_the_masks_roughness_plus_the_dry_add()
    {
        // Design section 9's table: the T-zone's 0.42 is the wet look; dry, it is 0.60.
        Assert.Equal(0.60, 0.42 + Rates.SkinDryRoughnessAdd, 9);
        Assert.Equal(0.45, Rates.ClothWetRoughness);
        Assert.Equal(0.8, Rates.ClothWetBrightness);
    }

    [Fact]
    public void A_wetness_block_with_no_drying_time_is_refused()
    {
        var text = string.Join("\n", File.ReadAllLines(Path.Combine(TestData.RepoRoot, "game", "data", "character_lighting.json"))
            .Where(l => !l.TrimStart().StartsWith("//", StringComparison.Ordinal)))
            .Replace("\"dry_time_s\": 240", "\"dry_time_s\": 0", StringComparison.Ordinal);
        var table = JsonData.Parse<CharacterLightingTable>(text, "character_lighting.json");
        var errors = new List<string>();
        table.Validate(errors);
        Assert.Contains(errors, e => e.Contains("wetness.dry_time_s", StringComparison.Ordinal));
    }

    [Fact]
    public void A_shelter_without_a_shape_or_a_height_is_refused()
    {
        var bad = new ShelterDef { Label = "awning", Poly = [[0.0, 0.0], [1.0, 0.0]], UnderM = double.NaN };
        var errors = new List<string>();
        bad.Validate("hub", 3, errors);
        Assert.Contains(errors, e => e.Contains("shelters[3] (awning): poly", StringComparison.Ordinal));
        Assert.Contains(errors, e => e.Contains("under_m", StringComparison.Ordinal));
    }

    [Fact]
    public void Every_hub_shelter_is_valid_and_the_hub_has_its_roofs()
    {
        var errors = new List<string>();
        for (var i = 0; i < Hub.Shelters.Count; i++)
        {
            Hub.Shelters[i].Validate("hub", i, errors);
        }
        Assert.Empty(errors);
        foreach (var label in new[] { "rusty_anchor", "fish_hall", "Skyway deck", "shop awning", "stall awning" })
        {
            Assert.Contains(Hub.Shelters, s => s.Label == label);
        }
    }
}
