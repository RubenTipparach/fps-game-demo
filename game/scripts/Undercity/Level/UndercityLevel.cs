// The root of an Undercity level: places the player at the run's spawn, builds the services and
// wires every node that needs them, applies the core's host actions (open, npc, drop), runs the
// law and disguise watch, and handles travel and saves.
//
// It lives in the Godot layer because it is the level loader (CLAUDE.md 5.3): the rules it calls
// are the core's; it only turns engine events into core calls and core results into nodes.

#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using Brushfire;
using Godot;
using Undercity.Core;
using Undercity.Core.Combat;
using Undercity.Core.Perception;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>The root node of an Undercity level scene.</summary>
public partial class UndercityLevel : Node3D, ILevelHost
{
    /// <summary>The level id in data/levels, such as "hub".</summary>
    [Export] public string LevelId = "hub";

    /// <summary>The player scene.</summary>
    [Export] public PackedScene PlayerScene = GD.Load<PackedScene>("res://scenes/undercity/player.tscn");

    /// <summary>The UI scene (implements <see cref="IScreens"/>).</summary>
    [Export] public PackedScene ScreensScene = GD.Load<PackedScene>("res://ui/undercity/screens.tscn");

    /// <summary>The scene for items on the floor.</summary>
    [Export] public PackedScene WorldItemScene = GD.Load<PackedScene>("res://scenes/undercity/world_item.tscn");

    /// <summary>The conversation rig (openspec/changes/archive/2026-09-29-character-lighting).</summary>
    [Export] public PackedScene ConversationRigScene = GD.Load<PackedScene>("res://scenes/undercity/conversation_rig.tscn");

    /// <summary>
    /// For the AutoTest harness only: false takes conversations without the character lighting
    /// (the rig and the wrist glow), as the hub was lit before it, for the before-and-after checks.
    /// </summary>
    public bool ConversationRigOn { get; set; } = true;

    /// <summary>Seconds between law and disguise checks.</summary>
    private const double WatchIntervalS = 0.2;

    /// <summary>How far a resident or trooper notices a crime, metres.</summary>
    private const float ReportRangeM = 12f;

    /// <summary>How far a trooper notices a drawn weapon, metres.</summary>
    private const float LawSightM = 25f;

    /// <summary>How far the disguise chip looks for an observer of the outfit's faction, metres.</summary>
    private const float DisguiseChipRangeM = 25f;

    private Session? _session;
    private Action<string>? _travel;
    private IShell? _shell;
    private Services? _services;
    private Node? _screensNode;
    private PlayerController? _player;
    private LevelDef? _def;
    private LevelWater? _water;
    private IReadOnlyDictionary<string, CrowdLook>? _crowd;
    private readonly Dictionary<string, Node> _stable = new(StringComparer.Ordinal);
    private double _watchS;
    private bool _weaponSeenThisDraw;
    private int _drops;
    private ConversationRig? _rig;
    private Tween? _framing;

    /// <summary>
    /// Called by the composition root as the level enters the tree, before _Ready: the run, how to
    /// change level, and the application (loading, the title screen, options).
    /// </summary>
    public void Begin(Session session, Action<string> travel, IShell shell)
    {
        _session = session;
        _travel = travel;
        _shell = shell;
    }

    private GameState State => _session!.State;

    private IScreens Screens => _services!.Screens;

    // ------------------------------------------------------------------ ILevelHost

    /// <inheritdoc/>
    public string Id => LevelId;

    /// <inheritdoc/>
    public LevelDef Def => _def!;

    /// <inheritdoc/>
    public LevelWater Water => _water!;

    /// <inheritdoc/>
    public IReadOnlyDictionary<string, CrowdLook> Crowd => _crowd!;

    /// <inheritdoc/>
    public PlayerController Player => _player!;

    /// <inheritdoc/>
    public Vector3 PlayerEye => _player!.EyePosition;

    private readonly Dictionary<string, double> _restricted = new(StringComparer.Ordinal);

    /// <inheritdoc/>
    public double RestrictedS => _restricted.Count == 0 ? 0 : _restricted.Values.Max();

    /// <inheritdoc/>
    public void SetRestricted(string zoneId, double seconds)
    {
        if (seconds <= 0)
        {
            _restricted.Remove(zoneId);
        }
        else
        {
            _restricted[zoneId] = seconds;
        }
    }

