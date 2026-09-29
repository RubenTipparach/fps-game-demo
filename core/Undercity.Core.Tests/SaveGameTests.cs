// Saves round-trip, and a damaged save loads as the nearest legal state (CLAUDE.md 5.6).

using Undercity.Core.Data;
using Undercity.Core.Progression;

namespace Undercity.Core.Tests;

public class SaveGameTests
{
    [Fact]
    public void A_save_round_trips_through_json()
    {
        var s = TestData.NewGame();
        s.Character.AddXp(700, "test");
        s.Character.Raise(Skill.Stealth);
        s.PickUp("data_shard", 2, stolenFrom: "residents");
        s.World.SetFlag("tank_ok");
        s.Quests.Start("m1_rat_trap");
        s.CompleteObjective("m1_rat_trap/petra");
        var json = s.Save().ToJson();

        var (back, repairs) = GameState.Load(TestData.Data, SaveGame.FromJson(json));
        Assert.Empty(repairs);
        Assert.Equal(json, back.Save().ToJson());
        Assert.Equal(2, back.Character.Level);
        Assert.True(back.Inventory.Pack.Stacks.Single(x => x.Def.Id == "data_shard").StolenFrom == "residents",
            "stolen goods stay stolen across a save");
    }

    [Fact]
    public void Ninety_medkits_in_one_stack_load_as_five()
    {
        var save = TestData.NewGame().Save();
        save.Inventory.Stacks.Add(new Undercity.Core.Kit.StackSave { Item = "medkit", Count = 90, X = 9, Y = 5 });
        var (s, repairs) = GameState.Load(TestData.Data, SaveGame.FromJson(save.ToJson()));
        Assert.Equal(1 + 5, s.Inventory.Pack.Count("medkit"));
        Assert.Contains(repairs, r => r.Contains("medkit x90", StringComparison.Ordinal));
    }

    [Fact]
    public void An_unknown_item_in_a_save_is_dropped_with_a_warning()
    {
        var save = TestData.NewGame().Save();
        save.Inventory.Stacks.Add(new Undercity.Core.Kit.StackSave { Item = "plasma_rifle", X = 9, Y = 5 });
        var (_, repairs) = GameState.Load(TestData.Data, save);
        Assert.Contains("unknown item 'plasma_rifle' dropped", repairs);
    }

    [Fact]
    public void A_save_from_a_newer_build_is_refused()
    {
        var save = TestData.NewGame().Save();
        save.Version = SaveGame.CurrentVersion + 1;
        Assert.Throws<DataException>(() => GameState.Load(TestData.Data, save));
    }
}
