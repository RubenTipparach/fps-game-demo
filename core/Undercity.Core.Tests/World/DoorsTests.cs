// The sliding entrances' timings (openspec/changes/hub-doorways, design section 3.3; owner K2):
// the shipped data/doors.json, and what validation refuses; and the hub's door approaches, where
// the placement test starts its walks.

using Undercity.Core.Data;
using Undercity.Core.World;

namespace Undercity.Core.Tests.World;

public sealed class DoorsTests
{
    private static string ShippedText() =>
        string.Join("\n", File.ReadAllLines(Path.Combine(TestData.RepoRoot, "game", "data", "doors.json"))
            .Where(l => !l.TrimStart().StartsWith("//", StringComparison.Ordinal)));

    private static List<string> Errors(string json)
    {
        var errors = new List<string>();
        JsonData.Parse<DoorsTable>(json, "doors.json").Validate(errors);
        return errors;
    }

    [Fact]
    public void A_person_opens_an_entrance_well_before_reaching_it()
    {
        var d = TestData.Data.Doors.Sliding;
        // At a walk (1.5 m/s) the leaves have NpcTriggerRadiusM / 1.5 s; a 1.55 m leaf needs 1.55 / speed.
        Assert.True(d.NpcTriggerRadiusM / 1.5 > 1.55 / d.SpeedMps,
            "a walker reaches the doorway only after its widest leaf is open, so nobody stops at a closed entrance");
        Assert.True(d.NpcTriggerRadiusM <= d.TriggerRadiusM, "the runner, who moves fastest, is noticed furthest out");
    }

    [Fact]
    public void A_door_that_never_moves_is_refused()
    {
        Assert.Empty(Errors(ShippedText()));
        var errors = Errors(ShippedText().Replace("\"speed_mps\": 2.4", "\"speed_mps\": 0", StringComparison.Ordinal));
        Assert.Contains(errors, e => e.Contains("sliding.speed_mps", StringComparison.Ordinal));
    }

    [Fact]
    public void Every_exterior_door_of_the_hub_has_an_approach_to_walk_from()
    {
        var hub = TestData.Data.Levels["hub"];
        // 21 exterior doors in the enterable buildings and the three shells' entrances (design section 3.7).
        Assert.Equal(24, hub.Approaches.Count);
        Assert.Equal(18, hub.Approaches.Count(a => a.Kind == "entrance"));
        var fishHall = hub.Approaches.Single(a => a.Door == "fish_hall:0");
        // 1 m outside the north entrance at (174, 76), whose wall faces north (-y).
        Assert.Equal((174.0, 75.0), (fishHall.At[0], fishHall.At[1]));
    }

    [Fact]
    public void A_misspelt_knob_is_refused()
    {
        Assert.Throws<DataException>(() => JsonData.Parse<DoorsTable>(
            ShippedText().Replace("\"wait_s\"", "\"wait\"", StringComparison.Ordinal), "doors.json"));
    }
}
