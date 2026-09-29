// What the runner sees and hears with their head under water: the underwater view (a full-screen
// fog, shaders/underwater.gdshader) shows, and the SFX bus, which the world's sounds pass through,
// goes through its low-pass filter (audio/default_bus_layout.tres). The UI and music are untouched
// (openspec/changes/archive/2026-09-29-water-and-swimming, design section 6).
//
// It lives in the Godot layer because it only switches a view and an audio effect; where the
// water is comes from the level (LevelWater).

#nullable enable
using Godot;

namespace Undercity.Client;

/// <summary>The underwater view: the quad in front of the player's camera.</summary>
public partial class UnderwaterView : MeshInstance3D, IWired
{
    /// <summary>The bus whose low-pass filter muffles the world under water.</summary>
    [Export] public string Bus { get; set; } = "SFX";

    private LevelWater? _water;
    private int _bus = -1;
    private int _lowPass = -1;

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _water = services.Level.Water;
        _bus = AudioServer.GetBusIndex(Bus);
        for (var i = 0; _bus >= 0 && i < AudioServer.GetBusEffectCount(_bus); i++)
        {
            if (AudioServer.GetBusEffect(_bus, i) is AudioEffectLowPassFilter)
            {
                _lowPass = i;
            }
        }
        if (_lowPass < 0)
        {
            GD.PushError($"[Undercity] the {Bus} bus has no low-pass filter for under water (audio/default_bus_layout.tres)");
        }
        Visible = false;
    }

    public override void _Process(double delta)
    {
        if (_water is null)
        {
            return;
        }
        var eye = GlobalPosition;
        var under = _water.SurfaceAt(eye) is { } s && eye.Y < s;
        if (under == Visible)
        {
            return;
        }
        Visible = under;
        if (_lowPass >= 0)
        {
            AudioServer.SetBusEffectEnabled(_bus, _lowPass, under);
        }
    }

    public override void _ExitTree()
    {
        if (_lowPass >= 0)
        {
            AudioServer.SetBusEffectEnabled(_bus, _lowPass, false);
        }
    }
}
