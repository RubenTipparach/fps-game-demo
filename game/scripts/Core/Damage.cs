using Godot;

namespace Brushfire;

public enum DamageKind { Bullet, Explosion, Melee, Plasma, Hazard }

public struct DamageInfo
{
    public float Amount;
    public DamageKind Kind;
    public Vector3 Point;
    public Vector3 Direction;   // direction the damage travels (from attacker to victim)
    public Vector3 Knockback;   // velocity change applied to the victim
    public Node3D Source;       // attacker (may be null)
    public string WeaponId;     // the weapon's id in Undercity's data/weapons.json, or null (Brushfire's weapons)
    public int Hits;            // pellets or rounds this damage sums; 1 when unset

    public DamageInfo(float amount, DamageKind kind, Vector3 point, Vector3 direction, Node3D source = null)
    {
        Amount = amount;
        Kind = kind;
        Point = point;
        Direction = direction;
        Knockback = Vector3.Zero;
        Source = source;
        WeaponId = null;
        Hits = 1;
    }
}

/// <summary>Anything that can be shot: player, enemies, explosive barrels.</summary>
public interface IDamageable
{
    bool IsDead { get; }
    void TakeDamage(DamageInfo info);
}

/// <summary>
/// Something hurt that shows its own hits: Undercity's people bleed where Brushfire's robots
/// spark. A weapon asks this first and falls back to Fx.RobotHit.
/// </summary>
public interface IHitEffect
{
    void ShowHit(Vector3 point, Vector3 normal);
}

/// <summary>Physics layer bits (see Project Settings > Layer Names > 3D Physics).</summary>
public static class Layers
{
    public const uint World = 1 << 0;
    public const uint Player = 1 << 1;
    public const uint Enemy = 1 << 2;
    public const uint Pickup = 1 << 3;
    public const uint Projectile = 1 << 4;
    public const uint Debris = 1 << 5;

    /// <summary>What bullets and line-of-sight checks collide with.</summary>
    public const uint Shootable = World | Player | Enemy;
}

public static class Events
{
    /// <summary>A loud noise (gunfire, explosion) that can alert enemies.</summary>
    public static event System.Action<Vector3, float> Noise;
    public static event System.Action<Node3D> EnemyKilled;
    public static event System.Action<string> Message;

    public static void EmitNoise(Vector3 position, float radius) => Noise?.Invoke(position, radius);

    public static void EmitEnemyKilled(Node3D enemy) => EnemyKilled?.Invoke(enemy);
    public static void EmitMessage(string text) => Message?.Invoke(text);

    /// <summary>Called on scene change so dead listeners from the previous level are dropped.</summary>
    public static void Clear()
    {
        Noise = null;
        EnemyKilled = null;
        Message = null;
    }
}

/// <summary>Area damage with line-of-sight falloff (rockets, barrels, enemy plasma).</summary>
public static class Explosions
{
    public static void Explode(Node3D context, Vector3 center, float radius, float damage, Node3D source,
        float knockback = 12f, float selfDamageScale = 0.5f)
    {
        var world = context.GetWorld3D();
        var space = world.DirectSpaceState;
        var shape = new SphereShape3D { Radius = radius };
        var query = new PhysicsShapeQueryParameters3D
        {
            Shape = shape,
            Transform = new Transform3D(Basis.Identity, center),
            CollisionMask = Layers.Player | Layers.Enemy | Layers.World,
            CollideWithAreas = false,
            CollideWithBodies = true,
        };
        var hits = space.IntersectShape(query, 64);
        var done = new System.Collections.Generic.HashSet<ulong>();
        foreach (var hit in hits)
        {
            if (hit["collider"].AsGodotObject() is not Node3D body || body is not IDamageable target || target.IsDead)
                continue;
            if (!done.Add(body.GetInstanceId()))
                continue;
            Vector3 targetCenter = body.GlobalPosition + Vector3.Up * 0.9f;
            float dist = center.DistanceTo(targetCenter);
            // Walls block splash damage.
            var ray = PhysicsRayQueryParameters3D.Create(center, targetCenter, Layers.World);
            if (space.IntersectRay(ray).Count > 0 && dist > 1.0f)
                continue;
            float falloff = Mathf.Clamp(1f - dist / radius, 0f, 1f);
            float amount = damage * Mathf.Lerp(0.25f, 1f, falloff);
            if (body == source)
                amount *= selfDamageScale;
            Vector3 dir = (targetCenter - center).Normalized();
            if (dir.LengthSquared() < 0.01f)
                dir = Vector3.Up;
            var info = new DamageInfo(amount, DamageKind.Explosion, targetCenter, dir, source)
            {
                Knockback = (dir + Vector3.Up * 0.35f).Normalized() * knockback * falloff,
            };
            target.TakeDamage(info);
        }
        Events.EmitNoise(center, 30f);
    }
}
