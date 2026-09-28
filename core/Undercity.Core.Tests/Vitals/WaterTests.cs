// Breath, stamina and the belt in water, against the shipped data/water.json
// (openspec/changes/water-and-swimming: "Breath runs out under water", "Swimming tires the
// swimmer", "No weapon while swimming").

using Undercity.Core.Data;
using Undercity.Core.Vitals;

namespace Undercity.Core.Tests.Vitals;

public class WaterTests
{
    private static void Run(GameState s, double seconds, double step = 0.1)
    {
        for (var t = 0.0; t < seconds - 1e-9; t += step)
        {
            s.Tick(step);
        }
    }

    [Fact]
    public void Staying_down_for_50_s_leaves_no_breath_and_60_health()
    {
        var s = TestData.NewGame();
        Assert.Equal(100, s.Health.Max);
        s.SetWater(WaterContact.Submerged);
        Run(s, 50);
        Assert.Equal(0, s.Breath.Value, 6);
        Assert.True(Math.Abs(s.Health.Value - 60) < 0.01,
            $"45 s of breath then 5 s at 8 damage a second should leave 60 health, got {s.Health.Value}");
    }

    [Fact]
    public void Three_seconds_at_the_surface_refill_an_empty_breath()
    {
        var s = TestData.NewGame();
        s.SetWater(WaterContact.Submerged);
        Run(s, 46);
        s.SetWater(WaterContact.Swimming);
        Run(s, 3);
        Assert.True(s.Breath.Full, $"breath should be full after 3 s at the surface, got {s.Breath.Value}");
    }

    [Fact]
    public void Breath_does_no_damage_while_it_lasts()
    {
        var s = TestData.NewGame();
        s.SetWater(WaterContact.Submerged);
        Run(s, 44);
        Assert.Equal(s.Health.Max, s.Health.Value, 6);
    }

    [Fact]
    public void A_130_s_swim_tires_the_runner_to_half_speed_without_hurting_them()
    {
        var s = TestData.NewGame();
        s.SetWater(WaterContact.Swimming);
        Run(s, 130);
        Assert.True(s.Stamina.Tired, "0.8 a second from 100 runs out at 125 s");
        var speed = s.Data.Water.SwimSpeedMps * s.Stamina.SpeedFactor;
        Assert.InRange(speed, 1.4, 1.6);
        Assert.Equal(s.Health.Max, s.Health.Value, 6);
    }

    [Fact]
    public void Nine_seconds_on_the_quay_refill_stamina()
    {
        var s = TestData.NewGame();
        s.SetWater(WaterContact.Swimming);
        Run(s, 130);
        s.SetWater(WaterContact.Dry);
        Run(s, 9);
        Assert.Equal(s.Stamina.Max, s.Stamina.Value, 6);
    }

    [Fact]
    public void Wading_does_not_use_stamina()
    {
        var s = TestData.NewGame();
        s.SetWater(WaterContact.Wading);
        Run(s, 60);
        Assert.Equal(s.Stamina.Max, s.Stamina.Value, 6);
    }

    [Fact]
    public void Starting_to_swim_holsters_the_drawn_weapon()
    {
        var s = TestData.NewGame();
        s.UseBelt(s.Inventory.Belt.ToList().IndexOf("pistol"));
        Assert.Equal("pistol", s.Drawn);
        s.SetWater(WaterContact.Swimming);
        Assert.Null(s.Drawn);
    }

    [Fact]
    public void The_belt_refuses_to_draw_while_swimming_and_says_why()
    {
        var s = TestData.NewGame();
        var said = new List<string>();
        s.Feed += said.Add;
        s.SetWater(WaterContact.Swimming);
        Assert.Equal(BeltResult.Refused, s.UseBelt(s.Inventory.Belt.ToList().IndexOf("pistol")));
        Assert.Null(s.Drawn);
        Assert.Contains("Not while swimming.", said);
    }

    [Fact]
    public void Wading_still_allows_a_draw()
    {
        var s = TestData.NewGame();
        s.SetWater(WaterContact.Wading);
        Assert.Equal(BeltResult.Drawn, s.UseBelt(s.Inventory.Belt.ToList().IndexOf("pistol")));
    }

    [Fact]
    public void Breath_and_stamina_survive_a_save_and_a_load()
    {
        var s = TestData.NewGame();
        s.SetWater(WaterContact.Submerged);
        Run(s, 20);
        var (loaded, _) = GameState.Load(TestData.Data, SaveGame.FromJson(s.Save().ToJson()));
        Assert.Equal(s.Breath.Value, loaded.Breath.Value, 6);
        Assert.Equal(s.Stamina.Value, loaded.Stamina.Value, 6);
    }

    [Fact]
    public void A_version_1_save_loads_with_full_breath_and_stamina()
    {
        var save = TestData.NewGame().Save();
        save.Version = 1;
        save.Breath = null;
        save.Stamina = null;
        var (loaded, _) = GameState.Load(TestData.Data, SaveGame.FromJson(save.ToJson()));
        Assert.True(loaded.Breath.Full && loaded.Stamina.Value == loaded.Stamina.Max,
            "saves from before water must not start the runner out of breath");
    }

    [Fact]
    public void A_water_table_with_swimming_shallower_than_wading_is_refused()
    {
        var text = TestData.Source.Read("water.json")
            .Replace("\"swim_depth_m\": 1.2", "\"swim_depth_m\": 0.05", StringComparison.Ordinal);
        var ex = Assert.Throws<DataException>(() => JsonData.Load<WaterTable>(new OneFile("water.json", text), "water.json"));
        Assert.Contains("swim_depth_m", ex.Message, StringComparison.Ordinal);
    }

    private sealed class OneFile(string path, string text) : IDataSource
    {
        public string Read(string relativePath) =>
            relativePath == path ? text : throw new FileNotFoundException(relativePath);

        public bool Exists(string relativePath) => relativePath == path;

        public IReadOnlyList<string> List(string relativeFolder) => [];
    }
}
