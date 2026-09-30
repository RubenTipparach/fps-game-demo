// The character lighting check (scenes/undercity/tests/lighting_test.tscn): loads the hub and checks
// what a capture can't pin (openspec/changes/archive/2026-09-29-character-lighting, "New lights touch only
// characters" and "The conversation rig is motivated and coloured by district"): every person's
// meshes are on the characters layer as well as the world's, the runner's own view isn't, the
// wrist light and the rig light only that layer, a conversation with Silk in Lantern Row wears
// Lantern Row's gels with its key on the side the core names, the view narrows to the framing's
// width, and the rig ramps out and is freed when the conversation ends. It also checks "Characters
// are dry under a roof and wet in the rain": Tank behind the Anchor's bar starts dry and Dace at the
// checkpoint gate soaked, every mesh of their bodies carries that value, their skin is drawn by the
// skin shader, and a soaked body under a roof dries at the data's rate. And that the level hands
// its puddle mask to the ground's shader (openspec/changes/archive/2026-09-30-street-puddles, design section 3.7): the
// globals hold the level data's mask, rect and decode numbers once the hub has loaded, and the
// street's asphalt and paving are drawn by the ground shader. Prints PASS or FAIL per check and
// quits with 1 on any failure.
//
//   flock /tmp/undercity-godot.lock timeout 600 godot --headless --path game res://scenes/undercity/tests/lighting_test.tscn
//
// It lives beside the other level checks because it runs the level's own scene; the numbers it
// expects come from data/character_lighting.json, as the lights' do.

#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Brushfire;
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>The headless character lighting check.</summary>
public partial class LightingTest : Node3D
{
    /// <summary>The level the check runs in.</summary>
    [Export] public string LevelScene { get; set; } = "res://levels/undercity/hub/hub.tscn";

    private UndercityLevel? _level;
    private int _checks;
    private int _fail;

    private UndercityLevel L => _level!;

    /// <inheritdoc/>
    public override async void _Ready()
    {
        try
        {
            AutoTest.Active = true;
            _level = GD.Load<PackedScene>(LevelScene).Instantiate<UndercityLevel>();
            AddChild(_level);
            await Frames(10);
            var t = L.AutoTestState!.Data.CharacterLighting;
            var bit = 1u << (t.CharactersLayer - 1);
            PeopleOnTheCharactersLayer(bit);
            TheRunnersViewIsNot(bit);
            TheWristLight(t, bit);
            await TheRig(t, bit);
            DryIndoorsWetInTheRain(t.Wetness);
            TheGroundDrawsThePuddles(L.AutoTestState!.Data.Levels["hub"].Puddles);
        }
        catch (Exception e)
        {
            Check("the test ran", false, e.ToString());
        }
        GD.Print($"[lighting_test] {_checks - _fail} of {_checks} passed");
        GetTree().Quit(_fail > 0 ? 1 : 0);
    }

    private void TheGroundDrawsThePuddles(PuddlesDef? puddles)
    {
        Check("the hub has puddles in its level data", puddles != null, puddles is null ? "none" : $"{puddles.List.Count} puddles");
        if (puddles is null)
        {
            return;
        }
        // A headless run's renderer keeps no shader globals, so this reads what the level handed
        // over (PuddleShading.Applied); the captures show the renderer drawing it.
        Check("the level hands the ground its puddles as it loads", ReferenceEquals(PuddleShading.Applied, puddles),
            ReferenceEquals(PuddleShading.Applied, puddles) ? "the hub's" : PuddleShading.Applied is null ? "none" : "another level's");
        var mask = ResourceLoader.Exists(puddles.Mask) ? GD.Load<Texture2D>(puddles.Mask) : null;
        Check("its mask loads as a texture over the level's rect", mask != null && mask.GetWidth() > 0,
            mask is null ? $"no {puddles.Mask}" : $"{mask.GetWidth()} x {mask.GetHeight()} over {puddles.RectM[2]} x {puddles.RectM[3]} m");
        foreach (var name in new[] { "asphalt", "paving_wet" })
        {
            var m = GD.Load<Material>($"res://materials/{name}.tres");
            Check($"the street's {name} is drawn by the ground shader",
                m is ShaderMaterial { Shader.ResourcePath: "res://shaders/city_ground.gdshader" }, m?.GetType().Name ?? "missing");
        }
    }

    private void PeopleOnTheCharactersLayer(uint bit)
    {
        var npcs = L.Npcs().ToList();
        var off = npcs.SelectMany(n => Meshes(n).Where(g => (g.Layers & 1u) == 0 || (g.Layers & bit) == 0)
            .Select(g => $"{n.Name}/{g.Name} layers {g.Layers}")).ToList();
        Check("every person's meshes are on the world's layer and the characters'", npcs.Count > 0 && off.Count == 0,
            off.Count == 0 ? $"{npcs.Count} people" : string.Join(", ", off.Take(5)));
    }

