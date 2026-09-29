// The disguise verdict and the hub's law (openspec/changes/perception-and-disguise).

using Undercity.Core.Perception;
using Undercity.Core.Progression;

namespace Undercity.Core.Tests.Perception;

public class DisguiseTests
{
    // Mother Rat, the Drains' boss: Intelligence 4, so her scrutiny range is 2 + 2 x 4 = 10 m.
    private static readonly Observer MotherRat = new("drain_rats", 4);

    private static GameState InRatColours(int deception)
    {
        var s = TestData.NewGame();
        s.Character.AddSkillPoints(10);
        s.Character.Raise(Skill.Stealth);
        s.Character.Raise(Skill.Stealth);
        while (s.Character.Rank(Skill.Deception) < deception)
        {
            Assert.True(s.Character.Raise(Skill.Deception));
        }
        s.PickUp("rat_jacket", 1);
        Assert.True(s.Inventory.Equip(s.Inventory.Pack.Stacks.First(x => x.Def.Id == "rat_jacket")));
        return s;
    }

    [Fact]
    public void Mother_Rat_scrutinises_to_10_m()
    {
        var s = TestData.NewGame();
        Assert.Equal(10, DisguiseRules.ScrutinyM(TestData.Data.Perception.Disguise, s.Character, 4), 6);
    }

    [Fact]
    public void Cover_3_is_blown_at_10_m_but_passes_at_16_m()
    {
        var s = InRatColours(1);
        Assert.Equal(3, DisguiseRules.Cover(s.Character, s.Inventory));
        Assert.Equal(Verdict.Blown, s.Judge(MotherRat, new Situation(10)).Verdict);
        Assert.Equal(Verdict.Accepted, s.Judge(MotherRat, new Situation(16)).Verdict);
    }

    [Fact]
    public void Cover_5_holds_against_her_even_face_to_face()
    {
        var s = InRatColours(3);
        Assert.Equal(5, DisguiseRules.Cover(s.Character, s.Inventory));
        Assert.Equal(Verdict.Accepted, s.Judge(MotherRat, new Situation(1, Talking: true)).Verdict);
    }

    [Fact]
    public void The_wrong_colours_are_no_disguise_at_all()
    {
        var s = InRatColours(3);
        Assert.Equal(Verdict.NotDisguised, s.Judge(new Observer("scrap_kings", 1), new Situation(30)).Verdict);
    }

    [Fact]
    public void A_drawn_weapon_blows_a_disguise_after_the_grace_period()
    {
        var s = InRatColours(1);
        Assert.Equal(Verdict.Blown, s.Judge(MotherRat, new Situation(30, WeaponDrawnS: 0.1)).Verdict);
    }

    [Fact]
    public void An_unfoolable_observer_ignores_any_disguise()
    {
        var s = InRatColours(3);
        var dog = new Observer("drain_rats", 1, Unfoolable: true);
        Assert.Equal(Verdict.NotDisguised, s.Judge(dog, new Situation(30)).Verdict);
    }

    [Fact]
    public void Goggles_and_a_respirator_without_the_jacket_are_no_disguise()
    {
        var s = TestData.NewGame();
        s.Inventory.Wear(TestData.Data.Items.Get("rat_goggles"));
        s.Inventory.Wear(TestData.Data.Items.Get("rat_respirator"));
        Assert.True(s.Inventory.DisguiseQuality == 0, "the faction comes from the body piece; the street jacket is still worn");
        Assert.Equal(Verdict.NotDisguised, s.Judge(MotherRat, new Situation(30)).Verdict);
    }

    [Fact]
    public void The_whole_outfit_adds_up_its_quality()
    {
        var s = InRatColours(1);
        s.Inventory.Wear(TestData.Data.Items.Get("rat_goggles"));
        s.Inventory.Wear(TestData.Data.Items.Get("rat_respirator"));
        Assert.Equal(2 + 1 + 1, s.Inventory.DisguiseQuality);
    }
}

public class LawWatchTests
{
    [Fact]
    public void MerSec_warns_once_then_fights_a_second_weapon_inside_the_window()
    {
        var law = new LawWatch(TestData.Data.Perception.Law);
        Assert.Equal(LawResponse.Warn, law.WeaponSeen());
        law.Tick(30);
        Assert.Equal(LawResponse.Hostile, law.WeaponSeen());
    }

    [Fact]
    public void The_warning_is_forgotten_after_the_window()
    {
        var law = new LawWatch(TestData.Data.Perception.Law);
        law.WeaponSeen();
        law.Tick(61);
        Assert.Equal(LawResponse.Warn, law.WeaponSeen());
    }

    [Fact]
    public void Any_shot_turns_MerSec_hostile()
    {
        var law = new LawWatch(TestData.Data.Perception.Law);
        Assert.Equal(LawResponse.Hostile, law.ShotFired());
    }

    [Fact]
    public void A_witnessed_crime_costs_five_with_the_residents_and_is_reported()
    {
        var s = TestData.NewGame();
        var before = s.Reputation.Get("residents");
        Assert.Equal(LawResponse.Report, s.ReportCrime("Kessler"));
        Assert.Equal(before - 5, s.Reputation.Get("residents"));
    }
}
