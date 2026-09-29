// The crowd lineup (scenes/undercity/tests/crowd_lineup.tscn; openspec/changes/archive/2026-09-29-crowd-variety,
// task 4.1): the civilian bodies and MerSec's three faces in rows of seven under a plain studio
// light, the first row as built and then every row dressed, each civilian in a palette and a pair
// of accessories so that every accessory is shown, held in its own idle. It dresses them with the
// game's own code (CrowdDress, CrowdPicker.IdleFor), so the stills show what the hub draws. Writes
// one still per row to BRUSHFIRE_LINEUP_OUT (default user://lineup) and quits.
//
//   DISPLAY=:99 BRUSHFIRE_LINEUP_OUT=/tmp/lineup godot --path game res://scenes/undercity/tests/crowd_lineup.tscn
//
// It lives with the checks because it is a capture, not a level: nothing here is a rule.

#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Godot;
using Undercity.Core;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>The lineup capture.</summary>
public partial class CrowdLineup : Node3D
{
    /// <summary>Metres between neighbours in a row (an open umbrella is 1 m across).</summary>
    [Export] public float SpacingM { get; set; } = 1.1f;

    /// <summary>Bodies in a row.</summary>
    [Export] public int PerRow { get; set; } = 7;

    /// <summary>Seconds the idles play before a still, so every body is in its pose.</summary>
    [Export] public float SettleS { get; set; } = 1.0f;

    /// <summary>MerSec's faces, shown after the civilians as their rows are authored in npcs.json.</summary>
    private static readonly string[] Troopers = { "mersec", "mersec_b", "mersec_c" };

    /// <summary>Accessory pairs that between them show every accessory, one per slot.</summary>
    private static readonly string[][] Pairs =
    {
        new[] { "umbrella", "cigarette" }, new[] { "cap", "headphones" }, new[] { "bag", "visor" },
        new[] { "briefcase", "implant" }, new[] { "beanie", "respirator" }, new[] { "prosthetic", "cigarette" },
        new[] { "umbrella", "visor" },
    };

    private readonly List<Node3D> _row = new();

    /// <inheritdoc/>
    public override async void _Ready()
    {
        var fail = 0;
        try
        {
            var data = GameData.Load(new GodotDataSource());
            var outDir = OS.GetEnvironment("BRUSHFIRE_LINEUP_OUT") is { Length: > 0 } o ? o : "user://lineup";
            DirAccess.MakeDirRecursiveAbsolute(outDir);
            var civilians = data.Crowd.BodyPools["civilian"].Order(StringComparer.Ordinal).ToList();
            var bodies = civilians.Concat(Troopers).ToList();
            var palettes = data.Crowd.Palettes.Keys.Order(StringComparer.Ordinal).ToList();
            var shot = 1;
            for (var r = 0; r * PerRow < bodies.Count; r++)
            {
                var ids = bodies.Skip(r * PerRow).Take(PerRow).ToList();
                if (r == 0)
                {
                    await Row(ids, data, _ => null);
                    Save(outDir, $"{shot++:00}_as_built_{ids[0]}_to_{ids[^1]}.png");
                }
                await Row(ids, data, id =>
                {
                    var i = civilians.IndexOf(id);
                    if (i < 0)
                    {
                        return null;     // a trooper keeps the authored look
                    }
                    var pair = Pairs[i % Pairs.Length];
                    var idle = CrowdPicker.IdleFor(pair, data.Crowd, "idle");
                    return new CrowdLook("lineup", id, palettes[(i + 1) % palettes.Count], pair, 1.0, idle, null);
                });
                Save(outDir, $"{shot++:00}_dressed_{ids[0]}_to_{ids[^1]}.png");
            }
        }
        catch (Exception e)
        {
            GD.PrintErr($"FAIL [crowd_lineup] {e}");
            fail++;
        }
        GetTree().Quit(fail > 0 ? 1 : 0);
    }

    // Lays out one row facing the camera (+Z), dressed as `look` says (null: as built), each
    // playing its idle, and lets the idles settle.
    private async Task Row(List<string> ids, GameData data, Func<string, CrowdLook?> look)
    {
        foreach (var n in _row)
        {
            n.QueueFree();
        }
        _row.Clear();
        await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        for (var i = 0; i < ids.Count; i++)
        {
            var model = GD.Load<PackedScene>($"res://scenes/undercity/npcs/{ids[i]}.tscn").Instantiate<Node3D>();
            model.Position = new Vector3((i - (ids.Count - 1) / 2f) * SpacingM, 0, 0);
            AddChild(model);
            _row.Add(model);
            var dressed = look(ids[i]);
            if (dressed is not null)
            {
                CrowdDress.Apply(model, dressed, data.Crowd, w => GD.PrintErr($"FAIL [crowd_lineup] {ids[i]}: {w}"));
            }
            if (model.GetNodeOrNull<AnimationPlayer>("Anim") is { } anim && data.NpcBodies.Clip(dressed?.Idle ?? "idle") is { } clip)
            {
                anim.Play(clip);
            }
        }
        await ToSignal(GetTree().CreateTimer(SettleS), SceneTreeTimer.SignalName.Timeout);
        for (var i = 0; i < 3; i++)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        }
        GD.Print($"[crowd_lineup] {string.Join(", ", ids.Select(id => look(id) is { } l ? $"{id} ({l.Palette}: {string.Join(" + ", l.Accessories)})" : id))}");
    }

    private void Save(string dir, string name)
    {
        var path = $"{dir.TrimEnd('/')}/{name}";
        GetViewport().GetTexture().GetImage().SavePng(path);
        GD.Print($"[crowd_lineup] still {path}");
    }
}
