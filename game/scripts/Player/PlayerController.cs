using Godot;

namespace Brushfire;

/// <summary>
/// Quake-flavoured first-person controller.
///  * Ground/air acceleration + friction model (strafe-jumping and bunny-hopping work).
///  * Coyote time and jump buffering, crouch-jumping, headroom-checked uncrouch.
///  * Stair stepping up/down with camera smoothing (no bumpy capsule climbing).
///  * Physics runs at a fixed tick with physics interpolation; the camera is updated every
///    rendered frame from the interpolated body transform, and mouse look is applied
///    immediately, so aiming stays crisp at any frame rate.
///  * Head bob, strafe tilt, landing dip, sprint FOV, recoil and trauma-based screen shake.
/// </summary>
public partial class PlayerController : CharacterBody3D, IDamageable
{
    public static PlayerController Instance { get; private set; }

    [ExportGroup("Movement")]
    [Export] public float WalkSpeed = 7.5f;
    [Export] public float SprintSpeed = 10.5f;
    [Export] public float CrouchSpeed = 3.6f;
    [Export] public float GroundAccel = 12f;
    [Export] public float Friction = 6.5f;
    [Export] public float StopSpeed = 2.5f;
    [Export] public float AirAccel = 14f;
    [Export] public float AirSpeedCap = 1.1f;
    [Export] public float Gravity = 22f;
    [Export] public float JumpVelocity = 7.4f;
    [Export] public float MaxStepHeight = 0.45f;
    [Export] public float CoyoteTime = 0.12f;
    [Export] public float JumpBufferTime = 0.14f;
    [Export] public float MaxHorizontalSpeed = 24f;

    [ExportGroup("Body")]
    [Export] public float StandHeight = 1.8f;
    [Export] public float CrouchHeight = 1.05f;
    [Export] public float StandEye = 1.62f;
    [Export] public float CrouchEye = 0.92f;

    [ExportGroup("Camera")]
    [Export] public float BobAmount = 0.05f;
    [Export] public float StrideLength = 2.3f;   // metres per full bob cycle (two footsteps)
    [Export] public float StrafeTiltDegrees = 1.4f;
    [Export] public float SprintFovBoost = 7f;

    [ExportGroup("Stats")]
    [Export] public int MaxHealth = 100;
    [Export] public int MaxOverheal = 200;
    [Export] public int MaxArmor = 200;

    public float Health { get; private set; }
    public float Armor { get; private set; }
    public bool IsDead { get; private set; }
    public Camera3D Camera => _camera;
    public WeaponManager Weapons => _weapons;
    public Hud Hud => _hud;
    public float Yaw => _yaw;
    public float Pitch => _pitch;
    /// <summary>0..1 how much the head is currently bobbing; weapons sway with it.</summary>
    public float BobWeight => _bobWeight;
    public float BobPhase => _bobPhase;
    public bool Sprinting => _sprinting;
    public Vector3 LookDirection => -Basis.FromEuler(new Vector3(_pitch, _yaw, 0)).Z;
    /// <summary>Eye position at the current physics tick (use for hitscan origin).</summary>
    public Vector3 EyePosition => GlobalPosition + Vector3.Up * _eyeHeight;

    CollisionShape3D _shapeNode;
    CylinderShape3D _shape;
    Node3D _rig;
    Camera3D _camera;
    WeaponManager _weapons;
    Hud _hud;
    SpotLight3D _flashlight;
    FastNoiseLite _shakeNoise;

    float _yaw, _pitch;
    float _eyeHeight;
    bool _crouched, _sprinting;
    float _coyote, _jumpBuffer;
    bool _wasOnFloor;
    bool _snappedStairsLastFrame;
    float _prevVelY;
    float _bobPhase, _bobWeight;
    float _stepSmooth;
    float _landOffset, _landVelocity;
    float _tilt;
    float _fov;
    float _trauma;
    Vector2 _recoil;          // x = pitch (rad), y = yaw (rad)
    float _shakeTime;
    float _deathTimer;
    float _hurtSoundCooldown;

