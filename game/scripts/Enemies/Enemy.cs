using System.Collections.Generic;
using Godot;

namespace Brushfire;

public enum EnemyKind { Grunt, Brute, Drone }

/// <summary>
/// Data-driven enemy AI with three archetypes:
///  * Grunt: walks the navmesh, telegraphs, then fires a hitscan burst.
///  * Brute: heavy melee charger that roars and lunges.
///  * Drone: hovering turret that circles the player and lobs plasma.
/// Perception: sight cone + line of sight, and hearing (gunfire/explosions emit noise).
/// Visuals are rigid parts under "Rig" animated procedurally; on death each part becomes a
/// physics gib, old-school style.
/// </summary>
public partial class Enemy : CharacterBody3D, IDamageable
{
    enum State { Idle, Chase, Windup, Attack, Pain, Dead }

    [ExportGroup("Archetype")]
    [Export] public EnemyKind Kind = EnemyKind.Grunt;
    [Export] public float MaxHealth = 60f;
    [Export] public float MoveSpeed = 4.2f;
    [Export] public float ChargeSpeed = 9f;
    [Export] public float TurnSpeed = 8f;
    [Export] public float EyeHeight = 1.55f;
    [Export] public bool Ambush;             // ignores noise until it sees the player
    /// <summary>Key/values from a TrenchBroom monster_* entity (filled in by func_godot).</summary>
    [Export] public Godot.Collections.Dictionary func_godot_properties = new();

    [ExportGroup("Perception")]
    [Export] public float SightRange = 45f;
    [Export] public float FieldOfView = 140f;

    [ExportGroup("Attack")]
    [Export] public float AttackRange = 24f;
    [Export] public float PreferredRange = 0f; // drones keep their distance
    [Export] public float AttackCooldown = 1.8f;
    [Export] public float WindupTime = 0.5f;
    [Export] public float Damage = 6f;
    [Export] public int BurstCount = 3;
    [Export] public float BurstInterval = 0.11f;
    [Export] public float Inaccuracy = 3f;
    [Export] public PackedScene ProjectileScene;
    [Export] public float PainChance = 0.55f;

    [ExportGroup("Drone")]
    [Export] public float HoverHeight = 2.8f;

    [ExportGroup("Drops")]
    [Export] public PackedScene DropScene;
    [Export(PropertyHint.Range, "0,1")] public float DropChance = 0.5f;

    public bool IsDead => _state == State.Dead;

    State _state = State.Idle;
    float _health;
    float _stateTime;
    float _cooldown;
    float _perceptionTimer;
    bool _canSee;
    bool _alerted;
    Vector3 _lastKnown;
    float _repathTimer;
    float _walkPhase;
    float _flashTimer;
    int _burstLeft;
    float _burstTimer;
    float _stuckTimer;
    Vector3 _strafe;
    float _strafeTimer;
    float _chargeTimer;
    float _stepTimer;
    float _circleDir = 1f;
    Vector3 _lastDamageDir = Vector3.Forward;

    NavigationAgent3D _agent;
    Node3D _rig, _head, _torso, _legL, _legR, _armL, _armR, _muzzle;
    OmniLight3D _eyeLight;
    float _eyeBaseEnergy;
    AudioStreamPlayer3D _voice;
    AudioStreamPlayer3D _hum;
    readonly List<MeshInstance3D> _meshes = new();
    static StandardMaterial3D _flashMaterial;
    static readonly List<Enemy> All = new();

    public override void _EnterTree() => All.Add(this);
    public override void _ExitTree()
    {
        All.Remove(this);
        Events.Noise -= OnNoise;
    }

