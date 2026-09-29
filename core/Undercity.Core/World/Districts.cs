// A level's districts (data/levels/<id>.json "districts", exported from the layout): named areas
// the conversation rig takes its gels from (openspec/changes/character-lighting, design
// section 4).
//
// It lives in the core with the level's other data: the layout (tools/levels/layouts/<id>.py
// "districts") is the single source, and tools/levels/export_level_data.py copies it here.

namespace Undercity.Core.World;

/// <summary>A district: an id and its outline in layout metres.</summary>
public sealed class DistrictDef
{
    /// <summary>The district's id, such as "lantern_row".</summary>
    public required string Id { get; init; }

    /// <summary>The outline, as [x, y] pairs in layout metres (the engine's x and z).</summary>
    public required IReadOnlyList<IReadOnlyList<double>> Poly { get; init; }

    /// <summary>True when the point (x, y) in layout metres lies inside the outline.</summary>
    public bool Contains(double x, double y) => LayoutPolygon.Contains(Poly, x, y);
}