    public override void _EnterTree() => Instance = this;

    public override void _ExitTree()
    {
        if (Instance == this)
            Instance = null;
    }

    public override void _Ready()
    {
        _shapeNode = GetNode<CollisionShape3D>("CollisionShape3D");
        _shape = (CylinderShape3D)_shapeNode.Shape.Duplicate();
        _shapeNode.Shape = _shape;
        _rig = GetNode<Node3D>("CameraRig");
        _camera = GetNode<Camera3D>("CameraRig/Camera3D");
        _weapons = GetNode<WeaponManager>("CameraRig/Camera3D/WeaponManager");
        _flashlight = GetNode<SpotLight3D>("CameraRig/Camera3D/Flashlight");
        _hud = GetNode<Hud>("Hud");

        _rig.TopLevel = true;
        _rig.PhysicsInterpolationMode = PhysicsInterpolationModeEnum.Off;
        _shakeNoise = new FastNoiseLite { NoiseType = FastNoiseLite.NoiseTypeEnum.Perlin, Frequency = 18f };

        Health = MaxHealth;
        Armor = 0;
        _eyeHeight = StandEye;
        _fov = Game.Instance.Settings.Fov;
        _yaw = GlobalRotation.Y;
        GlobalRotation = Vector3.Zero; // the body never rotates; yaw lives in the camera rig
        SetStanding(true);

        FloorMaxAngle = Mathf.DegToRad(46f);
        FloorSnapLength = 0.12f;
        FloorConstantSpeed = true;
        FloorBlockOnWall = true;
        MaxSlides = 6;
        ResetPhysicsInterpolation();
        UpdateCamera(0);
    }

    // ------------------------------------------------------------------ input

    public override void _UnhandledInput(InputEvent e)
    {
        if (IsDead)
        {
            if (_deathTimer > 1.2f && (e.IsActionPressed("fire") || e.IsActionPressed("jump")))
                Game.Instance.RestartLevel();
            return;
        }
        if (e is InputEventMouseMotion motion && InputEnabled)
        {
            var s = Game.Instance.Settings;
            float scale = Mathf.DegToRad(0.1f) * s.MouseSensitivity;
            // Motion.ScreenRelative ignores the canvas stretch so sensitivity is resolution independent.
            Vector2 rel = motion.ScreenRelative;
            _yaw -= rel.X * scale;
            _pitch -= rel.Y * scale * (s.InvertY ? -1 : 1);
            _pitch = Mathf.Clamp(_pitch, Mathf.DegToRad(-89f), Mathf.DegToRad(89f));
        }
        else if (e.IsActionPressed("flashlight"))
        {
            _flashlight.Visible = !_flashlight.Visible;
            Audio.Play2D(this, "ui_click", -8f);
        }
    }

    void GamepadLook(float dt)
    {
        Vector2 look = Input.GetVector("look_left", "look_right", "look_up", "look_down");
        if (look == Vector2.Zero)
            return;
        var s = Game.Instance.Settings;
        // Squared response curve: precise small movements, fast turns at full deflection.
        look = look.Normalized() * look.LengthSquared();
        _yaw -= look.X * Mathf.DegToRad(200f) * s.GamepadSensitivity * dt;
        _pitch -= look.Y * Mathf.DegToRad(140f) * s.GamepadSensitivity * dt * (s.InvertY ? -1 : 1);
        _pitch = Mathf.Clamp(_pitch, Mathf.DegToRad(-89f), Mathf.DegToRad(89f));
    }

    // ------------------------------------------------------------------ physics

