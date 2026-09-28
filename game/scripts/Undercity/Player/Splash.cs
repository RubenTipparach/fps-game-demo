// A splash where something falls into water: the runner, a body, a dropped item
// (openspec/changes/water-and-swimming, design section 5). One place makes every splash, so they
// all look alike and scale alike.
//
// It lives in the Godot layer because it is only an effect: scenes/undercity/splash.tscn, played
// once and freed.

#nullable enable
using Godot;

namespace Undercity.Client;

/// <summary>A one-shot splash of droplets.</summary>
public partial class Splash : GpuParticles3D
{
    private static PackedScene? _scene;

    /// <summary>
    /// Throws up water at <paramref name="at"/> (on the surface), sized by <paramref name="strength"/>
    /// from 0 (a pebble) to 1 (a body falling from the quay), in the scene <paramref name="context"/> is in.
    /// </summary>
    public static void At(Node context, Vector3 at, float strength)
    {
        if (!context.IsInsideTree() || context.GetTree().CurrentScene is not { } root)
        {
            return;
        }
        _scene ??= GD.Load<PackedScene>("res://scenes/undercity/splash.tscn");
        var s = _scene.Instantiate<Splash>();
        root.AddChild(s);
        s.GlobalPosition = at;
        var k = Mathf.Clamp(strength, 0.1f, 1f);
        s.AmountRatio = k;
        s.Scale = Vector3.One * Mathf.Lerp(0.5f, 1.2f, k);
        s.Emitting = true;
        s.Finished += s.QueueFree;
    }
}
