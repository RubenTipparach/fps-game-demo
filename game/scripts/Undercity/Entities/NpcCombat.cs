// How a person defends themselves once violence starts: a fighter closes in and shoots or swings,
// everyone else flees along the navmesh, cowers or surrenders (openspec/changes/hub-combat,
// design section 5).
//
// It lives in the Godot layer because it moves a body and plays clips. Who does what is the
// core's (CombatRules.DefenceOf and Respond), and so are an NPC's aim and what a hit does to the
// runner (CombatRules.NpcShotHits, GameState.TakeHit): this asks, then acts. Every number comes
// from data/combat.json and data/weapons.json. NpcActor owns one and hands it each physics frame
// while it is active.

#nullable enable
using System;
using Brushfire;
using Godot;
using Undercity.Core.Combat;
using Undercity.Core.Data;

namespace Undercity.Client;

/// <summary>What a person who isn't fighting is doing about the violence around them.</summary>
public enum NpcMode
{
    /// <summary>Going about their business.</summary>
    Calm,

    /// <summary>Running to a point away from the shooting.</summary>
    Fleeing,

    /// <summary>Down and covering.</summary>
    Cowering,

    /// <summary>Hands up.</summary>
    Surrendered,
}

/// <summary>One person's fight, flight or surrender.</summary>
public sealed class NpcCombat
{
    // Directions tried for a flee point, degrees either side of straight away from the threat,
    // and how far along each, in multiples of combat.json's flee_m.
    private static readonly float[] FleeFanDeg = { 0, 30, -30, 60, -60, 90, -90, 120, -120 };
    private static readonly float[] FleeReach = { 1.0f, 1.4f };

    // Where in the Sword_Attack clip the blow lands, as a fraction of its length.
    private const float SwingLandsAt = 0.45f;

    // A fleeing person stops this close to their flee point, metres; the point is chosen this much
    // farther than flee_m, so where they stop is still flee_m from the threat.
    private const float ArriveM = 1f;

    // A fleeing person who moves less than this in StuckS has nowhere to go, and cowers.
    private const float StuckM = 0.3f;
    private const double StuckS = 2.0;

    private readonly NpcActor _npc;
    private readonly Services _s;
    private readonly NavigationAgent3D? _nav;
    private readonly Node3D? _held;

    private double _threatAtS = double.NegativeInfinity;
    private Vector3 _threat;
    private Vector3 _fleeTo;
    private double _cooldownS;
    private int _burstLeft;
    private int _loaded;
    private double _reloadS;
    private long _shots;
    private double _swingS = -1;
    private double _swingLengthS;
    private double _flinchS;
    private Vector3 _stuckFrom;
    private double _stuckS;

    /// <summary>Takes a person's defence and weapon; <paramref name="nav"/> moves them, <paramref name="held"/> is the weapon in their hand.</summary>
    public NpcCombat(NpcActor npc, Services services, Defence defence, WeaponDef? weapon, NavigationAgent3D? nav, Node3D? held)
    {
        _npc = npc;
        _s = services;
        Defence = defence;
        Weapon = weapon;
        _nav = nav;
        _held = held;
        _loaded = weapon?.Magazine ?? 0;
        if (_held is not null)
        {
            _held.Visible = false;
        }
    }

    /// <summary>What this person does when violence starts.</summary>
    public Defence Defence { get; }

    /// <summary>What they fight with, or null.</summary>
    public WeaponDef? Weapon { get; }

    /// <summary>What they're doing, when they aren't fighting.</summary>
    public NpcMode Mode { get; private set; }

    /// <summary>True while they fight: a fighter with a weapon whom the world holds hostile, while the runner lives.</summary>
    public bool Fighting => Defence == Defence.Fight && Weapon is not null && _npc.Hostile && !_s.State.Dead;

    /// <summary>True while they are doing anything about violence.</summary>
    public bool Active => Fighting || Mode != NpcMode.Calm || _flinchS > 0;

    private CombatTable T => _s.Data.Combat;

