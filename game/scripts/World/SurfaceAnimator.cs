using Godot;

namespace Brushfire;

/// <summary>
/// Unreal-style animated surfaces (UT99 checklist item 13): scrolls a material's UVs (flowing
/// lava, conveyor belts, screens) and optionally pulses its emission like machinery. The
/// material is shared, so every surface using it animates together, the same way Unreal's
/// panning textures did. Offsets are restored on exit so the .tres on disk never changes.
/// </summary>
public partial class SurfaceAnimator : Node
{
    [Export] public BaseMaterial3D Material;
    /// <summary>UV1 offset change per second (in texture repeats).</summary>
    [Export] public Vector2 Scroll = new(0.03f, 0f);
    /// <summary>Emission pulse: 0 = none, 0.2 = +-20 %.</summary>
    [Export] public float PulseAmount = 0f;
    [Export] public float PulseSpeed = 1.3f;

    Vector3 _baseOffset;
    float _baseEmission;
    double _time;

    public override void _Ready()
    {
        if (Material == null)
        {
            SetProcess(false);
            return;
        }
        _baseOffset = Material.Uv1Offset;
        _baseEmission = Material.EmissionEnergyMultiplier;
    }

    public override void _Process(double delta)
    {
        _time += delta;
        var o = _baseOffset + new Vector3(Scroll.X, Scroll.Y, 0f) * (float)_time;
        Material.Uv1Offset = new Vector3(Mathf.PosMod(o.X, 1f), Mathf.PosMod(o.Y, 1f), o.Z);
        if (PulseAmount > 0f)
        {
            float wave = Mathf.Sin((float)_time * PulseSpeed * Mathf.Tau) * 0.6f
                         + Mathf.Sin((float)_time * PulseSpeed * 2.7f) * 0.4f;
            Material.EmissionEnergyMultiplier = _baseEmission * (1f + PulseAmount * wave);
        }
    }

    public override void _ExitTree()
    {
        if (Material == null)
            return;
        Material.Uv1Offset = _baseOffset;
        Material.EmissionEnergyMultiplier = _baseEmission;
    }
}
