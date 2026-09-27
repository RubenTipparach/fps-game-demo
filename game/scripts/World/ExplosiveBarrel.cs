using Godot;

namespace Brushfire;

/// <summary>Shoot it. It explodes. Chains into other barrels.</summary>
public partial class ExplosiveBarrel : StaticBody3D, IDamageable
{
    [Export] public float Health = 25f;
    [Export] public float BlastDamage = 110f;
    [Export] public float BlastRadius = 5f;

    public bool IsDead { get; private set; }

    public override void _Ready()
    {
        CollisionLayer = Layers.World;
        foreach (var n in FindChildren("*", "GeometryInstance3D", true, false))
            ((GeometryInstance3D)n).GIMode = GeometryInstance3D.GIModeEnum.Dynamic;
    }

    public void TakeDamage(DamageInfo info)
    {
        if (IsDead)
            return;
        Health -= info.Amount;
        if (Health > 0f)
            return;
        IsDead = true;
        // A short fuse makes chain reactions ripple instead of all popping on one frame.
        float fuse = info.Kind == DamageKind.Explosion ? (float)GD.RandRange(0.12, 0.25) : 0.02f;
        GetTree().CreateTimer(fuse, false, true).Timeout += Detonate;
    }

    void Detonate()
    {
        if (!IsInsideTree())
            return;
        Vector3 c = GlobalPosition + Vector3.Up * 0.6f;
        CollisionLayer = 0;
        Visible = false;
        Explosions.Explode(this, c, BlastRadius, BlastDamage, this);
        Fx.Explosion(this, c, 1.2f);
        QueueFree();
    }
}
