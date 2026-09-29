// The NPC body table: clips for every state an NPC can be in, and a ragdoll that settles in the
// time the spec gives (openspec/changes/archive/2026-09-28-npc-characters).

using Undercity.Core.Data;
using Undercity.Core.World;

namespace Undercity.Core.Tests.World;

public sealed class NpcBodiesTests
{
    private static NpcBodyTable Parse(string json)
    {
        var table = JsonData.Parse<NpcBodyTable>(json, "npc_bodies.json");
        var errors = new List<string>();
        table.Validate(errors);
        if (errors.Count > 0)
        {
            throw new DataException("npc_bodies.json", string.Join("; ", errors));
        }
        return table;
    }

    private const string Ragdoll = """
        "ragdoll": {"settle_s": 3.0, "friction": 0.8, "linear_damp_per_s": 0.05, "angular_damp_per_s": 0.8,
          "bodies": [{"bone": "Hips", "to": "Spine", "radius_m": 0.13, "mass_kg": 12.0, "joint": "none"},
                     {"bone": "LeftLowerLeg", "to": "LeftFoot", "radius_m": 0.065, "mass_kg": 4.0, "joint": "hinge",
                      "a_deg": -140, "b_deg": 0 FLEX}]}
        """;

    private static string Table(string clips, string flex = ", \"flex\": [0, 0, -1]") =>
        "{\"clips\": {" + clips + "}, \"blend_s\": 0.25, " + Ragdoll.Replace("FLEX", flex, StringComparison.Ordinal) + "}";

    private const string AllClips = "\"idle\": \"Idle\", \"walk\": \"Walk\", \"talk\": \"Idle_Talking\", \"guard\": \"Idle\", \"hostile\": \"Idle\"";

    [Fact]
    public void The_shipped_ragdoll_freezes_three_seconds_after_it_falls()
    {
        Assert.Equal(3.0, TestData.Data.NpcBodies.Ragdoll.SettleS);
    }

    [Fact]
    public void Every_state_an_npc_idles_in_has_a_clip()
    {
        foreach (var npc in TestData.Data.Npcs.Npcs)
        {
            Assert.True(TestData.Data.NpcBodies.Clip(npc.Idle) is not null, $"{npc.Id} idles as '{npc.Idle}'");
        }
    }

    /// <summary>The animation names in a .glb's JSON chunk, with the "_Loop" suffix the import strips.</summary>
    private static List<string> GlbClips(string resPath)
    {
        var bytes = File.ReadAllBytes(Path.Combine(TestData.RepoRoot, "game", resPath));
        var length = BitConverter.ToInt32(bytes, 12);
        using var doc = System.Text.Json.JsonDocument.Parse(bytes.AsMemory(20, length));
        return doc.RootElement.GetProperty("animations").EnumerateArray()
            .Select(a => a.GetProperty("name").GetString()!)
            .Select(n => n.EndsWith("_Loop", StringComparison.Ordinal) ? n[..^"_Loop".Length] : n)
            .ToList();
    }

    [Fact]
    public void Every_clip_the_table_names_is_in_the_shipped_libraries()
    {
        // The libraries the NPC scenes hold (tools/godot/gen_npc_scenes.gd): UAL with no prefix, ours as "undercity/".
        var clips = GlbClips("animations/ual/ual_standard.glb")
            .Concat(GlbClips("animations/undercity_clips.glb").Select(c => "undercity/" + c)).ToHashSet(StringComparer.Ordinal);
        foreach (var (state, clip) in TestData.Data.NpcBodies.Clips)
        {
            Assert.True(clips.Contains(clip), $"the state '{state}' plays '{clip}', which no library has");
        }
    }

    [Fact]
    public void A_table_without_a_walk_clip_is_refused()
    {
        var ex = Assert.Throws<DataException>(() => Parse(Table(AllClips.Replace("\"walk\": \"Walk\", ", "", StringComparison.Ordinal))));
        Assert.Contains("'walk'", ex.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_knee_hinge_without_a_flex_direction_is_refused()
    {
        var ex = Assert.Throws<DataException>(() => Parse(Table(AllClips, flex: "")));
        Assert.Contains("LeftLowerLeg", ex.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Every_npc_model_has_a_generated_scene()
    {
        var models = TestData.Data.Npcs.Npcs.Select(n => n.Model).Concat(TestData.Data.Crowd.BodyPools.Values.SelectMany(p => p)).Distinct();
        foreach (var model in models)
        {
            var scene = Path.Combine(TestData.RepoRoot, "game", "scenes", "undercity", "npcs", model + ".tscn");
            Assert.True(File.Exists(scene), $"'{model}' has no scene; run tools/godot/gen_npc_scenes.gd (README, Undercity's NPC bodies)");
        }
    }

    [Fact]
    public void A_complete_table_loads()
    {
        Assert.Equal("Walk", Parse(Table(AllClips)).Clip("walk"));
    }
}
