// A person in a level: a named NPC or a civilian. Stands, or walks a patrol, plays idle, walk and
// talk, greets the runner, and opens its dialog tree on use. Its faction and intelligence decide
// how the disguise rule judges the runner in front of it. It can be shot: the core's damage rule
// decides what a hit does, and its NpcCombat fights, flees, cowers or surrenders. Its body is a
// generated NPC scene (game/scenes/undercity/npcs/<model>.tscn) that plays the shared animation
// library and falls as a ragdoll when it collapses.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): who it is comes from
// data/npcs.json, what it says from its dialog tree, which clip plays for each state from
// data/npc_bodies.json, and every judgement and every hit from the core. Its status and health
// are kept under its target key (a named NPC's id, a civilian's stable id;
// openspec/changes/archive/2026-09-28-hub-combat, design section 9). A civilian's body, outfit
// palette, accessories, height and idle are the core's crowd pick (ILevelHost.Crowd,
// openspec/changes/archive/2026-09-29-crowd-variety), applied here. Its body is wet in the rain and
// dry under a roof by the core's rule, carried to its meshes by BodyWetness
// (openspec/changes/character-lighting, design section 9).

#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using Brushfire;
using Godot;
using Undercity.Core.Combat;
using Undercity.Core.Data;
using Undercity.Core.Dialog;
using Undercity.Core.Perception;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>An NPC or civilian.</summary>
public partial class NpcActor : CharacterBody3D, IWired, IInteractable, IStable, IDamageable, IHitEffect
{
    /// <summary>Walking speed on a patrol, m/s (the character walk cycles are authored at 1.4 m/s).</summary>
    [Export] public float WalkSpeed = 1.4f;

    /// <summary>Seconds a patroller waits at each point.</summary>
    [Export] public float PatrolWaitS = 2.5f;

    /// <summary>How close the runner must come for a greeting, metres.</summary>
    [Export] public float GreetRangeM = 3.0f;

    /// <summary>Seconds between greetings.</summary>
    [Export] public float GreetCooldownS = 30f;

    /// <summary>The half-angle of an NPC's view, degrees.</summary>
    [Export] public float ViewHalfAngleDeg = 60f;

    /// <summary>Within this distance an NPC notices the runner whatever way it faces, metres.</summary>
    [Export] public float NoticeRangeM = 2.5f;

    private const float Gravity = 20f;

    private Services? _s;
    private NpcDef? _def;
    private DialogTree? _tree;
    private AnimationPlayer? _anim;
    private NpcRagdoll? _ragdoll;
    private NpcTarget? _target;
    private NpcCombat? _combat;
    private BodyWetness? _wetness;
    private Node3D? _held;
    private Vector3 _heldMuzzle;
    private double _oneShotS;
    private string _idle = "idle";
    private readonly List<Vector3> _patrol = new();
    private int _patrolIndex;
    private double _waitS;
    private double _greetS;
    private bool _talking;

    /// <inheritdoc/>
    public string StableId => Entity.StableIdOf(this);

    /// <summary>The NPC id in data/npcs.json, or "civ" for a civilian.</summary>
    public string NpcId => Entity.Meta(this, "npc", "civ");

    /// <summary>Who they are, for the HUD and the dialog screen.</summary>
    public string DisplayName => _def?.Name ?? "Resident";

    /// <summary>Their faction id.</summary>
    public string Faction => _def?.Faction ?? "residents";

    /// <summary>
    /// The key their status and health are kept under in the world: a named NPC's id, which
    /// dialog and quests read, or a civilian's own stable id.
    /// </summary>
    public string TargetKey => _target?.Key ?? StableId;

    /// <summary>How they fight, flee, cower or surrender; null until wired.</summary>
    public NpcCombat? Combat => _combat;

    /// <summary>How wet their body is, 0 dry to 1 soaked; null until wired or without a body.</summary>
    public BodyWetness? BodyWetness => _wetness;

    /// <summary>Their intelligence, 1 to 5.</summary>
    public int Intelligence => _def?.Intelligence ?? 1;