    private void TheRunnersViewIsNot(uint bit)
    {
        var on = Meshes(L.Player).Where(g => (g.Layers & bit) != 0).Select(g => g.Name.ToString()).ToList();
        Check("the runner's own view isn't on the characters layer, so the wrist light doesn't wash it",
            on.Count == 0, on.Count == 0 ? "none" : string.Join(", ", on));
    }

    private void TheWristLight(CharacterLightingTable t, uint bit)
    {
        var wrist = L.Player.GetNodeOrNull<OmniLight3D>("CameraRig/Camera3D/Wrist");
        Check("the runner carries the wrist light", wrist != null, wrist?.GetPath().ToString() ?? "missing");
        if (wrist == null)
        {
            return;
        }
        Check("the wrist light lights characters only", wrist.LightCullMask == bit, $"cull mask {wrist.LightCullMask}");
        Check("the wrist light is always on and never baked", wrist.Visible && wrist.LightBakeMode == Light3D.BakeMode.Disabled,
            $"visible {wrist.Visible}, bake mode {wrist.LightBakeMode}");
        Check("the wrist light's energy and reach are the data's",
            Mathf.IsEqualApprox(wrist.LightEnergy, (float)t.Wrist.Energy) && Mathf.IsEqualApprox(wrist.OmniRange, (float)t.Wrist.RangeM),
            $"energy {wrist.LightEnergy} (data {t.Wrist.Energy}), range {wrist.OmniRange} m (data {t.Wrist.RangeM})");
    }

    private async Task TheRig(CharacterLightingTable t, uint bit)
    {
        var silk = L.Npcs().FirstOrDefault(n => n.NpcId == "silk");
        Check("Silk is in the hub", silk != null, silk?.Name ?? "missing");
        if (silk == null)
        {
            return;
        }
        var head = silk.FaceCentre;
        var district = L.Def.DistrictNear(head.X, head.Z);
        Check("Silk stands in Lantern Row", district == "lantern_row", district ?? "no district");
        var cam = L.Player.GetNode<Camera3D>("CameraRig/Camera3D");
        var fovBefore = cam.Fov;
        // Stand 1.8 m in front of her, as the use key's reach allows, looking at her face.
        var front = new Vector3(Mathf.Sin(silk.GlobalRotation.Y), 0, Mathf.Cos(silk.GlobalRotation.Y));
        L.Player.GlobalPosition = silk.GlobalPosition + front * 1.8f;
        var d = head - L.Player.GlobalPosition;
        L.Player.SetLook(Mathf.RadToDeg(Mathf.Atan2(-d.X, -d.Z)), 0);
        await Frames(2);

        // The use key's path: the dialog opens, which stops the body (so it stops setting the view's
        // width), and the level lights the conversation.
        silk.Use();
        await Seconds((float)Math.Max(t.Conversation.RampS, t.Framing.TimeS) + 0.1f);
        var rigs = GetTree().GetNodesInGroup(ConversationRig.Group).OfType<ConversationRig>().ToList();
        Check("a conversation opens one rig", rigs.Count == 1, $"{rigs.Count} rigs");
        if (rigs.Count != 1)
        {
            return;
        }
        var rig = rigs[0];
        var lights = new[] { "Key", "Rim", "Accent" }.Select(n => rig.GetNode<Light3D>(n)).ToList();
        Check("the rig lights characters only", lights.All(l => l.LightCullMask == bit),
            string.Join(", ", lights.Select(l => $"{l.Name} {l.LightCullMask}")));
        var defs = new[] { t.Conversation.Key, t.Conversation.Rim, t.Conversation.Accent };
        var ramped = lights.Zip(defs).All(p => Mathf.IsEqualApprox(p.First.LightEnergy, (float)p.Second.Energy, 0.01f));
        Check("the rig has ramped in to the data's energies", ramped,
            string.Join(", ", lights.Zip(defs).Select(p => $"{p.First.Name} {p.First.LightEnergy:0.00}/{p.Second.Energy}")));
        var want = t.Gels["lantern_row"];
        Check("the rim and accent wear Lantern Row's gels", SameColour(lights[1], t, want[0]) && SameColour(lights[2], t, want[1]),
            $"rim {lights[1].LightColor}, accent {lights[2].LightColor}; Lantern Row is {want[0]} and {want[1]}");
        var side = (lights[0].GlobalPosition - head).Dot(cam.GlobalBasis.X) > 0 ? "right" : "left";
        Check("the key stands on the side the rig was given", side == rig.KeySide, $"key on the {side}, rig says {rig.KeySide}");
        Check("the view narrows to the framing's width", Mathf.IsEqualApprox(cam.Fov, (float)t.Framing.FovDeg, 0.05f),
            $"fov {cam.Fov:0.0} (data {t.Framing.FovDeg}, before {fovBefore:0.0})");

        L.GetChildren().OfType<IScreens>().First().CloseAll();
        await Seconds((float)t.Conversation.RampS + 0.2f);
        Check("the rig ramps out and is freed when the conversation ends", !IsInstanceValid(rig) || rig.IsQueuedForDeletion(),
            IsInstanceValid(rig) ? "still there" : "gone");
    }

