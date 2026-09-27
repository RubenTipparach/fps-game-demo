// Conversations against the shipped trees: what shows, what greys, what a pick does
// (openspec/changes/dialog-and-social). The greyed choice and the outcome come from one rule.

using Undercity.Core.Dialog;
using Undercity.Core.Progression;

namespace Undercity.Core.Tests.Dialog;

public class DialogSessionTests
{
    private static DialogSession Talk(GameState s, string tree) =>
        s.Talk(TestData.Data.Dialogs[tree], new Speaker($"hub:{tree}", tree));

    private static ChoiceView Find(DialogSession d, string textStart) =>
        d.Choices().Single(c => c.Text.StartsWith(textStart, StringComparison.Ordinal));

    [Fact]
    public void A_story_condition_hides_a_choice_the_runner_knows_nothing_about()
    {
        var s = TestData.NewGame();
        var d = Talk(s, "tank");
        Assert.DoesNotContain(d.Choices(), c => c.Text.StartsWith("Silk sent for me", StringComparison.Ordinal));
        s.Quests.Start("t0_arrival");
        Assert.Contains(Talk(s, "tank").Choices(), c => c.Text.StartsWith("Silk sent for me", StringComparison.Ordinal));
    }

    [Fact]
    public void An_unmet_skill_check_shows_greyed_with_its_requirement()
    {
        var s = TestData.NewGame();
        var d = Talk(s, "tank");
        var talk = Find(d, "Silk's going to ask");
        Assert.False(talk.Enabled);
        Assert.Equal("[Persuasion 2]", talk.Requirement);
        Assert.False(d.Choose(talk.Index), "a greyed choice can't be picked");
    }

    [Fact]
    public void Paying_Tank_opens_the_back_room_and_he_remembers()
    {
        var s = TestData.NewGame();
        var opened = new List<string>();
        s.HostAction += (action, arg) => opened.Add($"{action} {arg}");
        var d = Talk(s, "tank");
        var bribe = Find(d, "For your trouble");
        Assert.Equal("[50 cr]", bribe.Requirement);
        Assert.True(d.Choose(bribe.Index));
        Assert.Equal(100, s.Inventory.Credits);
        Assert.Contains("open hub:anchor_backroom", opened);
        Assert.Equal("ok", Talk(s, "tank").NodeId);
    }

    [Fact]
    public void A_passed_check_pays_25_xp_per_dc_once()
    {
        var s = TestData.NewGame();
        s.Character.Raise(Skill.Persuasion);
        var d = Talk(s, "rivet");
        d.Choose(Find(d, "That Drain Rats jacket").Index);
        d.Choose(Find(d, "Sixty for a dead man's coat").Index);
        Assert.Equal(25, s.Character.TotalXp);
        var again = Talk(s, "rivet");
        again.Choose(Find(again, "That Drain Rats jacket").Index);
        var haggle = Find(again, "Sixty for a dead man's coat");
        Assert.Equal("[Persuasion 1: passed]", haggle.Requirement);
        again.Choose(haggle.Index);
        Assert.True(s.Character.TotalXp == 25, "the same check never pays twice");
    }

    [Fact]
    public void A_box_of_rounds_shows_and_charges_the_box_price()
    {
        var s = TestData.NewGame();
        var d = Talk(s, "kessler");
        d.Advance();
        d.Choose(Find(d, "Ammunition and tools").Index);
        var box = Find(d, "10mm rounds, box of 12");
        Assert.Equal("[24 cr]", box.Requirement);
        var rounds = s.Inventory.Pack.Count("ammo_10mm");
        Assert.True(d.Choose(box.Index));
        Assert.Equal(150 - 24, s.Inventory.Credits);
        Assert.Equal(rounds + 12, s.Inventory.Pack.Count("ammo_10mm"));
    }

    [Fact]
    public void Nguyen_gives_the_drain_code_to_customers_only()
    {
        var s = TestData.NewGame();
        var d = Talk(s, "nguyen");
        Assert.DoesNotContain(d.Choices(), c => c.Text.StartsWith("About that storm drain code", StringComparison.Ordinal));
        d.Choose(Find(d, "A bowl of noodles").Index);
        d.Choose(Find(d, "About that storm drain code").Index);
        Assert.True(s.World.Flag("code_storm_drain"));
    }

    [Fact]
    public void Dace_drops_the_debt_for_the_ledger_and_opens_the_checkpoint_for_good()
    {
        var s = TestData.NewGame();
        s.Character.Raise(Skill.Persuasion);
        s.Character.Raise(Skill.Persuasion);
        s.Quests.Start("s3_mouses_debt");
        s.World.SetFlag("dace_evidence");
        var d = Talk(s, "dace");
        d.Choose(Find(d, "About Mouse's debt").Index);
        d.Choose(Find(d, "Your checkpoint ledger").Index);
        Assert.True(s.Quests.IsDone("s3_mouses_debt/settle"));
        Assert.True(s.World.Flag("dace_waves"));
        Assert.Equal("waved", Talk(s, "dace").NodeId);
    }

    [Fact]
    public void A_civilian_always_says_the_same_thing_for_the_same_seed()
    {
        var a = TestData.NewGame(seed: 11);
        var b = TestData.NewGame(seed: 11);
        var tree = TestData.Data.Dialogs["civilian"];
        var lineA = a.Talk(tree, new Speaker("hub:civ_07", null)).Line;
        var lineB = b.Talk(tree, new Speaker("hub:civ_07", null)).Line;
        Assert.Equal(lineA, lineB);
        Assert.Contains(lineA, TestData.Data.Npcs.Civilians.SmallTalk);
    }
}
