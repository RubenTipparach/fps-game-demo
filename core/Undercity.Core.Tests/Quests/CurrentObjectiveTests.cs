// The objective the HUD and the pause menu both show (openspec/specs/title-and-pause: "the HUD
// and the pause menu show the same objective").

namespace Undercity.Core.Tests.Quests;

public sealed class CurrentObjectiveTests
{
    [Fact]
    public void With_no_active_quest_there_is_no_objective()
    {
        Assert.Null(TestData.NewGame().Quests.Current());
    }

    [Fact]
    public void The_first_active_quest_shows_its_first_objective_not_yet_done()
    {
        var state = TestData.NewGame();
        state.Quests.Start("t0_arrival");
        var quest = TestData.Data.Quests.Get("t0_arrival");
        var first = quest.Objectives.First(o => !o.Hidden);

        var current = state.Quests.Current();

        Assert.Equal("t0_arrival", current?.Quest.Id);
        Assert.Equal(first.Id, current?.Objective?.Id);
    }
}
