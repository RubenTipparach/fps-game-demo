// The crowd rule (openspec/changes/archive/2026-09-29-crowd-variety, "No lookalikes nearby" and "Civilians vary at
// runtime"): on the hub's real placements, with world seeds 1 to 100, no two civilians within
// 15 m share body and palette and no body is used more than three times; the same seed gives the
// same crowd; roles follow districts; umbrellas are for the open; accessories never double up on a
// slot; and civilians placed close together stand talking in pairs.

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
        Assert.Equal(35, Hub.Count);
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
            Assert.Equal(look.Partner, again[sid].Partner);
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
    public void About_a_third_of_the_civilians_in_the_open_who_may_carry_one_hold_an_umbrella_and_nobody_sheltered()
    {
        int outdoor = 0, umbrellas = 0;
        foreach (var seed in Seeds)
        {
            var looks = CrowdPicker.Assign(seed, Hub, Table);
            foreach (var (sid, place) in Hub)
            {
                var carries = looks[sid].Accessories.Contains(Table.Umbrella);
                Assert.False(place.Sheltered && carries, $"seed {seed}: {sid} holds an umbrella under cover");
                if (!place.Sheltered && Table.Roles[looks[sid].Role].Accessories.Contains(Table.Umbrella))
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
    public void Civilians_placed_in_a_pair_face_each_other_and_talk_unless_an_accessory_sets_the_idle()
    {
        var partners = CrowdPicker.TalkPartners(Hub, Table);
        Assert.True(partners.Count >= 8, $"the hub places at least four talking pairs; it has {partners.Count / 2}");
        foreach (var seed in Seeds)
        {
            var looks = CrowdPicker.Assign(seed, Hub, Table);
            foreach (var (sid, look) in looks)
            {
                Assert.Equal(partners.GetValueOrDefault(sid), look.Partner);
                if (look.Partner is { } other)
                {
                    Assert.Equal(sid, looks[other].Partner);
                    Assert.True(CrowdPicker.Distance(Hub[sid], Hub[other]) <= Table.TalkPairRadiusM, $"{sid} and {other} stand too far apart to talk");
                    // An umbrella is held up, a bag hangs: what they carry keeps its idle.
                    var forced = look.Accessories.Select(a => Table.Accessories[a].Idle).FirstOrDefault(i => i is not null);
                    Assert.Equal(forced ?? CrowdPicker.TalkIdle, look.Idle);
                }
            }
        }
    }

    [Fact]
    public void Nobody_stands_in_two_pairs()
    {
        var place = new CrowdPlace { At = new[] { 0.0, 0.0 } };
        var crowd = new Dictionary<string, CrowdPlace>
        {
            ["a"] = place,
            ["b"] = new CrowdPlace { At = new[] { 1.0, 0.0 } },
            ["c"] = new CrowdPlace { At = new[] { 1.5, 0.0 } },
        };
        var partners = CrowdPicker.TalkPartners(crowd, Table);
        Assert.Equal("c", partners["b"]);
        Assert.False(partners.ContainsKey("a"), "a is left out: b is closer to c than to a, and nobody talks in a three");
    }

    [Fact]
    public void Every_accessory_has_its_prop_and_a_mount_the_bodies_carry()
    {
        foreach (var (id, a) in Table.Accessories)
        {
            var glb = Path.Combine(TestData.RepoRoot, "game", "models", "undercity", "props", id + ".glb");
            Assert.True(File.Exists(glb), $"'{id}' has no prop; run tools/blender/build_undercity_props.py");
            Assert.True(TestData.Data.NpcBodies.Mounts.ContainsKey(a.Mount), $"'{id}' hangs from '{a.Mount}', which no body has");
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
