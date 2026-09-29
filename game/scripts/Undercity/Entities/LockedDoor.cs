// A door or barrier with a lock: shows the lock's prompt, opens by its plan, and swings its moving
// part open. A dialog effect can open it too ("open": "hub:checkpoint_barrier").
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): the lock rule and whether it's
// open are the core's (LevelState.Opened).

#nullable enable
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>A locked door or checkpoint barrier.</summary>
public partial class LockedDoor : Node3D, IWired, IInteractable, IOpenable
{
    /// <summary>The part that moves: the leaf's hinge or the barrier's arm.</summary>
    [Export] public NodePath Moving = "Hinge";

    /// <summary>The moving part's rotation when open, degrees.</summary>
    [Export] public Vector3 OpenRotationDeg = new(0, 95, 0);

    /// <summary>Seconds to open.</summary>
    [Export] public float OpenTimeS = 0.7f;

    private Services? _s;
    private DoorDef? _def;
    private Node3D? _moving;
    private Vector3 _closedDeg;
    private float _open;
    private bool _opening;

    /// <inheritdoc/>
    public string StableId => Entity.StableIdOf(this);

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _s = services;
        if (!services.Level.Def.Doors.TryGetValue(StableId, out _def))
        {
            GD.PushError($"[Undercity] {StableId}: no door in data/levels/{services.Level.Id}.json");
        }
        _moving = GetNodeOrNull<Node3D>(Moving);
        _closedDeg = _moving?.RotationDegrees ?? Vector3.Zero;
        if (services.State.IsOpened(services.Level.Id, StableId))
        {
            _open = 1;
            _opening = true;
            Pose();
        }
    }

    /// <inheritdoc/>
    public Interaction Describe() =>
        _s is null || _def is null || _opening ? Interaction.None : Entity.DescribeLock(_s, StableId, _def.Lock, "");

    /// <inheritdoc/>
    public void Use()
    {
        if (_s is not null && _def is not null && Entity.OpenLock(_s, StableId, _def.Lock, _def.Owner))
        {
            Swing();
        }
    }

    /// <inheritdoc/>
    public void Open()
    {
        if (_s is null)
        {
            return;
        }
        _s.State.World.Level(_s.Level.Id).Opened.Add(StableId);
        Swing();
    }

    private void Swing()
    {
        _opening = true;
        Brushfire.Audio.Play3D(this, "door_open", GlobalPosition, -6f);
    }

    public override void _Process(double delta)
    {
        if (!_opening || _open >= 1)
        {
            return;
        }
        _open = Mathf.Min(1, _open + (float)delta / Mathf.Max(0.01f, OpenTimeS));
        Pose();
    }

    private void Pose()
    {
        if (_moving is not null)
        {
            var t = Mathf.SmoothStep(0, 1, _open);
            _moving.RotationDegrees = _closedDeg + OpenRotationDeg * t;
        }
    }
}
