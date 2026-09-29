// An item on the floor: placed by the layout or dropped by the runner. Taking it picks up what
// fits; the rest stays. A dropped item comes to rest on the floor under it: it falls through air
// and sinks through water at data/water.json's item_sink_mps (openspec/changes/archive/2026-09-29-water-and-swimming).
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
    private bool _resting;
    private float _fallMps;

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
        _resting = _placed;     // the layout puts its items where they lie
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
    public override void _PhysicsProcess(double delta)
    {
        if (_resting || _s is null)
        {
            return;
        }
        var dt = (float)delta;
        var p = GlobalPosition;
        var water = _s.Level.Water;
        var inWater = water.SurfaceAt(p) is { } surface && p.Y < surface;
        if (inWater && _fallMps > (float)water.Table.ItemSinkMps + 0.5f)
        {
            ParticleBurst.Splash(this, new Vector3(p.X, water.SurfaceAt(p)!.Value, p.Z), 0.15f);    // fell in from above
        }
        _fallMps = inWater ? (float)water.Table.ItemSinkMps
            : _fallMps + (float)ProjectSettings.GetSetting("physics/3d/default_gravity").AsDouble() * dt;
        var step = _fallMps * dt;
        var query = PhysicsRayQueryParameters3D.Create(p + Vector3.Up * 0.05f, p + Vector3.Down * (step + 0.02f), Brushfire.Layers.World);
        var hit = GetWorld3D().DirectSpaceState.IntersectRay(query);
        if (hit.Count > 0)
        {
            GlobalPosition = hit["position"].AsVector3();
            _resting = true;
            return;
        }
        GlobalPosition = p + Vector3.Down * step;
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