    public override void _PhysicsProcess(double delta)
    {
        float dt = (float)delta;
        _hurtSoundCooldown -= dt;
        if (IsDead)
        {
            DeadPhysics(dt);
            return;
        }

        UpdateCrouch(dt);

        Vector2 input = Input.GetVector("move_left", "move_right", "move_forward", "move_back");
        var yawBasis = new Basis(Vector3.Up, _yaw);
        Vector3 wish = yawBasis * new Vector3(input.X, 0, input.Y);
        float wishAmount = Mathf.Min(wish.Length(), 1f);
        Vector3 wishDir = wishAmount > 0.001f ? wish.Normalized() : Vector3.Zero;

        bool onFloor = IsOnFloor() || _snappedStairsLastFrame;
        _sprinting = Input.IsActionPressed("sprint") && !_crouched && input.Y < -0.3f && onFloor
                     || (_sprinting && !onFloor && Input.IsActionPressed("sprint"));
        float targetSpeed = _crouched ? CrouchSpeed : (_sprinting ? SprintSpeed : WalkSpeed);
        float wishSpeed = targetSpeed * wishAmount;

        _coyote = onFloor ? CoyoteTime : _coyote - dt;
        // Pressing jump buffers it; holding it re-jumps the moment you land (auto bunny hop).
        bool jumpHeld = Input.IsActionPressed("jump") && onFloor;
        _jumpBuffer = Input.IsActionJustPressed("jump") || jumpHeld ? JumpBufferTime : _jumpBuffer - dt;

        Vector3 vel = Velocity;
        if (onFloor && vel.Y <= 0.01f)
        {
            // Holding a buffered jump on landing skips friction for that tick: bunny hopping.
            if (_jumpBuffer <= 0f)
                ApplyFriction(ref vel, dt);
            Accelerate(ref vel, wishDir, wishSpeed, GroundAccel, dt);
            vel.Y = Mathf.Min(vel.Y, 0f);
        }
        else
        {
            AirAccelerate(ref vel, wishDir, wishSpeed, dt);
            vel.Y -= Gravity * dt;
        }

        if (_jumpBuffer > 0f && _coyote > 0f)
        {
            vel.Y = JumpVelocity;
            _jumpBuffer = 0f;
            _coyote = 0f;
            _snappedStairsLastFrame = false;
            Audio.Play2D(this, "player_jump", -10f);
        }

        var horizontal = new Vector2(vel.X, vel.Z);
        if (horizontal.Length() > MaxHorizontalSpeed)
        {
            horizontal = horizontal.Normalized() * MaxHorizontalSpeed;
            vel.X = horizontal.X;
            vel.Z = horizontal.Y;
        }
        Velocity = vel;

        bool wasOnFloor = IsOnFloor();
        if (!SnapUpStairs(dt))
        {
            MoveAndSlide();
            SnapDownStairs(wasOnFloor);
        }

        bool nowOnFloor = IsOnFloor() || _snappedStairsLastFrame;
        if (nowOnFloor && !_wasOnFloor)
            OnLanded(-_prevVelY);
        _wasOnFloor = nowOnFloor;
        _prevVelY = Velocity.Y;
    }

    void ApplyFriction(ref Vector3 vel, float dt)
    {
        var h = new Vector3(vel.X, 0, vel.Z);
        float speed = h.Length();
        if (speed < 0.01f)
        {
            vel.X = vel.Z = 0f;
            return;
        }
        float control = Mathf.Max(speed, StopSpeed);
        float newSpeed = Mathf.Max(speed - control * Friction * dt, 0f);
        h *= newSpeed / speed;
        vel.X = h.X;
        vel.Z = h.Z;
    }

    static void Accelerate(ref Vector3 vel, Vector3 wishDir, float wishSpeed, float accel, float dt)
    {
        float current = vel.Dot(wishDir);
        float add = wishSpeed - current;
        if (add <= 0f)
            return;
        float step = Mathf.Min(accel * wishSpeed * dt, add);
        vel += wishDir * step;
    }

