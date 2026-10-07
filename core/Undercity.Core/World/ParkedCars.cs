// A level's parked vehicles (data/levels/<id>.json "cars", exported from the level's plan): each
// car spot's model, where it stands and which way it faces (openspec/changes/archive/2026-09-30-street-vehicles).
//
// It lives in the core beside the level's other placements so the level data is validated in one
// place, and so the in-engine placement check compares the built level with the plan's own list
// rather than with a hand-typed count: the plan (tools/levels/city_plan.py, City.vehicle) is the
// single source, and tools/levels/export_level_data.py copies it here.

namespace Undercity.Core.World;

/// <summary>One parked vehicle: its entity id, its model, its place and its heading.</summary>
public sealed class ParkedCarDef
{
    /// <summary>The entity's id, "001": the level's node is "car_001".</summary>
    public required string Id { get; init; }

    /// <summary>The variant, "sedan_maroon": its model is models/undercity/props/vehicle_&lt;model&gt;.glb.</summary>
    public required string Model { get; init; }

    /// <summary>Where it stands, [x, y] in layout metres (the engine's x and z), its footprint's centre.</summary>
    public required IReadOnlyList<double> At { get; init; }

    /// <summary>The compass heading its front faces, degrees: 0 north (-y), 90 east.</summary>
    public required double HeadingDeg { get; init; }

    /// <summary>Adds a message to <paramref name="errors"/> for each thing wrong with the car.</summary>
    public void Validate(string level, ICollection<string> errors)
    {
        if (string.IsNullOrWhiteSpace(Id) || string.IsNullOrWhiteSpace(Model))
        {
            errors.Add($"levels.{level}.cars: a car needs an id and a model");
        }
        if (At.Count != 2 || !At.All(double.IsFinite))
        {
            errors.Add($"levels.{level}.cars.{Id}: at needs [x, y] in finite metres");
        }
        if (!double.IsFinite(HeadingDeg))
        {
            errors.Add($"levels.{level}.cars.{Id}: heading_deg must be a finite angle");
        }
    }
}
