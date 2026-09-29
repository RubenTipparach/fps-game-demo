// A level exit: a drain gate, a grate, a lift panel, or a road you walk off the end of. It may
// have a lock (opened once, it stays open) and conditions; using it travels.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): the lock, the conditions and
// where it leads are data; travel and the autosave are the level's.

#nullable enable
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>An exit placed by the level's entity layout.</summary>
public partial class LevelExit : Node3D, IWired, IInteractable, IStable
{
    /// <summary>True for an exit taken by walking into it (a road); false for one you use (a gate).</summary>
    [Export] public bool WalkIn;

    private Services? _s;
    private ExitDef? _def;

    /// <inheritdoc/>
    public string StableId => Entity.StableIdOf(this);

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _s = services;
        if (!services.Level.Def.Exits.TryGetValue(StableId, out _def))
        {
            GD.PushError($"[Undercity] {StableId}: no exit in data/levels/{services.Level.Id}.json");
            return;
        }
        if (WalkIn && GetNodeOrNull<Area3D>("Area") is { } area)
        {
            area.BodyEntered += body =>
            {
                if (body is Brushfire.PlayerController && Describe().Enabled)
                {
                    Use();
                }
            };
        }
    }

    /// <inheritdoc/>
    public Interaction Describe()
    {
        if (_s is null || _def is null)
        {
            return Interaction.None;
        }
        if (Entity.IsLocked(_s, StableId, _def.Lock))
        {
            return Entity.DescribeLock(_s, StableId, _def.Lock, "");
        }
        return _s.State.Holds(_def.If) ? new Interaction(_def.Label, true) : new Interaction(_def.LockedText, false);
    }

    /// <inheritdoc/>
    public void Use()
    {
        if (_s is null || _def is null)
        {
            return;
        }
        if (Entity.IsLocked(_s, StableId, _def.Lock))
        {
            Entity.OpenLock(_s, StableId, _def.Lock!, null);
            return;
        }
        _s.Level.Travel(_def);
    }
}
