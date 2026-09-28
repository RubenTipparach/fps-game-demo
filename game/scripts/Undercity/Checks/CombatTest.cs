// The combat check (scenes/undercity/tests/combat_test.tscn): loads the hub and fires the Kestrel
// with the real keys, the real weapon and the real people (openspec/changes/hub-combat): drawing
// it, a shot's damage by the rule and its zone, a kill that leaves the other civilians alive, a
// shot no trooper hears, civilians fleeing and cowering, the magazine and a reload, Silk
// surrendering and Tank holding at a shot he only hears and fighting when shot, MerSec turning
// hostile at a shot and firing back, and the runner's death fading the screen. Prints PASS or
// FAIL per check and quits with 1 on any failure.
//
//   flock /tmp/undercity-godot.lock timeout 900 godot --headless --path game res://scenes/undercity/tests/combat_test.tscn
//
// It lives beside the entity scripts because it runs the level's own scene. The damage it expects
// is the core's rule applied to data/weapons.json and data/npcs.json, never a copied number; the
// ranges and times are the spec delta's and data/combat.json's.

#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Brushfire;
using Godot;
using Undercity.Core;
using Undercity.Core.Combat;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>The headless combat check.</summary>
public partial class CombatTest : Node3D
{
    /// <summary>The level the runner fights in.</summary>
    [Export] public string LevelScene { get; set; } = "res://levels/undercity/hub/hub.tscn";

    private UndercityLevel? _level;
    private PlayerController? _p;
    private GameState? _s;
    private int _checks;
    private int _fail;

    private PlayerController P => _p!;

    private GameState S => _s!;

    private UndercityLevel L => _level!;

    private float Hz => Engine.PhysicsTicksPerSecond;

    private CombatTable T => S.Data.Combat;

    private WeaponDef Kestrel => S.Data.Weapons.Find("kestrel")!;

    /// <inheritdoc/>
    public override async void _Ready()
    {
        try
        {
            AutoTest.Active = true;     // the keys below drive the body, as a script's would
            _level = GD.Load<PackedScene>(LevelScene).Instantiate<UndercityLevel>();
            AddChild(_level);
            await Ticks(10);
            _p = _level.Player;
            _s = _level.AutoTestState;
            await Drawing();
            await AShotByTheRule();
            await AHeadshot();
            await KillingOneCivilian();
            await PeopleFleeAndCower();
            await TheMagazine();
            await AtTheBar();
            await MerSecAtAShot();
            await Dying();
        }
        catch (Exception e)
        {
            Check("the test ran", false, e.ToString());
        }
        GD.Print($"[combat_test] {_checks - _fail} of {_checks} passed");
        GetTree().Quit(_fail > 0 ? 1 : 0);
    }

