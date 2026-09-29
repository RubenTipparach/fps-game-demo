// The crowd rule (openspec/changes/crowd-variety, "No lookalikes nearby" and "Civilians vary at
// runtime"): on the hub's real placements, with world seeds 1 to 100, no two civilians within
// 15 m share body and palette and no body is used more than three times; the same seed gives the
// same crowd; roles follow districts; umbrellas are for outdoors; and accessories never double up
// on a slot.

using Undercity.Core.Data;
using Undercity.Core.World;

namespace Undercity.Core.Tests.World;

public sealed class CrowdTests
{
    private static CrowdTable Table => TestData.Data.Crowd;

    private static IReadOnlyDictionary<string, CrowdPlace> Hub => TestData.Data.Levels["hub"].Crowd;

    private static IEnumerable<ulong> Seeds => Enumerable.Range(1, 100).Select(s => (ulong)s);

    [Fact]
    public void The_hub_places_every_civilian()
    {
        var civilians = TestData.Data.Levels["hub"].Npcs.Where(n => n.Value == "civ").Select(n => n.Key).OrderBy(k => k, StringComparer.Ordinal);
        Assert.Equal(civilians, Hub.Keys.OrderBy(k => k, StringComparer.Ordinal));
        Assert.Equal(31, Hub.Count);
    }

    [Fact]
    public void No_two_civilians_within_15_m_share_body_and_palette_for_seeds_1_to_100()
    {
        foreach (var seed in Seeds)
        {
            var looks = CrowdPicker.Assign(seed, Hub, Table);
            var ids = looks.Keys.OrderBy(k => k, StringComparer.Ordinal).ToArray();
            for (var i = 0; i < ids.Length; i++)
            {
                for (var j = i + 1; j < ids.Length; j++)
                {
                    var (a, b) = (looks[ids[i]], looks[ids[j]]);
                    if (a.Body == b.Body && a.Palette == b.Palette)
                    {
                        var d = CrowdPicker.Distance(Hub[ids[i]], Hub[ids[j]]);
                        Assert.True(d > Table.LookalikeRadiusM,
                            $"seed {seed}: {ids[i]} and {ids[j]} are twins ({a.Body}, {a.Palette}) {d:0.0} m apart");
                    }
                }
            }
        }
    }

    [Fact]
    public void No_body_is_used_more_than_three_times_for_seeds_1_to_100()
    {
        foreach (var seed in Seeds)
        {
            var worst = CrowdPicker.Assign(seed, Hub, Table).Values.GroupBy(l => l.Body).MaxBy(g => g.Count())!;
            Assert.True(worst.Count() <= Table.MaxPerBody, $"seed {seed}: {worst.Key} is used {worst.Count()} times");
        }
    }

    [Fact]
    public void The_same_seed_gives_the_same_crowd_whatever_order_the_places_come_in()
    {
        var once = CrowdPicker.Assign(7, Hub, Table);
        var reversed = Hub.Reverse().ToDictionary(p => p.Key, p => p.Value);
        var again = CrowdPicker.Assign(7, reversed, Table);
        foreach (var (sid, look) in once)
        {
            Assert.Equal(look.Body, again[sid].Body);
            Assert.Equal(look.Palette, again[sid].Palette);
            Assert.Equal(look.Accessories, again[sid].Accessories);
            Assert.Equal(look.Scale, again[sid].Scale);
            Assert.Equal(look.Idle, again[sid].Idle);
        }
    }

    [Fact]
    public void A_different_seed_gives_a_different_crowd()
    {
        var a = CrowdPicker.Assign(7, Hub, Table);
        var b = CrowdPicker.Assign(8, Hub, Table);
        Assert.True(a.Count(p => p.Value.Body != b[p.Key].Body) > Hub.Count / 2, "most civilians change body with the seed");
    }

    [Fact]
    public void Market_civilians_are_shoppers_and_dock_civilians_dockhands()
    {
        var looks = CrowdPicker.Assign(7, Hub, Table);
        foreach (var (sid, place) in Hub)
        {
            Assert.Equal(Table.RoleFor(place.District), looks[sid].Role);
        }
        Assert.Contains(looks.Values, l => l.Role == "shopper");
        Assert.Contains(looks.Values, l => l.Role == "dockhand");
    }

    [Fact]
    public void About_a_third_of_the_outdoor_civilians_who_may_carry_one_hold_an_umbrella_and_nobody_indoors()
    {
        int outdoor = 0, umbrellas = 0;
        foreach (var seed in Seeds)
        {
            var looks = CrowdPicker.Assign(seed, Hub, Table);
            foreach (var (sid, place) in Hub)
            {
                var carries = looks[sid].Accessories.Contains(Table.Umbrella);
                Assert.False(place.Indoors && carries, $"seed {seed}: {sid} holds an umbrella indoors");
                if (!place.Indoors && Table.Roles[looks[sid].Role].Accessories.Contains(Table.Umbrella))
                {
                    outdoor++;
                    umbrellas += carries ? 1 : 0;
                }
            }
        }
        var share = (double)umbrellas / outdoor;
        Assert.InRange(share, Table.RainUmbrellaShare - 0.05, Table.RainUmbrellaShare + 0.05);
    }

    [Fact]
    public void An_umbrella_is_held_up_and_no_slot_carries_two()
    {
        foreach (var seed in Seeds)
        {
            foreach (var (sid, look) in CrowdPicker.Assign(seed, Hub, Table))
            {
                Assert.True(look.Accessories.Count <= Table.MaxAccessories, $"seed {seed}: {sid} carries {look.Accessories.Count}");
                var slots = look.Accessories.Select(a => Table.Accessories[a].Slot).ToList();
                Assert.Equal(slots.Count, slots.Distinct().Count());
                if (look.Accessories.Contains(Table.Umbrella))
                {
                    Assert.Equal(Table.Accessories[Table.Umbrella].Idle, look.Idle);
                }
                Assert.InRange(look.Scale, Table.ScaleRange[0], Table.ScaleRange[1]);
            }
        }
    }

    [Fact]
    public void A_role_naming_a_pool_that_isnt_there_is_refused()
    {
        var text = string.Join("\n", File.ReadAllLines(Path.Combine(TestData.RepoRoot, "game", "data", "crowd.json"))
            .Where(l => !l.TrimStart().StartsWith("//", StringComparison.Ordinal)))
            .Replace("\"shopper\": {\"bodies\": \"civilian\"", "\"shopper\": {\"bodies\": \"tourists\"", StringComparison.Ordinal);
        var table = JsonData.Parse<CrowdTable>(text, "crowd.json");
        var errors = new List<string>();
        table.Validate(errors);
        Assert.Contains(errors, e => e.Contains("no body pool 'tourists'", StringComparison.Ordinal));
    }
}
