using Godot;

namespace Brushfire;

/// <summary>
/// Straight-flying projectile (rockets, plasma balls). Moves with ray sweeps every physics
/// tick so it can never tunnel through thin walls, then deals direct and/or splash damage.
/// A child named "Trail" (particles) is detached on impact so the smoke lingers.
/// </summary>
public partial class Projectile : Node3D
{
    [Export] public float Speed = 26f;
    [Export] public float DirectDamage = 100f;
    [Export] public float SplashDamage = 90f;
    [Export] public float SplashRadius = 4.2f;
    [Export] public float Knockback = 13f;
    [Export] public float Lifetime = 8f;
    [Export] public float Radius = 0.1f;
    [Export] public DamageKind Kind = DamageKind.Explosion;
    [Export] public bool Explodes = true;
    [Export] public Color ImpactColor = new(0.3f, 0.8f, 1f);

    Node3D _shooter;
    Vector3 _velocity;
    uint _mask;
    float _age;
    bool _done;

    public void Launch(Vector3 position, Vector3 direction, Node3D shooter, uint mask)
    {
        _shooter = shooter;
        _mask = mask;
        _velocity = direction.Normalized() * Speed;
        GlobalPosition = position;
        LookAt(position + direction, Mathf.Abs(direction.Y) > 0.99f ? Vector3.Right : Vector3.Up);
        ResetPhysicsInterpolation();
    }

    public override void _PhysicsProcess(double delta)
    {
        if (_done)
            return;
        float dt = (float)delta;
        _age += dt;
        if (_age > Lifetime)
        {
            QueueFree();
            return;
        }
        Vector3 from = GlobalPosition;
        Vector3 to = from + _velocity * dt;
        var space = GetWorld3D().DirectSpaceState;
        var query = PhysicsRayQueryParameters3D.Create(from, to + _velocity.Normalized() * Radius, _mask);
        if (_shooter is CollisionObject3D co)
            query.Exclude = new Godot.Collections.Array<Rid> { co.GetRid() };
        var hit = space.IntersectRay(query);
        if (hit.Count > 0)
        {
            ForceImpact((Vector3)hit["position"], (Vector3)hit["normal"], hit["collider"].AsGodotObject());
            return;
        }
        GlobalPosition = to;
    }

    public void ForceImpact(Vector3 point, Vector3 normal, GodotObject collider)
    {
        if (_done)
            return;
        _done = true;
        Vector3 dir = _velocity.Normalized();
        if (collider is IDamageable target && !target.IsDead && DirectDamage > 0f)
        {
            target.TakeDamage(new DamageInfo(DirectDamage, Kind, point, dir, _shooter)
            {
                Knockback = dir * Knockback * 0.5f,
            });
            if (_shooter is PlayerController p)
                p.Hud.ShowHitMarker(target.IsDead);
        }
        Vector3 center = point + normal * 0.15f;
        if (Explodes)
        {
            Explosions.Explode(this, center, SplashRadius, SplashDamage, _shooter, Knockback);
            Fx.Explosion(this, center, SplashRadius / 4.2f);
        }
        else
        {
            Fx.PlasmaImpact(this, center, normal, ImpactColor);
        }
        var trail = GetNodeOrNull<GpuParticles3D>("Trail") as Node3D ?? GetNodeOrNull<CpuParticles3D>("Trail");
        if (trail != null)
        {
            var xf = trail.GlobalTransform;
            RemoveChild(trail);
            GetParent().AddChild(trail);
            trail.GlobalTransform = xf;
            if (trail is CpuParticles3D cpu)
            {
                cpu.Emitting = false;
                GetTree().CreateTimer(cpu.Lifetime + 0.1).Timeout += cpu.QueueFree;
            }
        }
        QueueFree();
    }
}