    public override void _Ready()
    {
        // TrenchBroom: "ambush" key or spawnflag 1, like Quake monsters.
        if (func_godot_properties.TryGetValue("ambush", out var amb) && amb.AsString() is "1" or "true")
            Ambush = true;
        if (func_godot_properties.TryGetValue("spawnflags", out var sf) && (sf.AsInt32() & 1) != 0)
            Ambush = true;
        AddToGroup("enemies");
        _health = MaxHealth;
        _agent = GetNodeOrNull<NavigationAgent3D>("NavigationAgent3D");
        _rig = GetNode<Node3D>("Rig");
        _head = _rig.GetNodeOrNull<Node3D>("Head");
        _torso = _rig.GetNodeOrNull<Node3D>("Torso");
        _legL = _rig.GetNodeOrNull<Node3D>("LegL");
        _legR = _rig.GetNodeOrNull<Node3D>("LegR");
        _armL = _rig.GetNodeOrNull<Node3D>("ArmL");
        _armR = _rig.GetNodeOrNull<Node3D>("ArmR");
        _muzzle = _rig.FindChild("Muzzle", true, false) as Node3D;
        _eyeLight = _rig.FindChild("EyeLight", true, false) as OmniLight3D;
        if (_eyeLight != null)
            _eyeBaseEnergy = _eyeLight.LightEnergy;
        _voice = GetNodeOrNull<AudioStreamPlayer3D>("Voice");
        _hum = GetNodeOrNull<AudioStreamPlayer3D>("Hum");
        CollectMeshes(_rig);
        _flashMaterial ??= new StandardMaterial3D
        {
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
            AlbedoColor = new Color(1f, 0.9f, 0.8f, 0.55f),
            Transparency = BaseMaterial3D.TransparencyEnum.Alpha,
            BlendMode = BaseMaterial3D.BlendModeEnum.Add,
        };

        if (Kind == EnemyKind.Drone)
            MotionMode = MotionModeEnum.Floating;
        FloorMaxAngle = Mathf.DegToRad(46f);
        FloorSnapLength = 0.3f;
        _cooldown = (float)GD.RandRange(0.3, 1.2);
        _circleDir = GD.Randf() < 0.5f ? -1f : 1f;
        _walkPhase = GD.Randf() * Mathf.Tau;
        Events.Noise += OnNoise;
    }

    void CollectMeshes(Node n)
    {
        foreach (var c in n.GetChildren())
        {
            if (c is MeshInstance3D m)
                _meshes.Add(m);
            CollectMeshes(c);
        }
    }

    // ------------------------------------------------------------------ perception

    void OnNoise(Vector3 position, float radius)
    {
        if (IsDead || _alerted || Ambush || !IsInsideTree())
            return;
        if (GlobalPosition.DistanceTo(position) <= radius)
        {
            _lastKnown = PlayerController.Instance?.GlobalPosition ?? position;
            Alert();
        }
    }

    Vector3 EyePos => GlobalPosition + Vector3.Up * EyeHeight;

    bool CheckSight(PlayerController player)
    {
        Vector3 target = player.GlobalPosition + Vector3.Up * 1.2f;
        Vector3 to = target - EyePos;
        float dist = to.Length();
        if (dist > SightRange)
            return false;
        if (!_alerted)
        {
            Vector3 fwd = -GlobalBasis.Z;
            if (Mathf.RadToDeg(fwd.AngleTo(to)) > FieldOfView * 0.5f && dist > 4f)
                return false;
        }
        var q = PhysicsRayQueryParameters3D.Create(EyePos, target, Layers.World);
        return GetWorld3D().DirectSpaceState.IntersectRay(q).Count == 0;
    }

    void Alert()
    {
        if (_alerted)
            return;
        _alerted = true;
        if (_state == State.Idle)
            SetState(State.Chase);
        PlayVoice(Kind == EnemyKind.Brute ? "brute_roar" : "enemy_alert");
        // Wake nearby friends.
        foreach (var e in All)
            if (e != this && !e._alerted && e.GlobalPosition.DistanceTo(GlobalPosition) < 10f)
            {
                e._lastKnown = _lastKnown;
                e.CallDeferred(MethodName.Alert);
            }
    }

    void PlayVoice(string sound, float db = 0f)
    {
        var stream = Audio.Pick(sound);
        if (_voice == null || stream == null)
        {
            Audio.Play3D(this, sound, EyePos, db);
            return;
        }
        _voice.Stream = stream;
        _voice.VolumeDb = db;
        _voice.PitchScale = 1f + (float)GD.RandRange(-0.08, 0.08);
        _voice.Play();
    }

    void SetState(State s)
    {
        _state = s;
        _stateTime = 0f;
    }

    // ------------------------------------------------------------------ update

