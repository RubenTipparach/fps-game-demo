// The ladder motor: climbing a ladder out of the water, or down into it (openspec/changes/archive/
// 2026-09-29-water-and-swimming, design section 4). Facing the ladder with forward held takes hold and
// climbs; back climbs down; jump pushes off. At the top the climber steps onto the floor, and
// from the floor "Climb down" (the ladder's use prompt) takes hold at the top.
//
// It lives in the Godot layer because it moves a physics body. Its numbers are data/water.json's,
// and the ladder's size and place are the level plan's (Ladder.cs).

#nullable enable
using System.Collections.Generic;
using Godot;
using Undercity.Core.Vitals;

namespace Undercity.Client;

/// <summary>Holds a body on a ladder, one physics tick at a time.</summary>
public sealed class LadderMotor
{
    /// <summary>How fast a climber is pulled onto the ladder's line, per second.</summary>
    private const float SnapPerS = 12f;

    private readonly WaterTable _t;
    private Vector3 _from;
    private Vector3 _to;
    private float _stepT = -1f;
    private bool _releaseAfterStep;

    /// <summary>A motor with <paramref name="table"/>'s numbers.</summary>
    public LadderMotor(WaterTable table) => _t = table;

    /// <summary>The ladder held, or null.</summary>
    public Ladder? On { get; private set; }

    /// <summary>True while holding a ladder (or stepping on or off one).</summary>
    public bool Active => On is not null;

    /// <summary>
    /// Takes hold of a ladder in reach that the body faces (look against the wall at least
    /// ladder_facing_dot) with forward held. True when it did.
    /// </summary>
    public bool TryGrab(Brushfire.PlayerController body, IEnumerable<Ladder> ladders, BodyInput input, float radius)
    {
        if (!input.Forward)
        {
            return false;
        }
        var look = body.LookDirection;
        look.Y = 0;
        if (look.LengthSquared() < 1e-6f)
        {
            return false;
        }
        look = look.Normalized();
        foreach (var l in ladders)
        {
            if (InReach(l, body, radius) && look.Dot(l.Into) >= (float)_t.LadderFacingDot)
            {
                On = l;
                return true;
            }
        }
        return false;
    }

    /// <summary>
    /// From the floor at a ladder's top: turns the body to face the wall and moves it onto the
    /// ladder, feet a metre under the top, over ladder_top_step_s.
    /// </summary>
    public void GrabFromTop(Brushfire.PlayerController body, Ladder l, float radius)
    {
        On = l;
        var into = l.Into;
        body.SetLook(Mathf.RadToDeg(Mathf.Atan2(-into.X, -into.Z)), 0f);
        StartStep(body.GlobalPosition, l.HoldPoint(radius, l.TopM - 1.0f), release: false);
    }

    private void StartStep(Vector3 from, Vector3 to, bool release)
    {
        _from = from;
        _to = to;
        _stepT = 0f;
        _releaseAfterStep = release;
    }

    /// <summary>Lets go.</summary>
    public void Release()
    {
        On = null;
        _stepT = -1f;
    }

    /// <summary>
    /// Moves the body one tick on the ladder, over water whose surface is at <paramref name="surfaceY"/>
    /// (null where there is none). Returns false when it let go this tick (pushed off, or climbed
    /// down into water deep enough to swim, or off the bottom): the other rules move the body from here.
    /// </summary>
    public bool Step(Brushfire.PlayerController body, BodyInput input, float radius, float? surfaceY, float dt)
    {
        var l = On!;
        if (_stepT >= 0f)
        {
            _stepT = Mathf.Min(_stepT + dt / (float)_t.LadderTopStepS, 1f);
            body.GlobalPosition = _from.Lerp(_to, Smooth(_stepT));
            body.Velocity = Vector3.Zero;
            if (_stepT >= 1f)
            {
                _stepT = -1f;
                if (_releaseAfterStep)
                {
                    On = null;
                }
            }
            return true;
        }
        if (input.JumpPressed)
        {
            body.Velocity = -l.Into * (float)_t.LadderPushOffMps;
            Release();
            return false;
        }
        var climb = input.Forward ? (float)_t.LadderSpeedMps : input.Back ? -(float)_t.LadderSpeedMps : 0f;
        var p = body.GlobalPosition;
        var toLine = l.HoldPoint(radius, p.Y) - p;
        body.Velocity = toLine * SnapPerS + Vector3.Up * climb;
        body.MoveAndSlide();
        p = body.GlobalPosition;

        if (climb > 0 && p.Y >= l.TopM + 0.05f)
        {
            // over the top: step in to the landing, clear of anything on the way; the floor takes the body from there
            var to = new Vector3(l.Landing.X, l.TopM + 0.02f, l.Landing.Z);
            if (!body.TestMove(new Transform3D(Basis.Identity, to + Vector3.Up * 0.02f), Vector3.Up * 0.01f))
            {
                StartStep(p, to, release: true);
            }
            else
            {
                body.Velocity = Vector3.Zero;    // blocked at the top: hold on
            }
            return true;
        }
        var swimDeep = surfaceY is { } sy && p.Y < sy - (float)_t.SwimDepthM;
        if ((climb < 0 && (swimDeep || body.EyePosition.Y < l.BottomM)) || !InReach(l, body, radius))
        {
            Release();
            return false;
        }
        return true;
    }

    private bool InReach(Ladder l, Brushfire.PlayerController body, float radius) =>
        l.InReach(body.GlobalPosition, body.EyePosition.Y, radius, (float)_t.LadderReachM, (float)_t.LadderSideReachM);

    private static float Smooth(float t) => t * t * (3f - 2f * t);
}
