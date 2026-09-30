// The ground shader's puddle globals: the level's puddle mask, the rect it covers, and the numbers
// its two channels decode with (openspec/changes/street-puddles, design section 3.4). The ground
// shader (shaders/city_ground.gdshader) reads them; project.godot declares an empty rect, so the
// editor and the lightmap bake draw no puddles, and this sets them from the level data's
// "puddles" when a level starts, or clears the rect for a level without any.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): where the water stands is the
// plan's and the core's (Undercity.Core.World.PuddlesDef); this only hands it to the renderer.

#nullable enable
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>Sets the ground shader's puddle globals from a level's puddles.</summary>
public static class PuddleShading
{
    /// <summary>The mask texture: grey the distance to a puddle's edge, alpha the ground's height.</summary>
    public const string Mask = "puddle_mask";

    /// <summary>The mask's rect in world x and z, metres: x, z, width, depth. Width 0 draws no puddles.</summary>
    public const string RectM = "puddle_rect_m";

    /// <summary>The distance the mask's grey spans either side of an edge, metres.</summary>
    public const string RangeM = "puddle_range_m";

    /// <summary>The heights the mask's alpha spans, metres.</summary>
    public const string HeightM = "puddle_height_m";

    /// <summary>The puddles last handed to the renderer, null for none: what a headless check reads,
    /// since a headless run's renderer keeps no globals (lighting_test.tscn).</summary>
    public static PuddlesDef? Applied { get; private set; }

    /// <summary>Hands a level's puddles to the ground shader, or none when <paramref name="puddles"/> is null.</summary>
    public static void Apply(PuddlesDef? puddles)
    {
        Applied = puddles;
        if (puddles is null)
        {
            RenderingServer.GlobalShaderParameterSet(RectM, Vector4.Zero);
            return;
        }
        RenderingServer.GlobalShaderParameterSet(Mask, GD.Load<Texture2D>(puddles.Mask));
        RenderingServer.GlobalShaderParameterSet(RangeM, (float)puddles.RangeM);
        RenderingServer.GlobalShaderParameterSet(HeightM, new Vector2((float)puddles.HeightM[0], (float)puddles.HeightM[1]));
        // Layout (x, y) is the engine's (x, z) (tools/levels/puddle_mask.py).
        RenderingServer.GlobalShaderParameterSet(RectM, new Vector4((float)puddles.RectM[0], (float)puddles.RectM[1],
            (float)puddles.RectM[2], (float)puddles.RectM[3]));
    }
}