    public override void _PhysicsProcess(double delta)
    {
        if (_state == State.Dead)
            return;
        float dt = (float)delta;
        _stateTime += dt;
        _cooldown -= dt;
        _flashTimer -= dt;
        if (_flashTimer <= 0f && _meshes.Count > 0 && _meshes[0].MaterialOverlay != null)
            foreach (var m in _meshes)
                m.MaterialOverlay = null;

        var player = PlayerController.Instance;
        bool playerAlive = player != null && !player.IsDead;

        _perceptionTimer -= dt;
        if (_perceptionTimer <= 0f)
        {
            _perceptionTimer = 0.15f + GD.Randf() * 0.05f;
            _canSee = playerAlive && CheckSight(player);
            if (_canSee)
            {
                _lastKnown = player.GlobalPosition;
                if (!_alerted)
                    Alert();
            }
        }

        Vector3 desired = Vector3.Zero;
        float dist = playerAlive ? GlobalPosition.DistanceTo(player.GlobalPosition) : 999f;
        Vector3 faceTarget = _lastKnown;

        switch (_state)
        {
            case State.Idle:
                break;

            case State.Chase:
                if (!playerAlive)
                    break;
                if (_canSee && _cooldown <= 0f && dist <= AttackRange)
                {
                    SetState(State.Windup);
                    if (Kind == EnemyKind.Brute)
                        PlayVoice("brute_attack", -2f);
                    break;
                }
                desired = ChaseVelocity(player, dist, dt);
                if (desired.LengthSquared() > 0.1f && Kind != EnemyKind.Drone)
                    faceTarget = GlobalPosition + desired;
                if (_canSee && Kind != EnemyKind.Brute)
                    faceTarget = player.GlobalPosition;
                break;

            case State.Windup:
                faceTarget = playerAlive ? player.GlobalPosition : _lastKnown;
                if (Kind == EnemyKind.Brute && playerAlive)
                    desired = (player.GlobalPosition - GlobalPosition).Normalized() * ChargeSpeed * 0.6f;
                if (_stateTime >= WindupTime)
                {
                    SetState(State.Attack);
                    _burstLeft = Kind == EnemyKind.Brute ? 1 : BurstCount;
                    _burstTimer = 0f;
                }
                break;

            case State.Attack:
                faceTarget = playerAlive ? player.GlobalPosition : _lastKnown;
                _burstTimer -= dt;
                if (_burstLeft > 0 && _burstTimer <= 0f)
                {
                    _burstLeft--;
                    _burstTimer = BurstInterval;
                    if (playerAlive)
                        PerformAttack(player);
                }
                if (_burstLeft <= 0 && _burstTimer <= 0f)
                {
                    _cooldown = AttackCooldown * (float)GD.RandRange(0.75, 1.3);
                    SetState(State.Chase);
                }
                break;

            case State.Pain:
                if (_stateTime > 0.28f)
                    SetState(_alerted ? State.Chase : State.Idle);
                break;
        }

        Face(faceTarget, dt);
        Move(desired, dt);
        Animate(dt);
    }

    Vector3 ChaseVelocity(PlayerController player, float dist, float dt)
    {
        if (Kind == EnemyKind.Drone)
            return DroneVelocity(player, dist, dt);

        float speed = MoveSpeed;
        if (Kind == EnemyKind.Brute)
        {
            _chargeTimer -= dt;
            if (_canSee && dist > 5f && dist < 16f && _chargeTimer < -3f)
            {
                _chargeTimer = 1.4f;
                PlayVoice("brute_roar", -3f);
            }
            if (_chargeTimer > 0f)
                speed = ChargeSpeed;
        }
        else if (_canSee && dist < AttackRange * 0.35f)
        {
            // Grunts don't hug the player: strafe instead.
            _strafeTimer -= dt;
            if (_strafeTimer <= 0f)
            {
                _strafeTimer = (float)GD.RandRange(0.6, 1.4);
                Vector3 side = (player.GlobalPosition - GlobalPosition).Cross(Vector3.Up).Normalized();
                _strafe = side * (GD.Randf() < 0.5f ? -1f : 1f);
            }
            return _strafe * speed * 0.7f;
        }

        Vector3 target = _canSee ? player.GlobalPosition : _lastKnown;
        Vector3 next = target;
        if (_agent != null)
        {
            _repathTimer -= dt;
            if (_repathTimer <= 0f)
            {
                _repathTimer = 0.25f;
                _agent.TargetPosition = target;
            }
            if (!_agent.IsNavigationFinished())
            {
                Vector3 p = _agent.GetNextPathPosition();
                if (p.DistanceSquaredTo(GlobalPosition) > 0.01f)
                    next = p;
            }
        }
        Vector3 dir = next - GlobalPosition;
        dir.Y = 0f;
        if (dir.Length() < 0.5f && !_canSee)
            return Vector3.Zero; // reached last known position
        dir = dir.Normalized();
        dir += Separation() * 0.8f;
        // Unstick: if we keep pushing into something, sidestep for a moment.
        if (GetRealVelocity().Length() < 0.3f && _state == State.Chase)
            _stuckTimer += dt;
        else
            _stuckTimer = 0f;
        if (_stuckTimer > 0.8f)
        {
            _stuckTimer = -0.6f;
            _strafe = dir.Cross(Vector3.Up) * (GD.Randf() < 0.5f ? -1f : 1f);
        }
        if (_stuckTimer < 0f)
            dir = (dir + _strafe * 1.5f).Normalized();
        return dir.Normalized() * speed;
    }

