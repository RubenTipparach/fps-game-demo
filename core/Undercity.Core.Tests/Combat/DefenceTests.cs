// Who does what when violence starts, and whether an NPC's shot hits (openspec/changes/hub-combat,
// design section 5), against the shipped data/npcs.json and data/combat.json.

using Undercity.Core.Combat;

namespace Undercity.Core.Tests.Combat;

public class DefenceTests
{
    private static CombatTable T => TestData.Data.Combat;

    [Theory]
    [InlineData("tank", Defence.Fight)]
    [InlineData("silk", Defence.Surrender)]
    [InlineData("mouse", Defence.Flee)]
    public void A_named_NPC_takes_the_defence_their_data_gives(string id, Defence expected)
    {
        var def = TestData.Data.Npcs.Find(id)!;
        Assert.Equal(expected, CombatRules.DefenceOf(def, TestData.Data.Npcs.Civilians, 7, $"hub:{id}"));
    }

    [Fact]
    public void A_civilian_takes_the_pools_seeded_defence()
    {
        var pool = TestData.Data.Npcs.Civilians;
        Assert.Equal(CombatRules.CivilianDefence(pool.Defences, 7, "hub:civ_07"), CombatRules.DefenceOf(null, pool, 7, "hub:civ_07"));
    }

    [Theory]
    [InlineData(Provocation.ShotHeard, null)]
    [InlineData(Provocation.Hurt, Defence.Fight)]
    [InlineData(Provocation.MurderSeen, Defence.Fight)]
    public void A_fighter_fights_when_hurt_or_when_one_of_their_own_is_killed_not_at_a_shot_heard(Provocation what, Defence? expected)
    {
        Assert.Equal(expected, CombatRules.Respond(Defence.Fight, what));
    }

    [Theory]
    [InlineData(Defence.Flee)]
    [InlineData(Defence.Cower)]
    [InlineData(Defence.Surrender)]
    public void Everyone_else_takes_their_defence_at_the_first_shot(Defence defence)
    {
        foreach (var what in Enum.GetValues<Provocation>())
        {
            Assert.Equal(defence, CombatRules.Respond(defence, what));
        }
    }

    [Fact]
    public void The_same_shot_by_the_same_shooter_always_lands_the_same_way()
    {
        for (var shot = 0; shot < 50; shot++)
        {
            Assert.Equal(CombatRules.NpcShotHits(T.HitChance, 7, "mersec_1", shot, 15, false, false),
                CombatRules.NpcShotHits(T.HitChance, 7, "mersec_1", shot, 15, false, false));
        }
    }

    [Fact]
    public void A_trooper_at_15_m_hits_about_a_quarter_of_their_shots()
    {
        var hits = Enumerable.Range(0, 2000).Count(i => CombatRules.NpcShotHits(T.HitChance, 7, "mersec_1", i, 15, false, false));
        Assert.True(hits is > 440 and < 560, $"{hits} of 2000 at a 0.25 chance");
    }
}