    /// <summary>True for MerSec troopers who enforce the law.</summary>
    public bool IsLaw => _def?.Law ?? false;

    /// <summary>True when they report crimes: residents and MerSec.</summary>
    public bool Reports => Faction is "residents" || IsLaw;

    /// <summary>True unless knocked out, dead or gone.</summary>
    public bool Alive => Status is NpcStatus.Alive or NpcStatus.Hostile;

    /// <summary>True when this NPC is hostile to the runner.</summary>
    public bool Hostile => Status == NpcStatus.Hostile;

    private NpcStatus Status => _s is null || _target is null ? NpcStatus.Alive : _s.State.World.Npc(_target.Key);

    /// <inheritdoc/>
    public bool IsDead => !Alive;

    private Vector3 Eye => GlobalPosition + Vector3.Up * 1.6f;

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _s = services;
        AddToGroup("npcs");
        var data = services.Data;
        _def = NpcId == "civ" ? null : data.Npcs.Find(NpcId);
        if (NpcId != "civ" && _def is null)
        {
            GD.PushError($"[Undercity] {StableId}: unknown npc '{NpcId}'");
        }
        _tree = data.Dialogs[_def?.Dialog ?? data.Npcs.Civilians.Dialog];
        var look = _def is null ? services.Level.Crowd.GetValueOrDefault(StableId) : null;
        if (_def is null && look is null)
        {
            GD.PushError($"[Undercity] {StableId}: a civilian the level's crowd block doesn't place (tools/levels/export_level_data.py)");
        }
        _idle = _def?.Idle ?? look?.Idle ?? "idle";
        _target = _def is null ? NpcTarget.Civilian(data.Npcs.Civilians, StableId, Faction, DisplayName) : NpcTarget.For(_def);
        LoadModel(_def?.Model ?? look?.Body);
        if (look is not null)
        {
            Dress(look, data.Crowd);
        }
        var weapon = _def?.Weapon is { } wid ? data.Weapons.Find(wid) : null;
        _held = Hold(weapon);
        OnCharactersLayer(data.CharacterLighting.CharactersLayer);
        if (GetNodeOrNull<Node3D>("Model") is { } model)
        {
            _wetness = new BodyWetness(model, services.Level.Def.Shelters, data.CharacterLighting.Wetness, GlobalPosition);
        }
        _combat = new NpcCombat(this, services, CombatRules.DefenceOf(_def, data.Npcs.Civilians, services.State.World.Seed, StableId),
            weapon, GetNodeOrNull<NavigationAgent3D>("Nav"), _held);
        ParsePatrol(Entity.Meta(this, "patrol"), Entity.Meta(this, "patrol_start", "0"));
        if (Status is NpcStatus.Gone or NpcStatus.Dead)
        {
            Hide();
        }
        Play(_patrol.Count > 0 ? "walk" : _idle);
    }

    private void LoadModel(string? modelId)
    {
        if (modelId is null)
        {
            return;
        }
        var path = $"res://scenes/undercity/npcs/{modelId}.tscn";
        if (!ResourceLoader.Exists(path))
        {
            GD.PushWarning($"[Undercity] {StableId}: no NPC scene {path} (tools/godot/gen_npc_scenes.gd)");
            return;
        }
        var model = GD.Load<PackedScene>(path).Instantiate<Node3D>();
        model.Name = "Model";
        // The bodies face +Z; a node's forward is -Z.
        model.RotationDegrees = new Vector3(0, 180, 0);
        AddChild(model);
        _anim = model.GetNodeOrNull<AnimationPlayer>("Anim");
        _ragdoll = model.FindChildren("Ragdoll", "", true, false).OfType<NpcRagdoll>().FirstOrDefault();
        if (_anim is null || _ragdoll is null)
        {
            GD.PushWarning($"[Undercity] {StableId}: {path} lacks its Anim or Ragdoll node; regenerate it");
        }
    }

    /// <summary>
    /// Dresses a civilian as the crowd rule chose (openspec/changes/archive/2026-09-29-crowd-variety, design section
    /// 2), by the one dressing code (<see cref="CrowdDress"/>), and turns them to a talking partner.
    /// </summary>
    private void Dress(CrowdLook look, CrowdTable crowd)
    {
        if (GetNodeOrNull<Node3D>("Model") is not { } model)
        {
            return;
        }
        CrowdDress.Apply(model, look, crowd, w => GD.PushWarning($"[Undercity] {StableId}: {w}"));
        // The partner's place, layout metres (x east, y south) as Godot's x and z.
        if (look.Partner is { } partner && _s!.Level.Def.Crowd.TryGetValue(partner, out var other))
        {
            var to = new Vector3((float)other.At[0] - GlobalPosition.X, 0, (float)other.At[1] - GlobalPosition.Z);
            Rotation = new Vector3(0, Mathf.Atan2(-to.X, -to.Z), 0);
        }
    }

    /// <summary>
    /// Plays the clip data/npc_bodies.json gives a state, once the ragdoll's joints are ready. A
    /// clip started with <see cref="PlayOnce"/> plays to its end first.
    /// </summary>
    internal void Play(string state)
    {
        if (_oneShotS > 0 || _anim is null || _s is null || _ragdoll is { Prepared: false } || _ragdoll is { Collapsed: true })
        {
            return;
        }
        var bodies = _s.Data.NpcBodies;
        var clip = bodies.Clip(state) ?? bodies.Clip("idle");
        if (clip is null || !_anim.HasAnimation(clip))
        {
            return;
        }
        if (_anim.CurrentAnimation != clip)
        {
            _anim.Play(clip, bodies.BlendS);
        }
    }

    /// <summary>
    /// Plays a state's clip from its start (a shot, a flinch, a swing), even if it is playing.
    /// Returns its length in seconds, or 0 when it can't play.
    /// </summary>
    internal double PlayOnce(string state)
    {
        if (_anim is null || _s is null || _ragdoll is { Prepared: false } || _ragdoll is { Collapsed: true })
        {
            return 0;
        }
        var bodies = _s.Data.NpcBodies;
        if (bodies.Clip(state) is not { } clip || !_anim.HasAnimation(clip))
        {
            return 0;
        }
        _anim.Play(clip, bodies.BlendS * 0.5);
        _anim.Seek(0, true);
        _oneShotS = _anim.GetAnimation(clip).Length;
        return _oneShotS;
    }

    /// <summary>
    /// Puts a weapon's hand model in their right hand (the NPC scene's RightHand/Grip), hidden until
    /// they fight. Null when the weapon has none or the body has no hand attachment.
    /// </summary>
    private Node3D? Hold(WeaponDef? weapon)
    {
        if (weapon?.HandModel is not { } path || GetNodeOrNull("Model") is not { } model)
        {
            return null;
        }
        var grip = model.FindChild("Grip", true, false) as Node3D;
        if (grip is null || !ResourceLoader.Exists(path))
        {
            GD.PushWarning($"[Undercity] {StableId}: can't hold {path} (no RightHand/Grip, or no model)");
            return null;
        }
        var held = GD.Load<PackedScene>(path).Instantiate<Node3D>();
        held.Name = "Held";
        grip.AddChild(held);
        // The muzzle: the model's front end (its -Z extent), near its top, where every hand
        // model's barrel runs (tools/blender/build_undercity_props.py).
        var box = held.GetChildren().OfType<MeshInstance3D>().Select(m => m.Transform * m.GetAabb())
            .Aggregate(default(Aabb?), (a, b) => a is { } x ? x.Merge(b) : b);
        _heldMuzzle = box is { } bb ? new Vector3(0, bb.End.Y - 0.03f, bb.Position.Z) : new Vector3(0, 0.1f, -0.2f);
        return held;
    }

    /// <summary>
    /// Puts the body's meshes (and what they hold) on the characters' visual layer as well as the
    /// world's, so the wrist light and the conversation rig reach them and nothing else
    /// (openspec/changes/character-lighting, design section 2).
    /// </summary>
    private void OnCharactersLayer(int layer)
    {
        if (GetNodeOrNull("Model") is not { } model)
        {
            return;
        }
        var bits = 1u | (1u << (layer - 1));
        foreach (var g in model.FindChildren("*", "GeometryInstance3D", true, false).OfType<GeometryInstance3D>())
        {
            g.Layers = bits;
        }
    }

    /// <summary>
    /// The middle of their face, world space, at eye height: 0.1 m up the head bone (measured on
    /// the conversation shots: the eyes sit there on every body), or a standing head's eyes when
    /// the body has no skeleton. The conversation rig lights around it, D9's framing places it,
    /// and the face-box instrument measures around it.
    /// </summary>
    public Vector3 FaceCentre
    {
        get
        {
            var sk = GetNodeOrNull("Model")?.FindChild("GeneralSkeleton", true, false) as Skeleton3D;
            var head = sk?.FindBone("Head") ?? -1;
            return head < 0 ? GlobalPosition + Vector3.Up * 1.62f
                : sk!.GlobalTransform * sk.GetBoneGlobalPose(head) * new Vector3(0, 0.1f, 0);
        }
    }

    /// <summary>Where their shots come from: the held weapon's muzzle, or chest height in front of them.</summary>
    public Vector3 Muzzle => _held is { } h
        ? h.GlobalTransform * _heldMuzzle
        : GlobalPosition + Vector3.Up * 1.35f - GlobalBasis.Z * 0.4f;

    /// <summary>True once the body has collapsed (dead or knocked out).</summary>
    public bool Collapsed => _ragdoll?.Collapsed ?? false;

    /// <summary>
    /// The body falls as a ragdoll and freezes after data/npc_bodies.json's settle time. The
    /// caller records why (dead or knocked out) in the world; this only moves the body. A push
    /// (newton-seconds, world space) shoves the chest, as a hit would.
    /// </summary>
    public void Collapse(Vector3 pushNs = default)
    {
        if (_ragdoll is null || _ragdoll.Collapsed || _s is null)
        {
            return;
        }
        _anim?.Stop(keepState: true);
        Velocity = Vector3.Zero;
        CollisionLayer = 0;
        CollisionMask = 0;
        _ragdoll.Collapse(_s.Data.NpcBodies.Ragdoll.SettleS, pushNs, _s.Level.Water);
    }

    private void ParsePatrol(string spec, string start)
    {
        // Layout metres (x east, y south) to Godot (x east, z south); the height follows the floor.
        foreach (var pair in spec.Split(';', StringSplitOptions.RemoveEmptyEntries))
        {
            var xy = pair.Split(',');
            if (xy.Length == 2 && float.TryParse(xy[0], System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out var x)
                && float.TryParse(xy[1], System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out var y))
            {
                _patrol.Add(new Vector3(x, 0, y));
            }
        }
        if (_patrol.Count > 0 && int.TryParse(start, out var i))
        {
            _patrolIndex = Math.Clamp(i, 0, _patrol.Count - 1);
        }
    }

    // ------------------------------------------------------------------ frame

    public override void _PhysicsProcess(double delta)
    {
        if (_s is null || !Visible || Collapsed)
        {
            return;
        }
        var dt = (float)delta;
        _oneShotS -= delta;
        _wetness?.Tick(delta, GlobalPosition);
        var v = Velocity;
        v.Y = IsOnFloor() ? 0 : v.Y - Gravity * dt;
        var player = _s.Level.Player;
        var toPlayer = player.GlobalPosition - GlobalPosition;
        toPlayer.Y = 0;
        if (!_talking && _combat is { Active: true })
        {
            var h = _combat.Step(delta);
            v.X = h.X;
            v.Z = h.Z;
        }
        else if (_talking || Status == NpcStatus.Hostile)
        {
            v.X = v.Z = 0;
            FaceToward(toPlayer, dt);
            Play(_talking ? "talk" : "hostile");
        }
        else if (_patrol.Count > 0)
        {
            var target = _patrol[_patrolIndex];
            var to = new Vector3(target.X - GlobalPosition.X, 0, target.Z - GlobalPosition.Z);
            if (_waitS > 0)
            {
                _waitS -= delta;
                v.X = v.Z = 0;
                Play(_idle);
            }
            else if (to.Length() < 0.5f)
            {
                _patrolIndex = (_patrolIndex + 1) % _patrol.Count;
                _waitS = PatrolWaitS;
            }
            else
            {
                var dir = to.Normalized();
                v.X = dir.X * WalkSpeed;
                v.Z = dir.Z * WalkSpeed;
                FaceToward(dir, dt);
                Play("walk");
            }
        }
        else
        {
            v.X = v.Z = 0;
            Play(_idle);
        }
        Velocity = v;
        MoveAndSlide();
        if (_combat is not { Active: true })
        {
            Greet(toPlayer.Length(), delta);
        }
    }

    /// <summary>Turns them toward <paramref name="dir"/> (flattened), smoothly.</summary>
    internal void FaceToward(Vector3 dir, float dt)
    {
        dir.Y = 0;
        if (dir.LengthSquared() < 0.0001f)
        {
            return;
        }
        var want = Mathf.Atan2(-dir.X, -dir.Z);
        Rotation = new Vector3(0, Mathf.LerpAngle(Rotation.Y, want, 1f - Mathf.Exp(-6f * dt)), 0);
    }

    private void Greet(float distance, double delta)
    {
        _greetS -= delta;
        if (_greetS > 0 || _talking || distance > GreetRangeM || !CanSee(_s!.Level.PlayerEye, GreetRangeM))
        {
            return;
        }
        _greetS = GreetCooldownS;
        Say("greeting", "");
    }

    // ------------------------------------------------------------------ senses

    /// <summary>True when <paramref name="eye"/> is within range, in view (or very close), and unobstructed.</summary>
    public bool CanSee(Vector3 eye, float rangeM)
    {
        if (!Visible || !Alive)
        {
            return false;
        }
        var to = eye - Eye;
        var d = to.Length();
        if (d > rangeM)
        {
            return false;
        }
        var forward = -GlobalBasis.Z;
        var flat = new Vector3(to.X, 0, to.Z).Normalized();
        if (d > NoticeRangeM && forward.Dot(flat) < Mathf.Cos(Mathf.DegToRad(ViewHalfAngleDeg)))
        {
            return false;
        }
        return ClearLine(eye);
    }

    /// <summary>True when nothing of the level stands between their eyes and <paramref name="to"/>.</summary>
    public bool ClearLine(Vector3 to)
    {
        var query = PhysicsRayQueryParameters3D.Create(Eye, to, Brushfire.Layers.World);
        query.Exclude = new Godot.Collections.Array<Rid> { GetRid() };
        return GetWorld3D().DirectSpaceState.IntersectRay(query).Count == 0;
    }

    /// <summary>This NPC's disguise verdict on the runner at <paramref name="distanceM"/>. The one disguise rule is the core's.</summary>
    public Judgement Judge(float distanceM, bool talking)
    {
        var s = _s!.State;
        var player = _s.Level.Player;
        return s.Judge(new Observer(Faction, Intelligence),
            new Situation(distanceM, talking, s.Drawn is null ? 0 : s.DrawnS, player.Crouched, _s.Level.RestrictedS));
    }

    /// <summary>A bark of <paramref name="type"/> from this NPC's tree, or <paramref name="fallback"/>; nothing if both are empty.</summary>
    public void Say(string type, string fallback)
    {
        var line = fallback;
        if (_tree is not null && _tree.Barks.TryGetValue(type, out var lines) && lines.Count > 0)
        {
            // Seeded by who and when, so it varies but a replay hears the same lines (CLAUDE.md 5.4).
            var rng = SeededRandom.For(_s!.State.World.Seed, StableId, $"bark:{type}:{(long)_s.State.World.PlayTimeS}");
            line = lines[rng.Next(lines.Count)];
        }
        if (line.Length > 0)
        {
            _s!.Screens.Bark(DisplayName, line);
        }
    }

    /// <summary>Applies a dialog effect's "npc" action: hostile, calm, flee or gone.</summary>
    public void React(string what)
    {
        switch (what)
        {
            case "hostile":
                _s!.State.World.SetNpc(TargetKey, NpcStatus.Hostile);
                break;
            case "calm":
                _s!.State.World.SetNpc(TargetKey, NpcStatus.Alive);
                break;
            case "flee" or "gone":
                Hide();
                break;
        }
    }

    private new void Hide()
    {
        Visible = false;
        CollisionLayer = 0;
    }

    // ------------------------------------------------------------------ hurting

    /// <inheritdoc/>
    public void TakeDamage(DamageInfo info)
    {
        if (_s is null || _target is null || !Alive || info.WeaponId is null || _s.Data.Weapons.Find(info.WeaponId) is not { } weapon)
        {
            return;
        }
        // The zone from the hit's height on the standing body (design section 3), and the core's
        // damage rule once per round or pellet that hit, stopping at the one that kills.
        var zone = CombatRules.ZoneAt(_s.Data.Combat.Zones, info.Point.Y - GlobalPosition.Y);
        var hit = default(NpcHit);
        for (var i = 0; i < Math.Max(1, info.Hits) && !hit.Killed; i++)
        {
            hit = _s.State.HurtNpc(_target, weapon, zone);
        }
        var from = info.Source?.GlobalPosition ?? _s.Level.Player.GlobalPosition;
        if (info.Source is PlayerController)
        {
            _s.Screens.ShowHitMarker(hit.Killed);
        }
        if (hit.Killed)
        {
            _talking = false;
            var along = info.Direction.LengthSquared() > 0 ? info.Direction.Normalized() : -GlobalBasis.Z;
            Collapse(along * (float)_s.Data.Combat.DeathPushNs);
            _s.Level.Killed(this, from);
            return;
        }
        _combat?.Hurt(zone, from);
    }

    /// <inheritdoc/>
    public void ShowHit(Vector3 point, Vector3 normal) => ParticleBurst.Play(this, ParticleBurst.BloodScene, point, 0.5f, normal);

    /// <summary>Something that may set them off: a shot heard, a friend killed in view.</summary>
    public void Provoke(Provocation what, Vector3 from)
    {
        if (Alive && Visible && !Collapsed)
        {
            _combat?.Provoke(what, from);
        }
    }

    // ------------------------------------------------------------------ talking

    /// <inheritdoc/>
    public Interaction Describe()
    {
        if (_s is null || !Alive)
        {
            return Interaction.None;
        }
        return Status == NpcStatus.Hostile || _combat is { Active: true }
            ? new Interaction($"{DisplayName} won't talk", false)
            : new Interaction($"Talk to {DisplayName}", true);
    }

    /// <inheritdoc/>
    public void Use()
    {
        if (_s is null || _tree is null)
        {
            return;
        }
        var distance = GlobalPosition.DistanceTo(_s.Level.Player.GlobalPosition);
        Judgement? judgement = null;
        if (_s.State.Inventory.OutfitFaction == Faction)
        {
            judgement = Judge(distance, talking: true);
        }
        var accepted = judgement?.Verdict is Verdict.Accepted;
        var speaker = new Speaker(StableId, _def?.Id, accepted);
        var session = _s.State.Talk(_tree, speaker);
        var role = _def?.Role ?? "resident";
        _talking = true;
        _s.Screens.OpenDialog(session, new SpeakerView(DisplayName, role, judgement, Intelligence));
        _s.Level.ConversationOpened(this);
        WaitForClose(session);
    }

    private async void WaitForClose(DialogSession session)
    {
        while (IsInstanceValid(this) && !session.Over && _s!.Screens.Blocking)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        }
        _talking = false;
        if (IsInstanceValid(this))
        {
            _s!.Level.ConversationClosed(this);
        }
    }
}
