// Hurting and killing people, and what it costs (openspec/changes/hub-combat, design sections 4
// and 6); the runner's health, armour and death (section 7).

using Undercity.Core.Combat;
using Undercity.Core.Quests;
using Undercity.Core.World;

namespace Undercity.Core.Tests.Combat;

public class ViolenceTests
{
    private static WeaponDef W(string id) => TestData.Data.Weapons.Find(id)!;

    private static NpcTarget Npc(string id) => NpcTarget.For(TestData.Data.Npcs.Find(id)!);

    private static NpcTarget Civ(string stableId) =>
        NpcTarget.Civilian(TestData.Data.Npcs.Civilians, stableId, "residents", "Civilian");

    [Fact]
    public void Three_torso_shots_kill_a_civilian()
    {
        var s = TestData.NewGame();
        var c = Civ("hub:civ_01");
        Assert.False(s.HurtNpc(c, W("kestrel"), HitZone.Torso).Killed);
        Assert.False(s.HurtNpc(c, W("kestrel"), HitZone.Torso).Killed);
        Assert.True(s.HurtNpc(c, W("kestrel"), HitZone.Torso).Killed);
        Assert.Equal(NpcStatus.Dead, s.World.Npc("hub:civ_01"));
    }

    [Fact]
    public void Killing_one_civilian_leaves_the_others_alive()
    {
        // The regression: every civilian's status was kept under the one id "civ".
        var s = TestData.NewGame();
        for (var i = 0; i < 3; i++)
        {
            s.HurtNpc(Civ("hub:civ_01"), W("kestrel"), HitZone.Torso);
        }
        Assert.Equal(NpcStatus.Dead, s.World.Npc("hub:civ_01"));
        Assert.Equal(NpcStatus.Alive, s.World.Npc("hub:civ_02"));
        Assert.NotEqual(Civ("hub:civ_01").Key, Civ("hub:civ_02").Key);
    }

    [Fact]
    public void The_first_hurt_is_assault_once_and_a_death_is_murder()
    {
        var s = TestData.NewGame();
        var before = s.Reputation.Get("mersec");
        var trooper = Npc("mersec_gate");
        s.HurtNpc(trooper, W("kestrel"), HitZone.Torso);
        s.HurtNpc(trooper, W("kestrel"), HitZone.Torso);
        Assert.Equal(before - 15, s.Reputation.Get("mersec"));
        while (!s.HurtNpc(trooper, W("kestrel"), HitZone.Head).Killed)
        {
        }
        Assert.Equal(before - 15 - 50, s.Reputation.Get("mersec"));
    }

    [Fact]
    public void A_dead_body_takes_no_more_damage_and_costs_nothing_more()
    {
        var s = TestData.NewGame();
        var c = Civ("hub:civ_03");
        for (var i = 0; i < 3; i++)
        {
            s.HurtNpc(c, W("kestrel"), HitZone.Torso);
        }
        var rep = s.Reputation.Get("residents");
        Assert.Equal(0, s.HurtNpc(c, W("kestrel"), HitZone.Torso).Damage);
        Assert.Equal(rep, s.Reputation.Get("residents"));
    }

    [Fact]
    public void A_dead_quest_giver_fails_their_quests_and_the_feed_says_why()
    {
        var s = TestData.NewGame();
        var said = new List<string>();
        s.Feed += said.Add;
        s.Quests.Start("t0_arrival");
        while (!s.HurtNpc(Npc("silk"), W("kestrel"), HitZone.Head).Killed)
        {
        }
        Assert.Equal(QuestState.Failed, s.Quests.State("t0_arrival"));
        Assert.Equal(QuestState.Failed, s.Quests.State("m1_rat_trap"));
        Assert.Equal(QuestState.NotStarted, s.Quests.State("s1_kingmaker"));
        Assert.Contains("Silk is dead.", said);
    }

    [Fact]
    public void An_NPCs_health_survives_a_save_and_a_load()
    {
        var s = TestData.NewGame();
        s.HurtNpc(Npc("tank"), W("kestrel"), HitZone.Torso);
        var (loaded, _) = GameState.Load(TestData.Data, SaveGame.FromJson(s.Save().ToJson()));
        Assert.Equal(s.NpcHealth(Npc("tank")), loaded.NpcHealth(Npc("tank")), 6);
        Assert.True(loaded.NpcHealth(Npc("tank")) < 150);
    }

    [Fact]
    public void A_shot_heard_by_MerSec_turns_them_hostile_without_a_warning()
    {
        var s = TestData.NewGame();
        Assert.Equal(Undercity.Core.Perception.LawResponse.Hostile, s.Law.ShotFired());
        Assert.True(s.Law.Hostile);
    }

    [Fact]
    public void A_trooper_burst_hit_costs_18_with_no_armour_and_the_vest_takes_30_percent()
    {
        var s = TestData.NewGame();
        Assert.Equal(18, s.TakeHit(W("mersec_pistol")), 6);
        s.Inventory.Wear(TestData.Data.Items.Get("kevlar_vest"));
        Assert.Equal(18 * 0.7, s.TakeHit(W("mersec_pistol")), 6);
    }

    [Fact]
    public void Health_climbs_back_to_25_five_seconds_after_the_last_hit_and_stops()
    {
        var s = TestData.NewGame();
        while (s.Health.Value > 20)
        {
            s.TakeHit(W("mersec_pistol"));
        }
        var low = s.Health.Value;
        for (var t = 0.0; t < 4.9; t += 0.1)
        {
            s.Tick(0.1);
        }
        Assert.Equal(low, s.Health.Value, 6);
        for (var t = 0.0; t < 20; t += 0.1)
        {
            s.Tick(0.1);
        }
        Assert.Equal(25, s.Health.Value, 6);
    }

    [Fact]
    public void Taking_the_last_of_your_health_kills_you_once()
    {
        var s = TestData.NewGame();
        var deaths = 0;
        s.Died += () => deaths++;
        while (!s.Dead)
        {
            s.TakeHit(W("mersec_pistol"), HitZone.Head);
        }
        Assert.Equal(0, s.TakeHit(W("mersec_pistol")));
        for (var t = 0.0; t < 30; t += 0.1)
        {
            s.Tick(0.1);
        }
        Assert.Equal(1, deaths);
        Assert.Equal(0, s.Health.Value, 6);
    }

    [Fact]
    public void Drowning_kills()
    {
        var s = TestData.NewGame();
        s.SetWater(Undercity.Core.Vitals.WaterContact.Submerged);
        for (var t = 0.0; t < 60 && !s.Dead; t += 0.1)
        {
            s.Tick(0.1);
        }
        Assert.True(s.Dead, "45 s of breath, then 8 a second from 100 health: dead by 57.5 s");
    }

    [Fact]
    public void The_dead_cant_fire()
    {
        var s = TestData.NewGame();
        s.UseBelt(s.Inventory.Belt.ToList().IndexOf("pistol"));
        while (!s.Dead)
        {
            s.TakeHit(W("mersec_pistol"), HitZone.Head);
        }
        Assert.Null(s.Drawn);
        Assert.False(s.FireDrawn());
    }
}
