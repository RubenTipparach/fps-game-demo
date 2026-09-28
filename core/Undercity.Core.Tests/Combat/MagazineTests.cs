// Loaded rounds and the reload rule (openspec/changes/hub-combat, design section 2).

using Undercity.Core.Combat;

namespace Undercity.Core.Tests.Combat;

public class MagazineTests
{
    private static GameState Drawn(int roundsInPack)
    {
        var s = TestData.NewGame();
        s.Inventory.Pack.Remove("ammo_10mm", s.Inventory.Pack.Count("ammo_10mm"));
        if (roundsInPack > 0)
        {
            s.PickUp("ammo_10mm", roundsInPack);
        }
        s.UseBelt(s.Inventory.Belt.ToList().IndexOf("pistol"));
        return s;
    }

    private static void Empty(GameState s)
    {
        while (s.FireDrawn())
        {
        }
    }

    [Fact]
    public void The_Kestrel_comes_loaded_with_the_kits_24_rounds_in_the_pack()
    {
        var s = TestData.NewGame();
        s.UseBelt(s.Inventory.Belt.ToList().IndexOf("pistol"));
        Assert.Equal((12, 24), s.Rounds);
    }

    [Fact]
    public void Twelve_shots_empty_it_and_the_thirteenth_clicks()
    {
        var s = Drawn(24);
        for (var i = 0; i < 12; i++)
        {
            Assert.True(s.FireDrawn(), $"shot {i + 1}");
        }
        Assert.False(s.FireDrawn(), "an empty magazine fires nothing");
        Assert.Equal((0, 24), s.Rounds);
    }

    [Fact]
    public void A_reload_takes_what_fits_from_the_pack()
    {
        var s = Drawn(24);
        Empty(s);
        Assert.Equal(12, s.ReloadDrawn());
        Assert.Equal((12, 12), s.Rounds);
    }

    [Fact]
    public void A_partial_reload_takes_only_what_the_pack_holds()
    {
        var s = Drawn(5);
        Empty(s);
        Assert.Equal(5, s.ReloadDrawn());
        Assert.Equal((5, 0), s.Rounds);
    }

    [Fact]
    public void Reloading_a_full_magazine_takes_nothing()
    {
        var s = Drawn(24);
        Assert.Equal(0, s.ReloadDrawn());
        Assert.Equal((12, 24), s.Rounds);
    }

    [Fact]
    public void With_no_rounds_the_reload_says_so_and_changes_nothing()
    {
        var s = Drawn(0);
        Empty(s);
        var said = new List<string>();
        s.Feed += said.Add;
        Assert.Equal(0, s.ReloadDrawn());
        Assert.Equal((0, 0), s.Rounds);
        Assert.Contains("No rounds.", said);
    }

    [Fact]
    public void Loaded_rounds_survive_a_save_and_a_load()
    {
        var s = Drawn(24);
        for (var i = 0; i < 5; i++)
        {
            s.FireDrawn();
        }
        var (loaded, _) = GameState.Load(TestData.Data, SaveGame.FromJson(s.Save().ToJson()));
        loaded.UseBelt(loaded.Inventory.Belt.ToList().IndexOf("pistol"));
        Assert.Equal((7, 24), loaded.Rounds);
    }

    [Fact]
    public void A_damaged_save_loads_its_magazine_clamped()
    {
        var save = TestData.NewGame().Save();
        save.Magazines = new SortedDictionary<string, int>(StringComparer.Ordinal) { ["pistol"] = 99, ["medkit"] = 3 };
        var (s, repairs) = GameState.Load(TestData.Data, SaveGame.FromJson(save.ToJson()));
        s.UseBelt(s.Inventory.Belt.ToList().IndexOf("pistol"));
        Assert.Equal(12, s.Rounds!.Value.Loaded);
        Assert.Equal(2, repairs.Count(r => r.StartsWith("magazines:", StringComparison.Ordinal)));
    }

    [Fact]
    public void A_version_2_save_loads_every_firearm_full()
    {
        var save = TestData.NewGame().Save();
        save.Version = 2;
        save.Magazines = null;
        var (s, _) = GameState.Load(TestData.Data, SaveGame.FromJson(save.ToJson()));
        s.UseBelt(s.Inventory.Belt.ToList().IndexOf("pistol"));
        Assert.Equal(12, s.Rounds!.Value.Loaded);
    }

    [Fact]
    public void A_melee_weapon_swings_without_rounds()
    {
        var s = TestData.NewGame();
        s.UseBelt(s.Inventory.Belt.ToList().IndexOf("stun_baton"));
        Assert.True(s.FireDrawn());
        Assert.Null(s.Rounds);
    }
}