    /// <summary>The run, for the AutoTest harness only (scripted captures set up state and log it).</summary>
    public GameState? AutoTestState => _session?.State;

    /// <summary>The node with a stable id, or null.</summary>
    public Node3D? FindStable(string stableId) => _stable.TryGetValue(stableId, out var n) ? n as Node3D : null;

    // ------------------------------------------------------------------ start

    public override void _Ready()
    {
        if (_session is null)
        {
            GD.PushError("[Undercity] a level started without a session; is the Game autoload missing?");
            return;
        }
        _def = _session.State.Data.Levels[LevelId];
        _water = new LevelWater(_def.Water, _session.State.Data.Water);
        // The whole crowd at once, from the world seed: no two neighbours look alike, and a save
        // sees the same crowd (openspec/changes/archive/2026-09-29-crowd-variety).
        _crowd = CrowdPicker.Assign(State.World.Seed, _def.Crowd, State.Data.Crowd);
        // Dry skin and wet cloth read the data's numbers (openspec/changes/archive/2026-09-29-character-lighting, design section 9).
        CharacterShading.Apply(State.Data.CharacterLighting.Wetness);
        // The ground draws the plan's puddles from the level's mask (openspec/changes/street-puddles).
        PuddleShading.Apply(_def.Puddles);
        State.World.CurrentLevel = LevelId;

        _player = PlayerScene.Instantiate<PlayerController>();
        PlaceAtSpawn(_player, State.World.Spawn);
        AddChild(_player);
        _player.ResetPhysicsInterpolation();

        _screensNode = ScreensScene.Instantiate();
        AddChild(_screensNode);
        var screens = (IScreens)_screensNode;

        _services = new Services(State, this, screens, _session.Saves, _shell!);
        foreach (var n in Descendants(this))
        {
            if (n is IStable s)
            {
                _stable[s.StableId] = n;
            }
        }
        ((IWired)_screensNode).Wire(_services);
        foreach (var w in Descendants(this).Where(n => !IsUnder(n, _screensNode)).OfType<IWired>())
        {
            w.Wire(_services);
        }
        GetTree().NodeAdded += OnNodeAdded;
        State.HostAction += OnHost;
        State.Died += OnDied;

        Input.MouseMode = Input.MouseModeEnum.Captured;
        _session.Save(SavesTable.Auto);
    }

    public override void _ExitTree()
    {
        GetTree().NodeAdded -= OnNodeAdded;
        if (_session is not null)
        {
            State.HostAction -= OnHost;
            State.Died -= OnDied;
        }
    }

    private void PlaceAtSpawn(Node3D body, string spawnId)
    {
        var marker = FindSpawn(spawnId) ?? FindSpawn("start");
        if (marker is null)
        {
            GD.PushWarning($"[Undercity] no spawn '{spawnId}' or 'start' in {LevelId}");
            return;
        }
        // Placed before it enters the tree, so it never touches anything at the origin.
        body.Transform = new Transform3D(Basis.FromEuler(new Vector3(0, marker.GlobalRotation.Y, 0)),
            marker.GlobalPosition + Vector3.Up * 0.05f);
    }

    private Node3D? FindSpawn(string id) => GetTree().GetNodesInGroup("ent_spawn").OfType<Node3D>()
        .FirstOrDefault(n => n.HasMeta("id") && n.GetMeta("id").AsString() == id);

    private void OnNodeAdded(Node node)
    {
        if (_services is null || _screensNode is null || IsUnder(node, _screensNode))
        {
            return;
        }
        if (node is IStable s)
        {
            _stable[s.StableId] = node;
        }
        if (node is IWired w)
        {
            // After the node's own _Ready, as for everything wired at load.
            Callable.From(() =>
            {
                if (IsInstanceValid(node))
                {
                    w.Wire(_services);
                }
            }).CallDeferred();
        }
    }

    private static IEnumerable<Node> Descendants(Node root)
    {
        foreach (var c in root.GetChildren())
        {
            yield return c;
            foreach (var d in Descendants(c))
            {
                yield return d;
            }
        }
    }

