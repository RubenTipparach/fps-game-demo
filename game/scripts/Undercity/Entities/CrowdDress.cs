// Puts a civilian's crowd look on a body (openspec/changes/archive/2026-09-29-crowd-variety, design section 2): the
// height on the model, the outfit palette as character_outfit.gdshader's instance uniforms (skin,
// hair and eyes don't take them), and each accessory's prop on its mount in the NPC scene.
//
// It lives in the Godot layer beside NpcActor because it only applies what the core's crowd rule
// chose (CrowdPicker). It is the one implementation of that: NpcActor dresses the hub's civilians
// with it and the lineup capture (Checks/CrowdLineup.cs) dresses its row with it, so the capture
// shows what the game draws (CLAUDE.md 5.1).

#nullable enable
using System;
using System.Linq;
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>Dresses a body as a crowd look says.</summary>
public static class CrowdDress
{
    /// <summary>
    /// Scales <paramref name="model"/> (an NPC scene instance), recolours its outfit and hangs the
    /// look's accessories on their mounts. <paramref name="warn"/> hears of an accessory that can't
    /// be worn (no mount, or no prop).
    /// </summary>
    public static void Apply(Node3D model, CrowdLook look, CrowdTable crowd, Action<string> warn)
    {
        model.Scale = Vector3.One * (float)look.Scale;
        var palette = crowd.Palettes[look.Palette];
        foreach (var g in model.FindChildren("*", "GeometryInstance3D", true, false).OfType<GeometryInstance3D>())
        {
            g.SetInstanceShaderParameter("hue_deg", (float)palette.HueDeg);
            g.SetInstanceShaderParameter("sat", (float)palette.Sat);
        }
        foreach (var id in look.Accessories)
        {
            Wear(model, id, crowd.Accessories[id], warn);
        }
    }

    /// <summary>Puts an accessory's prop (game/models/undercity/props/&lt;id&gt;.glb) on its mount in the NPC scene.</summary>
    private static void Wear(Node3D model, string id, AccessoryDef accessory, Action<string> warn)
    {
        var path = $"res://models/undercity/props/{id}.glb";
        if (model.FindChild(accessory.Mount, true, false) is not Node3D mount || !ResourceLoader.Exists(path))
        {
            warn($"can't wear {id} (no mount '{accessory.Mount}' in the NPC scene, or no {path})");
            return;
        }
        var prop = GD.Load<PackedScene>(path).Instantiate<Node3D>();
        prop.Name = id;
        mount.AddChild(prop);
    }
}
