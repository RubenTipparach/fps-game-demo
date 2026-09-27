// Lock resolution: key, then code, then pick, then hack (openspec/changes/world-interaction).

using Undercity.Core.Locks;
using Undercity.Core.Progression;

namespace Undercity.Core.Tests.Locks;

public class LockRulesTests
{
    private static LockDef StormDrain => TestData.Data.Levels["hub"].Exits["hub:storm_drain"].Lock!;

    [Fact]
    public void Without_the_code_or_the_skill_the_prompt_says_what_would_open_it()
    {
        var s = TestData.NewGame();
        var plan = s.PlanLock(StormDrain);
        Assert.False(plan.CanOpen);
        Assert.Equal("Locked door: needs the code, or Lockpicking 1", plan.Prompt);
    }

    [Fact]
    public void A_known_code_beats_picking_and_costs_no_lockpick()
    {
        var s = TestData.NewGame();
        s.Character.Raise(Skill.Lockpicking);
        s.World.SetFlag("code_storm_drain");
        var plan = s.PlanLock(StormDrain);
        Assert.Equal(LockWay.Code, plan.Way);
        Assert.Null(plan.Consumes);
    }

    [Fact]
    public void Picking_takes_one_second_per_tier_and_a_safe_twice_that()
    {
        var s = TestData.NewGame();
        s.Character.AddSkillPoints(10);
        for (var i = 0; i < 3; i++)
        {
            s.Character.Raise(Skill.Lockpicking);
        }
        var door = new LockDef { Tier = 2 };
        var safe = TestData.Data.Levels["hub"].Containers["hub:kessler_safe"].Lock!;
        Assert.Equal(2.0, s.PlanLock(door).HoldS, 3);
        Assert.Equal(3 * 2.0, s.PlanLock(safe).HoldS, 3);
        s.Character.Raise(Skill.Lockpicking);
        Assert.True(Math.Abs(s.PlanLock(door).HoldS - 1.0) < 1e-9, "Fast Picks (Lockpicking 4) halves pick time");
    }

    [Fact]
    public void A_device_lock_can_only_be_hacked()
    {
        var s = TestData.NewGame();
        s.Character.Raise(Skill.Lockpicking);
        var lift = TestData.Data.Levels["hub"].Exits["hub:lift_up"].Lock!;
        Assert.Equal("Locked system: needs Hacking 1", s.PlanLock(lift).Prompt);
        s.Character.Raise(Skill.Hacking);
        Assert.Equal(LockWay.Hack, s.PlanLock(lift).Way);
    }

    [Fact]
    public void Opening_a_lock_uses_the_lockpick_and_pays_xp_once()
    {
        var s = TestData.NewGame();
        s.Character.Raise(Skill.Lockpicking);
        var picks = s.Inventory.Pack.Count("lockpick");
        Assert.True(s.OpenLock(StormDrain, "hub", "hub:storm_drain"));
        Assert.Equal(picks - 1, s.Inventory.Pack.Count("lockpick"));
        Assert.True(s.IsOpened("hub", "hub:storm_drain"));
        Assert.Equal(TestData.Data.Progression.Xp.LockPerTier * 1, s.Character.TotalXp);
        s.OpenLock(StormDrain, "hub", "hub:storm_drain");
        Assert.True(s.Character.TotalXp == TestData.Data.Progression.Xp.LockPerTier, "a lock pays once");
    }
}
