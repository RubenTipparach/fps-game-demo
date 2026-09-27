using Godot;

namespace Brushfire;

/// <summary>Rotary chaingun: spins up before firing, spread blooms under sustained fire.</summary>
public partial class ChaingunWeapon : Weapon
{
    [Export] public float SpinUpTime = 0.28f;
    [Export] public float MaxBloom = 2.8f;
    Node3D _barrels;
    float _spin;
    float _bloom;
    bool _wasSpinning;

    public override float CurrentSpread => SpreadDegrees + _bloom;

    public override void _Ready()
    {
        base._Ready();
        _barrels = FindChild("Barrels", true, false) as Node3D;
    }

    public override void Tick(float dt, bool trigger, bool justPressed)
    {
        bool spinning = trigger && HasAmmo;
        if (spinning && !_wasSpinning && _spin < 0.3f)
            Audio.Play2D(this, "chaingun_windup", -8f, 0.02f);
        _wasSpinning = spinning;
        _spin = Mathf.MoveToward(_spin, spinning ? 1f : 0f, dt / (spinning ? SpinUpTime : 0.9f));
        if (_barrels != null)
            _barrels.RotateZ(_spin * 28f * dt);
        _bloom = Mathf.MoveToward(_bloom, 0f, dt * 3.5f);
        // Only allow the trigger through once the barrels are up to speed.
        base.Tick(dt, trigger && (_spin > 0.85f || !HasAmmo), justPressed);
    }

    protected override void Fire()
    {
        base.Fire();
        _bloom = Mathf.Min(_bloom + 0.22f, MaxBloom);
    }

    public override void OnHolster()
    {
        _spin = 0f;
        _bloom = 0f;
    }
}
