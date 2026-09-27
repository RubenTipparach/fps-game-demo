// A person in a level: a named NPC or a civilian. Stands, or walks a patrol, plays idle, walk and
// talk, greets the runner, and opens its dialog tree on use. Its faction and intelligence decide
// how the disguise rule judges the runner in front of it.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): who it is comes from
// data/npcs.json, what it says from its dialog tree, and every judgement from the core.

#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using Godot;
using Undercity.Core.Data;
using Undercity.Core.Dialog;
using Undercity.Core.Perception;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>An NPC or civilian.</summary>
public partial class NpcActor : CharacterBody3D, IWired, IInteractable, IStable
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

    /// <summary>Their intelligence, 1 to 5.</summary>
    public int Intelligence => _def?.Intelligence ?? 1;

    /// <summary>True for MerSec troopers who enforce the law.</summary>
    public bool IsLaw => _def?.Law ?? false;

    /// <summary>True when they report crimes: residents and MerSec.</summary>
    public bool Reports => Faction is "residents" || IsLaw;

    /// <summary>True unless knocked out, dead or gone.</summary>
    public bool Alive => Status is NpcStatus.Alive or NpcStatus.Hostile;

    private NpcStatus Status => _s is null || _def is null ? NpcStatus.Alive : _s.State.World.Npc(_def.Id);

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
        _idle = _def?.Idle ?? "idle";
        LoadModel(ModelId(data));
        ParsePatrol(Entity.Meta(this, "patrol"), Entity.Meta(this, "patrol_start", "0"));
        if (Status is NpcStatus.Gone or NpcStatus.Dead)
        {
            Hide();
        }
        Play(_patrol.Count > 0 ? "walk" : _idle);
    }

    private string ModelId(Undercity.Core.GameData data)
    {
        if (_def is not null)
        {
            return _def.Model;
        }
        // A civilian's look is chosen by its stable id, so a save always sees the same crowd (CLAUDE.md 5.4).
        var models = data.Npcs.Civilians.Models;
        return models[SeededRandom.For(_s!.State.World.Seed, StableId, "civilian_model").Next(models.Count)];
    }

    private void LoadModel(string modelId)
    {
        var path = $"res://models/characters/{modelId}.glb";
        if (!ResourceLoader.Exists(path))
        {
            GD.PushWarning($"[Undercity] {StableId}: no model {path}");
            return;
        }
        var model = GD.Load<PackedScene>(path).Instantiate<Node3D>();
        model.Name = "Model";
        // The characters face +Z; a node's forward is -Z.
        model.RotationDegrees = new Vector3(0, 180, 0);
        AddChild(model);
        _anim = model.FindChildren("*", "AnimationPlayer", true, false).OfType<AnimationPlayer>().FirstOrDefault();
        if (_anim is null)
        {
            return;
        }
        // glTF has no loop flag; every character clip loops (tools/blender/build_characters.py).
        foreach (var name in _anim.GetAnimationList())
        {
            _anim.GetAnimation(name).LoopMode = Animation.LoopModeEnum.Linear;
        }
    }

    private void Play(string clip)
    {
        if (_anim is not null && _anim.HasAnimation(clip) && _anim.CurrentAnimation != clip)
        {
            _anim.Play(clip, 0.25);
        }
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
        if (_s is null || !Visible)
        {
            return;
        }
        var dt = (float)delta;
        var v = Velocity;
        v.Y = IsOnFloor() ? 0 : v.Y - Gravity * dt;
        var player = _s.Level.Player;
        var toPlayer = player.GlobalPosition - GlobalPosition;
        toPlayer.Y = 0;
        if (_talking || Status == NpcStatus.Hostile)
        {
            v.X = v.Z = 0;
            Face(toPlayer, dt);
            Play(_talking ? "talk" : "guard");
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
                Face(dir, dt);
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
        Greet(toPlayer.Length(), delta);
    }

    private void Face(Vector3 dir, float dt)
    {
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
        var query = PhysicsRayQueryParameters3D.Create(Eye, eye, Brushfire.Layers.World);
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
                _s!.State.World.SetNpc(_def?.Id ?? StableId, NpcStatus.Hostile);
                break;
            case "calm":
                _s!.State.World.SetNpc(_def?.Id ?? StableId, NpcStatus.Alive);
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

    // ------------------------------------------------------------------ talking

    /// <inheritdoc/>
    public Interaction Describe()
    {
        if (_s is null || !Alive)
        {
            return Interaction.None;
        }
        return Status == NpcStatus.Hostile
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
        WaitForClose(session);
    }

    private async void WaitForClose(DialogSession session)
    {
        while (IsInstanceValid(this) && !session.Over && _s!.Screens.Blocking)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        }
        _talking = false;
    }
}
