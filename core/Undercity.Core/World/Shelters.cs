// A level's shelters (data/levels/<id>.json "shelters", exported from the level's plan): every
// roof the rain can't pass, by its footprint and the height of its underside. A building's
// footprint, an awning, a kiosk's roof, the Skyway's deck and a walkway are each one
// (openspec/changes/archive/2026-09-29-character-lighting, design section 9).
//
// It lives in the core because whether a character stands in the rain is a rule the wetness step,
// its tests and a future save must agree about (CLAUDE.md 5.1, 5.2). The plan
// (tools/levels/city_plan.py, Plan.shelter) is the single source of the shapes, and
// tools/levels/export_level_data.py copies them here.

namespace Undercity.Core.World;

/// <summary>A roof: its footprint in layout metres and the height of its underside.</summary>
public sealed class ShelterDef
{
    /// <summary>What it is, for messages: a building's id, "shop awning", "Skyway deck".</summary>
    public required string Label { get; init; }

    /// <summary>The footprint, as [x, y] pairs in layout metres (the engine's x and z).</summary>
    public required IReadOnlyList<IReadOnlyList<double>> Poly { get; init; }

    /// <summary>The height of the roof's underside at its lowest, metres.</summary>
    public required double UnderM { get; init; }

    /// <summary>
    /// True when this roof is over someone whose feet are at (x, y, <paramref name="feetM"/>):
    /// the point lies inside the footprint, and the underside is at least
    /// <paramref name="headroomM"/> above the feet. Standing on the roof itself leaves no
    /// headroom, so a roof never shelters the people on it.
    /// </summary>
    public bool Covers(double x, double y, double feetM, double headroomM) =>
        UnderM - feetM >= headroomM && LayoutPolygon.Contains(Poly, x, y);

    /// <summary>Adds a message to <paramref name="errors"/> for each thing wrong with the shelter.</summary>
    public void Validate(string level, int index, ICollection<string> errors)
    {
        if (string.IsNullOrWhiteSpace(Label))
        {
            errors.Add($"levels.{level}.shelters[{index}]: needs a label");
        }
        if (!LayoutPolygon.IsValid(Poly))
        {
            errors.Add($"levels.{level}.shelters[{index}] ({Label}): poly needs 3 or more [x, y] points of finite metres");
        }
        if (!double.IsFinite(UnderM))
        {
            errors.Add($"levels.{level}.shelters[{index}] ({Label}): under_m must be a finite height");
        }
    }
}
