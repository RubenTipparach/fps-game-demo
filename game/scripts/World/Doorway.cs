using System.Collections.Generic;
using Godot;

namespace Brushfire;

/// <summary>
/// Quake 2 / Unreal style split door: a static, lightmapped frame with two sliding leaves
/// (<see cref="Door"/> bodies in controlled mode) and red/green status lights on the lintel.
/// Opens for the player and for enemies, stays open while anyone is in the doorway.
/// </summary>
public partial class Doorway : Node3D
{
    [Export] public float TriggerRadius = 3.6f;
    [Export] public float Wait = 1.8f;
    [Export] public bool Locked;

    readonly List<Door> _leaves = new();
    MeshInstance3D _status;
    StandardMaterial3D _red, _green;
    AudioStreamPlayer3D _audio;
    bool _open;
    float _wait;

    public override void _Ready()
    {
        foreach (var n in FindChildren("*", "AnimatableBody3D", true, false))
            if (n is Door d)
            {
                d.Controlled = true;
                _leaves.Add(d);
            }
        _status = FindChild("Status*", true, false) as MeshInstance3D;
        _red = StatusMaterial(new Color(1f, 0.12f, 0.06f));
        _green = StatusMaterial(new Color(0.2f, 1f, 0.3f));
        if (_status != null)
            _status.MaterialOverride = _red;
        _audio = new AudioStreamPlayer3D { Bus = "World", UnitSize = 9f, MaxDistance = 60f, Position = new Vector3(0, 2f, 0) };
        AddChild(_audio);
    }

    static StandardMaterial3D StatusMaterial(Color c) => new()
    {
        AlbedoColor = c * 0.4f,
        EmissionEnabled = true,
        Emission = c,
        EmissionEnergyMultiplier = 5f,
        Roughness = 0.3f,
    };

    bool SomeoneNear()
    {
        Vector3 c = GlobalPosition + Vector3.Up;
        var player = PlayerController.Instance;
        if (player != null && !player.IsDead && player.GlobalPosition.DistanceTo(c) < TriggerRadius)
            return true;
        foreach (var n in GetTree().GetNodesInGroup("enemies"))
            if (n is Node3D e && e.GlobalPosition.DistanceTo(c) < TriggerRadius - 0.6f)
                return true;
        return false;
    }

    public override void _PhysicsProcess(double delta)
    {
        if (Locked)
            return;
        if (SomeoneNear())
        {
            _wait = Wait;
            if (!_open)
                SetOpen(true);
        }
        else if (_open)
        {
            _wait -= (float)delta;
            if (_wait <= 0f)
                SetOpen(false);
        }
    }

    void SetOpen(bool open)
    {
        _open = open;
        foreach (var d in _leaves)
            d.WantOpen = open;
        if (_status != null)
            _status.MaterialOverride = open ? _green : _red;
        _audio.Stream = Audio.Pick(open ? "door_open" : "door_close");
        _audio.Play();
    }
}
