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
///         {"render_scale": 0.67} (the 3D view's resolution scale, for long captures on lavapipe)
///         {"shot": "tank.png", "face_box": "hub:tank"} (also writes tank.png.face.json: the head's box on screen)
///         {"rig": false} (conversations without the character lighting, the rig and the wrist glow: before and after)
///         {"skin_before_wetness": true} (skin as it was before wetness, the mask everywhere; false: the data's again)
///         {"hold": "action" | ["action", ...], "frames": n} | {"press": "action"} | {"give": "all"} | {"weapon": slot}
///         {"log": "text"} | {"stats": true} | {"level": index} | {"quit": true}
/// Undercity: {"scene": "res://levels/undercity/hub/hub.tscn"} | {"key": "1"} (a raw key press)
///         {"goto": "hub:tank", "distance": m} (stand facing a stable entity) | {"talk": "tank"}
///         {"setup": {"credits": n, "items": ["id:n"], "wear": ["id"], "flags": [..], "skills": {"persuasion": 2},
///                    "quests": [..], "health": n, "breath": s, "stamina": n}} | {"state": true} (log the run and the water)
///         {"click": "SaveHere"} (press a button by node name: title, pause, save rows by slot)
///         {"kill": "tank" | "hub:civ_01", "at": [x,y,z]} (the NPC dies and its body falls, from "at" if given;
///                    test only until combat lands) | {"look": [yaw, pitch]} (turn without moving)
///         {"face": [x,y,z]} (look at a point) | {"walk_to": [x,z], "within": m, "max": frames} (steer there, forward held)
///         {"hide": "node"} | {"show": "node"} (a node of the running scene, by name) | {"camera": [x,y,z], "look_at": [x,y,z]}
///                    (a free camera; {"camera": false}: the player's again): openspec/changes/vehicle-fixes, design
///                    section 2.3, the ground under a parked car seen from above with the car hidden
/// </summary>
public partial class AutoTest : Node
{
    /// <summary>True while a script drives the game: here, or the headless water test (Undercity's SwimTest).</summary>
    public static bool Active { get; internal set; }
    public static bool God { get; private set; }

    string _out = "user://autotest";

    public override void _Ready()
    {
        Active = true;
        ProcessMode = ProcessModeEnum.Always;
        _ = Run(OS.GetEnvironment("BRUSHFIRE_AUTOTEST"));
    }

    Camera3D _freeCam;

    /// <summary>Hides or shows every drawn node of the running scene with this name (a measurement
    /// instrument: openspec/changes/vehicle-fixes, design section 2.3). A marker of the same name
    /// draws nothing, so it's left alone.</summary>
    void ShowNode(string name, bool visible)
    {
        var found = GetTree().CurrentScene?.FindChildren(name, nameof(GeometryInstance3D), true, false)
            .OfType<GeometryInstance3D>().ToList();
        if (found == null || found.Count == 0)
            GD.PrintErr($"[AutoTest] no drawn node {name} to {(visible ? "show" : "hide")}");
        foreach (var n in found ?? new())
            n.Visible = visible;
    }

    /// <summary>A free camera at a point looking at another, made current; false hands the view
    /// back to the player's camera (a measurement instrument: openspec/changes/vehicle-fixes, design
    /// section 2.3).</summary>
    void FreeCamera(Variant at, Variant lookAt)
    {
        if (at.VariantType == Variant.Type.Bool)
        {
            _freeCam?.QueueFree();
            _freeCam = null;
            PlayerController.Instance?.GetNodeOrNull<Camera3D>("CameraRig/Camera3D")?.MakeCurrent();
            return;
        }
        if (_freeCam == null)
        {
            _freeCam = new Camera3D { Name = "AutoTestCamera" };
            GetTree().CurrentScene.AddChild(_freeCam);
        }
        var a = at.AsGodotArray();
        var l = lookAt.AsGodotArray();
        var from = new Vector3((float)a[0], (float)a[1], (float)a[2]);
        var to = new Vector3((float)l[0], (float)l[1], (float)l[2]);
        // straight down needs an up that isn't the view's own axis
        var up = Mathf.Abs((to - from).Normalized().Y) > 0.99f ? Vector3.Forward : Vector3.Up;
        _freeCam.LookAtFromPosition(from, to, up);
        _freeCam.MakeCurrent();
    }

    async Task Frames(int n)
    {
        for (int i = 0; i < n; i++)
            await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
    }

