// A level's water bodies (data/levels/<id>.json "water", exported from the layout), and the one
// rule for how deep in water a body is.
//
// It lives in the core because the swim motor, ragdoll buoyancy, sinking items and the level's
// placement checks must all agree on where water is and how deep it is (CLAUDE.md 5.1;
// openspec/changes/archive/2026-09-29-water-and-swimming). The layout (tools/levels/layouts/<id>.py "water") is the
// single source; tools/levels/export_level_data.py copies it here.

using Undercity.Core.Data;
using Undercity.Core.Vitals;

namespace Undercity.Core.World;

/// <summary>A body of water: a polygon in layout metres (x east, y south), with its surface and bed heights.</summary>
public sealed class WaterBody
{
    /// <summary>The water body's id, unique in its level.</summary>
    public required string Id { get; init; }

    /// <summary>The height of the surface, metres (the engine's up axis).</summary>
    public required double SurfaceM { get; init; }

    /// <summary>The height of the bed, metres.</summary>
    public required double BedM { get; init; }

    /// <summary>The outline, as [x, y] pairs in layout metres (the engine's x and z).</summary>
    public required IReadOnlyList<IReadOnlyList<double>> Poly { get; init; }

    /// <summary>True when the point (x, y) in layout metres lies inside the outline.</summary>
    public bool Contains(double x, double y) => LayoutPolygon.Contains(Poly, x, y);

    /// <summary>Adds a message per problem: fewer than 3 points, a non-finite value, a bed above the surface.</summary>
    public void Validate(string level, ICollection<string> errors)
    {
        if (!LayoutPolygon.IsValid(Poly))
        {
            errors.Add($"levels.{level}.water.{Id}: poly needs 3 or more [x, y] points of finite metres");
        }
        if (!double.IsFinite(SurfaceM) || !double.IsFinite(BedM) || BedM >= SurfaceM)
        {
            errors.Add($"levels.{level}.water.{Id}: bed_m must be a finite height below surface_m");
        }
    }
}

/// <summary>The one rule for how deep in water a body is.</summary>
public static class WaterRules
{
    /// <summary>The water body at (x, y) in layout metres, or null.</summary>
    public static WaterBody? At(IEnumerable<WaterBody> bodies, double x, double y) =>
        bodies.FirstOrDefault(w => w.Contains(x, y));

    /// <summary>
    /// How much of a body is in <paramref name="water"/>: from the height of its feet and its
    /// eyes, by the depths in <paramref name="table"/>. The eyes under the surface are always
    /// <see cref="WaterContact.Submerged"/>.
    /// </summary>
    public static WaterContact Contact(WaterTable table, WaterBody? water, double feetM, double eyeM)
    {
        if (water is null || !double.IsFinite(feetM) || !double.IsFinite(eyeM))
        {
            return WaterContact.Dry;
        }
        if (eyeM < water.SurfaceM)
        {
            return WaterContact.Submerged;
        }
        var depth = water.SurfaceM - feetM;
        return depth > table.SwimDepthM ? WaterContact.Swimming
            : depth > table.WadeDepthM ? WaterContact.Wading
            : WaterContact.Dry;
    }
}