    void AirAccelerate(ref Vector3 vel, Vector3 wishDir, float wishSpeed, float dt)
    {
        // Quake air physics: the speed cap only applies along the wish direction, so turning while
        // strafing adds speed. The acceleration itself scales with the uncapped wish speed.
        float capped = Mathf.Min(wishSpeed, AirSpeedCap);
        float current = vel.Dot(wishDir);
        float add = capped - current;
        if (add <= 0f)
            return;
        float step = Mathf.Min(AirAccel * wishSpeed * dt, add);
        vel += wishDir * step;
    }

    // -------------------------------------------------------------- stairs

    bool TestMotion(Transform3D from, Vector3 motion, PhysicsTestMotionResult3D result)
    {
        var p = new PhysicsTestMotionParameters3D { From = from, Motion = motion, Margin = 0.001f };
        return PhysicsServer3D.BodyTestMotion(GetRid(), p, result);
    }

    bool SnapUpStairs(float dt)
    {
        if (!(IsOnFloor() || _snappedStairsLastFrame))
            return false;
        float height = Stairs.TryStepUp(this, dt, MaxStepHeight);
        if (height <= 0f)
            return false;
        _stepSmooth -= height; // the camera eases up the step instead of popping
        _snappedStairsLastFrame = true;
        return true;
    }

    void SnapDownStairs(bool wasOnFloor)
    {
        bool snapped = false;
        if (wasOnFloor || _snappedStairsLastFrame)
        {
            float dy = Stairs.TryStepDown(this, MaxStepHeight);
            if (dy < 0f)
            {
                _stepSmooth -= dy;
                snapped = true;
            }
        }
        _snappedStairsLastFrame = snapped;
    }

    // -------------------------------------------------------------- crouch

    void SetStanding(bool standing)
    {
        float h = standing ? StandHeight : CrouchHeight;
        _shape.Height = h;
        _shapeNode.Position = new Vector3(0, h * 0.5f, 0);
    }

    bool HasHeadroom()
    {
        var r = new PhysicsTestMotionResult3D();
        return !TestMotion(GlobalTransform, Vector3.Up * (StandHeight - CrouchHeight), r);
    }

    void UpdateCrouch(float dt)
    {
        bool want = Input.IsActionPressed("crouch");
        float diff = StandHeight - CrouchHeight;
        if (want && !_crouched)
        {
            _crouched = true;
            SetStanding(false);
            if (!IsOnFloor())
            {
                // Crouch-jump: tuck the legs up instead of dropping the head.
                var r = new PhysicsTestMotionResult3D();
                Vector3 lift = TestMotion(GlobalTransform, Vector3.Up * diff, r) ? r.GetTravel() : Vector3.Up * diff;
                GlobalPosition += lift;
                _eyeHeight -= lift.Y;
            }
        }
        else if (!want && _crouched)
        {
            if (IsOnFloor())
            {
                if (HasHeadroom())
                {
                    _crouched = false;
                    SetStanding(true);
                }
            }
            else
            {
                // Mid-air: extend the legs downward if there is room below.
                var r = new PhysicsTestMotionResult3D();
                if (!TestMotion(GlobalTransform, Vector3.Down * diff, r))
                {
                    GlobalPosition += Vector3.Down * diff;
                    _eyeHeight += diff;
                    _crouched = false;
                    SetStanding(true);
                }
                else if (HasHeadroom())
                {
                    _crouched = false;
                    SetStanding(true);
                }
            }
        }
        float targetEye = _crouched ? CrouchEye : StandEye;
        _eyeHeight = Mathf.Lerp(_eyeHeight, targetEye, 1f - Mathf.Exp(-14f * dt));
    }