    /// <summary>
    /// A measurement instrument (openspec/changes/weapon-bob, design section 2): holds forward (and
    /// sprint, with "sprint": true) for "frames" rendered frames and writes a CSV row per frame to
    /// the out folder: seconds, ground speed m/s, the bob's phase (rad) and weight, the camera's
    /// height over the feet (m), and the view weapon's offset (m) and turn (rad) from the camera.
    /// </summary>
    async Task TraceWalk(PlayerController player, string file, Godot.Collections.Dictionary step)
    {
        int frames = step.TryGetValue("frames", out var f) ? f.AsInt32() : 180;
        bool sprint = step.TryGetValue("sprint", out var s) && s.AsBool();
        var cam = player.GetNode<Node3D>("CameraRig/Camera3D");
        var vm = player.GetNode<Node3D>("CameraRig/Camera3D/WeaponManager/ViewmodelRoot");
        var rows = new System.Text.StringBuilder("t_s,speed_mps,phase_rad,weight,cam_y_m,vm_x_m,vm_y_m,vm_pitch_rad,vm_yaw_rad,vm_roll_rad\n");
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        Input.ActionPress("move_forward");
        if (sprint)
            Input.ActionPress("sprint");
        double t = 0;
        for (int i = 0; i < frames; i++)
        {
            await Frames(1);
            t += GetProcessDeltaTime();
            var v = player.Velocity with { Y = 0 };
            var local = cam.GlobalTransform.AffineInverse() * vm.GlobalTransform;
            var rot = local.Basis.GetEuler();
            rows.Append(string.Join(",", new[] { t, v.Length(), player.BobPhase, player.BobWeight,
                cam.GlobalPosition.Y - player.GlobalPosition.Y, local.Origin.X, local.Origin.Y, rot.X, rot.Y, rot.Z }
                .Select(x => x.ToString("0.#####", inv)))).Append('\n');
        }
        Input.ActionRelease("move_forward");
        Input.ActionRelease("sprint");
        FileAccess.Open(_out.PathJoin(file), FileAccess.ModeFlags.Write).StoreString(rows.ToString());
        GD.Print($"[AutoTest] trace {_out.PathJoin(file)}: {frames} frames");
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
            if (step.TryGetValue("look", out var lk) && player != null)
            {
                var a = lk.AsGodotArray();
                player.SetLook((float)a[0], (float)a[1]);
            }
            if (step.TryGetValue("face", out var fc) && player != null)
            {
                // look at a point: [x, y, z]
                var a = fc.AsGodotArray();
                var d = new Vector3((float)a[0], (float)a[1], (float)a[2]) - player.EyePosition;
                player.SetLook(Mathf.RadToDeg(Mathf.Atan2(-d.X, -d.Z)),
                    Mathf.RadToDeg(Mathf.Atan2(d.Y, new Vector2(d.X, d.Z).Length())));
            }
            if (step.TryGetValue("walk_to", out var wt) && player != null)
            {
                // steer toward [x, z] with forward held (walking or swimming) until within "within" metres
                var a = wt.AsGodotArray();
                var goal = new Vector2((float)a[0], (float)a[1]);
                float within = step.TryGetValue("within", out var wv) ? (float)wv.AsDouble() : 0.5f;
                int max = step.TryGetValue("max", out var mv) ? mv.AsInt32() : 600;
                float pitchDeg = Mathf.RadToDeg(player.Pitch);
                Input.ActionPress("move_forward");
                for (int i = 0; i < max; i++)
                {
                    var here = new Vector2(player.GlobalPosition.X, player.GlobalPosition.Z);
                    var to = goal - here;
                    if (to.Length() <= within)
                        break;
                    player.SetLook(Mathf.RadToDeg(Mathf.Atan2(-to.X, -to.Y)), pitchDeg);
                    await Frames(1);
                }
                Input.ActionRelease("move_forward");
            }
            if (step.TryGetValue("trace", out var tr) && player != null)
                await TraceWalk(player, tr.AsString(), step);
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
                // one action, or several held together: {"hold": ["move_forward", "crouch"]}
                int frames = step.TryGetValue("frames", out var f) ? f.AsInt32() : 30;
                var actions = action.VariantType == Variant.Type.Array
                    ? action.AsGodotArray().Select(a => a.AsString()).ToArray()
                    : new[] { action.AsString() };
                foreach (var a in actions)
                    Input.ActionPress(a);
                await Frames(frames);
                foreach (var a in actions)
                    Input.ActionRelease(a);
            }
            if (step.TryGetValue("press", out var pa))
            {
                Input.ActionPress(pa.AsString());
                await Frames(2);
                Input.ActionRelease(pa.AsString());
            }
            if (step.TryGetValue("hide", out var hide))
                ShowNode(hide.AsString(), false);
            if (step.TryGetValue("show", out var show))
                ShowNode(show.AsString(), true);
            if (step.TryGetValue("camera", out var cam))
                FreeCamera(cam, step.TryGetValue("look_at", out var la) ? la : default);
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
            if (step.TryGetValue("render_scale", out var rs))  // the 3D view's resolution scale; the UI stays sharp (lavapipe captures)
                GetViewport().Scaling3DScale = (float)rs.AsDouble();
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
            if (step.TryGetValue("render_stats", out _))    // what the last frame drew (hub-skyline's draw-call count)
                GD.Print($"[AutoTest] render: draw calls {Performance.GetMonitor(Performance.Monitor.RenderTotalDrawCallsInFrame)} " +
                         $"primitives {Performance.GetMonitor(Performance.Monitor.RenderTotalPrimitivesInFrame)} " +
                         $"objects {Performance.GetMonitor(Performance.Monitor.RenderTotalObjectsInFrame)}");
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
        if (step.TryGetValue("click", out var click))
        {
            // Presses a button by node name anywhere in the current scene: menus, the pause screen, save rows.
            var button = GetTree().CurrentScene?.FindChild(click.AsString(), true, false) as BaseButton;
            if (button == null)
                GD.PrintErr($"[AutoTest] no button named '{click}'");
            else if (button.Disabled)
                GD.Print($"[AutoTest] '{click}' is disabled");
            else
                button.EmitSignal(BaseButton.SignalName.Pressed);
            await Frames(4);
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
            if (d.TryGetValue("breath", out var br))
                state.Breath.Set(br.AsDouble());
            if (d.TryGetValue("stamina", out var st))
                state.Stamina.Set(st.AsDouble());
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
        if (step.TryGetValue("rig", out var rig))    // character lighting on or off, for the before-and-after checks
            level.ConversationRigOn = rig.AsBool();
        // Skin as it was before wetness (openspec/changes/archive/2026-09-29-character-lighting, design section 9):
        // with no dry add, every skin is the roughness mask, wet or dry. For before-and-after shots.
        if (step.TryGetValue("skin_before_wetness", out var before))
        {
            if (before.AsBool())
                RenderingServer.GlobalShaderParameterSet(Undercity.Client.CharacterShading.SkinDryRoughnessAdd, 0f);
            else
                Undercity.Client.CharacterShading.Apply(level.AutoTestState!.Data.CharacterLighting.Wetness);
        }
        if (step.TryGetValue("face_box", out var fb))
            WriteFaceBox(level, fb.AsString(), step.TryGetValue("shot", out var fs) ? fs.AsString() : null);
        if (step.TryGetValue("probe", out var probeId))
        {
            foreach (var n in level.Npcs().Where(n => n.NpcId == probeId.AsString()))
            {
                var model = n.GetNodeOrNull<Node3D>("Model");
                var p = PlayerController.Instance;
                GD.Print($"[AutoTest] probe {n.StableId}: rot {n.RotationDegrees} global {n.GlobalRotationDegrees} " +
                         $"fwd {-n.GlobalBasis.Z} det {n.GlobalBasis.Determinant():0.00} parent {n.GetParent().Name} " +
                         $"parent_det {(n.GetParent() as Node3D)?.GlobalBasis.Determinant():0.00} model_fwd {(model != null ? model.GlobalBasis.Z : Vector3.Zero)} " +
                         $"to_player {(p.GlobalPosition - n.GlobalPosition).Normalized()}");
                if (model?.FindChildren("*", "Skeleton3D", true, false).FirstOrDefault() is Skeleton3D sk)
                    foreach (var bone in new[] { "root", "pelvis", "chest", "head" })
                    {
                        int i = sk.FindBone(bone);
                        if (i >= 0)
                            GD.Print($"[AutoTest]   {bone}: global fwd {(sk.GlobalTransform * sk.GetBoneGlobalPose(i)).Basis.Z}");
                    }
            }
        }
        if (step.TryGetValue("talk", out var npcId))
        {
            var npc = level.Npcs().FirstOrDefault(n => n.NpcId == npcId.AsString());
            npc?.Use();
            await Frames(3);
        }
        if (step.TryGetValue("kill", out var killId))
        {
            // Test harness: the NPC is dead in the world, under its target key, and its body falls.
            // A shot kills through the damage rule; this skips the shooting.
            var npc = level.Npcs().FirstOrDefault(n => n.NpcId == killId.AsString() || n.StableId == killId.AsString());
            if (npc == null)
                GD.PrintErr($"[AutoTest] no npc '{killId}'");
            else
            {
                if (step.TryGetValue("at", out var at))
                {
                    var a = at.AsGodotArray();
                    npc.GlobalPosition = new Vector3((float)a[0], (float)a[1], (float)a[2]);
                    await Frames(2);
                }
                state.World.SetNpc(npc.TargetKey, Undercity.Core.World.NpcStatus.Dead);
                var away = npc.GlobalPosition - PlayerController.Instance.GlobalPosition;
                away.Y = 0;
                npc.Collapse(away.Normalized() * 40f);
                GD.Print($"[AutoTest] {npc.StableId} collapses");
            }
            await Frames(2);
        }
        if (step.TryGetValue("state", out _))
        {
            var c = state.Character;
            GD.Print($"[AutoTest] state: level {c.Level} xp {c.Xp}/{c.XpToNext} points {c.SkillPoints} credits {state.Inventory.Credits} " +
                     $"health {state.Health.Value:0}/{state.Health.Max:0} drawn {state.Drawn ?? "-"} " +
                     $"rounds {(state.Rounds is { } r ? $"{r.Loaded}/{r.Reserve}" : "-")}{(state.Reloading ? " reloading" : "")} " +
                     $"law {(state.Law.Hostile ? "hostile" : "calm")}{(state.Dead ? " DEAD" : "")}");
            var p = PlayerController.Instance;
            GD.Print($"[AutoTest] water: {state.Water} breath {state.Breath.Value:0.0}/{state.Breath.Max:0} " +
                     $"stamina {state.Stamina.Value:0.0}/{state.Stamina.Max:0} feet {p?.GlobalPosition}");
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

    // The instrument for openspec/changes/archive/2026-09-29-character-lighting (design section 5): the speaker's head
    // box projected to the screen, written beside the step's shot for tools/measure/face_luma.py.
    // The box is 0.24 m wide and runs 0.12 m below to 0.14 m above the head's middle
    // (NpcActor.FaceCentre), in the camera's plane.
    void WriteFaceBox(Undercity.Client.UndercityLevel level, string who, string shot)
    {
        var npc = level.Npcs().FirstOrDefault(n => n.StableId == who || n.NpcId == who);
        var cam = GetViewport().GetCamera3D();
        if (shot == null || cam == null || npc == null)
        {
            GD.PrintErr($"[AutoTest] face_box: no '{who}', no camera, or no shot in the step");
            return;
        }
        var middle = npc.FaceCentre;
        var right = cam.GlobalBasis.X;
        var up = cam.GlobalBasis.Y;
        // UnprojectPosition answers in the viewport's visible rectangle (the project's 1920 x 1080
        // base, stretched); the shot is the image the viewport's texture gives, the window's pixels.
        // Scale by that image's own size: the texture's reported size isn't it (854 x 480 in a
        // 1280 x 720 window, measured), and the box must land where the shot's pixels are.
        var vp = GetViewport();
        var toPixels = (Vector2)vp.GetTexture().GetImage().GetSize() / vp.GetVisibleRect().Size;
        // Metres from the eyes, measured on the conversation shots: the face runs from the chin
        // 0.12 m below to the hairline 0.07 m above and is 0.15 m wide; the head, ears and crown
        // included, 0.22 m wide from 0.14 m below to 0.14 m above.
        Godot.Collections.Array Box(float halfWidth, float below, float above)
        {
            var c = new[] { (-halfWidth, -below), (halfWidth, -below), (-halfWidth, above), (halfWidth, above) }
                .Select(o => cam.UnprojectPosition(middle + right * o.Item1 + up * o.Item2) * toPixels).ToArray();
            return new Godot.Collections.Array { c.Min(p => p.X), c.Min(p => p.Y), c.Max(p => p.X), c.Max(p => p.Y) };
        }
        var rig = GetTree().GetFirstNodeInGroup("conversation_rig");
        var box = new Godot.Collections.Dictionary
        {
            ["who"] = npc.StableId,
            ["box"] = Box(0.075f, 0.12f, 0.07f),
            ["head"] = Box(0.11f, 0.14f, 0.14f),
            // Which side the conversation rig put its key on; "none" before the rig exists.
            ["key_side"] = rig != null && rig.HasMeta("key_side") ? rig.GetMeta("key_side").AsString() : "none",
            // How wet the speaker is, 0 dry to 1 soaked (design section 9).
            ["wetness"] = npc.BodyWetness?.Value ?? -1,
        };
        string file = _out.PathJoin(shot + ".face.json");
        using var f = FileAccess.Open(file, FileAccess.ModeFlags.Write);
        f.StoreString(Json.Stringify(box));
        GD.Print($"[AutoTest] face box {file}");
    }
}
