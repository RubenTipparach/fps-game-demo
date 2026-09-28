// The save rule and the save tuning (openspec/specs/title-and-pause).

namespace Undercity.Core.Tests;

public sealed class SaveRulesTests
{
    private static readonly SavesTable Saves = TestData.Data.Saves;

    [Fact]
    public void Saving_is_allowed_when_nobody_hostile_is_watching_and_nobody_is_talking()
    {
        Assert.True(SaveRules.CanSave(new SaveSituation(false, false), out var reason));
        Assert.Equal("", reason);
    }

    [Fact]
    public void A_watching_hostile_refuses_the_save_and_says_why()
    {
        Assert.False(SaveRules.CanSave(new SaveSituation(false, true), out var reason));
        Assert.Equal("Not while hostiles can see you.", reason);
    }

    [Fact]
    public void A_conversation_refuses_the_save_and_says_why()
    {
        Assert.False(SaveRules.CanSave(new SaveSituation(true, false), out var reason));
        Assert.Equal("Not during a conversation.", reason);
    }

    [Fact]
    public void The_slots_are_quick_auto_and_three_named_slots()
    {
        Assert.Equal("quick,auto,slot_1,slot_2,slot_3", string.Join(',', Saves.Slots));
    }

    [Fact]
    public void The_player_may_write_every_slot_but_auto()
    {
        Assert.True(Saves.Writable("quick"));
        Assert.True(Saves.Writable("slot_3"));
        Assert.False(Saves.Writable("auto"), "the autosave is the game's; a player save there would be lost at the next door");
        Assert.False(Saves.Writable("slot_4"));
    }

    [Fact]
    public void Quit_to_title_asks_only_once_the_newest_save_is_older_than_five_minutes()
    {
        var now = new DateTime(2026, 9, 27, 21, 0, 0, DateTimeKind.Utc);
        Assert.Equal(300, Saves.QuitWarnAfterS);
        Assert.False(Saves.WarnBeforeQuit(now.AddSeconds(-300), now), "exactly 300 s is still fresh");
        Assert.True(Saves.WarnBeforeQuit(now.AddSeconds(-301), now));
        Assert.True(Saves.WarnBeforeQuit(null, now), "with no save at all, quitting loses everything");
    }
}
