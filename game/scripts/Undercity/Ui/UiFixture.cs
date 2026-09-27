// Test support for the UI checks (ui_size_test.tscn, ui_capture.tscn): a run on the real data, a
// level host that is only a stub, and a staged mid-game state (disguised, a weapon drawn, quests
// under way) so every screen has something real to show.
//
// It lives beside the screens because it builds exactly what the level loader hands them
// (Services); nothing in it is used in play.

#nullable enable
using System.Collections.Generic;
using System.Linq;
using Godot;
using Undercity.Core;
using Undercity.Core.Perception;
using Undercity.Core.Progression;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>A level with no scene: it records drops and is never witnessed.</summary>
public sealed class StubLevelHost : ILevelHost
{
    /// <summary>A stub for <paramref name="def"/>.</summary>
    public StubLevelHost(LevelDef def) => Def = def;

    /// <summary>What was dropped: item id and count.</summary>
    public List<(string Item, int Count)> Dropped { get; } = new();

    /// <inheritdoc/>
    public string Id => Def.Id;

    /// <inheritdoc/>
    public LevelDef Def { get; }

    /// <summary>No body: the HUD's compass stays where it is.</summary>
    public Brushfire.PlayerController Player => null!;

    /// <inheritdoc/>
    public Vector3 PlayerEye => Vector3.Zero;

    /// <inheritdoc/>
    public void Travel(ExitDef exit)
    {
    }

    /// <inheritdoc/>
    public void DropAtPlayer(string itemId, int count, string? stolenFrom) => Dropped.Add((itemId, count));

    /// <inheritdoc/>
    public double RestrictedS => 0;

    /// <inheritdoc/>
    public void SetRestricted(string zoneId, double seconds)
    {
    }

    /// <inheritdoc/>
    public bool CrimeWitnessed(out string witness)
    {
        witness = "";
        return false;
    }
}

/// <summary>Builds the services and the staged state for the UI checks.</summary>
public static class UiFixture
{
    /// <summary>The seed of the staged run.</summary>
    public const ulong Seed = 7;

    /// <summary>A new run on the real data (seed <see cref="Seed"/>), in the hub, wired to <paramref name="screens"/>.</summary>
    public static Services NewServices(IScreens screens)
    {
        var data = GameData.Load(new GodotDataSource());
        var state = GameState.NewGame(data, Seed);
        var saves = new SaveStore(ProjectSettings.GlobalizePath("user://ui_check_saves"));
        return new Services(state, new StubLevelHost(data.Levels["hub"]), screens, saves);
    }

    /// <summary>
    /// Stages the run like the mockups' "In the Drains, disguised": the Drain Rats outfit worn,
    /// level 3, Deception 2, the Kestrel drawn, some damage taken, quests under way.
    /// </summary>
    public static void Stage(GameState s)
    {
        foreach (var (id, n) in new[]
        {
            ("rat_jacket", 1), ("rat_respirator", 1), ("rat_goggles", 1), ("dart_pistol", 1), ("ammo_darts", 9),
            ("emp_grenade", 2), ("noodles", 2), ("data_shard", 1), ("synth_whisky", 1), ("sewer_service_key", 1),
            ("pump_room_key", 1), ("neural_chip", 1), ("ammo_10mm", 12),
        })
        {
            s.PickUp(id, n);
        }
        foreach (var id in new[] { "rat_jacket", "rat_respirator" })
        {
            s.Inventory.Equip(s.Inventory.Pack.Stacks.First(x => x.Def.Id == id));
        }
        s.Inventory.SetBelt(5, "lockpick");
        s.Inventory.SetBelt(6, "multitool");
        s.Character.AddXp(1850, "ui_check", "staged");
        s.Character.Raise(Skill.Deception);
        s.Character.Raise(Skill.Stealth);
        s.Character.Raise(Skill.Lockpicking);
        s.Quests.Start("t0_arrival");
        s.CompleteObjective("t0_arrival/meet_silk");
        s.CompleteQuest("t0_arrival");
        s.Quests.Start("m1_rat_trap");
        s.CompleteObjective("m1_rat_trap/petra");
        s.CompleteObjective("m1_rat_trap/enter");
        s.Quests.Reveal("m1_rat_trap/find");
        s.Quests.Start("s3_mouses_debt");
        s.UseBelt(1);
        s.Health.Lose(28);
    }

    /// <summary>The HUD's level-driven parts as in the F11 mockup: Twitch looking twice, a lock in front.</summary>
    public static void StageHud(Services services)
    {
        var s = services.State;
        var twitch = s.Judge(new Observer("drain_rats", 3), new Situation(7));
        services.Screens.ShowDisguise(new DisguiseView(UiText.Faction(s.Data, "drain_rats"), twitch, "Twitch", 3, 7));
        services.Screens.ShowPrompt("Pick cage, tier 2 (hold 2.0 s)", true);
        services.Screens.ShowHold(0.4);
        services.Screens.Bark("Twitch", "Oi. Where'd Mother say you were posted?");
        services.Screens.ShowAlert("MerSec: Put it away.");
    }

    /// <summary>Every node under <paramref name="root"/>, depth first, including ones added at runtime.</summary>
    public static IEnumerable<Node> Descendants(Node root)
    {
        foreach (var c in root.GetChildren())
        {
            yield return c;
            foreach (var d in Descendants(c))
            {
                yield return d;
            }
        }
    }

    /// <summary>A terminal with every part filled: several pages, a long body and actions.</summary>
    public static TerminalDef BusyTerminal(GameData data)
    {
        var real = data.Levels["hub"].Terminals["hub:capsule_terminal"];
        return new TerminalDef
        {
            Title = real.Title,
            Pages = real.Pages,
            Actions = new[] { new TerminalAction { Label = "Open the locker" }, new TerminalAction { Label = "Print the rent slip" } },
        };
    }
}