    // -------------------------------------------------------------- camera

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        if (!IsDead)
            GamepadLook(dt);
        UpdateCamera(dt);
    }

    void UpdateCamera(float dt)
    {
        var settings = Game.Instance.Settings;
        Vector3 hVel = new(Velocity.X, 0, Velocity.Z);
        float hSpeed = hVel.Length();
        bool grounded = IsOnFloor() || _snappedStairsLastFrame;

        // Head bob, weighted by speed so it fades in and out smoothly.
        float targetWeight = grounded && !IsDead ? Mathf.Clamp(hSpeed / WalkSpeed, 0f, 1.3f) : 0f;
        _bobWeight = Mathf.Lerp(_bobWeight, targetWeight, 1f - Mathf.Exp(-10f * dt));
        float prevPhase = _bobPhase;
        if (grounded)
            _bobPhase += hSpeed / StrideLength * Mathf.Tau * dt;
        // A footstep each time the bob reaches its lowest point (twice per cycle).
        if (grounded && hSpeed > 1.2f
            && Mathf.FloorToInt(prevPhase / Mathf.Pi + 0.5f) != Mathf.FloorToInt(_bobPhase / Mathf.Pi + 0.5f))
            Footstep(hSpeed);
        float bobScale = settings.HeadBob ? BobAmount * _bobWeight : 0f;
        float bobY = -Mathf.Abs(Mathf.Sin(_bobPhase)) * bobScale + bobScale * 0.5f;
        float bobX = Mathf.Sin(_bobPhase * 0.5f) * bobScale * 0.6f;

        // Landing dip spring.
        Springs.Step(ref _landOffset, ref _landVelocity, 0f, 120f, 14f, dt);
        // Stair smoothing.
        _stepSmooth = Mathf.Lerp(_stepSmooth, 0f, 1f - Mathf.Exp(-16f * dt));

        // Strafe tilt.
        var right = new Basis(Vector3.Up, _yaw).X;
        float side = IsDead ? 0f : hVel.Dot(right) / SprintSpeed;
        _tilt = Mathf.Lerp(_tilt, -side * Mathf.DegToRad(StrafeTiltDegrees), 1f - Mathf.Exp(-8f * dt));

        // Recoil recovers towards zero.
        _recoil = _recoil.Lerp(Vector2.Zero, 1f - Mathf.Exp(-9f * dt));

        // Trauma shake.
        _trauma = Mathf.Max(_trauma - dt * 1.4f, 0f);
        _shakeTime += dt;
        float shake = _trauma * _trauma;
        float shakePitch = _shakeNoise.GetNoise2D(_shakeTime * 60f, 0f) * shake * 0.06f;
        float shakeYaw = _shakeNoise.GetNoise2D(0f, _shakeTime * 60f) * shake * 0.06f;
        float shakeRoll = _shakeNoise.GetNoise2D(_shakeTime * 60f, 100f) * shake * 0.08f;

        float deathRoll = 0f;
        if (IsDead)
            deathRoll = Mathf.DegToRad(35f) * Mathf.Clamp(_deathTimer * 1.5f, 0f, 1f);

        Transform3D body = GetGlobalTransformInterpolated();
        var basis = Basis.FromEuler(new Vector3(_pitch + _recoil.X + shakePitch, _yaw + _recoil.Y + shakeYaw,
            _tilt + shakeRoll + deathRoll));
        Vector3 eye = body.Origin + Vector3.Up * (_eyeHeight + _stepSmooth + _landOffset + bobY);
        eye += basis.X * bobX;
        _rig.GlobalTransform = new Transform3D(basis, eye);

        float targetFov = settings.Fov + (_sprinting && hSpeed > WalkSpeed * 0.9f ? SprintFovBoost : 0f);
        _fov = Mathf.Lerp(_fov, targetFov, 1f - Mathf.Exp(-8f * dt));
        _camera.Fov = HorizontalToVerticalFov(_fov);
    }

    /// <summary>The FOV option is horizontal at 16:9 (what players expect); Camera3D wants vertical.</summary>
    static float HorizontalToVerticalFov(float horizontalDegrees)
    {
        float h = Mathf.DegToRad(horizontalDegrees);
        return Mathf.RadToDeg(2f * Mathf.Atan(Mathf.Tan(h * 0.5f) * 9f / 16f));
    }

    void Footstep(float speed)
    {
        float vol = Mathf.Lerp(-16f, -7f, Mathf.Clamp(speed / SprintSpeed, 0f, 1f));
        if (_crouched)
            vol -= 8f;
        Audio.Play2D(this, "footstep", vol, 0.1f);
    }

    void OnLanded(float fallSpeed)
    {
        if (fallSpeed < 2f)
            return;
        _landVelocity -= Mathf.Min(fallSpeed * 0.16f, 3.2f);
        float vol = Mathf.Lerp(-16f, -2f, Mathf.Clamp((fallSpeed - 2f) / 12f, 0f, 1f));
        Audio.Play2D(this, "player_land", vol, 0.08f);
        if (fallSpeed > 9f)
            AddTrauma(Mathf.Clamp((fallSpeed - 9f) / 10f, 0.1f, 0.5f));
    }

    // -------------------------------------------------------------- feedback API

    /// <summary>Set the view direction (degrees). Used by spawn points and the autotest runner.</summary>
    public void SetLook(float yawDegrees, float pitchDegrees)
    {
        _yaw = Mathf.DegToRad(yawDegrees);
        _pitch = Mathf.DegToRad(pitchDegrees);
    }

    /// <summary>True when gameplay input should be read (mouse captured, or a scripted test).</summary>
    public static bool InputEnabled => Input.MouseMode == Input.MouseModeEnum.Captured || AutoTest.Active;

    public void AddTrauma(float amount) => _trauma = Mathf.Clamp(_trauma + amount, 0f, 1f);

    /// <summary>Kick the view: pitch/yaw in degrees.</summary>
    public void AddRecoil(float pitchDegrees, float yawDegrees)
    {
        _recoil += new Vector2(Mathf.DegToRad(pitchDegrees), Mathf.DegToRad(yawDegrees));
    }

    public void AddVelocity(Vector3 impulse)
    {
        Velocity += impulse;
        if (impulse.Y > 0.5f)
            _snappedStairsLastFrame = false;
    }

    // -------------------------------------------------------------- health

    public void TakeDamage(DamageInfo info)
    {
        if (IsDead || info.Amount <= 0f)
            return;
        float amount = AutoTest.God ? 0f : info.Amount;
        if (Armor > 0f)
        {
            float absorbed = Mathf.Min(Armor, amount * 0.6f);
            Armor -= absorbed;
            amount -= absorbed;
        }
        Health -= amount;
        if (info.Knockback != Vector3.Zero)
            AddVelocity(info.Knockback);
        AddTrauma(Mathf.Clamp(info.Amount / 60f, 0.12f, 0.6f));
        _hud.OnDamaged(info, this);
        if (Health <= 0f)
        {
            Die();
            return;
        }
        if (_hurtSoundCooldown <= 0f)
        {
            Audio.Play2D(this, "player_hurt", -3f);
            _hurtSoundCooldown = 0.35f;
        }
    }

    public bool GiveHealth(int amount, bool overheal = false)
    {
        int cap = overheal ? MaxOverheal : MaxHealth;
        if (Health >= cap)
            return false;
        Health = Mathf.Min(Health + amount, cap);
        return true;
    }

    public bool GiveArmor(int amount)
    {
        if (Armor >= MaxArmor)
            return false;
        Armor = Mathf.Min(Armor + amount, MaxArmor);
        return true;
    }

    void Die()
    {
        Health = 0f;
        IsDead = true;
        _deathTimer = 0f;
        _weapons.Visible = false;
        _flashlight.Visible = false;
        Audio.Play2D(this, "player_death", 0f, 0f);
        _hud.ShowCenterMessage("YOU DIED", "Press FIRE to restart");
        SetStanding(false);
    }

    void DeadPhysics(float dt)
    {
        _deathTimer += dt;
        _eyeHeight = Mathf.Lerp(_eyeHeight, 0.25f, 1f - Mathf.Exp(-5f * dt));
        Vector3 vel = Velocity;
        vel.Y -= Gravity * dt;
        if (IsOnFloor())
            ApplyFriction(ref vel, dt);
        Velocity = vel;
        MoveAndSlide();
    }
}