    private static bool IsUnder(Node n, Node ancestor) => n == ancestor || ancestor.IsAncestorOf(n);

    // ------------------------------------------------------------------ frame

    public override void _Process(double delta)
    {
        if (_services is null || _player is null)
        {
            return;
        }
        // A screen that takes the mouse also stops the body: no walking through a conversation, or
        // on after death while the screen fades.
        _player.ProcessMode = Screens.Blocking || State.Dead ? ProcessModeEnum.Disabled : ProcessModeEnum.Inherit;
        State.Tick(delta);
        _watchS -= delta;
        if (_watchS <= 0)
        {
            _watchS = WatchIntervalS;
            WatchLaw();
            WatchDisguise();
        }
    }

    public override void _UnhandledInput(InputEvent e)
    {
        if (_services is null)
        {
            return;
        }
        if (e.IsActionPressed("quicksave"))
        {
            State.Say(TrySave(SavesTable.Quick, out var reason) ? "Quicksaved." : reason);
        }
        else if (e.IsActionPressed("quickload"))
        {
            if (!_shell!.Load(SavesTable.Quick))
            {
                State.Say("No quicksave.");
            }
        }
        else if (e is InputEventMouseButton { Pressed: true } && !Screens.Blocking && Input.MouseMode != Input.MouseModeEnum.Captured)
        {
            Input.MouseMode = Input.MouseModeEnum.Captured;
        }
        else if (!Screens.Blocking)
        {
            for (var i = 0; i < 10; i++)
            {
                if (e.IsActionPressed($"belt_{i + 1}"))
                {
                    State.UseBelt(i);
                    _weaponSeenThisDraw = false;
                }
            }
        }
    }

    // ------------------------------------------------------------------ host actions

    private void OnHost(string action, string arg)
    {
        switch (action)
        {
            case "open" when _stable.TryGetValue(arg, out var n) && n is IOpenable o:
                o.Open();
                break;
            case "npc":
                var parts = arg.Split(':', 2);
                foreach (var npc in Npcs().Where(x => x.NpcId == parts[0]))
                {
                    npc.React(parts.Length > 1 ? parts[1] : "");
                }
                break;
            case "drop":
                var (item, count) = GameState.ParseSpec(arg);
                DropAtPlayer(item, count, null);
                break;
            default:
                GD.PushWarning($"[Undercity] host action '{action}' ({arg}) has no handler here");
                break;
        }
    }

    /// <inheritdoc/>
    public void DropAtPlayer(string itemId, int count, string? stolenFrom)
    {
        var node = WorldItemScene.Instantiate<WorldItem>();
        node.SetMeta("id", $"drop_{++_drops}");
        node.SetMeta("item", count > 1 ? $"{itemId}:{count}" : itemId);
        if (stolenFrom is not null)
        {
            node.SetMeta("stolen_from", stolenFrom);
        }
        // The body never turns; the look yaw lives on the camera rig.
        var forward = new Vector3(-Mathf.Sin(_player!.Yaw), 0, -Mathf.Cos(_player.Yaw));
        node.Position = _player.GlobalPosition + forward * 0.8f + Vector3.Up * 0.05f;
        AddChild(node);
    }

    // ------------------------------------------------------------------ travel and saves

    /// <inheritdoc/>
    public void Travel(ExitDef exit)
    {
        if (exit.Target == LevelId)
        {
            var marker = FindSpawn(exit.Spawn);
            if (marker is not null)
            {
                _player!.GlobalPosition = marker.GlobalPosition + Vector3.Up * 0.05f;
                _player.SetLook(Mathf.RadToDeg(marker.GlobalRotation.Y), 0);
                _player.ResetPhysicsInterpolation();
            }
            return;
        }
        var entry = State.Data.LevelIndex.Find(exit.Target);
        if (entry is not { Built: true })
        {
            State.Say($"{entry?.Title ?? exit.Target}: not in this build.");
            return;
        }
        State.World.CurrentLevel = exit.Target;
        State.World.Spawn = exit.Spawn;
        _session!.Save(SavesTable.Auto);
        _travel!(exit.Target);
    }

    /// <summary>Saves to a slot now, without the save rule: the game's own autosaves (a level change, the capsule bed).</summary>
    public void SaveTo(string slot) => _session!.Save(slot);