    Vector3 DroneVelocity(PlayerController player, float dist, float dt)
    {
        Vector3 toPlayer = player.GlobalPosition - GlobalPosition;
        toPlayer.Y = 0f;
        Vector3 flat = toPlayer.Normalized();
        Vector3 side = flat.Cross(Vector3.Up) * _circleDir;
        _strafeTimer -= dt;
        if (_strafeTimer <= 0f)
        {
            _strafeTimer = (float)GD.RandRange(1.5, 3.5);
            if (GD.Randf() < 0.4f)
                _circleDir = -_circleDir;
        }
        float range = PreferredRange > 0f ? PreferredRange : 8f;
        Vector3 v = side * MoveSpeed * 0.7f;
        if (!_canSee || dist > range + 2f)
            v += flat * MoveSpeed;
        else if (dist < range - 2f)
            v -= flat * MoveSpeed;

        // Hold altitude above the floor below, respecting the ceiling.
        var space = GetWorld3D().DirectSpaceState;
        float targetY = player.GlobalPosition.Y + HoverHeight;
        var down = space.IntersectRay(PhysicsRayQueryParameters3D.Create(GlobalPosition, GlobalPosition + Vector3.Down * 20f, Layers.World));
        var up = space.IntersectRay(PhysicsRayQueryParameters3D.Create(GlobalPosition, GlobalPosition + Vector3.Up * 6f, Layers.World));
        if (down.Count > 0)
            targetY = Mathf.Max(targetY, ((Vector3)down["position"]).Y + 1.2f);
        if (up.Count > 0)
            targetY = Mathf.Min(targetY, ((Vector3)up["position"]).Y - 1.0f);
        v.Y = Mathf.Clamp((targetY - GlobalPosition.Y) * 2f, -MoveSpeed, MoveSpeed);
        v += Separation() * 2f;
        return v;
    }

    Vector3 Separation()
    {
        Vector3 push = Vector3.Zero;
        foreach (var e in All)
        {
            if (e == this || e.IsDead)
                continue;
            Vector3 d = GlobalPosition - e.GlobalPosition;
            d.Y = 0f;
            float l = d.Length();
            if (l < 1.4f && l > 0.001f)
                push += d / l * (1.4f - l);
        }
        return push;
    }

    void Face(Vector3 target, float dt)
    {
        Vector3 d = target - GlobalPosition;
        d.Y = 0f;
        if (d.LengthSquared() < 0.01f)
            return;
        float want = Mathf.Atan2(-d.X, -d.Z);
        float speed = _state is State.Windup or State.Attack ? TurnSpeed * 1.5f : TurnSpeed;
        Rotation = new Vector3(0, Mathf.LerpAngle(Rotation.Y, want, 1f - Mathf.Exp(-speed * dt)), 0);
    }

    void Move(Vector3 desired, float dt)
    {
        Vector3 v = Velocity;
        if (Kind == EnemyKind.Drone)
        {
            v = v.Lerp(desired, 1f - Mathf.Exp(-3f * dt));
            Velocity = v;
            MoveAndSlide();
            return;
        }
        float accel = IsOnFloor() ? 10f : 2f;
        Vector3 h = new Vector3(v.X, 0, v.Z).Lerp(new Vector3(desired.X, 0, desired.Z), 1f - Mathf.Exp(-accel * dt));
        v.X = h.X;
        v.Z = h.Z;
        v.Y = IsOnFloor() ? Mathf.Min(v.Y, 0f) : v.Y - 22f * dt;
        Velocity = v;
        bool wasOnFloor = IsOnFloor();
        if (!(wasOnFloor && Stairs.TryStepUp(this, dt, 0.5f) > 0f))
        {
            MoveAndSlide();
            if (wasOnFloor)
                Stairs.TryStepDown(this, 0.5f);
        }
    }