    private double Now => _s.State.World.PlayTimeS;

    /// <summary>
    /// Something happened that may set them off: a shot heard, a hit taken, a friend killed in
    /// view, from <paramref name="from"/>. The core says what they do about it.
    /// </summary>
    public void Provoke(Provocation what, Vector3 from)
    {
        _threatAtS = Now;
        _threat = from;
        switch (CombatRules.Respond(Defence, what))
        {
            case Defence.Fight when !_npc.Hostile:
                _npc.React("hostile");
                break;
            case Defence.Flee when Mode is NpcMode.Calm:
                StartFlee();
                break;
            case Defence.Cower when Mode is not NpcMode.Fleeing:
                Mode = NpcMode.Cowering;
                break;
            case Defence.Surrender:
                Mode = NpcMode.Surrendered;
                break;
        }
    }

    /// <summary>They were hit in <paramref name="zone"/> and lived: they flinch, then answer it.</summary>
    public void Hurt(HitZone zone, Vector3 from)
    {
        _flinchS = _npc.PlayOnce(zone == HitZone.Head ? "hit_head" : "hit_chest");
        _swingS = -1;
        Provoke(Provocation.Hurt, from);
    }

    /// <summary>Moves and animates them for one physics frame. Returns their horizontal velocity, m/s.</summary>
    public Vector3 Step(double dt)
    {
        _cooldownS -= dt;
        if (_held is not null)
        {
            _held.Visible = Fighting;
        }
        if (_flinchS > 0)
        {
            _flinchS -= dt;
            return Vector3.Zero;
        }
        if (Fighting)
        {
            return Weapon!.Melee ? Brawl(dt) : Shoot(dt);
        }
        switch (Mode)
        {
            case NpcMode.Fleeing:
                return Flee(dt);
            case NpcMode.Cowering:
                _npc.Play("cower");
                if (Now - _threatAtS > T.CowerS)
                {
                    Mode = NpcMode.Calm;
                }
                return Vector3.Zero;
            case NpcMode.Surrendered:
                _npc.FaceToward(ToRunner(), (float)dt);
                _npc.Play("surrender");
                if (ToRunner().Length() > T.SurrenderRadiusM && Now - _threatAtS > T.CowerS)
                {
                    Mode = NpcMode.Calm;
                }
                return Vector3.Zero;
            default:
                return Vector3.Zero;
        }
    }

    // ------------------------------------------------------------------ fighting

    private Vector3 ToRunner()
    {
        var to = _s.Level.Player.GlobalPosition - _npc.GlobalPosition;
        to.Y = 0;
        return to;
    }

    private bool SeesRunner(float distanceM) => distanceM <= T.Fight.SightM && _npc.ClearLine(_s.Level.PlayerEye);

    /// <summary>A fighter goes after the runner while they see them, or for a while after the last shot or hit.</summary>
    private bool Pursuing(bool sees) => sees || Now - _threatAtS <= T.Fight.PursueS;

    private Vector3 Shoot(double dt)
    {
        var w = Weapon!;
        var to = ToRunner();
        var d = to.Length();
        var sees = SeesRunner(d);
        if (_reloadS > 0)
        {
            _reloadS -= dt;
            _npc.FaceToward(to, (float)dt);
            if (_reloadS <= 0)
            {
                _loaded = w.Magazine;
            }
            return Vector3.Zero;
        }
        if (!Pursuing(sees))
        {
            if (double.IsFinite(_threatAtS))
            {
                _npc.FaceToward(_threat - _npc.GlobalPosition, (float)dt);
            }
            _npc.Play("hostile");
            return Vector3.Zero;
        }
        if (!sees || d > T.Fight.CloseToM)
        {
            return MoveTo(_s.Level.Player.GlobalPosition, T.RunMps, "run", dt);
        }
        if (d < T.Fight.BackOffM)
        {
            var back = _npc.GlobalPosition - to.Normalized() * (float)(T.Fight.BackOffM - d + 1);
            var v = MoveTo(back, T.RunMps, "run", dt);
            _npc.FaceToward(to, (float)dt);
            return v;
        }
        _npc.FaceToward(to, (float)dt);
        _npc.Play("aim");
        if (_cooldownS <= 0)
        {
            FireOnce(w, d);
        }
        return Vector3.Zero;
    }

