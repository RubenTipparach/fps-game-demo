// A level's puddles (data/levels/<id>.json "puddles", exported from the level's plan): where rain
// water stands, and how to read the mask the ground's shader draws them from
// (openspec/changes/archive/2026-09-30-street-puddles, design sections 3.4 and 3.5).
//
// It lives in the core because where the rain falls is one rule. A puddle may lie only where the
// core's wetness rule says a character would get wet (Wetness.Sheltered), and the check that
// proves it asks the core, not a copy of the rule. The plan (tools/levels/city_plan.py,
// City.puddles()) is the single source of the shapes, and tools/levels/puddle_mask.py writes the
// mask with the numbers carried here, which the level hands to the shader.

namespace Undercity.Core.World;

/// <summary>A level's puddles and the mask the ground's shader reads them from.</summary>
public sealed class PuddlesDef
{
    /// <summary>The mask's resource path: grey the distance to a puddle's edge, alpha the ground's height.</summary>
    public required string Mask { get; init; }

    /// <summary>What the mask covers, [x, y, width, depth] in layout metres (the engine's x and z).</summary>
    public required IReadOnlyList<double> RectM { get; init; }

    /// <summary>The grey channel spans distances of -RangeM to +RangeM metres, inside negative.</summary>
    public required double RangeM { get; init; }

    /// <summary>The alpha channel spans heights [low, high] in metres.</summary>
    public required IReadOnlyList<double> HeightM { get; init; }

    /// <summary>Every puddle, in the plan's order.</summary>
    public IReadOnlyList<PuddleDef> List { get; init; } = Array.Empty<PuddleDef>();

    /// <summary>Adds a message to <paramref name="errors"/> for each thing wrong with the puddles.</summary>
    public void Validate(string level, ICollection<string> errors)
    {
        if (string.IsNullOrWhiteSpace(Mask))
        {
            errors.Add($"levels.{level}.puddles.mask: needs the mask's path");
        }
        if (RectM.Count != 4 || !RectM.All(double.IsFinite) || RectM[2] <= 0 || RectM[3] <= 0)
        {
            errors.Add($"levels.{level}.puddles.rect_m: needs [x, y, width, depth], finite metres, width and depth over 0");
        }
        if (!double.IsFinite(RangeM) || RangeM <= 0)
        {
            errors.Add($"levels.{level}.puddles.range_m: must be a finite distance over 0");
        }
        if (HeightM.Count != 2 || !HeightM.All(double.IsFinite) || HeightM[1] <= HeightM[0])
        {
            errors.Add($"levels.{level}.puddles.height_m: needs [low, high], finite metres, high over low");
        }
        foreach (var dup in List.GroupBy(p => p.Id).Where(g => g.Count() > 1))
        {
            errors.Add($"levels.{level}.puddles: puddle '{dup.Key}' is given twice");
        }
        foreach (var p in List)
        {
            p.Validate(level, errors);
        }
    }
}

/// <summary>One puddle: its outline and the ground it lies on.</summary>
public sealed class PuddleDef
{
    /// <summary>Where water gathers to make a puddle (design section 3.5).</summary>
    public static readonly IReadOnlyList<string> Kinds = ["gutter", "gully", "drip"];

    /// <summary>The puddle's id, "gutter_012".</summary>
    public required string Id { get; init; }

    /// <summary>"gutter", "gully" or "drip".</summary>
    public required string Kind { get; init; }

    /// <summary>A point inside it, [x, y] in layout metres.</summary>
    public required IReadOnlyList<double> At { get; init; }

    /// <summary>The height of the ground it lies on, metres.</summary>
    public required double GroundM { get; init; }

    /// <summary>The outline, as [x, y] pairs in layout metres.</summary>
    public required IReadOnlyList<IReadOnlyList<double>> Poly { get; init; }

    /// <summary>
    /// True when the core's wetness rule puts every point of the outline, and the point inside,
    /// in the rain: nobody standing there would be under a roof.
    /// </summary>
    public bool InTheRain(IReadOnlyList<ShelterDef> shelters, WetnessDef wetness) =>
        Poly.Append(At).All(p => !Wetness.Sheltered(shelters, p[0], p[1], GroundM, wetness));

    /// <summary>Adds a message to <paramref name="errors"/> for each thing wrong with the puddle.</summary>
    public void Validate(string level, ICollection<string> errors)
    {
        if (!Kinds.Contains(Kind))
        {
            errors.Add($"levels.{level}.puddles.{Id}: kind '{Kind}' isn't one of {string.Join(", ", Kinds)}");
        }
        if (At.Count != 2 || !At.All(double.IsFinite))
        {
            errors.Add($"levels.{level}.puddles.{Id}: at needs [x, y] in finite metres");
        }
        if (!double.IsFinite(GroundM))
        {
            errors.Add($"levels.{level}.puddles.{Id}: ground_m must be a finite height");
        }
        if (!LayoutPolygon.IsValid(Poly))
        {
            errors.Add($"levels.{level}.puddles.{Id}: poly needs 3 or more [x, y] points of finite metres");
        }
    }
}