    // ------------------------------------------------------------------ attacks

    void PerformAttack(PlayerController player)
    {
        Vector3 muzzle = _muzzle?.GlobalPosition ?? EyePos;
        Vector3 chest = player.GlobalPosition + Vector3.Up * 1.1f;
        switch (Kind)
        {
            case EnemyKind.Grunt:
            {
                Vector3 dir = (chest - muzzle).Normalized();
                // Moving targets are harder to hit.
                float spread = Inaccuracy + player.Velocity.Length() * 0.35f;
                dir = Jitter(dir, spread);
                var q = PhysicsRayQueryParameters3D.Create(muzzle, muzzle + dir * 80f, Layers.World | Layers.Player);
                q.Exclude = new Godot.Collections.Array<Rid> { GetRid() };
                var hit = GetWorld3D().DirectSpaceState.IntersectRay(q);
                Vector3 end = muzzle + dir * 80f;
                if (hit.Count > 0)
                {
                    end = (Vector3)hit["position"];
                    if (hit["collider"].AsGodotObject() is PlayerController p)
                        p.TakeDamage(new DamageInfo(Damage, DamageKind.Bullet, end, dir, this));
                    else
                        Fx.Impact(this, end, (Vector3)hit["normal"], hit["collider"].AsGodotObject() as Node, GD.Randf() < 0.4f);
                }
                Fx.Tracer(this, muzzle, end);
                Fx.MuzzleFlashLight(this, muzzle, 2.5f);
                Audio.Play3D(this, "enemy_fire", muzzle, -2f);
                if (_armR != null)
                    _armR.Rotation += new Vector3(0.25f, 0, 0);
                break;
            }
            case EnemyKind.Drone:
            {
                if (ProjectileScene == null)
                    break;
                // Partial lead on the player's movement.
                float t = muzzle.DistanceTo(chest) / 18f;
                Vector3 aim = chest + player.Velocity * t * 0.5f;
                var proj = ProjectileScene.Instantiate<Projectile>();
                GetTree().CurrentScene.AddChild(proj);
                proj.Launch(muzzle, Jitter((aim - muzzle).Normalized(), Inaccuracy), this, Layers.World | Layers.Player);
                Audio.Play3D(this, "plasma_fire", muzzle, 0f);
                break;
            }
            case EnemyKind.Brute:
            {
                Audio.Play3D(this, "brute_attack", EyePos, 0f);
                Vector3 to = player.GlobalPosition - GlobalPosition;
                if (to.Length() < 3.2f && (-GlobalBasis.Z).AngleTo(new Vector3(to.X, 0, to.Z)) < Mathf.DegToRad(70f))
                {
                    Vector3 dir = new Vector3(to.X, 0, to.Z).Normalized();
                    player.TakeDamage(new DamageInfo(Damage, DamageKind.Melee, player.GlobalPosition, dir, this)
                    {
                        Knockback = dir * 9f + Vector3.Up * 4f,
                    });
                }
                // Slam: both fists come down in front.
                if (_armR != null)
                    _armR.Rotation = new Vector3(1.3f, 0, 0);
                if (_armL != null)
                    _armL.Rotation = new Vector3(1.3f, 0, 0);
                break;
            }
        }
    }

    static Vector3 Jitter(Vector3 dir, float degrees)
    {
        Basis b = Basis.LookingAt(dir, Mathf.Abs(dir.Y) > 0.99f ? Vector3.Right : Vector3.Up);
        float r = Mathf.Tan(Mathf.DegToRad(degrees)) * Mathf.Sqrt(GD.Randf());
        float a = GD.Randf() * Mathf.Tau;
        return (dir + b.X * Mathf.Cos(a) * r + b.Y * Mathf.Sin(a) * r).Normalized();
    }

    // ------------------------------------------------------------------ animation

