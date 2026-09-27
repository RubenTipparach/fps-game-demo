// An item on the floor: placed by the layout or dropped by the runner. Taking it picks up what
// fits; the rest stays.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): pickup and stacking are the core's.

#nullable enable
using Godot;
using Undercity.Core;

namespace Undercity.Client;

/// <summary>An item lying in a level.</summary>
public partial class WorldItem : Node3D, IWired, IInteractable, IStable
{
    private Services? _s;
    private string _item = "";
    private int _count;
    private string? _stolenFrom;
    private bool _placed;

    /// <inheritdoc/>
    public string StableId => Entity.StableIdOf(this);

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _s = services;
        // A layout item's spec is in the level data; a dropped one carries it as metadata.
        _placed = services.Level.Def.Items.TryGetValue(StableId, out var spec);
        (_item, _count) = GameState.ParseSpec(_placed ? spec! : Entity.Meta(this, "item"));
        _stolenFrom = HasMeta("stolen_from") ? Entity.Meta(this, "stolen_from") : null;
        if (!services.Data.Items.Exists(_item))
        {
            GD.PushError($"[Undercity] {StableId}: unknown item '{_item}'");
            QueueFree();
            return;
        }
        if (_placed && services.State.World.Level(services.Level.Id).Taken.Contains(StableId))
        {
            QueueFree();
        }
    }

    /// <inheritdoc/>
    public Interaction Describe()
    {
        if (_s is null || _count <= 0)
        {
            return Interaction.None;
        }
        var name = _s.Data.Items.Get(_item).Name;
        return new Interaction(_count > 1 ? $"Take {name} x{_count}" : $"Take {name}", true);
    }

    /// <inheritdoc/>
    public void Use()
    {
        if (_s is null)
        {
            return;
        }
        var left = _s.State.PickUp(_item, _count, _stolenFrom);
        if (left == _count)
        {
            _s.State.Say("No room.");
            return;
        }
        Brushfire.Audio.Play2D(this, "pickup_ammo", -6f);
        _count = left;
        if (_count == 0)
        {
            if (_placed)
            {
                _s.State.World.Level(_s.Level.Id).Taken.Add(StableId);
            }
            QueueFree();
        }
    }
}
