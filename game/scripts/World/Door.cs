using Godot;

namespace Brushfire;

/// <summary>
/// Sliding door (AnimatableBody3D) that opens when the player or an enemy comes near and
/// closes after a delay. Doors move, so they are lit by light probes instead of lightmaps.
/// Works as a TrenchBroom brush entity (func_door) or a hand-placed scene.
/// </summary>
public partial class Door : AnimatableBody3D
{
    [Export] public Vector3 OpenOffset = new(0, 3.2f, 0);
    [Export] public float Speed = 3.5f;
    [Export] public float Wait = 2.5f;
    [Export] public float TriggerRadius = 3.2f;
    [Export] public bool Locked;
    /// <summary>Driven by a <see cref="Doorway"/> (split doors): no own trigger or sounds.</summary>
    [Export] public bool Controlled;
    /// <summary>Key/values from a TrenchBroom func_door (filled in by func_godot at map build).</summary>
    [Export] public Godot.Collections.Dictionary func_godot_properties = new();

    Vector3 _closed;
    float _open;       // 0 = closed, 1 = open
    float _waitTimer;
    int _dir;          // 1 opening, -1 closing, 0 idle
    AudioStreamPlayer3D _audio;

    /// <summary>Set by a Doorway controller when <see cref="Controlled"/>.</summary>
    public bool WantOpen { get; set; }
    public float OpenAmount => _open;

    public override void _Ready()
    {
        if (func_godot_properties.Count > 0)
            ApplyMapProperties(func_godot_properties);
        _closed = Position;
        SyncToPhysics = true;
        CollisionLayer = Layers.World;
        _audio = new AudioStreamPlayer3D { Bus = "World", UnitSize = 8f, MaxDistance = 60f };
        AddChild(_audio);
        // func_godot builds meshes at the body origin; make them dynamic-GI so probes light them.
        foreach (var n in FindChildren("*", "GeometryInstance3D", true, false))
            ((GeometryInstance3D)n).GIMode = GeometryInstance3D.GIModeEnum.Dynamic;
    }

    Vector3 Center
    {
        get
        {
            foreach (var n in GetChildren())
                if (n is CollisionShape3D cs)
                    return cs.GlobalPosition;
            return GlobalPosition;
        }
    }

    bool SomeoneNear()
    {
        Vector3 c = Center - OpenOffset * _open;
        var player = PlayerController.Instance;
        if (player != null && !player.IsDead && player.GlobalPosition.DistanceTo(c) < TriggerRadius + 1f)
            return true;
        foreach (var n in GetTree().GetNodesInGroup("enemies"))
            if (n is Node3D e && e.GlobalPosition.DistanceTo(c) < TriggerRadius)
                return true;
        return false;
    }

    public override void _PhysicsProcess(double delta)
    {
        float dt = (float)delta;
        if (Locked)
            return;
        bool near = Controlled ? WantOpen : SomeoneNear();
        if (near)
        {
            _waitTimer = Controlled ? 0f : Wait;
            if (_open < 1f && _dir != 1)
            {
                _dir = 1;
                if (!Controlled)
                    Play("door_open");
            }
        }
        else if (_open > 0f && _dir != -1)
        {
            _waitTimer -= dt;
            if (_waitTimer <= 0f)
            {
                _dir = -1;
                if (!Controlled)
                    Play("door_close");
            }
        }
        if (_dir != 0)
        {
            float len = Mathf.Max(OpenOffset.Length(), 0.01f);
            _open = Mathf.Clamp(_open + _dir * Speed / len * dt, 0f, 1f);
            if (_open is <= 0f or >= 1f)
                _dir = 0;
            float eased = Mathf.SmoothStep(0f, 1f, _open);
            Position = _closed + OpenOffset * eased;
        }
    }

    void Play(string sound)
    {
        _audio.Stream = Audio.Pick(sound);
        _audio.Play();
    }

    /// <summary>Map keys: "angle" (-1 = up, -2 = down, else yaw), "lip", "speed", "wait" (Quake units).</summary>
    void ApplyMapProperties(Godot.Collections.Dictionary props)
    {
        float lip = props.TryGetValue("lip", out var l) ? (float)l.AsDouble() / 32f : 0.1f;
        if (props.TryGetValue("speed", out var s))
            Speed = (float)s.AsDouble() / 32f;
        if (props.TryGetValue("wait", out var w))
            Wait = (float)w.AsDouble();
        float angle = props.TryGetValue("angle", out var a) ? (float)a.AsDouble() : -1f;
        // Size comes from the generated collision shape.
        Vector3 size = Vector3.One * 3f;
        foreach (var n in GetChildren())
            if (n is CollisionShape3D { Shape: ConvexPolygonShape3D poly })
            {
                var aabb = new Aabb(poly.Points[0], Vector3.Zero);
                foreach (var p in poly.Points)
                    aabb = aabb.Expand(p);
                size = aabb.Size;
            }
        if (angle == -1f)
            OpenOffset = new Vector3(0, size.Y - lip, 0);
        else if (angle == -2f)
            OpenOffset = new Vector3(0, -(size.Y - lip), 0);
        else
        {
            // Quake yaw: 0 = +X (east), 90 = north (-Z in Godot)
            float rad = Mathf.DegToRad(angle);
            var dir = new Vector3(Mathf.Cos(rad), 0, -Mathf.Sin(rad));
            float extent = Mathf.Abs(dir.X) * size.X + Mathf.Abs(dir.Z) * size.Z;
            OpenOffset = dir * (extent - lip);
        }
    }
}
