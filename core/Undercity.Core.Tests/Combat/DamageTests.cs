// The damage rule, the hit zones and the NPCs' aim, against the shipped data/combat.json and
// data/weapons.json (openspec/changes/hub-combat, design sections 3 and 5).

using Undercity.Core.Combat;

namespace Undercity.Core.Tests.Combat;

public class DamageTests
{
    private static CombatTable T => TestData.Data.Combat;

    private static WeaponDef Kestrel => TestData.Data.Weapons.Find("kestrel")!;

    private static int ShotsToKill(double health, double resistPct, HitZone zone)
    {
        var per = CombatRules.Damage(T, Kestrel, zone, resistPct, targetIsPlayer: false);
        return (int)Math.Ceiling(health / per - 1e-9);
    }

    [Theory]
    [InlineData("civilian", 60, 0, 3, 2)]
    [InlineData("MerSec trooper", 120, 35, 9, 5)]
    [InlineData("Tank", 150, 15, 9, 5)]
    public void The_Kestrel_kills_in_the_designed_number_of_shots(string who, double health, double resist, int torso, int head)
    {
        Assert.True(ShotsToKill(health, resist, HitZone.Torso) == torso, $"{who}: torso shots");
        Assert.True(ShotsToKill(health, resist, HitZone.Head) == head, $"{who}: head shots");
    }

    [Fact]
    public void A_resistance_above_the_cap_counts_only_to_the_cap()
    {
        Assert.Equal(22 * 0.25, CombatRules.Damage(T, Kestrel, HitZone.Torso, 90, targetIsPlayer: false), 6);
        Assert.Equal(22 * 0.40, CombatRules.Damage(T, Kestrel, HitZone.Torso, 90, targetIsPlayer: true), 6);
    }

    [Fact]
    public void Headhunter_makes_a_headshot_triple()
    {
        Assert.Equal(66, CombatRules.Damage(T, Kestrel, HitZone.Head, 0, targetIsPlayer: false, headshotMult: 1.5), 6);
    }

    [Theory]
    [InlineData(1.80, HitZone.Head)]
    [InlineData(1.52, HitZone.Head)]
    [InlineData(1.51, HitZone.Torso)]
    [InlineData(0.85, HitZone.Torso)]
    [InlineData(0.84, HitZone.Limbs)]
    [InlineData(0.10, HitZone.Limbs)]
    public void A_hit_lands_in_the_zone_its_height_says(double heightM, HitZone zone)
    {
        Assert.Equal(zone, CombatRules.ZoneAt(T.Zones, heightM));
    }

    [Fact]
    public void A_trooper_at_15_m_hits_a_still_runner_a_quarter_of_the_time()
    {
        Assert.Equal(0.25, CombatRules.HitChance(T.HitChance, 15, moving: false, crouched: false), 6);
    }

    [Fact]
    public void Hit_chance_never_leaves_its_bounds()
    {
        Assert.Equal(T.HitChance.Base, CombatRules.HitChance(T.HitChance, 0, false, false), 6);
        Assert.InRange(CombatRules.HitChance(T.HitChance, -5, false, false), T.HitChance.Min, T.HitChance.Max);
        Assert.Equal(T.HitChance.Min, CombatRules.HitChance(T.HitChance, 200, true, true), 6);
        Assert.Equal(T.HitChance.Min, CombatRules.HitChance(T.HitChance, double.NaN, false, false), 6);
    }

    [Fact]
    public void A_civilians_defence_is_the_same_for_the_same_seed_and_id()
    {
        var pool = TestData.Data.Npcs.Civilians;
        var a = CombatRules.CivilianDefence(pool.Defences, 7, "hub:civ_07");
        Assert.Equal(a, CombatRules.CivilianDefence(pool.Defences, 7, "hub:civ_07"));
    }

    [Fact]
    public void About_seven_in_ten_civilians_flee_and_the_rest_cower()
    {
        var pool = TestData.Data.Npcs.Civilians;
        var picks = Enumerable.Range(1, 1000).Select(i => CombatRules.CivilianDefence(pool.Defences, 7, $"hub:civ_{i:000}")).ToList();
        var flee = picks.Count(d => d == Defence.Flee);
        Assert.InRange(flee, 650, 750);
        Assert.Equal(1000 - flee, picks.Count(d => d == Defence.Cower));
    }

    [Fact]
    public void Every_NPC_has_health_and_a_defence_and_every_fighter_a_weapon()
    {
        foreach (var n in TestData.Data.Npcs.Npcs)
        {
            Assert.True(n.Health > 0, $"{n.Id} needs health");
            var d = CombatRules.ParseDefence(n.Defence);
            Assert.True(d is not null, $"{n.Id}: defence '{n.Defence}'");
            if (d == Defence.Fight)
            {
                Assert.True(n.Weapon is not null && TestData.Data.Weapons.Find(n.Weapon) is not null, $"{n.Id} fights with a weapon in weapons.json");
            }
        }
    }

    [Fact]
    public void Every_weapon_an_item_names_is_in_weapons_json()
    {
        foreach (var i in TestData.Data.Items.Items.Where(i => i.Weapon is not null))
        {
            Assert.True(TestData.Data.Weapons.Find(i.Weapon!) is { NpcOnly: false }, $"{i.Id}: '{i.Weapon}'");
        }
    }
}
