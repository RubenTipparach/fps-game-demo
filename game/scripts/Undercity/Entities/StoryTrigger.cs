// A walk-in trigger: a discovery, a secret, a message. When the runner walks in and its
// conditions hold, its effects run, once per save unless it repeats.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): conditions and effects are data
// run by the core's dialog world, the same rules a conversation uses.

#nullable enable
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>A trigger placed by the level's entity layout.</summary>
public partial class StoryTrigger : Area3D, IWired, IStable
{
    private Services? _s;
    private TriggerDef? _def;

    /// <inheritdoc/>
    public string StableId => Entity.StableIdOf(this);

    private string FiredFlag => $"fired:{StableId}";

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _s = services;
        if (!services.Level.Def.Triggers.TryGetValue(StableId, out _def))
        {
            GD.PushError($"[Undercity] {StableId}: no trigger in data/levels/{services.Level.Id}.json");
            return;
        }
        BodyEntered += OnEntered;
    }

    private void OnEntered(Node3D body)
    {
        if (body is not Brushfire.PlayerController || _s is null || _def is null)
        {
            return;
        }
        if (_def.Once && _s.State.World.Flag(FiredFlag) || !_s.State.Holds(_def.If))
        {
            return;
        }
        if (_def.Once)
        {
            _s.State.World.SetFlag(FiredFlag);
            Brushfire.Audio.Play2D(this, "secret_found", -8f);
        }
        _s.State.Apply(_def.Do, StableId);
    }
}