    /// <inheritdoc/>
    public string SaveRefusal()
    {
        var hostile = Seer(n => n.Hostile, (float)State.Data.Saves.HostileWatchM) is not null;
        return SaveRules.CanSave(new SaveSituation(Screens.InConversation, hostile), out var reason) ? "" : reason;
    }

    /// <inheritdoc/>
    public bool TrySave(string slot, out string reason)
    {
        reason = SaveRefusal();
        if (reason.Length > 0)
        {
            return false;
        }
        _session!.Save(slot);
        return true;
    }

    // ------------------------------------------------------------------ who sees the runner

    /// <summary>The NPCs in this level.</summary>
    public IEnumerable<NpcActor> Npcs() => GetTree().GetNodesInGroup("npcs").OfType<NpcActor>();

    /// <summary>The nearest NPC matching <paramref name="who"/> that can see the runner within <paramref name="rangeM"/>.</summary>
    public NpcActor? Seer(Func<NpcActor, bool> who, float rangeM)
    {
        NpcActor? best = null;
        var bestD = float.MaxValue;
        foreach (var npc in Npcs().Where(who))
        {
            var d = npc.GlobalPosition.DistanceTo(_player!.GlobalPosition);
            if (d < bestD && npc.CanSee(PlayerEye, rangeM))
            {
                best = npc;
                bestD = d;
            }
        }
        return best;
    }

    /// <inheritdoc/>
    public bool CrimeWitnessed(out string witness)
    {
        var npc = Seer(n => n.Reports && n.Alive, ReportRangeM);
        witness = npc?.DisplayName ?? "";
        return npc is not null;
    }


    private void WatchLaw()
    {
        if (State.Drawn is null)
        {
            _weaponSeenThisDraw = false;
            return;
        }
        if (_weaponSeenThisDraw || State.Law.Hostile)
        {
            return;
        }
        var cop = Seer(n => n.IsLaw && n.Alive, LawSightM);
        if (cop is null)
        {
            return;
        }
        _weaponSeenThisDraw = true;
        switch (State.Law.WeaponSeen())
        {
            case LawResponse.Warn:
                cop.Say("weapon_warning", "Put it away.");
                Screens.ShowAlert($"{cop.DisplayName}: put it away.");
                break;
            case LawResponse.Hostile:
                TurnLawHostile(cop);
                break;
        }
    }

    /// <summary>MerSec turns on the runner: every trooper goes hostile and the alarm sounds.</summary>
    public void TurnLawHostile(NpcActor who)
    {
        who.Say("alarm", "Hostile!");
        foreach (var npc in Npcs().Where(n => n.IsLaw && n.Alive))
        {
            npc.React("hostile");
        }
        Screens.ShowAlert("MerSec is hostile.");
    }

    // ------------------------------------------------------------------ violence

    /// <inheritdoc/>
    public void ShotHeard(Vector3 at, float radiusM, bool byRunner)
    {
        var heard = Npcs().Where(n => n.Alive && n.GlobalPosition.DistanceTo(at) <= radiusM).ToList();
        if (byRunner && !State.Law.Hostile && heard.FirstOrDefault(n => n.IsLaw) is { } trooper
            && State.Law.ShotFired() == LawResponse.Hostile)
        {
            TurnLawHostile(trooper);
        }
        foreach (var npc in heard)
        {
            npc.Provoke(Provocation.ShotHeard, at);
        }
    }

    /// <inheritdoc/>
    public void Killed(NpcActor victim, Vector3 from)
    {
        // Their own who see the body fall: the victim's faction, alive, with a clear line to it.
        var body = victim.GlobalPosition + Vector3.Up * 1.0f;
        foreach (var npc in Npcs().Where(n => n != victim && n.Alive && n.Faction == victim.Faction
                     && n.GlobalPosition.DistanceTo(body) <= (float)State.Data.Combat.Fight.SightM && n.ClearLine(body)))
        {
            npc.Provoke(Provocation.MurderSeen, from);
        }
    }

    // ------------------------------------------------------------------ conversations

