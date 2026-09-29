// A container: a locker, safe, crate or box with fixed contents and maybe a lock and an owner.
// Searching takes everything that fits; what doesn't stays for later. Taking from an owner in
// view of a resident or trooper is theft.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): contents, leftovers and stolen
// marking are the core's (GameState.Search).

#nullable enable
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>A container placed by the level's entity layout.</summary>
public partial class LootContainer : Node3D, IWired, IInteractable, IOpenable
{
    private Services? _s;
    private ContainerDef? _def;

    /// <inheritdoc/>
    public string StableId => Entity.StableIdOf(this);

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _s = services;
        if (!services.Level.Def.Containers.TryGetValue(StableId, out _def))
        {
            GD.PushError($"[Undercity] {StableId}: no container in data/levels/{services.Level.Id}.json");
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
        return _s.State.ContentsOf(_s.Level.Id, StableId, _def).Count == 0
            ? new Interaction($"Empty {_def.Noun}", false)
            : new Interaction($"Search {_def.Noun}", true);
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
            Entity.OpenLock(_s, StableId, _def.Lock!, _def.Owner);
            return;
        }
        if (_s.State.Search(_s.Level.Id, StableId, _def))
        {
            Brushfire.Audio.Play2D(this, "pickup_ammo", -6f);
            if (_def.Owner is not null)
            {
                Entity.Witness(_s);
            }
        }
    }

    /// <inheritdoc/>
    public void Open() => _s?.State.World.Level(_s.Level.Id).Opened.Add(StableId);
}
