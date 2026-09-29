// The character lighting table (openspec/changes/character-lighting, design section 7): the
// shipped data/character_lighting.json, the gels each district takes, and what validation refuses.

using Undercity.Core.Data;
using Undercity.Core.World;

namespace Undercity.Core.Tests.World;

public sealed class CharacterLightingTests
{
    private static CharacterLightingTable Shipped => TestData.Data.CharacterLighting;

    private static CharacterLightingTable Parse(string json)
    {
        var table = JsonData.Parse<CharacterLightingTable>(json, "character_lighting.json");
        var errors = new List<string>();
        table.Validate(errors);
        if (errors.Count > 0)
        {
            throw new DataException("character_lighting.json", string.Join("; ", errors));
        }
        return table;
    }

    private static string ShippedText() =>
        string.Join("\n", File.ReadAllLines(Path.Combine(TestData.RepoRoot, "game", "data", "character_lighting.json"))
            .Where(l => !l.TrimStart().StartsWith("//", StringComparison.Ordinal)));

    [Fact]
    public void Every_hub_district_has_a_rim_and_an_accent_gel()
    {
        foreach (var district in new[] { "lantern_row", "sump_market", "tin_stacks", "kiln", "drydock", "spire_foundations" })
        {
            Assert.True(Shipped.Gels.TryGetValue(district, out var pair) && pair.Count == 2, $"{district} has its gels");
        }
    }

    [Fact]
    public void The_rim_takes_the_districts_gel_and_the_accent_its_complement()
    {
        var c = Shipped.Conversation;
        Assert.Equal("magenta", Shipped.RoleFor(c.Rim, "lantern_row"));
        Assert.Equal("cyan", Shipped.RoleFor(c.Accent, "lantern_row"));
        Assert.Equal("key_warm", Shipped.RoleFor(c.Key, "lantern_row"));
    }

    [Fact]
    public void A_colour_role_reads_as_its_hex()
    {
        var (r, g, b) = Shipped.Rgb("key_warm");
        Assert.Equal((1.0, 0xe2 / 255.0, 0xc4 / 255.0), (r, g, b));
    }

    [Fact]
    public void A_light_naming_an_unknown_colour_is_refused()
    {
        var ex = Assert.Throws<DataException>(() => Parse(ShippedText().Replace("\"color\": \"deck_glow\"", "\"color\": \"deck_glo\"", StringComparison.Ordinal)));
        Assert.Contains("wrist.color", ex.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_key_without_a_cone_is_refused()
    {
        var ex = Assert.Throws<DataException>(() => Parse(ShippedText().Replace("\"spot_angle_deg\": 35", "\"spot_angle_deg\": 0", StringComparison.Ordinal)));
        Assert.Contains("conversation.key is a spot", ex.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void The_world_layer_is_not_the_characters_layer()
    {
        var ex = Assert.Throws<DataException>(() => Parse(ShippedText().Replace("\"characters_layer\": 2", "\"characters_layer\": 1", StringComparison.Ordinal)));
        Assert.Contains("characters_layer", ex.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void The_key_goes_on_the_side_the_scene_is_lit_from()
    {
        var lights = new[] { new NearbyLight(Side: 3, DistanceM: 4, Energy: 2), new NearbyLight(Side: -2, DistanceM: 6, Energy: 2) };
        Assert.Equal("right", Shipped.KeySide(lights));
    }

    [Fact]
    public void A_light_beyond_the_motivation_radius_doesnt_count()
    {
        var far = Shipped.Conversation.MotivationRadiusM + 1;
        var lights = new[] { new NearbyLight(Side: 5, DistanceM: far, Energy: 50), new NearbyLight(Side: -1, DistanceM: 3, Energy: 1) };
        Assert.Equal("left", Shipped.KeySide(lights));
    }

    [Fact]
    public void Every_hub_district_takes_its_gels_by_where_it_is()
    {
        var hub = TestData.Data.Levels["hub"];
        Assert.Equal(hub.Districts.Select(d => d.Id).OrderBy(d => d, StringComparer.Ordinal),
            Shipped.Gels.Keys.OrderBy(d => d, StringComparer.Ordinal));
        // The Rusty Anchor (68-112 x 44-70) is on Lantern Row, as the design's gel table says.
        Assert.Equal("lantern_row", hub.DistrictAt(90, 57));
        Assert.Equal("sump_market", hub.DistrictAt(118, 97));
        Assert.Null(hub.DistrictAt(203, 60));     // the Cut, between districts
    }

    [Fact]
    public void A_speaker_between_districts_takes_the_nearest_ones_gels()
    {
        var hub = TestData.Data.Levels["hub"];
        Assert.Equal("drydock", hub.DistrictNear(211, 60));     // the Cut's east quay, 2 m from the dry dock
        Assert.Equal("sump_market", hub.DistrictNear(118, 97)); // inside one: that one
    }
}
