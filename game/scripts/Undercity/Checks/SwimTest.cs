// The water check (scenes/undercity/tests/swim_test.tscn): loads the hub and drives the runner
// through the water with the real keys, the real body and the real level (openspec/changes/
// water-and-swimming): falling off the quay by the Tin Bridge and floating, swimming speed, a dive
// and breath, climbing out by a quay ladder, climbing back down it, a mantle onto a moored boat,
// a body that floats and an item that sinks. Prints PASS or FAIL per check and quits with 1 on any
// failure.
//
//   flock /tmp/undercity-godot.lock timeout 600 godot --headless --path game res://scenes/undercity/tests/swim_test.tscn
//
// It lives beside the entity scripts because it runs the level's own scene; the numbers it expects
// are the requirement's (the spec delta), and the ones it moves by are data/water.json's.

#nullable enable
using System;
using System.Linq;
using System.Threading.Tasks;
using Brushfire;
using Godot;
using Undercity.Core;
using Undercity.Core.Vitals;

namespace Undercity.Client;

/// <summary>The headless water check.</summary>
public partial class SwimTest : Node3D
{
    /// <summary>The level the runner swims in.</summary>
    [Export] public string LevelScene { get; set; } = "res://levels/undercity/hub/hub.tscn";

    private UndercityLevel? _level;
    private PlayerController? _p;
    private PlayerWater? _w;
    private GameState? _s;
    private int _checks;
    private int _fail;

    private PlayerController P => _p!;

    private PlayerWater W => _w!;

    private GameState S => _s!;

