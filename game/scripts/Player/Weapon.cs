using System.Collections.Generic;
using Godot;

namespace Brushfire;

/// <summary>
/// Base weapon: ammo, fire rate, hitscan with spread, muzzle flash, recoil and noise.
/// Child nodes: "Muzzle" (Marker3D at the barrel tip) with an optional "Muzzle/Flash" mesh.
/// </summary>
public partial class Weapon : Node3D
{
    [Export] public string DisplayName = "Weapon";
    [Export] public int Slot = 1;
    [Export] public bool Owned;
    [Export] public AmmoType Ammo = AmmoType.Shells;
    [Export] public int AmmoPerShot = 1;
    [Export] public float FireInterval = 0.5f;
    [Export] public float Damage = 10f;
    [Export] public int Pellets = 1;
    [Export] public float SpreadDegrees;
    [Export] public float Range = 250f;
    [Export] public float ViewKick = 1.5f;
    [Export] public Vector3 KickPush = new(0f, 0.01f, 0.08f);
    [Export] public float KickPitch = 6f;
    [Export] public string FireSound = "";
    [Export] public float FireVolumeDb;
    [Export] public float NoiseRadius = 35f;
    [Export] public bool Tracers;

    public WeaponManager Manager;
    protected float Cooldown;
    Node3D _muzzle;
    Node3D _flash;
    float _flashTimer;

    public bool HasAmmo => Manager.GetAmmo(Ammo) >= AmmoPerShot;
    public bool ReadyToFire => Cooldown <= 0f;
    /// <summary>Current spread in degrees; the crosshair opens up to match.</summary>
    public virtual float CurrentSpread => SpreadDegrees;
    protected PlayerController Player => Manager.Player;

    public override void _Ready()
    {
        _muzzle = FindChild("Muzzle", true, false) as Node3D;
        _flash = _muzzle?.GetNodeOrNull<Node3D>("Flash");
        if (_flash != null)
            _flash.Visible = false;
    }

    public virtual void Tick(float dt, bool trigger, bool justPressed)
    {
        Cooldown -= dt;
        _flashTimer -= dt;
        if (_flash != null)
            _flash.Visible = _flashTimer > 0f && Visible;
        if (Cooldown > 0f || !trigger)
            return;
        if (!HasAmmo)
        {
            if (justPressed)
            {
                Audio.Play2D(this, "dry_fire", -6f);
                Cooldown = 0.3f;
            }
            return;
        }
        TryFire(dt);
    }

    protected void TryFire(float dt)
    {
        Manager.TakeAmmo(Ammo, AmmoPerShot);
        // Carry the remainder so the fire rate is exact regardless of frame rate.
        Cooldown = Mathf.Max(Cooldown, -dt) + FireInterval;
        Fire();
    }

    protected virtual void Fire()
    {
        PlayFireEffects();
        FireHitscan(Pellets, Damage, CurrentSpread);
    }

    public virtual void OnHolster() { }

    protected Vector3 MuzzlePosition => _muzzle?.GlobalPosition ?? Player.EyePosition;

    protected void PlayFireEffects()
    {
        if (!string.IsNullOrEmpty(FireSound))
            Audio.Play2D(this, FireSound, FireVolumeDb, 0.04f);
        if (_flash != null)
        {
            _flashTimer = 0.045f;
            _flash.Rotation = new Vector3(0, 0, (float)GD.RandRange(0, Mathf.Tau));
            _flash.Scale = Vector3.One * (float)GD.RandRange(0.8, 1.25);
        }
        Fx.MuzzleFlashLight(this, Player.EyePosition + Player.LookDirection * 0.7f);
        Manager.Kick(KickPush, KickPitch, ViewKick);
        Events.EmitNoise(Player.GlobalPosition, NoiseRadius);
        Game.Instance.Stats.ShotsFired++;
    }

    protected void FireHitscan(int pellets, float damage, float spreadDegrees)
    {
        var player = Player;
        Vector3 origin = player.EyePosition;
        Basis aim = Basis.FromEuler(new Vector3(player.Pitch, player.Yaw, 0f));
        var space = player.GetWorld3D().DirectSpaceState;
        var exclude = new Godot.Collections.Array<Rid> { player.GetRid() };
        var hits = new Dictionary<GodotObject, (float amount, Vector3 point, Vector3 dir)>();
        int fxCount = 0;

        for (int i = 0; i < pellets; i++)
        {
            Vector3 dir = SpreadDirection(aim, spreadDegrees, i, pellets);
            var query = PhysicsRayQueryParameters3D.Create(origin, origin + dir * Range, Layers.World | Layers.Enemy);
            query.Exclude = exclude;
            var hit = space.IntersectRay(query);
            if (hit.Count == 0)
            {
                if (Tracers)
                    Fx.Tracer(this, MuzzlePosition, origin + dir * 60f);
                continue;
            }
            var pos = (Vector3)hit["position"];
            var normal = (Vector3)hit["normal"];
            var collider = hit["collider"].AsGodotObject();
            if (Tracers)
                Fx.Tracer(this, MuzzlePosition, pos);
            if (collider is IDamageable target && !target.IsDead)
            {
                hits.TryGetValue(collider, out var acc);
                hits[collider] = (acc.amount + damage, pos, dir);
                if (fxCount++ < 4)
                    Fx.RobotHit(this, pos, normal);
            }
            else
            {
                Fx.Impact(this, pos, normal, collider as Node, i < 2);
            }
        }

        foreach (var (obj, (amount, point, dir)) in hits)
        {
            var target = (IDamageable)obj;
            target.TakeDamage(new DamageInfo(amount, DamageKind.Bullet, point, dir, player)
            {
                Knockback = dir * Mathf.Min(amount * 0.05f, 5f),
            });
            Game.Instance.Stats.ShotsHit++;
            player.Hud.ShowHitMarker(target.IsDead);
        }
    }

    static Vector3 SpreadDirection(Basis aim, float spreadDegrees, int index, int count)
    {
        Vector3 forward = -aim.Z;
        if (spreadDegrees <= 0f)
            return forward;
        float r, a;
        if (count > 1)
        {
            // Shotgun: a jittered sunflower pattern. Consistent and readable, never all-miss.
            r = index == 0 ? 0f : Mathf.Sqrt((index + 0.5f) / count) + (float)GD.RandRange(-0.08, 0.08);
            a = index * 2.39996f + (float)GD.RandRange(-0.3, 0.3);
        }
        else
        {
            r = Mathf.Sqrt(GD.Randf());
            a = GD.Randf() * Mathf.Tau;
        }
        float t = Mathf.Tan(Mathf.DegToRad(spreadDegrees)) * r;
        return (forward + aim.X * (Mathf.Cos(a) * t) + aim.Y * (Mathf.Sin(a) * t)).Normalized();
    }
}
