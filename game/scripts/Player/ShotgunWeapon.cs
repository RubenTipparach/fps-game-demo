using Godot;

namespace Brushfire;

/// <summary>Pump shotgun: 10 pellets, pump action animation after each shot.</summary>
public partial class ShotgunWeapon : Weapon
{
    Node3D _pump;
    Vector3 _pumpRest;
    float _pumpTimer = -1f;

    public override void _Ready()
    {
        base._Ready();
        _pump = FindChild("Pump", true, false) as Node3D;
        if (_pump != null)
            _pumpRest = _pump.Position;
    }

    protected override void Fire()
    {
        base.Fire();
        _pumpTimer = 0f;
    }

    public override void Tick(float dt, bool trigger, bool justPressed)
    {
        base.Tick(dt, trigger, justPressed);
        if (_pumpTimer < 0f || _pump == null)
            return;
        float before = _pumpTimer;
        _pumpTimer += dt;
        const float start = 0.28f, length = 0.36f;
        if (before < start && _pumpTimer >= start)
            Audio.Play2D(this, "shotgun_pump", -5f, 0.03f);
        float t = Mathf.Clamp((_pumpTimer - start) / length, 0f, 1f);
        float stroke = Mathf.Sin(t * Mathf.Pi); // back then forward
        _pump.Position = _pumpRest + new Vector3(0, 0, 0.11f * stroke);
        Rotation = new Vector3(Mathf.DegToRad(-6f) * stroke, 0, Mathf.DegToRad(8f) * stroke);
        if (t >= 1f)
        {
            _pumpTimer = -1f;
            Rotation = Vector3.Zero;
        }
    }

    public override void OnHolster()
    {
        _pumpTimer = -1f;
        if (_pump != null)
            _pump.Position = _pumpRest;
        Rotation = Vector3.Zero;
    }
}