    private float Hz => Engine.PhysicsTicksPerSecond;

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
            _w = _p.GetNode<PlayerWater>("Water");
            _s = _level.AutoTestState;
            await FallingIn();
            await SwimmingSpeed();
            await TiredSwimming();
            await NoWeaponWhileSwimming();
            await Diving();
            await OutByTheLadder();
            await OntoTheShip();
            await DownTheLadder();
            await OntoABoat();
            await ABodyFloats();
            await AnItemSinks();
        }
        catch (Exception e)
        {
            Check("the test ran", false, e.ToString());
        }
        GD.Print($"[swim_test] {_checks - _fail} of {_checks} passed");
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
        GD.Print($"[swim_test] {(ok ? "PASS" : "FAIL")} {what}: {detail}");
    }

    private static float YawTo(Vector3 d) => Mathf.RadToDeg(Mathf.Atan2(-d.X, -d.Z));

    private float Surface => _level!.Water.SurfaceAt(P.GlobalPosition) ?? float.NaN;

    /// <summary>Puts the runner's feet at <paramref name="feet"/>, still, looking along <paramref name="look"/>.</summary>
    private async Task Place(Vector3 feet, Vector3 look, float pitchDeg = 0f)
    {
        ReleaseAll();
        P.GlobalPosition = feet;
        P.Velocity = Vector3.Zero;
        P.SetLook(YawTo(look), pitchDeg);
        P.ResetPhysicsInterpolation();
        await Ticks(2);
    }

    /// <summary>Puts a swimmer at the surface at (x, z), floating, looking along <paramref name="look"/>.</summary>
    private async Task Float(float x, float z, Vector3 look)
    {
        var s = _level!.Water.SurfaceAt(new Vector3(x, 0, z)) ?? throw new InvalidOperationException($"no water at {x}, {z}");
        await Place(new Vector3(x, s + (float)S.Data.Water.FloatEyeAboveM - (P.EyePosition.Y - P.GlobalPosition.Y), z), look);
        await Seconds(0.5f);
    }

    private static void ReleaseAll()
    {
        foreach (var a in new[] { "move_forward", "move_back", "move_left", "move_right", "jump", "crouch" })
        {
            Input.ActionRelease(a);
        }
    }

    private async Task Press(string action)
    {
        Input.ActionPress(action);
        await Ticks(2);
        Input.ActionRelease(action);
    }

    /// <summary>A quay ladder on the Cut's west bank that climbs over the quay's kerb to the street behind it.</summary>
    private const string KerbedLadder = "the_cut_5";

    private Ladder LadderNamed(string id) => GetTree().GetNodesInGroup("ladders").OfType<Ladder>()
        .FirstOrDefault(l => l.HasMeta("id") && l.GetMeta("id").AsString() == id)
        ?? throw new InvalidOperationException($"no ladder '{id}' in the level");

    // ------------------------------------------------------------------ the checks

    /// <summary>"Falling in": off the quay by the Tin Bridge, floating within 2 s.</summary>
    private async Task FallingIn()
    {
        await Place(new Vector3(191.3f, 0.2f, 66f), Vector3.Right);
        Input.ActionPress("move_forward");
        var crossed = -1;
        for (var i = 0; i < Hz * 3 && crossed < 0; i++)
        {
            await Ticks(1);
            if (P.GlobalPosition.Y < Surface)
            {
                crossed = i;
            }
        }
        ReleaseAll();
        Check("the runner walks off the quay into the Cut", crossed >= 0, $"feet at {P.GlobalPosition.Y:0.00} m, surface {Surface:0.00} m");
        await Seconds(2f);
        var above = P.EyePosition.Y - Surface;
        Check("within 2 s they float with their eyes 0.10-0.20 m above the surface", above >= 0.10f && above <= 0.20f && W.Swimming,
            $"eyes {above:0.000} m above, {W.Contact}");
        Check("falling in doesn't hurt", S.Health.Value >= S.Health.Max, $"health {S.Health.Value:0.0}");
    }

    /// <summary>"Falling in": swimming forward moves them at 2.9-3.1 m/s.</summary>
    private async Task SwimmingSpeed()
    {
        await Float(203f, 70f, Vector3.Back);
        Input.ActionPress("move_forward");
        await Seconds(1.5f);
        var a = P.GlobalPosition;
        await Seconds(0.5f);
        var b = P.GlobalPosition;
        ReleaseAll();
        var speed = new Vector2(b.X - a.X, b.Z - a.Z).Length() / (Mathf.CeilToInt(0.5f * Hz) / Hz);
        Check("swimming forward moves at 2.9-3.1 m/s", speed >= 2.9f && speed <= 3.1f, $"{speed:0.00} m/s");
        Check("swimming stays at the surface looking level", Mathf.Abs(b.Y - a.Y) < 0.05f, $"rose {b.Y - a.Y:0.000} m");
    }

    /// <summary>"A long swim": with no stamina left, the runner swims at 1.4-1.6 m/s.</summary>
    private async Task TiredSwimming()
    {
        await Float(203f, 70f, Vector3.Back);
        S.Stamina.Set(0);
        Input.ActionPress("move_forward");
        await Seconds(1.5f);
        var a = P.GlobalPosition;
        await Seconds(0.5f);
        var b = P.GlobalPosition;
        ReleaseAll();
        var speed = new Vector2(b.X - a.X, b.Z - a.Z).Length() / (Mathf.CeilToInt(0.5f * Hz) / Hz);
        Check("a swimmer with no stamina left swims at 1.4-1.6 m/s", speed >= 1.4f && speed <= 1.6f, $"{speed:0.00} m/s");
        S.Stamina.Set(S.Stamina.Max);
    }

    /// <summary>"Drawing in deep water": the belt refuses, and says why.</summary>
    private async Task NoWeaponWhileSwimming()
    {
        await Float(203f, 90f, Vector3.Forward);
        S.PickUp("pistol", 1);
        var slot = S.Inventory.Belt.ToList().IndexOf("pistol");
        var result = slot >= 0 ? S.UseBelt(slot) : BeltResult.Refused;
        Check("the belt refuses to draw while swimming", slot >= 0 && result == BeltResult.Refused && S.Drawn is null,
            $"slot {slot}, {result}, drawn {S.Drawn ?? "nothing"}");
    }

    /// <summary>A dive: crouch goes under, breath drains; up again, it refills in 3 s.</summary>
    private async Task Diving()
    {
        await Float(203f, 100f, Vector3.Forward);
        var full = S.Breath.Value;
        Input.ActionPress("crouch");
        await Seconds(1.5f);
        Input.ActionRelease("crouch");
        Check("crouch dives under the surface", W.Contact == WaterContact.Submerged, $"{W.Contact}, eyes {P.EyePosition.Y - Surface:0.00} m");
        await Seconds(2f);
        var drained = full - S.Breath.Value;
        Check("breath drains under water", drained > 2.5f && drained < 4.5f, $"{drained:0.00} s of breath used in about 3.5 s");
        var rose = await Until(() => W.Contact < WaterContact.Submerged, "jump", 4f);
        Check("jump rises to the surface", rose, $"{W.Contact}");
        await Seconds(3.1f);
        Check("breath refills in 3 s at the surface", S.Breath.Full, $"{S.Breath.Value:0.00} of {S.Breath.Max:0}");
    }

    private async Task<bool> Until(Func<bool> done, string action, float maxS)
    {
        Input.ActionPress(action);
        for (var i = 0; i < maxS * Hz; i++)
        {
            await Ticks(1);
            if (done())
            {
                Input.ActionRelease(action);
                return true;
            }
        }
        Input.ActionRelease(action);
        return false;
    }

    /// <summary>"Out by the ladder": facing a quay ladder with forward held, standing on the quay within 2 s.</summary>
    private async Task OutByTheLadder()
    {
        var l = LadderNamed(KerbedLadder);
        var start = l.HoldPoint(0.4f, 0) - l.Into * 0.3f;
        await Float(start.X, start.Z, l.Into);
        var t0 = Time.GetTicksMsec();
        var ticks = 0;
        Input.ActionPress("move_forward");
        var climbed = false;
        for (; ticks < Hz * 3 && !climbed; ticks++)
        {
            await Ticks(1);
            var p = P.GlobalPosition;
            climbed = !W.Climbing && P.IsOnFloor() && Mathf.Abs(p.Y - l.FloorM) < 0.1f && (p - l.GlobalPosition).Dot(l.Into) > 0.3f;
        }
        ReleaseAll();
        Check("facing a quay ladder with forward held climbs out onto the quay within 2 s", climbed && ticks <= Hz * 2,
            $"{ticks / Hz:0.00} s, feet {P.GlobalPosition.Y:0.00} m, floor {l.FloorM:0.00} m ({Time.GetTicksMsec() - t0} ms wall)");
    }

    /// <summary>The dry dock's derelict ship: its boarding ladder climbs from the basin to the deck.</summary>
    private async Task OntoTheShip()
    {
        var l = LadderNamed("dry_dock_hull_3");
        var start = l.HoldPoint(0.4f, 0) - l.Into * 0.3f;
        await Float(start.X, start.Z, l.Into);
        Input.ActionPress("move_forward");
        var aboard = false;
        for (var i = 0; i < Hz * 3 && !aboard; i++)
        {
            await Ticks(1);
            aboard = !W.Climbing && P.IsOnFloor() && Mathf.Abs(P.GlobalPosition.Y - l.FloorM) < 0.1f;
        }
        ReleaseAll();
        Check("the ship's boarding ladder climbs from the basin onto its deck", aboard,
            $"feet {P.GlobalPosition.Y:0.00} m, deck {l.TopM:0.00} m");
    }

    /// <summary>From the quay, "Climb down" takes hold at the top, and back climbs into the water.</summary>
    private async Task DownTheLadder()
    {
        var l = LadderNamed(KerbedLadder);
        await Place(l.Landing + Vector3.Up * 0.05f, -l.Into, -30f);
        await Ticks(5);
        Check("the ladder offers \"Climb down\" from the floor at its top", W.CanClimbDown(l) && l.Describe().Prompt == "Climb down",
            $"\"{l.Describe().Prompt}\"");
        l.Use();
        var down = await Until(() => W.Swimming, "move_back", 4f);
        await Seconds(1f);
        var above = P.EyePosition.Y - Surface;
        Check("back climbs down into the water and lets go, floating", down && !W.Climbing && above > 0.05f && above < 0.3f,
            $"{W.Contact}, climbing {W.Climbing}, eyes {above:0.00} m above the surface");
    }

    /// <summary>"Onto a boat": jumping in front of a moored boat's deck, 0.5 m above the surface.</summary>
    private async Task OntoABoat()
    {
        // the hub's first moored boat: its east side runs x 197.5, z 78-90; its deck is the surface + 0.5 m
        await Float(198.35f, 84f, Vector3.Left);
        await Press("jump");
        await Seconds(1f);
        var deck = Surface + 0.5f;
        var p = P.GlobalPosition;
        Check("jumping in front of a boat's deck climbs onto it", P.IsOnFloor() && Mathf.Abs(p.Y - deck) < 0.1f && p.X < 197.5f,
            $"feet {p.Y:0.00} m (deck {deck:0.00} m) at x {p.X:0.00}");
    }

    /// <summary>"A body in the Cut": a ragdoll in the water floats and comes to rest at the surface.</summary>
    private async Task ABodyFloats()
    {
        var npc = _level!.Npcs().OrderBy(n => n.GlobalPosition.DistanceTo(new Vector3(196f, 0f, 100f))).First();
        var s = _level.Water.SurfaceAt(new Vector3(203f, 0f, 110f))!.Value;
        npc.GlobalPosition = new Vector3(203f, s + 1.5f, 110f);
        await Ticks(2);
        npc.Collapse(Vector3.Down * 5f);
        var bones = npc.FindChildren("*", "PhysicalBone3D", true, false).OfType<Node3D>().ToArray();
        float Mean() => bones.Select(b => b.GlobalPosition.Y - s).DefaultIfEmpty().Average();
        var last = Mean();
        var moved = float.MaxValue;
        for (var i = 1; i <= 16; i++)
        {
            await Seconds(0.5f);
            var now = Mean();
            moved = Mathf.Abs(now - last);
            last = now;
            GD.Print($"[swim_test]   body at {i * 0.5f:0.0} s: bones {now:0.00} m from the surface on average");
        }
        var ys = bones.Select(b => b.GlobalPosition.Y - s).ToArray();
        Check("a body in the Cut floats at the surface and comes to rest there within 8 s",
            bones.Length > 0 && ys.Min() > -0.8f && ys.Max() < 0.6f && moved < 0.05f,
            bones.Length == 0 ? "no ragdoll bones" : $"{bones.Length} bones, {ys.Min():0.00} to {ys.Max():0.00} m from the surface, moving {moved / 0.5f:0.000} m/s");
    }

    /// <summary>"A dropped medkit": an item dropped while swimming sinks to the bed.</summary>
    private async Task AnItemSinks()
    {
        await Float(203f, 118f, Vector3.Forward);
        S.PickUp("medkit", 1);
        _level!.DropAtPlayer("medkit", 1, null);
        var bed = -4.5f;
        await Seconds(6f);
        var item = _level.GetChildren().OfType<WorldItem>().LastOrDefault();
        Check("an item dropped while swimming sinks to the bed", item is not null && Mathf.Abs(item.GlobalPosition.Y - bed) < 0.15f,
            item is null ? "no item" : $"at {item.GlobalPosition.Y:0.00} m, the bed {bed:0.00} m");
    }
}
