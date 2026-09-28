// A one-shot burst of particles from an authored scene: a splash where something falls into water
// (openspec/changes/water-and-swimming, design section 5), blood where a shot hits a person
// (openspec/changes/hub-combat). One place plays every burst, so they all scale alike and free
// themselves alike.
//
// It lives in the Godot layer because it is only an effect: scenes/undercity/splash.tscn and
// blood.tscn, each played once and freed.

#nullable enable
using System.Collections.Generic;
using Godot;

namespace Undercity.Client;

/// <summary>A one-shot particle burst.</summary>
public partial class ParticleBurst : GpuParticles3D
{
    /// <summary>Water thrown up where something falls in.</summary>
    public const string SplashScene = "res://scenes/undercity/splash.tscn";

    /// <summary>Blood where a shot hits a person.</summary>
    public const string BloodScene = "res://scenes/undercity/blood.tscn";

    private static readonly Dictionary<string, PackedScene> Scenes = new();

    /// <summary>
    /// Plays the burst <paramref name="scene"/> at <paramref name="at"/>, thrown along
    /// <paramref name="up"/> (the scene's +Y; world up when zero), sized by
    /// <paramref name="strength"/> from 0 (a pebble, a graze) to 1 (a body falling from the quay),
    /// in the scene <paramref name="context"/> is in.
    /// </summary>
    public static void Play(Node context, string scene, Vector3 at, float strength, Vector3 up = default)
    {
        if (!context.IsInsideTree() || context.GetTree().CurrentScene is not { } root)
        {
            return;
        }
        if (!Scenes.TryGetValue(scene, out var packed))
        {
            packed = Scenes[scene] = GD.Load<PackedScene>(scene);
        }
        var s = packed.Instantiate<ParticleBurst>();
        root.AddChild(s);
        var k = Mathf.Clamp(strength, 0.1f, 1f);
        var y = up.LengthSquared() > 1e-6f ? up.Normalized() : Vector3.Up;
        var x = Mathf.Abs(y.Dot(Vector3.Up)) > 0.99f ? Vector3.Right : Vector3.Up.Cross(y).Normalized();
        var basis = new Basis(x, y, x.Cross(y)).Scaled(Vector3.One * Mathf.Lerp(0.5f, 1.2f, k));
        s.GlobalTransform = new Transform3D(basis, at);
        s.AmountRatio = k;
        s.Emitting = true;
        s.Finished += s.QueueFree;
    }

    /// <summary>Throws up water at <paramref name="at"/> (on the surface), sized by <paramref name="strength"/>.</summary>
    public static void Splash(Node context, Vector3 at, float strength) => Play(context, SplashScene, at, strength);
}