    private void DryIndoorsWetInTheRain(WetnessDef def)
    {
        var tank = L.Npcs().FirstOrDefault(n => n.NpcId == "tank");
        var dace = L.Npcs().FirstOrDefault(n => n.NpcId == "dace");
        Check("Tank and Dace are in the hub with bodies", tank?.BodyWetness != null && dace?.BodyWetness != null,
            $"tank {tank?.BodyWetness?.Value.ToString("0.00") ?? "missing"}, dace {dace?.BodyWetness?.Value.ToString("0.00") ?? "missing"}");
        if (tank?.BodyWetness is not { } dry || dace?.BodyWetness is not { } wet)
        {
            return;
        }
        Check("Tank behind the Anchor's bar is under a roof and dry", dry.Sheltered && dry.Value == 0,
            $"sheltered {dry.Sheltered}, wetness {dry.Value:0.00} at {tank.GlobalPosition}");
        Check("Dace at the checkpoint gate is in the rain and soaked", !wet.Sheltered && wet.Value == 1,
            $"sheltered {wet.Sheltered}, wetness {wet.Value:0.00} at {dace.GlobalPosition}");
        foreach (var (who, body) in new[] { (tank, dry), (dace, wet) })
        {
            var meshes = Meshes(who).ToList();
            var off = meshes.Where(g => !Mathf.IsEqualApprox((float)g.GetInstanceShaderParameter(BodyWetness.Uniform), (float)body.Value))
                .Select(g => g.Name.ToString()).ToList();
            Check($"every mesh of {who.NpcId}'s body carries its wetness", meshes.Count > 0 && off.Count == 0,
                off.Count == 0 ? $"{meshes.Count} meshes at {body.Value:0.00}" : string.Join(", ", off.Take(5)));
            var skins = meshes.OfType<MeshInstance3D>()
                .SelectMany(m => Enumerable.Range(0, m.GetSurfaceOverrideMaterialCount()).Select(m.GetActiveMaterial))
                .Where(m => m?.ResourceName.EndsWith("_skin", StringComparison.Ordinal) == true).ToList();
            Check($"{who.NpcId}'s skin is drawn by the skin shader, which reads it",
                skins.Count > 0 && skins.All(m => m is ShaderMaterial { Shader.ResourcePath: "res://shaders/character_skin.gdshader" }),
                skins.Count == 0 ? "no skin material" : string.Join(", ", skins.Select(m => $"{m!.ResourceName} {m.GetClass()}")));
        }
        // A soaked body under a roof: Dace, asked with Tank's feet, dries 1 / dry_time_s a second. The
        // step also takes the time left since the last update, up to update_s more.
        wet.Tick(1.0, tank.GlobalPosition);
        double most = 1 - 1 / def.DryTimeS, least = 1 - (1 + def.UpdateS) / def.DryTimeS;
        Check("a soaked body under a roof dries at the data's rate", wet.Sheltered && wet.Value <= most + 1e-9 && wet.Value >= least - 1e-9,
            $"{wet.Value:0.0000} after 1 s (want {least:0.0000} to {most:0.0000})");
        Check("and its meshes follow", Meshes(dace).All(g => Mathf.IsEqualApprox((float)g.GetInstanceShaderParameter(BodyWetness.Uniform), (float)wet.Value)),
            $"{wet.Value:0.0000}");
    }

    private static bool SameColour(Light3D light, CharacterLightingTable t, string role)
    {
        var (r, g, b) = t.Rgb(role);
        return light.LightColor.IsEqualApprox(new Color((float)r, (float)g, (float)b));
    }

    private static IEnumerable<GeometryInstance3D> Meshes(Node n)
    {
        foreach (var c in n.GetChildren())
        {
            if (c is GeometryInstance3D g && c is not GpuParticles3D)
            {
                yield return g;
            }
            foreach (var d in Meshes(c))
            {
                yield return d;
            }
        }
    }

    private async Task Frames(int n)
    {
        for (var i = 0; i < n; i++)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        }
    }

    private async Task Seconds(float s)
    {
        await ToSignal(GetTree().CreateTimer(s), SceneTreeTimer.SignalName.Timeout);
    }

    private void Check(string what, bool ok, string detail)
    {
        _checks++;
        if (!ok)
        {
            _fail++;
        }
        GD.Print($"[lighting_test] {(ok ? "PASS" : "FAIL")} {what}: {detail}");
    }
}
