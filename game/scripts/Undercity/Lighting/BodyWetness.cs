// How wet a person's body is, carried to its shaders (openspec/changes/character-lighting,
// design section 9; the owner, survey J1: "he's not wet in doors"). Every update it asks the
// core whether a roof is over the person's feet, steps the wetness by the core's rule and sets
// the "wetness" instance uniform on every mesh of the body: the skin and outfit shaders read it,
// and other materials ignore it.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): where the rain reaches and how
// fast a body wets and dries are Undercity.Core.World.Wetness's, from the level's shelters and
// data/character_lighting.json; this only carries the value to the meshes.

#nullable enable
using System.Collections.Generic;
using System.Linq;
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>A body's wetness, stepped by the core's rule and set on its meshes.</summary>
public sealed class BodyWetness
{
    /// <summary>The instance uniform the character shaders read.</summary>
    public const string Uniform = "wetness";

    private readonly IReadOnlyList<ShelterDef> _shelters;
    private readonly WetnessDef _def;
    private readonly GeometryInstance3D[] _meshes;
    private double _sinceS;

    /// <summary>
    /// Starts the body at its place's wetness, so nobody dries on screen when a level loads.
    /// <paramref name="feet"/> is the person's feet in the level's frame (layout x and y are the
    /// engine's x and z).
    /// </summary>
    public BodyWetness(Node3D body, IReadOnlyList<ShelterDef> shelters, WetnessDef def, Vector3 feet)
    {
        _shelters = shelters;
        _def = def;
        _meshes = body.FindChildren("*", "GeometryInstance3D", true, false).OfType<GeometryInstance3D>().ToArray();
        Sheltered = Ask(feet);
        Value = Wetness.Start(Sheltered);
        Apply();
    }

    /// <summary>0 dry to 1 soaked.</summary>
    public double Value { get; private set; }

    /// <summary>True when a roof was over the body at the last update.</summary>
    public bool Sheltered { get; private set; }

    /// <summary>Advances the wetness by <paramref name="deltaS"/> seconds, asking again every update_s.</summary>
    public void Tick(double deltaS, Vector3 feet)
    {
        _sinceS += deltaS;
        if (_sinceS < _def.UpdateS)
        {
            return;
        }
        Sheltered = Ask(feet);
        Value = Wetness.Step(Value, Sheltered, _sinceS, _def);
        _sinceS = 0;
        Apply();
    }

    private bool Ask(Vector3 feet) => Wetness.Sheltered(_shelters, feet.X, feet.Z, feet.Y, _def);

    private void Apply()
    {
        foreach (var g in _meshes)
        {
            g.SetInstanceShaderParameter(Uniform, (float)Value);
        }
    }
}
