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
/// Undercity: {"scene": "res://levels/undercity/hub/hub.tscn"} | {"key": "1"} (a raw key press)
///         {"goto": "hub:tank", "distance": m} (stand facing a stable entity) | {"talk": "tank"}
///         {"setup": {"credits": n, "items": ["id:n"], "wear": ["id"], "flags": [..], "skills": {"persuasion": 2},
///                    "quests": [..], "health": n}} | {"state": true} (log the run)
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
            if (step.TryGetValue("scene", out var sc))
                await LoadScene(sc.AsString());
            await UndercityStep(step);
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

    async Task LoadScene(string path)
    {
        GetTree().CallDeferred(SceneTree.MethodName.ChangeSceneToFile, path);
        await Frames(10);
        while (PlayerController.Instance == null)
            await Frames(1);
        await Frames(10);
        GD.Print($"[AutoTest] loaded scene {path}");
    }

    /// <summary>Undercity steps. The runner is a test harness, so it reads the level's state directly.</summary>
    async Task UndercityStep(Godot.Collections.Dictionary step)
    {
        var level = GetTree().CurrentScene as Undercity.Client.UndercityLevel;
        var state = level?.AutoTestState;
        if (step.TryGetValue("key", out var k))
        {
            var code = OS.FindKeycodeFromString(k.AsString());
            Input.ParseInputEvent(new InputEventKey { Keycode = code, PhysicalKeycode = code, Pressed = true });
            await Frames(2);
            Input.ParseInputEvent(new InputEventKey { Keycode = code, PhysicalKeycode = code, Pressed = false });
            await Frames(2);
        }
        if (level == null || state == null)
            return;
        if (step.TryGetValue("setup", out var su))
        {
            var d = su.AsGodotDictionary();
            if (d.TryGetValue("credits", out var cr))
                state.Inventory.Earn(cr.AsInt32());
            if (d.TryGetValue("health", out var hp))
                state.Health.Set(hp.AsDouble());
            if (d.TryGetValue("items", out var items))
                foreach (var spec in items.AsGodotArray())
                {
                    var (id, n) = Undercity.Core.GameState.ParseSpec(spec.AsString());
                    state.PickUp(id, n);
                }
            if (d.TryGetValue("wear", out var wear))
                foreach (var id in wear.AsGodotArray())
                    state.Inventory.Wear(state.Data.Items.Get(id.AsString()));
            if (d.TryGetValue("flags", out var flags))
                foreach (var f in flags.AsGodotArray())
                    state.World.SetFlag(f.AsString());
            if (d.TryGetValue("quests", out var quests))
                foreach (var q in quests.AsGodotArray())
                    state.Quests.Start(q.AsString());
            if (d.TryGetValue("skills", out var skills))
                foreach (var (name, rank) in skills.AsGodotDictionary())
                {
                    var skill = System.Enum.Parse<Undercity.Core.Progression.Skill>(name.AsString(), true);
                    state.Character.AddSkillPoints(20);
                    while (state.Character.Rank(skill) < rank.AsInt32() && state.Character.Raise(skill)) { }
                }
        }
        if (step.TryGetValue("goto", out var g) && level.FindStable(g.AsString()) is { } target)
        {
            float dist = step.TryGetValue("distance", out var dv) ? (float)dv.AsDouble() : 1.8f;
            var fwd = -target.GlobalBasis.Z;
            fwd.Y = 0;
            fwd = fwd.LengthSquared() > 0 ? fwd.Normalized() : Vector3.Forward;
            var p = PlayerController.Instance;
            p.GlobalPosition = target.GlobalPosition + fwd * dist + Vector3.Up * 0.05f;
            p.Velocity = Vector3.Zero;
            var yaw = Mathf.RadToDeg(Mathf.Atan2(fwd.X, fwd.Z));
            p.SetLook(yaw, step.TryGetValue("pitch", out var pv) ? (float)pv.AsDouble() : -10f);
            p.ResetPhysicsInterpolation();
            await Frames(3);
        }
        if (step.TryGetValue("talk", out var npcId))
        {
            var npc = level.Npcs().FirstOrDefault(n => n.NpcId == npcId.AsString());
            npc?.Use();
            await Frames(3);
        }
        if (step.TryGetValue("state", out _))
        {
            var c = state.Character;
            GD.Print($"[AutoTest] state: level {c.Level} xp {c.Xp}/{c.XpToNext} points {c.SkillPoints} credits {state.Inventory.Credits} " +
                     $"health {state.Health.Value:0}/{state.Health.Max:0} drawn {state.Drawn ?? "-"} law {(state.Law.Hostile ? "hostile" : "calm")}");
            GD.Print($"[AutoTest] pack: {string.Join(", ", state.Inventory.Pack.Stacks.Select(x => $"{x.Def.Id}x{x.Count}{(x.StolenFrom != null ? "(stolen)" : "")}"))}");
            GD.Print($"[AutoTest] flags: {string.Join(", ", state.World.Flags)}");
            GD.Print($"[AutoTest] quests: {string.Join(", ", state.Quests.Table.Quests.Where(q => state.Quests.State(q.Id) != Undercity.Core.Quests.QuestState.NotStarted).Select(q => $"{q.Id}={state.Quests.State(q.Id)}"))}");
            GD.Print($"[AutoTest] rep: {string.Join(", ", state.Data.Factions.Factions.Select(f => $"{f.Id} {state.Reputation.Get(f.Id)}"))}");
        }
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
