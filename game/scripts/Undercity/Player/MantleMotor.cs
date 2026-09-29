// The mantle: a swimmer climbing onto a ledge whose top is 0.2-1.0 m above the water (a moored
// boat's deck, the outfall's ledge), with jump (openspec/changes/archive/2026-09-29-water-and-swimming, design
// section 4).
//
// It lives in the Godot layer because it probes the level's colliders and moves a physics body.
// The rise and reach are data/water.json's.

#nullable enable
using Godot;
using Undercity.Core.Vitals;

namespace Undercity.Client;

/// <summary>Pulls a swimmer up onto a ledge ahead, over mantle_time_s.</summary>
public sealed class MantleMotor
{
    /// <summary>The share of the mantle spent rising; the rest moves onto the ledge.</summary>
    private const float RiseShare = 0.6f;

    /// <summary>The ledge is searched for in steps of this, metres.</summary>
    private const float ProbeStepM = 0.05f;

    private readonly WaterTable _t;
    private Vector3 _from;
    private Vector3 _mid;
    private Vector3 _to;
    private float _t01 = -1f;

    /// <summary>A mantle with <paramref name="table"/>'s numbers.</summary>
    public MantleMotor(WaterTable table) => _t = table;

    /// <summary>True while pulling up.</summary>
    public bool Active => _t01 >= 0f;

    /// <summary>
    /// Looks for a ledge within mantle_reach_m ahead of a body of <paramref name="radius"/> metres,
    /// whose top is mantle_min_rise_m to mantle_max_rise_m above the water at <paramref name="surfaceY"/>,
    /// with room to stand on it. Starts the mantle and returns true when there is one.
    /// </summary>
    public bool TryStart(Brushfire.PlayerController body, float surfaceY, float radius)
    {
        var fwd = body.LookDirection;
        fwd.Y = 0;
        if (fwd.LengthSquared() < 1e-6f)
        {
            return false;
        }
        fwd = fwd.Normalized();
        var lo = surfaceY + (float)_t.MantleMinRiseM;
        var hi = surfaceY + (float)_t.MantleMaxRiseM;
        var feet = body.GlobalPosition;
        var space = body.GetWorld3D().DirectSpaceState;
        for (var d = radius + ProbeStepM; d <= radius + (float)_t.MantleReachM + 1e-4f; d += ProbeStepM)
        {
            var at = feet + fwd * d;
            var query = PhysicsRayQueryParameters3D.Create(new Vector3(at.X, hi + 0.05f, at.Z), new Vector3(at.X, lo - 0.05f, at.Z),
                Brushfire.Layers.World);
            query.Exclude = new Godot.Collections.Array<Rid> { body.GetRid() };
            var hit = space.IntersectRay(query);
            if (hit.Count == 0)
            {
                continue;
            }
            var top = hit["position"].AsVector3().Y;
            if (hit["normal"].AsVector3().Y < 0.7f || top < lo || top > hi)
            {
                return false;
            }
            // stand a body's width past the edge, and get there by rising, then moving over
            var mid = new Vector3(feet.X, top + 0.05f, feet.Z);
            var to = new Vector3(at.X, top + 0.02f, at.Z) + fwd * (radius + ProbeStepM);
            if (body.TestMove(body.GlobalTransform, mid - feet) || body.TestMove(new Transform3D(Basis.Identity, mid), to - mid))
            {
                return false;
            }
            _from = feet;
            _mid = mid;
            _to = to;
            _t01 = 0f;
            return true;
        }
        return false;
    }

    /// <summary>Moves the body one tick of the mantle.</summary>
    public void Step(Brushfire.PlayerController body, float dt)
    {
        _t01 = Mathf.Min(_t01 + dt / (float)_t.MantleTimeS, 1f);
        body.GlobalPosition = _t01 < RiseShare
            ? _from.Lerp(_mid, _t01 / RiseShare)
            : _mid.Lerp(_to, (_t01 - RiseShare) / (1f - RiseShare));
        body.Velocity = Vector3.Zero;
        if (_t01 >= 1f)
        {
            _t01 = -1f;
        }
    }
}
