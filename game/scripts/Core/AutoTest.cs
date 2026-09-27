using System.Linq;
using System.Threading.Tasks;
using Godot;

namespace Brushfire;

/// <summary>
/// Scripted playtest / screenshot runner, enabled with BRUSHFIRE_AUTOTEST=/path/script.json.
/// Used to smoke-test levels headlessly (under Xvfb) and to capture screenshots.
///
/// Script: { "level": 0, "out": "/tmp/shots", "god": true, "steps": [ step, ... ] }
/// Steps:  {"wait": frames} | {"teleport": [x,y,z], "yaw": deg, "pitch": deg} | {"shot": "name.png"}
///         {"debug_draw": 1} (unshaded, for checking geometry before a bake) | {"freeze": true} (enemies)
///         {"hold": "action", "frames": n} | {"press": "action"} | {"give": "all"} | {"weapon": slot}
///         {"log": "text"} | {"stats": true} | {"level": index} | {"quit": true}
/// </summary>
public partial class AutoTest : Node
{
    public static bool Active { get; private set; }
    public static bool God { get; private set; }

    string _out = "user://autotest";

    public override void _Ready()
    {
        Active = true;
        ProcessMode = ProcessModeEnum.Always;
        _ = Run(OS.GetEnvironment("BRUSHFIRE_AUTOTEST"));
    }

    async Task Frames(int n)
    {
        for (int i = 0; i < n; i++)
            await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
    }

    async Task Run(string scriptPath)
    {
        var text = FileAccess.GetFileAsString(scriptPath);
        var json = Json.ParseString(text).AsGodotDictionary();
        if (json.TryGetValue("out", out var o))
            _out = o.AsString();
        DirAccess.MakeDirRecursiveAbsolute(_out);
        God = json.TryGetValue("god", out var g) && g.AsBool();
        await Frames(5);
        if (json.TryGetValue("level", out var lvl))
            await LoadLevel(lvl.AsInt32());

        foreach (var stepVar in json["steps"].AsGodotArray())
        {
            var step = stepVar.AsGodotDictionary();
            var player = PlayerController.Instance;
            if (step.TryGetValue("level", out var li))
                await LoadLevel(li.AsInt32());
            if (step.TryGetValue("wait", out var w))
                await Frames(w.AsInt32());
            if (step.TryGetValue("teleport", out var tp) && player != null)
            {
                var a = tp.AsGodotArray();
                player.GlobalPosition = new Vector3((float)a[0], (float)a[1], (float)a[2]);
                player.Velocity = Vector3.Zero;
                player.SetLook(step.TryGetValue("yaw", out var yaw) ? (float)yaw.AsDouble() : 0f,
                    step.TryGetValue("pitch", out var pitch) ? (float)pitch.AsDouble() : 0f);
                player.ResetPhysicsInterpolation();
                await Frames(3);
            }
            if (step.TryGetValue("give", out _) && player != null)
            {
                player.Weapons.GiveWeapon(2, 200);
                player.Weapons.GiveWeapon(3, 20);
                player.Weapons.GiveAmmo(AmmoType.Shells, 50);
            }
            if (step.TryGetValue("weapon", out var ws) && player != null)
                player.Weapons.SwitchTo(player.Weapons.All.FirstOrDefault(x => x.Slot == ws.AsInt32()));
            if (step.TryGetValue("hold", out var action))
            {
                int frames = step.TryGetValue("frames", out var f) ? f.AsInt32() : 30;
                Input.ActionPress(action.AsString());
                await Frames(frames);
                Input.ActionRelease(action.AsString());
            }
            if (step.TryGetValue("press", out var pa))
            {
                Input.ActionPress(pa.AsString());
                await Frames(2);
                Input.ActionRelease(pa.AsString());
            }
            if (step.TryGetValue("shot", out var shot))
            {
                await ToSignal(RenderingServer.Singleton, RenderingServer.SignalName.FramePostDraw);
                var img = GetViewport().GetTexture().GetImage();
                string file = _out.PathJoin(shot.AsString());
                img.SavePng(file);
                GD.Print($"[AutoTest] screenshot {file}");
            }
            if (step.TryGetValue("freeze", out _))    // stop enemies walking into screenshots
                foreach (var e in GetTree().GetNodesInGroup("enemies"))
                    ((Node)e).ProcessMode = ProcessModeEnum.Disabled;
            if (step.TryGetValue("debug_draw", out var dd))    // 0 normal, 1 unshaded (geometry checks before a bake)
                GetViewport().DebugDraw = (Viewport.DebugDrawEnum)dd.AsInt32();
            if (step.TryGetValue("log", out var msg))
                GD.Print($"[AutoTest] {msg}");
            if (step.TryGetValue("stats", out _))
            {
                var s = Game.Instance.Stats;
                var p = PlayerController.Instance;
                GD.Print($"[AutoTest] kills {s.Kills}/{s.TotalEnemies} secrets {s.Secrets}/{s.TotalSecrets} " +
                         $"shots {s.ShotsHit}/{s.ShotsFired} player hp {p?.Health} armor {p?.Armor} pos {p?.GlobalPosition} " +
                         $"alive enemies {GetTree().GetNodesInGroup("enemies").Count} fps {Engine.GetFramesPerSecond()}");
            }
            if (step.TryGetValue("quit", out _))
            {
                GetTree().Quit();
                return;
            }
        }
        GetTree().Quit();
    }

    async Task LoadLevel(int index)
    {
        Game.Instance.StartLevel(index);
        await Frames(10);
        while (PlayerController.Instance == null)
            await Frames(1);
        await Frames(10);
        GD.Print($"[AutoTest] loaded level {index}: {Game.Levels[index].Title}");
    }
}
