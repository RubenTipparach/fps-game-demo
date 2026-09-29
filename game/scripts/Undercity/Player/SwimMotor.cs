// The swim motor: how a body moves in deep water (openspec/changes/archive/2026-09-29-water-and-swimming, design
// section 2). Quake's rule: you swim where you look. At the surface a pitch dead zone keeps a
// swimmer from diving by looking slightly down, and a damped spring floats the eyes just above the
// water; under it, a swimmer with no vertical input hovers.
//
// It lives in the Godot layer because it moves a physics body. Its numbers are data/water.json's,
// read through the core's WaterTable, and its one job is the stroke: which rule moves the body
// when is PlayerWater's.

#nullable enable
using Godot;
using Undercity.Core.Vitals;

namespace Undercity.Client;

/// <summary>Moves a body through water, one physics tick at a time.</summary>
public sealed class SwimMotor
{
    private readonly WaterTable _t;

    /// <summary>A motor with <paramref name="table"/>'s numbers.</summary>
    public SwimMotor(WaterTable table) => _t = table;

    /// <summary>The vertical speed a body keeps on falling through the surface, metres per second.</summary>
    public float Entry(float vy) => vy < 0 ? vy * (float)_t.EntryKeepFraction : vy;

    /// <summary>
    /// Moves <paramref name="body"/> one tick of <paramref name="dt"/> seconds in water whose surface
    /// is at <paramref name="surfaceY"/>. <paramref name="under"/> is true while the eyes are under
    /// it; every speed is multiplied by <paramref name="speedFactor"/> (a tired swimmer's is less than 1).
    /// </summary>
    public void Step(Brushfire.PlayerController body, float surfaceY, bool under, BodyInput input, float speedFactor, float dt)
    {
        var yaw = new Basis(Vector3.Up, body.Yaw);
        var forward = body.LookDirection;
        if (!under && Mathf.Abs(body.Pitch) < Mathf.DegToRad((float)_t.SurfacePitchDeadZoneDeg))
        {
            forward = -yaw.Z;
        }
        var wish = forward * -input.Move.Y + yaw.X * input.Move.X;
        if (!under && wish.Y > 0)
        {
            wish.Y = 0;     // out of the water is a ladder or a ledge, not a stroke
        }
        wish = wish.LimitLength(1f);

        var speed = (float)_t.SwimSpeedMps * speedFactor;
        var blend = 1f - Mathf.Exp(-(float)_t.AccelPerS * dt);
        var drag = Mathf.Exp(-(float)_t.DragPerS * dt);
        var v = body.Velocity;

        var along = new Vector3(v.X, 0, v.Z);
        var wishAlong = new Vector3(wish.X, 0, wish.Z) * speed;
        along = wishAlong.LengthSquared() > 1e-6f ? along + (wishAlong - along) * blend : along * drag;

        var vy = v.Y;
        float? wantY = input.Crouch ? -(float)_t.DiveSpeedMps * speedFactor
            : input.Jump && under ? (float)_t.RiseSpeedMps * speedFactor
            : wish.Y < -0.01f || (under && wish.Y > 0.01f) ? wish.Y * speed
            : null;
        if (wantY is { } w)
        {
            vy += (w - vy) * blend;
        }
        else if (!under)
        {
            var target = surfaceY + (float)_t.FloatEyeAboveM;
            vy += ((float)_t.FloatStiffnessPerS2 * (target - body.EyePosition.Y) - (float)_t.FloatDampingPerS * vy) * dt;
        }
        else
        {
            vy *= drag;
        }

        body.Velocity = new Vector3(along.X, vy, along.Z);
        body.MoveAndSlide();
    }
}