    void Animate(float dt)
    {
        float speed = new Vector2(Velocity.X, Velocity.Z).Length();
        float amount = Mathf.Clamp(speed / Mathf.Max(MoveSpeed, 0.1f), 0f, 1.5f);
        float stride = Kind == EnemyKind.Brute ? 2.6f : 1.8f;
        float prev = _walkPhase;
        _walkPhase += speed / stride * Mathf.Tau * dt;
        float s = Mathf.Sin(_walkPhase);
        float k = 1f - Mathf.Exp(-12f * dt);

        if (Kind == EnemyKind.Drone)
        {
            float t = Time.GetTicksMsec() / 1000f;
            _rig.Position = new Vector3(0, Mathf.Sin(t * 2.3f + _walkPhase) * 0.08f, 0);
            Vector3 localVel = GlobalBasis.Inverse() * Velocity;
            _rig.Rotation = new Vector3(Mathf.Clamp(localVel.Z * 0.06f, -0.4f, 0.4f), 0, Mathf.Clamp(-localVel.X * 0.06f, -0.4f, 0.4f));
        }
        else
        {
            if (_legL != null)
                _legL.Rotation = new Vector3(Mathf.Lerp(_legL.Rotation.X, s * 0.65f * amount, k), 0, 0);
            if (_legR != null)
                _legR.Rotation = new Vector3(Mathf.Lerp(_legR.Rotation.X, -s * 0.65f * amount, k), 0, 0);
            if (_torso != null)
                _torso.Position = new Vector3(_torso.Position.X, Mathf.Lerp(_torso.Position.Y, TorsoRestY + Mathf.Abs(s) * 0.05f * amount, k), _torso.Position.Z);
            if (Kind == EnemyKind.Brute && amount > 0.3f && Mathf.FloorToInt(prev / Mathf.Pi) != Mathf.FloorToInt(_walkPhase / Mathf.Pi))
                Audio.Play3D(this, "brute_step", GlobalPosition, -4f, 0.1f, 6f, 40f);

            bool aiming = _state is State.Windup or State.Attack || (_canSee && Kind == EnemyKind.Grunt);
            if (_armL != null)
            {
                float armL = Kind == EnemyKind.Brute && _state == State.Windup ? -2.4f : -s * 0.5f * amount;
                if (Kind == EnemyKind.Grunt && aiming)
                    armL = 1.2f;
                _armL.Rotation = new Vector3(Mathf.Lerp(_armL.Rotation.X, armL, k), 0, 0);
            }
            if (_armR != null)
            {
                float armR = Kind == EnemyKind.Brute && _state == State.Windup ? -2.4f : s * 0.5f * amount;
                if (Kind == EnemyKind.Grunt)
                    armR = aiming ? 1.45f : 0.5f;
                _armR.Rotation = new Vector3(Mathf.Lerp(_armR.Rotation.X, armR, k * 0.8f), 0, 0);
            }
        }

        if (_state == State.Pain)
            _rig.Rotation = new Vector3(-0.25f * (1f - _stateTime / 0.28f), _rig.Rotation.Y, _rig.Rotation.Z);
        else if (Kind != EnemyKind.Drone)
            _rig.Rotation = _rig.Rotation.Lerp(Vector3.Zero, k);

        if (_eyeLight != null)
        {
            float target = _state == State.Windup ? _eyeBaseEnergy * (3f + 2f * Mathf.Sin(_stateTime * 40f)) : _eyeBaseEnergy;
            _eyeLight.LightEnergy = Mathf.Lerp(_eyeLight.LightEnergy, target, 1f - Mathf.Exp(-20f * dt));
        }
    }

    float? _torsoRestY;
    float TorsoRestY => _torsoRestY ??= _torso?.Position.Y ?? 0f;

    // ------------------------------------------------------------------ damage

    public void TakeDamage(DamageInfo info)
    {
        if (IsDead)
            return;
        _health -= info.Amount;
        _lastDamageDir = info.Direction;
        if (info.Knockback != Vector3.Zero)
            Velocity += info.Knockback * (Kind == EnemyKind.Brute ? 0.3f : 1f);
        foreach (var m in _meshes)
            m.MaterialOverlay = _flashMaterial;
        _flashTimer = 0.07f;
        if (info.Source is PlayerController p)
        {
            _lastKnown = p.GlobalPosition;
            Alert();
        }
        if (_health <= 0f)
        {
            Die(info);
            return;
        }
        if (_state != State.Windup && _state != State.Attack && GD.Randf() < PainChance * Mathf.Clamp(info.Amount / 20f, 0.3f, 1f))
        {
            SetState(State.Pain);
            PlayVoice(Kind == EnemyKind.Brute ? "brute_roar" : "enemy_hurt", -4f);
        }
        else if (GD.Randf() < 0.3f)
        {
            PlayVoice("enemy_hurt", -6f);
        }
    }

