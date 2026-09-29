// How wet a character is: 0 dry to 1 soaked. It rises in the open, where the hub's rain falls,
// and falls under a roof, linearly at the rates in data/character_lighting.json "wetness"
// (openspec/changes/archive/2026-09-29-character-lighting, design section 9; the owner, survey J1: "he's not wet in
// doors").
//
// It lives in the core because where the rain reaches and how fast a character dries are rules
// (CLAUDE.md 5.1, 5.2): the node that carries the value to a body's shaders, the test that checks
// a speaker indoors and the level that starts everyone at their place's value all ask this code.

namespace Undercity.Core.World;

/// <summary>data/character_lighting.json "wetness": how fast characters wet and dry, and what it does to them.</summary>
public sealed class WetnessDef
{
    /// <summary>From dry to soaked in the open, seconds.</summary>
    public required double WetTimeS { get; init; }

    /// <summary>From soaked to dry under a roof, seconds.</summary>
    public required double DryTimeS { get; init; }

    /// <summary>How often a character asks whether it is sheltered and steps its wetness, seconds.</summary>
    public required double UpdateS { get; init; }

    /// <summary>A roof shelters a character when its underside is at least this far above their feet, metres.</summary>
    public required double HeadroomM { get; init; }

    /// <summary>Dry skin's roughness over the wet mask's, 0 to 1 (the mask is the wet look).</summary>
    public required double SkinDryRoughnessAdd { get; init; }

    /// <summary>Soaked cloth's roughness, 0 to 1 (dry cloth keeps the outfit's own).</summary>
    public required double ClothWetRoughness { get; init; }

    /// <summary>Soaked cloth's brightness over dry cloth's, 0 to 1 (wet cloth darkens).</summary>
    public required double ClothWetBrightness { get; init; }

    /// <summary>Adds a message to <paramref name="errors"/> for each value out of range.</summary>
    public void Validate(ICollection<string> errors)
    {
        void Positive(string at, double v)
        {
            if (!double.IsFinite(v) || v <= 0)
            {
                errors.Add($"wetness.{at} must be a finite number above zero");
            }
        }
        void Unit(string at, double v)
        {
            if (!double.IsFinite(v) || v is < 0 or > 1)
            {
                errors.Add($"wetness.{at} must be 0 to 1");
            }
        }
        Positive("wet_time_s", WetTimeS);
        Positive("dry_time_s", DryTimeS);
        Positive("update_s", UpdateS);
        if (!double.IsFinite(HeadroomM) || HeadroomM < 0)
        {
            errors.Add("wetness.headroom_m must be a finite number, zero or more");
        }
        Unit("skin_dry_roughness_add", SkinDryRoughnessAdd);
        Unit("cloth_wet_roughness", ClothWetRoughness);
        Unit("cloth_wet_brightness", ClothWetBrightness);
    }
}

/// <summary>The one rule for where the rain reaches a character and how wet it makes them.</summary>
public static class Wetness
{
    /// <summary>
    /// True when any of <paramref name="shelters"/> is over someone whose feet are at
    /// (x, y, <paramref name="feetM"/>) in layout metres.
    /// </summary>
    public static bool Sheltered(IEnumerable<ShelterDef> shelters, double x, double y, double feetM, WetnessDef def) =>
        shelters.Any(s => s.Covers(x, y, feetM, def.HeadroomM));

    /// <summary>
    /// A character's wetness when a level starts: what their place would have made them long
    /// ago, so nobody dries on screen at load.
    /// </summary>
    public static double Start(bool sheltered) => sheltered ? 0 : 1;

    /// <summary>
    /// The wetness after <paramref name="dtS"/> seconds: toward 1 at 1 / wet_time_s a second in
    /// the open, toward 0 at 1 / dry_time_s a second under a roof, and never outside 0 to 1. A
    /// value that isn't finite (a damaged save) starts again from the place's.
    /// </summary>
    public static double Step(double wetness, bool sheltered, double dtS, WetnessDef def)
    {
        if (!double.IsFinite(wetness))
        {
            return Start(sheltered);
        }
        var dt = double.IsFinite(dtS) ? Math.Max(dtS, 0) : 0;
        var next = sheltered ? wetness - dt / def.DryTimeS : wetness + dt / def.WetTimeS;
        return Math.Clamp(next, 0, 1);
    }
}