    private void FireOnce(WeaponDef w, float distanceM)
    {
        if (_loaded <= 0)
        {
            _reloadS = w.ReloadS;
            _npc.PlayOnce("reload");
            if (w.ReloadSound is { } rs)
            {
                Audio.Play3D(_npc, rs, _npc.Muzzle, -4f);
            }
            return;
        }
        _loaded--;
        _shots++;
        _burstLeft = (_burstLeft <= 0 ? w.Burst : _burstLeft) - 1;
        _cooldownS = _burstLeft > 0 ? 1 / w.RatePerS : Math.Max(w.BurstGapS, 1 / w.RatePerS);

        var muzzle = _npc.Muzzle;
        _npc.PlayOnce("shoot");
        if (w.FireSound is { } fs)
        {
            Audio.Play3D(_npc, fs, muzzle);
        }
        Fx.MuzzleFlashLight(_npc, muzzle);

        var player = _s.Level.Player;
        var flat = new Vector3(player.Velocity.X, 0, player.Velocity.Z);
        var moving = flat.Length() > T.HitChance.MovingMps;
        var seed = _s.State.World.Seed;
        var chest = _s.Level.PlayerEye + Vector3.Down * 0.45f;
        var hits = 0;
        for (var p = 0; p < w.Pellets; p++)
        {
            var shot = _shots * 16 + p;
            var hit = CombatRules.NpcShotHits(T.HitChance, seed, _npc.TargetKey, shot, distanceM, moving, player.Crouched);
            if (hit)
            {
                hits++;
                _s.State.TakeHit(w);
            }
            if (p < 3)
            {
                Fx.Tracer(_npc, muzzle, hit ? chest : Miss(chest, muzzle, seed, shot));
            }
        }
        if (hits > 0)
        {
            Audio.Play2D(_npc, "player_hurt", -4f);
        }
        _s.Level.ShotHeard(muzzle, (float)w.NoiseM, byRunner: false);
    }

    /// <summary>Where a missed shot goes: past the runner by half a metre to a metre and a half, from the shot's own stream.</summary>
    private Vector3 Miss(Vector3 chest, Vector3 muzzle, ulong seed, long shot)
    {
        var rng = SeededRandom.For(seed, _npc.TargetKey, $"miss:{shot}");
        var dir = (chest - muzzle).Normalized();
        var side = dir.Cross(Vector3.Up).Normalized();
        var angle = (float)(rng.NextDouble() * Math.Tau);
        var r = 0.5f + (float)rng.NextDouble();
        return chest + (side * Mathf.Cos(angle) + Vector3.Up * Mathf.Sin(angle)) * r + dir * 4f;
    }

    private Vector3 Brawl(double dt)
    {
        var w = Weapon!;
        var to = ToRunner();
        var d = to.Length();
        if (_swingS >= 0)
        {
            var before = _swingS;
            _swingS += dt;
            _npc.FaceToward(to, (float)dt);
            var lands = _swingLengthS * SwingLandsAt;
            if (before < lands && _swingS >= lands && d <= w.ReachM)
            {
                _s.State.TakeHit(w);
                Audio.Play2D(_npc, "player_hurt", -4f);
            }
            if (_swingS >= _swingLengthS)
            {
                _swingS = -1;
            }
            return Vector3.Zero;
        }
        if (!Pursuing(SeesRunner(d)))
        {
            _npc.Play("hostile");
            return Vector3.Zero;
        }
        if (d > w.ReachM)
        {
            return MoveTo(_s.Level.Player.GlobalPosition, T.RunMps, "run", dt);
        }
        _npc.FaceToward(to, (float)dt);
        if (_cooldownS > 0)
        {
            _npc.Play("hostile");
            return Vector3.Zero;
        }
        _cooldownS = 1 / w.RatePerS;
        _swingLengthS = Math.Max(_npc.PlayOnce("swing"), 0.1);
        _swingS = 0;
        if (w.FireSound is { } fs)
        {
            Audio.Play3D(_npc, fs, _npc.Muzzle, -2f);
        }
        _s.Level.ShotHeard(_npc.GlobalPosition, (float)w.NoiseM, byRunner: false);
        return Vector3.Zero;
    }