    private async Task Ticks(int n)
    {
        for (var i = 0; i < n; i++)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
        }
    }

    private Task Seconds(float s) => Ticks(Mathf.CeilToInt(s * Hz));

    private void Check(string what, bool ok, string detail)
    {
        _checks++;
        if (!ok)
        {
            _fail++;
        }
        GD.Print($"[combat_test] {(ok ? "PASS" : "FAIL")} {what}: {detail}");
    }

    private static float YawTo(Vector3 d) => Mathf.RadToDeg(Mathf.Atan2(-d.X, -d.Z));

    private IEnumerable<NpcActor> Npcs => L.Npcs().Where(n => n.Visible);

    private IEnumerable<NpcActor> Civilians => Npcs.Where(n => n.NpcId == "civ" && n.Alive);

    private float FromLaw(Vector3 p) => Npcs.Where(n => n.IsLaw).Select(n => n.GlobalPosition.DistanceTo(p)).DefaultIfEmpty(float.MaxValue).Min();

    /// <summary>Stands the runner on the navmesh about <paramref name="rangeM"/> from <paramref name="npc"/> with a clear shot at their chest, and aims there.</summary>
    private async Task<bool> StandFacing(NpcActor npc, float rangeM, float aimHeightM = 1.2f)
    {
        var map = npc.GetWorld3D().NavigationMap;
        var target = npc.GlobalPosition + Vector3.Up * aimHeightM;
        for (var i = 0; i < 12; i++)
        {
            var dir = Vector3.Forward.Rotated(Vector3.Up, Mathf.Tau * i / 12);
            var feet = NavigationServer3D.MapGetClosestPoint(map, npc.GlobalPosition + dir * rangeM);
            if (Mathf.Abs(feet.DistanceTo(npc.GlobalPosition) - rangeM) > 1.5f || L.Water.SurfaceAt(feet) is { } w && feet.Y < w)
            {
                continue;
            }
            P.GlobalPosition = feet + Vector3.Up * 0.05f;
            P.Velocity = Vector3.Zero;
            P.ResetPhysicsInterpolation();
            await Ticks(2);
            if (!npc.ClearLine(P.EyePosition))
            {
                continue;
            }
            Aim(target);
            await Ticks(2);
            return true;
        }
        return false;
    }

    private void Aim(Vector3 at)
    {
        var d = at - P.EyePosition;
        var flat = new Vector2(d.X, d.Z).Length();
        P.SetLook(YawTo(d), Mathf.RadToDeg(Mathf.Atan2(d.Y, flat)));
    }

    /// <summary>One pull of the trigger, then the weapon's time between shots.</summary>
    private async Task Fire()
    {
        Input.ActionPress("fire");
        await Ticks(2);
        Input.ActionRelease("fire");
        await Seconds((float)(1 / Kestrel.RatePerS) + 0.05f);
    }

    private async Task Draw()
    {
        if (S.Drawn != "pistol")
        {
            S.UseBelt(S.Inventory.Belt.ToList().IndexOf("pistol"));
        }
        await Seconds(0.4f);     // WeaponManager raises it over 0.22 s
    }

    private static UndercityHud? Hud(Node root) =>
        root.GetChildren().OfType<UndercityHud>().FirstOrDefault() ?? root.GetChildren().Select(Hud).FirstOrDefault(h => h is not null);

    // ------------------------------------------------------------------ the checks

    /// <summary>The belt draws the Kestrel into the hand, and the HUD shows its rounds.</summary>
    private async Task Drawing()
    {
        await Draw();
        var wm = P.GetNode<WeaponManager>("CameraRig/Camera3D/WeaponManager");
        Check("drawing the Kestrel puts it in the runner's hand", wm.Current is { WeaponId: "kestrel" } && wm.Current.Visible,
            $"current {wm.Current?.WeaponId ?? "none"}");
        Check("it comes loaded, the kit's rounds in the pack", S.Rounds == (12, 24), $"{S.Rounds}");
    }

    private NpcActor? _shot;
    private Vector3 _shotFrom;

    /// <summary>"A shot's damage": a torso shot on a civilian takes what the rule says, and no trooper hears it.</summary>
    private async Task AShotByTheRule()
    {
        _shot = Civilians.Where(n => FromLaw(n.GlobalPosition) > Kestrel.NoiseM + 10).OrderBy(n => n.StableId, StringComparer.Ordinal)
            .FirstOrDefault(n => n.Combat!.Defence == Defence.Flee);
        if (_shot is null || !await StandFacing(_shot, 5f))
        {
            Check("a civilian who flees stands where a shot can reach them, away from MerSec", false, "none found");
            return;
        }
        var target = NpcTarget.Civilian(S.Data.Npcs.Civilians, _shot.StableId, _shot.Faction, _shot.DisplayName);
        var before = S.NpcHealth(target);
        var from = P.GlobalPosition;
        _shotFrom = P.EyePosition;
        await Fire();
        var expected = CombatRules.Damage(T, Kestrel, HitZone.Torso, 0, targetIsPlayer: false);
        var taken = before - S.NpcHealth(target);
        Check("a torso shot takes the rule's damage", Mathf.IsEqualApprox((float)taken, (float)expected),
            $"{taken:0.0} of {before:0} (the rule: {expected:0.0})");
        Check("the civilian's health is kept under their own stable id", S.World.NpcHealth.ContainsKey(_shot.StableId),
            $"key {_shot.TargetKey}");
        Check("a shot no trooper hears leaves MerSec calm", !S.Law.Hostile, $"nearest trooper {FromLaw(from):0} m, noise {Kestrel.NoiseM} m");
        await Seconds(0.5f);
        Check("a civilian who flees runs when shot", _shot.Combat!.Mode == NpcMode.Fleeing, $"{_shot.Combat.Mode}");
    }

    /// <summary>"Hit zones": a hit high on the body counts as the head.</summary>
    private async Task AHeadshot()
    {
        var npc = Civilians.Where(n => n != _shot && FromLaw(n.GlobalPosition) > Kestrel.NoiseM + 10)
            .OrderBy(n => n.StableId, StringComparer.Ordinal).FirstOrDefault(n => n.Combat!.Defence == Defence.Cower);
        // 3 m away the Kestrel's 2° spread strays at most 0.105 m: 1.64 m stays within the head band (1.52-1.8).
        if (npc is null || !await StandFacing(npc, 3f, 1.64f))
        {
            Check("a civilian who cowers stands where a shot can reach them", false, "none found");
            return;
        }
        var target = NpcTarget.Civilian(S.Data.Npcs.Civilians, npc.StableId, npc.Faction, npc.DisplayName);
        var before = S.NpcHealth(target);
        await Fire();
        var expected = CombatRules.Damage(T, Kestrel, HitZone.Head, 0, targetIsPlayer: false);
        var taken = before - S.NpcHealth(target);
        Check("a shot at 1.64 m takes the head's damage", Mathf.IsEqualApprox((float)taken, (float)expected),
            $"{taken:0.0} (the rule, head: {expected:0.0})");
        await Seconds(0.8f);
        Check("a civilian who cowers drops where they are", npc.Combat!.Mode == NpcMode.Cowering, $"{npc.Combat.Mode}");
    }

    /// <summary>"Killing a civilian": they die in the world under their own key, and every other civilian lives.</summary>
    private async Task KillingOneCivilian()
    {
        var victim = Civilians.Where(n => FromLaw(n.GlobalPosition) > Kestrel.NoiseM + 10 && n.Combat!.Mode == NpcMode.Calm)
            .OrderBy(n => n.StableId, StringComparer.Ordinal).FirstOrDefault();
        if (victim is null || !await StandFacing(victim, 4f))
        {
            Check("a calm civilian to shoot", false, "none found");
            return;
        }
        var alive = Civilians.Count();
        var repBefore = S.Reputation.Get(victim.Faction);
        for (var i = 0; i < 6 && victim.Alive; i++)
        {
            Aim(victim.GlobalPosition + Vector3.Up * 1.2f);
            await Fire();
        }
        await Seconds(0.3f);
        Check("the civilian dies", !victim.Alive && S.World.Npc(victim.StableId) == NpcStatus.Dead && victim.Collapsed,
            $"{S.World.Npc(victim.StableId)}, collapsed {victim.Collapsed}");
        Check("every other civilian is still alive", Civilians.Count() == alive - 1, $"{Civilians.Count()} of {alive - 1}");
        var cost = T.Reputation.Assault + T.Reputation.Murder;
        Check("killing costs the assault and the murder reputation", S.Reputation.Get(victim.Faction) - repBefore == cost,
            $"{repBefore} to {S.Reputation.Get(victim.Faction)} (the data: {cost})");
    }

    /// <summary>"People flee or cower": the civilian shot first ends at least flee_m from the shot.</summary>
    private async Task PeopleFleeAndCower()
    {
        if (_shot is null)
        {
            return;
        }
        var start = _shot.GlobalPosition;
        for (var i = 0; i < 20 * Hz && _shot.Combat!.Mode == NpcMode.Fleeing; i++)
        {
            await Ticks(1);
        }
        await Seconds(0.2f);
        var away = new Vector2(_shot.GlobalPosition.X - _shotFrom.X, _shot.GlobalPosition.Z - _shotFrom.Z).Length();
        Check("a fleeing civilian ends at least 25 m from the shot, cowering",
            _shot.Combat!.Mode == NpcMode.Cowering && away >= T.FleeM,
            $"{_shot.Combat.Mode}, {away:0.0} m from the shot, {_shot.GlobalPosition.DistanceTo(start):0.0} m run");
    }

    /// <summary>"The magazine": it empties, a dry pull starts the reload, and the reload takes its time.</summary>
    private async Task TheMagazine()
    {
        P.SetLook(0, 60);     // at the sky
        while (S.Rounds is { Loaded: > 0 })
        {
            await Fire();
        }
        var reserve = S.Rounds!.Value.Reserve;
        Input.ActionPress("fire");
        await Ticks(2);
        Input.ActionRelease("fire");
        Check("pulling the trigger on an empty magazine starts a reload", S.Reloading, $"{S.Rounds}");
        var left = (float)S.ReloadLeftS;
        await Seconds(left - 0.1f);
        Check("the reload is still under way before its time", S.Reloading && left > (float)Kestrel.ReloadS - 0.1f,
            $"{S.ReloadLeftS:0.00} s left of {Kestrel.ReloadS} s");
        await Seconds(0.2f);
        var want = Math.Min(Kestrel.Magazine, reserve);
        Check("then the magazine is full from the pack", S.Rounds == (want, reserve - want), $"{S.Rounds}");
        Check("the HUD reads the rounds", Hud(L) is { } hud && hud.GetNode<Label>("%Loaded").Text == $"{want}",
            $"{Hud(L)?.GetNode<Label>("%Loaded").Text}");
    }

    /// <summary>
    /// "A gun drawn on the bar": in the Rusty Anchor a shot into the air makes Silk surrender, and
    /// Tank, who only hears it, holds; a shot at Tank brings him at the runner with his baton.
    /// </summary>
    private async Task AtTheBar()
    {
        var tank = Npcs.FirstOrDefault(n => n.NpcId == "tank");
        var silk = Npcs.FirstOrDefault(n => n.NpcId == "silk");
        if (tank is null || silk is null || !await StandFacing(tank, 5f))
        {
            Check("Tank and Silk in the Rusty Anchor", false, "not found, or no clear shot at Tank");
            return;
        }
        S.Health.Set(S.Health.Max);
        P.SetLook(Mathf.RadToDeg(P.Yaw), 60);     // into the ceiling
        await Fire();
        await Seconds(0.3f);
        Check("a shot heard in the bar makes Silk surrender", silk.Combat!.Mode == NpcMode.Surrendered,
            $"{silk.Combat.Mode}, {silk.GlobalPosition.DistanceTo(P.GlobalPosition):0.0} m away");
        Check("Tank, who only heard it, holds", !tank.Hostile && !tank.Combat!.Fighting, $"hostile {tank.Hostile}");
        Aim(tank.GlobalPosition + Vector3.Up * 1.2f);
        await Fire();
        var hit = false;
        for (var i = 0; i < 8 * Hz && !hit; i++)
        {
            await Ticks(1);
            hit = S.Health.Value < S.Health.Max;
        }
        Check("shot, Tank comes at the runner and lands his baton", tank.Combat!.Fighting && hit,
            $"fighting {tank.Combat.Fighting}, health {S.Health.Value:0}, {tank.GlobalPosition.DistanceTo(P.GlobalPosition):0.0} m away");
    }

    /// <summary>"Gunfire is a crime": a shot a trooper hears turns MerSec hostile, and they fire back.</summary>
    private async Task MerSecAtAShot()
    {
        var trooper = Npcs.Where(n => n.IsLaw && n.Alive).OrderBy(n => n.StableId, StringComparer.Ordinal).FirstOrDefault();
        if (trooper is null || !await StandFacing(trooper, 12f))
        {
            Check("a trooper to be heard by", false, "none found");
            return;
        }
        S.Health.Set(S.Health.Max);
        P.SetLook(YawTo(trooper.GlobalPosition - P.GlobalPosition) + 90, 50);     // a shot into the air
        await Fire();
        Check("a shot a trooper hears makes MerSec hostile at once", S.Law.Hostile && trooper.Hostile,
            $"law {(S.Law.Hostile ? "hostile" : "calm")}, {trooper.DisplayName} {P.GlobalPosition.DistanceTo(trooper.GlobalPosition):0.0} m away");
        var hurt = false;
        for (var i = 0; i < 12 * Hz && !hurt; i++)
        {
            await Ticks(1);
            hurt = S.Health.Value < S.Health.Max;
        }
        Check("a hostile trooper fires back and hits", hurt && trooper.Combat!.Fighting, $"health {S.Health.Value:0}, fighting {trooper.Combat!.Fighting}");
    }

    /// <summary>"Death": at no health the runner dies, and the screen fades to black.</summary>
    private async Task Dying()
    {
        S.Health.Set(1);
        for (var i = 0; i < 20 * Hz && !S.Dead; i++)
        {
            await Ticks(1);
        }
        Check("the runner dies at no health", S.Dead && S.Drawn is null, $"health {S.Health.Value:0}, drawn {S.Drawn ?? "nothing"}");
        await Seconds((float)T.DeathFadeS * 0.5f);
        var fade = Hud(L)?.GetNode<Control>("%Fade");
        Check("the screen fades to black over the death fade", fade is { Visible: true } && fade.Modulate.A is > 0.2f and < 0.9f,
            $"alpha {fade?.Modulate.A:0.00} half way");
    }
}
