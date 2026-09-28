// A level's water in engine coordinates: which body of water a point is in, and how deep a body
// is in it. Layout (x, y) is Godot (x, z), and heights are Godot y.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): where the water is comes from the
// level's data (data/levels/<id>.json "water", exported from the layout), and how deep a body is in
// it is the core's one rule (Undercity.Core.World.WaterRules). The player, ragdolls and dropped
// items all ask here, so they agree (openspec/changes/water-and-swimming).

#nullable enable
using System.Collections.Generic;
using Godot;
using Undercity.Core.Vitals;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>The water of one level, asked in engine coordinates.</summary>
public sealed class LevelWater
{
    private readonly IReadOnlyList<WaterBody> _bodies;

    /// <summary>Wraps a level's water bodies and the water table.</summary>
    public LevelWater(IReadOnlyList<WaterBody> bodies, WaterTable table)
    {
        _bodies = bodies;
        Table = table;
    }

    /// <summary>The swimming numbers (data/water.json).</summary>
    public WaterTable Table { get; }

    /// <summary>The water body under <paramref name="p"/> (any height), or null.</summary>
    public WaterBody? At(Vector3 p) => WaterRules.At(_bodies, p.X, p.Z);

    /// <summary>The water's surface height under <paramref name="p"/>, or null where there is no water.</summary>
    public float? SurfaceAt(Vector3 p) => At(p) is { } w ? (float)w.SurfaceM : null;

    /// <summary>How much of a body with its feet at <paramref name="feet"/> and its eyes at <paramref name="eyeY"/> is in water.</summary>
    public WaterContact Contact(Vector3 feet, float eyeY) => WaterRules.Contact(Table, At(feet), feet.Y, eyeY);

    /// <summary>
    /// How much of a sphere of <paramref name="radius"/> metres at <paramref name="centre"/> is under
    /// the surface, 0 to 1 by height (ragdoll buoyancy).
    /// </summary>
    public float SubmergedFraction(Vector3 centre, float radius)
    {
        if (SurfaceAt(centre) is not { } s || radius <= 0)
        {
            return 0;
        }
        return Mathf.Clamp((s - (centre.Y - radius)) / (2 * radius), 0f, 1f);
    }
}
