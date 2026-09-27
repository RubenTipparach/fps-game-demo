// A terminal: log in (hack it if it's locked), then read its pages and use its actions on the
// terminal screen. Its first login runs its on-read effects once (codes learned, evidence found).
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): pages and effects are data
// (data/levels/<id>.json), and the effects run through the core's dialog world.

#nullable enable
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>A terminal placed by the level's entity layout.</summary>
public partial class TerminalActor : Node3D, IWired, IInteractable, IStable
{
    private Services? _s;
    private TerminalDef? _def;

    /// <inheritdoc/>
    public string StableId => Entity.StableIdOf(this);

    private string ReadFlag => $"read:{StableId}";

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _s = services;
        if (!services.Level.Def.Terminals.TryGetValue(StableId, out _def))
        {
            GD.PushError($"[Undercity] {StableId}: no terminal in data/levels/{services.Level.Id}.json");
        }
    }

    /// <inheritdoc/>
    public Interaction Describe() =>
        _s is null || _def is null ? Interaction.None : Entity.DescribeLock(_s, StableId, _def.Lock, "Use terminal");

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
        if (!_s.State.World.Flag(ReadFlag))
        {
            _s.State.World.SetFlag(ReadFlag);
            _s.State.Apply(_def.OnRead, StableId);
        }
        Brushfire.Audio.Play2D(this, "ui_click", -6f);
        _s.Screens.OpenTerminal(StableId, _def);
    }
}
