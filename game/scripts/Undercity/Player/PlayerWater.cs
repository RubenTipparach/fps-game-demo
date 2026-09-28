// The runner in water: how deep they are (told to the core, which runs breath, stamina and the
// belt's refusal), and which rule moves the body on each tick: a mantle under way, a ladder held,
// the swim motor in deep water, or Brushfire's ground and air rules, slowed while wading
// (openspec/changes/water-and-swimming, design sections 2 and 4).
//
// It lives in the Godot layer because it turns the body's place into a core call and hands the
// body to a motor; each motor has the one job of moving it (SwimMotor, LadderMotor, MantleMotor).

#nullable enable
using System.Collections.Generic;
using System.Linq;
using Godot;
using Undercity.Core.Vitals;

namespace Undercity.Client;

/// <summary>The player's water state and the movement hand-off (a child of the player named "Water").</summary>
public partial class PlayerWater : Node, IWired, Brushfire.IMovementOverride
{
    private Services? _s;
    private Brushfire.PlayerController? _body;
    private LevelWater? _water;
    private SwimMotor? _swim;
    private LadderMotor? _ladder;
    private MantleMotor? _mantle;
    private float _radius;
    private float _prevFeetY = float.NaN;
    private double _strokeS;

    /// <summary>How much of the runner is in water, as last told to the core.</summary>
    public WaterContact Contact { get; private set; }

    /// <summary>True while the swim motor moves the body.</summary>
    public bool Swimming { get; private set; }

    /// <summary>True while holding a ladder.</summary>
    public bool Climbing => _ladder?.Active == true;

    /// <summary>True while pulling up onto a ledge.</summary>
    public bool Mantling => _mantle?.Active == true;

    /// <inheritdoc/>
    public float GroundSpeedFactor => Contact == WaterContact.Wading && _water is not null ? (float)_water.Table.WadeSpeedFactor : 1f;

    /// <inheritdoc/>
    public bool SprintAllowed => Contact < WaterContact.Wading;

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _s = services;
        _body = GetParent<Brushfire.PlayerController>();
        _water = services.Level.Water;
        var t = _water.Table;
        _swim = new SwimMotor(t);
        _ladder = new LadderMotor(t);
        _mantle = new MantleMotor(t);
        _radius = _body.GetNode<CollisionShape3D>("CollisionShape3D").Shape is CylinderShape3D c ? c.Radius : 0.4f;
        _body.Movement = this;
    }

    private IEnumerable<Ladder> Ladders() => GetTree().GetNodesInGroup("ladders").OfType<Ladder>();

    /// <summary>True when the runner stands on the floor at <paramref name="l"/>'s top, free to climb down it.</summary>
    public bool CanClimbDown(Ladder l) =>
        _body is not null && _ladder is not null && !_ladder.Active && _body.IsOnFloor()
        && _body.GlobalPosition.DistanceTo(l.Landing) < l.StepInM + 1.5f;

    /// <summary>Takes hold of <paramref name="l"/> from its top (its "Climb down" prompt).</summary>
    public void ClimbDown(Ladder l)
    {
        if (_body is not null && CanClimbDown(l))
        {
            _ladder!.GrabFromTop(_body, l, _radius);
        }
    }

    /// <inheritdoc/>
    public bool Drive(Brushfire.PlayerController body, float dt)
    {
        if (_water is null || _s is null || _swim is null || _ladder is null || _mantle is null)
        {
            return false;
        }
        var input = BodyInput.Read();
        var feet = body.GlobalPosition;
        var eyeY = body.EyePosition.Y;
        var surface = _water.SurfaceAt(feet);
        var entering = surface is { } s0 && _prevFeetY >= s0 && feet.Y < s0;
        _prevFeetY = feet.Y;
        SetContact(_water.Contact(feet, eyeY));

        Swimming = false;
        if (_mantle.Active)
        {
            _mantle.Step(body, dt);
            return true;
        }
        if ((_ladder.Active || _ladder.TryGrab(body, Ladders(), input, _radius)) && _ladder.Step(body, input, _radius, surface, dt))
        {
            return true;
        }
        if (surface is not { } s || !(Contact >= WaterContact.Swimming || InDeepWater(body, s)))
        {
            return false;
        }
        if (entering)
        {
            var v = body.Velocity;
            var hard = Mathf.Clamp(-v.Y / 12f, 0f, 1f);
            Brushfire.Audio.Play2D(body, "water_splash", Mathf.Lerp(-14f, -2f, hard), 0.1f);
            ParticleBurst.Splash(body, new Vector3(feet.X, s, feet.Z), hard);
            body.Velocity = new Vector3(v.X, _swim.Entry(v.Y), v.Z);
        }
        if (input.JumpPressed && Contact < WaterContact.Submerged && _mantle.TryStart(body, s, _radius))
        {
            _mantle.Step(body, dt);
            return true;
        }
        var tired = (float)_s.State.Stamina.SpeedFactor;
        _swim.Step(body, s, Contact == WaterContact.Submerged, input, tired, dt);
        Swimming = true;
        Strokes(body, input, dt);
        return true;
    }

    /// <summary>
    /// True when the feet are under the surface in water too deep to stand in: the body is off
    /// the floor and there is no floor within swim_depth_m of the surface below it.
    /// </summary>
    private bool InDeepWater(Brushfire.PlayerController body, float surfaceY)
    {
        var feet = body.GlobalPosition;
        if (feet.Y >= surfaceY || body.IsOnFloor())
        {
            return false;
        }
        var bottom = surfaceY - (float)_water!.Table.SwimDepthM - 0.1f;
        var query = PhysicsRayQueryParameters3D.Create(feet + Vector3.Up * 0.05f, new Vector3(feet.X, bottom, feet.Z), Brushfire.Layers.World);
        query.Exclude = new Godot.Collections.Array<Rid> { body.GetRid() };
        return body.GetWorld3D().DirectSpaceState.IntersectRay(query).Count == 0;
    }

    private void SetContact(WaterContact contact)
    {
        if (contact == Contact)
        {
            return;
        }
        if (Contact == WaterContact.Submerged && contact < WaterContact.Submerged
            && _s!.State.Breath.Value < _s.State.Breath.Max * _water!.Table.GaspBelowBreathFraction)
        {
            Brushfire.Audio.Play2D(_body!, "breath_gasp", -6f, 0.08f);
        }
        Contact = contact;
        _s!.State.SetWater(contact);
    }

    /// <summary>A stroke's sound while moving through the water: slower and heavier when tired.</summary>
    private void Strokes(Brushfire.PlayerController body, BodyInput input, float dt)
    {
        if (input.Move.LengthSquared() < 0.01f)
        {
            _strokeS = 0;
            return;
        }
        var t = _water!.Table;
        var low = _s!.State.Stamina.Value < _s.State.Stamina.Max * t.StaminaLowFraction;
        _strokeS -= dt;
        if (_strokeS > 0)
        {
            return;
        }
        _strokeS = low ? t.TiredStrokeS : t.StrokeS;
        Brushfire.Audio.Play2D(body, low ? "swim_stroke_tired" : "swim_stroke", Contact == WaterContact.Submerged ? -20f : -12f, 0.12f);
    }
}