    // ------------------------------------------------------------------ fleeing

    private void StartFlee()
    {
        if (FleePoint() is not { } p)
        {
            Mode = NpcMode.Cowering;
            return;
        }
        _fleeTo = p;
        _stuckFrom = _npc.GlobalPosition;
        _stuckS = 0;
        Mode = NpcMode.Fleeing;
    }

    private Vector3 Flee(double dt)
    {
        var left = _fleeTo - _npc.GlobalPosition;
        left.Y = 0;
        if (left.Length() < ArriveM || _nav is { } nav && nav.IsNavigationFinished() && nav.TargetPosition == _fleeTo)
        {
            Mode = NpcMode.Cowering;
            return Vector3.Zero;
        }
        _stuckS += dt;
        if (_stuckS >= StuckS)
        {
            if (_npc.GlobalPosition.DistanceTo(_stuckFrom) < StuckM)
            {
                Mode = NpcMode.Cowering;
                return Vector3.Zero;
            }
            _stuckFrom = _npc.GlobalPosition;
            _stuckS = 0;
        }
        return MoveTo(_fleeTo, T.SprintMps, "sprint", dt);
    }

    /// <summary>
    /// A point on the navmesh at least flee_m (and the arrival margin) from the threat, reachable
    /// from here and not under water: tried in a fan away from the threat, straight away first.
    /// </summary>
    private Vector3? FleePoint()
    {
        if (_nav is null)
        {
            return null;
        }
        var map = _nav.GetNavigationMap();
        var here = _npc.GlobalPosition;
        var away = here - _threat;
        away.Y = 0;
        away = away.LengthSquared() > 0.01f ? away.Normalized() : _npc.GlobalBasis.Z;
        var fleeM = (float)T.FleeM;
        foreach (var reach in FleeReach)
        {
            foreach (var deg in FleeFanDeg)
            {
                var want = here + away.Rotated(Vector3.Up, Mathf.DegToRad(deg)) * (fleeM + ArriveM) * reach;
                var p = NavigationServer3D.MapGetClosestPoint(map, want);
                var fromThreat = p - _threat;
                fromThreat.Y = 0;
                if (fromThreat.Length() < fleeM + ArriveM || _s.Level.Water.SurfaceAt(p) is { } surface && p.Y < surface)
                {
                    continue;
                }
                var path = NavigationServer3D.MapGetPath(map, here, p, true);
                if (path.Length > 0 && path[^1].DistanceTo(p) < 1f)
                {
                    return p;
                }
            }
        }
        return null;
    }

    // ------------------------------------------------------------------ moving

    /// <summary>Moves toward <paramref name="target"/> along the navmesh at <paramref name="speedMps"/>, playing <paramref name="clip"/>.</summary>
    private Vector3 MoveTo(Vector3 target, double speedMps, string clip, double dt)
    {
        var next = target;
        if (_nav is not null)
        {
            if (_nav.TargetPosition.DistanceTo(target) > 1f)
            {
                _nav.TargetPosition = target;
            }
            next = _nav.GetNextPathPosition();
        }
        var dir = next - _npc.GlobalPosition;
        dir.Y = 0;
        if (dir.LengthSquared() < 0.0025f)
        {
            return Vector3.Zero;
        }
        dir = dir.Normalized();
        _npc.FaceToward(dir, (float)dt);
        _npc.Play(clip);
        return dir * (float)speedMps;
    }
}
