using Godot;

namespace Brushfire;

public enum TriggerKind { Exit, Hurt, JumpPad, Secret, Message }

/// <summary>
/// Generic trigger volume. Place as an Area3D with a collision shape, or as a TrenchBroom
/// brush entity (trigger_exit, trigger_hurt, trigger_push, trigger_secret, trigger_message).
/// </summary>
public partial class Trigger : Area3D
{
    [Export] public TriggerKind Kind = TriggerKind.Exit;
    [Export] public float DamagePerSecond = 40f;
    [Export] public Vector3 PushVelocity = new(0, 14f, 0);
    [Export(PropertyHint.MultilineText)] public string Message = "";
    /// <summary>Key/values from a TrenchBroom trigger_* brush entity (filled in by func_godot).</summary>
    [Export] public Godot.Collections.Dictionary func_godot_properties = new();

    PlayerController _inside;
    float _hurtTick;
    bool _used;

    public override void _Ready()
    {
        if (func_godot_properties.Count > 0)
            ApplyMapProperties(func_godot_properties);
        CollisionLayer = 0;
        CollisionMask = Layers.Player | Layers.Enemy;
        Monitorable = false;
        BodyEntered += OnEntered;
        BodyExited += b => { if (b == _inside) _inside = null; };
        if (Kind == TriggerKind.Secret)
            AddToGroup("secrets");
        // Trigger brushes are invisible in game.
        foreach (var n in FindChildren("*", "MeshInstance3D", true, false))
            ((Node3D)n).Visible = false;
    }

    void OnEntered(Node3D body)
    {
        if (Kind == TriggerKind.Hurt && body is Enemy enemy && !enemy.IsDead)
        {
            enemy.TakeDamage(new DamageInfo(1000f, DamageKind.Hazard, enemy.GlobalPosition, Vector3.Up));
            return;
        }
        if (body is not PlayerController player || player.IsDead)
            return;
        switch (Kind)
        {
            case TriggerKind.Exit:
                if (!_used)
                {
                    _used = true;
                    LevelRoot.Current?.CompleteLevel();
                }
                break;
            case TriggerKind.Hurt:
                _inside = player;
                _hurtTick = 0f;
                break;
            case TriggerKind.JumpPad:
                player.Velocity = new Vector3(player.Velocity.X * 0.3f, 0, player.Velocity.Z * 0.3f);
                player.AddVelocity(PushVelocity);
                Audio.Play2D(this, "jump_pad", -3f);
                break;
            case TriggerKind.Secret:
                if (!_used)
                {
                    _used = true;
                    Game.Instance.Stats.Secrets++;
                    Audio.Play2D(this, "secret_found", -2f, 0f);
                    player.Hud.ShowCenterMessage("A SECRET AREA!", "", 2.5f);
                }
                break;
            case TriggerKind.Message:
                if (!_used)
                {
                    _used = true;
                    player.Hud.ShowCenterMessage(Message, "", 3.5f);
                }
                break;
        }
    }

    public override void _PhysicsProcess(double delta)
    {
        if (Kind != TriggerKind.Hurt || _inside == null)
            return;
        _hurtTick -= (float)delta;
        if (_hurtTick <= 0f)
        {
            _hurtTick = 0.25f;
            _inside.TakeDamage(new DamageInfo(DamagePerSecond * 0.25f, DamageKind.Hazard, _inside.GlobalPosition, Vector3.Up));
            Audio.Play2D(this, "lava_burn", -4f);
        }
    }

    void ApplyMapProperties(Godot.Collections.Dictionary props)
    {
        if (props.TryGetValue("classname", out var cn))
        {
            Kind = cn.AsString() switch
            {
                "trigger_hurt" => TriggerKind.Hurt,
                "trigger_push" => TriggerKind.JumpPad,
                "trigger_secret" => TriggerKind.Secret,
                "trigger_message" => TriggerKind.Message,
                _ => TriggerKind.Exit,
            };
        }
        if (props.TryGetValue("dmg", out var d))
            DamagePerSecond = (float)d.AsDouble();
        if (props.TryGetValue("message", out var m))
            Message = m.AsString();
        if (props.TryGetValue("speed", out var s))
        {
            float speed = (float)s.AsDouble() / 32f;
            PushVelocity = new Vector3(0, speed, 0);
            // Optional push direction (Quake yaw: 0 = +X quake = +Z Godot).
            if (props.TryGetValue("angle", out var ang) && ang.AsDouble() >= 0)
            {
                float a = Mathf.DegToRad((float)ang.AsDouble());
                PushVelocity += new Vector3(Mathf.Sin(a), 0, Mathf.Cos(a)) * speed * 0.3f;
            }
        }
    }
}