    void Die(DamageInfo info)
    {
        SetState(State.Dead);
        CollisionLayer = 0;
        CollisionMask = 0;
        RemoveFromGroup("enemies");
        Game.Instance.Stats.Kills++;
        Events.EmitEnemyKilled(this);
        Audio.Play3D(this, "enemy_death", EyePos, 2f);
        if (Kind == EnemyKind.Drone || info.Kind == DamageKind.Explosion || info.Amount > MaxHealth * 0.8f)
            Fx.Explosion(this, GlobalPosition + Vector3.Up * (Kind == EnemyKind.Drone ? 0f : 1f), 0.55f, false);
        else
            Fx.RobotHit(this, GlobalPosition + Vector3.Up * 1.2f, -info.Direction);
        _hum?.Stop();
        SpawnGibs(info);
        if (DropScene != null && GD.Randf() < DropChance)
        {
            var drop = DropScene.Instantiate<Node3D>();
            GetParent().AddChild(drop);
            drop.GlobalPosition = GlobalPosition + Vector3.Up * 0.3f;
            if (Kind == EnemyKind.Drone)
                drop.GlobalPosition = GroundBelow(GlobalPosition) + Vector3.Up * 0.3f;
        }
        QueueFree();
    }

    Vector3 GroundBelow(Vector3 from)
    {
        var hit = GetWorld3D().DirectSpaceState.IntersectRay(
            PhysicsRayQueryParameters3D.Create(from, from + Vector3.Down * 30f, Layers.World));
        return hit.Count > 0 ? (Vector3)hit["position"] : from;
    }

    void SpawnGibs(DamageInfo info)
    {
        var parent = GetParent();
        float force = info.Kind == DamageKind.Explosion ? 9f : 4.5f;
        foreach (var mesh in _meshes)
        {
            if (!mesh.Visible || mesh.Mesh == null)
                continue;
            var xf = mesh.GlobalTransform;
            Aabb box = mesh.Mesh.GetAabb();
            Vector3 size = (box.Size * xf.Basis.Scale).Clamp(Vector3.One * 0.08f, Vector3.One * 2f);
            var body = new RigidBody3D
            {
                CollisionLayer = Layers.Debris,
                CollisionMask = Layers.World | Layers.Debris,
                Mass = Mathf.Clamp(size.X * size.Y * size.Z * 60f, 0.5f, 30f),
                ContinuousCd = true,
            };
            var shape = new CollisionShape3D { Shape = new BoxShape3D { Size = size } };
            body.AddChild(shape);
            shape.Position = box.GetCenter() * xf.Basis.Scale;
            parent.AddChild(body);
            body.GlobalTransform = new Transform3D(xf.Basis.Orthonormalized(), xf.Origin);
            mesh.GetParent().RemoveChild(mesh);
            body.AddChild(mesh);
            mesh.Transform = new Transform3D(Basis.Identity.Scaled(xf.Basis.Scale), Vector3.Zero);
            mesh.MaterialOverlay = null;
            body.ResetPhysicsInterpolation();
            Vector3 random = new((float)GD.RandRange(-1, 1), (float)GD.RandRange(0.3, 1.2), (float)GD.RandRange(-1, 1));
            body.LinearVelocity = (info.Direction * force + random * 3.5f) * (Kind == EnemyKind.Brute ? 0.6f : 1f);
            body.AngularVelocity = new Vector3((float)GD.RandRange(-8, 8), (float)GD.RandRange(-8, 8), (float)GD.RandRange(-8, 8));
            var tween = body.CreateTween();
            tween.TweenInterval(7f + GD.Randf() * 3f);
            tween.TweenProperty(mesh, "scale", Vector3.One * 0.01f, 0.6f);
            tween.TweenCallback(Callable.From(body.QueueFree));
        }
        foreach (var light in _rig.FindChildren("*", "Light3D", true, false))
            ((Node)light).QueueFree();
    }
}