    /// <inheritdoc/>
    public void ConversationOpened(NpcActor speaker)
    {
        var t = State.Data.CharacterLighting;
        var cam = _player!.GetNode<Camera3D>("CameraRig/Camera3D");
        var head = speaker.FaceCentre;
        if (_player.GetNodeOrNull<Light3D>("CameraRig/Camera3D/Wrist") is { } wrist)
        {
            wrist.Visible = ConversationRigOn;
        }
        if (ConversationRigOn)
        {
            // The level's own lights near the speaker decide the key's side (the core's rule).
            var right = cam.GlobalBasis.X;
            var near = Descendants(this).OfType<Light3D>()
                .Where(l => l.IsVisibleInTree() && !IsUnder(l, _player!) && l is not DirectionalLight3D)
                .Select(l => new Undercity.Core.World.NearbyLight((l.GlobalPosition - head).Dot(right),
                    l.GlobalPosition.DistanceTo(head), l.LightEnergy));
            var district = Def.DistrictNear(head.X, head.Z) ?? t.Gels.Keys.Min(StringComparer.Ordinal)!;
            _rig?.FadeOut(0);
            _rig = ConversationRigScene.Instantiate<ConversationRig>();
            AddChild(_rig);
            _rig.Light(t, head, cam, t.KeySide(near), district);
        }
        // Mockup D9: the view narrows and the pitch recentres so the face sits face_from_top of the
        // way down the screen. The camera doesn't move. (The body is paused while the dialog is open;
        // when it resumes it sets the view's width from the options again.)
        var f = t.Framing;
        var eye = cam.GlobalPosition;
        var flat = new Vector2(head.X - eye.X, head.Z - eye.Z).Length();
        var toHeadDeg = Mathf.RadToDeg(Mathf.Atan2(head.Y - eye.Y, flat));
        var aboveCentreDeg = Mathf.RadToDeg(Mathf.Atan((0.5f - (float)f.FaceFromTop) * 2 * Mathf.Tan(Mathf.DegToRad((float)f.FovDeg) / 2)));
        var yawDeg = Mathf.RadToDeg(_player.Yaw);
        _framing?.Kill();
        _framing = CreateTween().SetParallel();
        _framing.TweenProperty(cam, "fov", (float)f.FovDeg, f.TimeS);
        _framing.TweenMethod(Callable.From<float>(p => _player.SetLook(yawDeg, p)), Mathf.RadToDeg(_player.Pitch),
            toHeadDeg - aboveCentreDeg, f.TimeS);
    }

    /// <inheritdoc/>
    public void ConversationClosed(NpcActor speaker)
    {
        var t = State.Data.CharacterLighting;
        _rig?.FadeOut(t.Conversation.RampS);
        _rig = null;
        _framing?.Kill();
        _framing = null;
    }

    /// <summary>The runner died: the screen fades out, then the newest save loads (or the title opens).</summary>
    private async void OnDied()
    {
        var fadeS = State.Data.Combat.DeathFadeS;
        Screens.FadeToBlack(fadeS);
        await ToSignal(GetTree().CreateTimer(fadeS, processAlways: true), SceneTreeTimer.SignalName.Timeout);
        if (_session?.Saves.Newest() is { } newest && _shell!.Load(newest.Slot))
        {
            return;
        }
        _shell?.ToTitle();
    }

    private void WatchDisguise()
    {
        var faction = State.Inventory.OutfitFaction;
        if (faction is null)
        {
            Screens.ShowDisguise(null);
            return;
        }
        NpcActor? nearest = null;
        var bestD = float.MaxValue;
        foreach (var npc in Npcs().Where(n => n.Faction == faction && n.Alive))
        {
            var d = npc.GlobalPosition.DistanceTo(_player!.GlobalPosition);
            if (d < bestD && d <= DisguiseChipRangeM)
            {
                nearest = npc;
                bestD = d;
            }
        }
        var name = State.Data.Factions.Factions.First(f => f.Id == faction).Name;
        if (nearest is null)
        {
            var alone = State.Judge(new Observer(faction, 1), new Situation(DisguiseChipRangeM + 1));
            Screens.ShowDisguise(new DisguiseView(name, alone, "", 0, 0));
            return;
        }
        var judgement = nearest.Judge(bestD, talking: false);
        Screens.ShowDisguise(new DisguiseView(name, judgement, nearest.DisplayName, nearest.Intelligence, bestD));
    }
}
