// The XP curve, rank costs and cross-tree perk requirements (openspec/changes/character-progression).

using Undercity.Core.Progression;

namespace Undercity.Core.Tests.Progression;

public class CharacterTests
{
    private static Character NewCharacter() => new(TestData.Data.Skills, TestData.Data.Progression);

    [Fact]
    public void Seventeen_hundred_xp_is_level_3_with_200_over_and_8_points()
    {
        var c = NewCharacter();
        c.AddXp(1700, "");
        Assert.Equal(3, c.Level);
        Assert.Equal(200, c.Xp);
        Assert.True(c.SkillPoints == 8, "4 start points plus 2 per level for two levels");
    }

    [Fact]
    public void The_next_level_costs_the_level_times_500()
    {
        var c = NewCharacter();
        Assert.Equal(500, c.XpToNext);
        c.AddXp(500, "");
        Assert.Equal(1000, c.XpToNext);
    }

    [Fact]
    public void Xp_from_one_source_is_paid_once()
    {
        var c = NewCharacter();
        Assert.True(c.AddXp(100, "lock:hub:outfall"));
        Assert.False(c.AddXp(100, "lock:hub:outfall"));
        Assert.Equal(100, c.TotalXp);
    }

    [Fact]
    public void Ranks_4_and_5_cost_two_points_each()
    {
        var c = NewCharacter();
        c.AddSkillPoints(20);
        var before = c.SkillPoints;
        for (var i = 0; i < 5; i++)
        {
            Assert.True(c.Raise(Skill.Hacking));
        }
        Assert.Equal(1 + 1 + 2 + 2 + 2, before - c.SkillPoints);
        Assert.False(c.Raise(Skill.Hacking), "5 is the top rank");
    }

    [Fact]
    public void Deadeye_needs_stealth_1_whatever_the_points()
    {
        var c = NewCharacter();
        c.AddSkillPoints(20);
        for (var i = 0; i < 4; i++)
        {
            c.Raise(Skill.Firearms);
        }
        var check = c.CanRaise(Skill.Firearms);
        Assert.False(check.Ok);
        Assert.Equal("needs Stealth 1", check.Reason);
        c.Raise(Skill.Stealth);
        Assert.True(c.Raise(Skill.Firearms));
    }

    [Fact]
    public void A_refused_raise_changes_nothing()
    {
        var c = NewCharacter();
        Assert.True(c.Raise(Skill.Melee) && c.Raise(Skill.Melee) && c.Raise(Skill.Melee), "1 + 1 + 2 spends the 4 start points");
        Assert.Equal(0, c.SkillPoints);
        var check = c.CanRaise(Skill.Melee);
        Assert.Equal("needs 2 points", check.Reason);
        Assert.False(c.Raise(Skill.Melee));
        Assert.Equal(3, c.Rank(Skill.Melee));
        Assert.Equal(0, c.SkillPoints);
    }

    [Fact]
    public void A_check_value_takes_at_most_one_from_gear()
    {
        var c = NewCharacter();
        Assert.Equal(1, c.CheckValue(Skill.Deception, 0));
        Assert.True(c.CheckValue(Skill.Deception, 3) == 2, "gear adds at most max_item_bonus (1)");
    }
}
