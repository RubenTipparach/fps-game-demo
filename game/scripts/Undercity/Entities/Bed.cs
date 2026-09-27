// The safehouse bed (capsule 12): sleep restores health and saves the run.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): resting is the core's rule.

#nullable enable
using Godot;

namespace Undercity.Client;

/// <summary>A bed the runner can sleep in.</summary>
public partial class Bed : Node3D, IWired, IInteractable, IStable
{
    private Services? _s;

    /// <inheritdoc/>
    public string StableId => Entity.StableIdOf(this);

    /// <inheritdoc/>
    public void Wire(Services services) => _s = services;

    /// <inheritdoc/>
    public Interaction Describe() => _s is null ? Interaction.None : new Interaction("Sleep", true);

    /// <inheritdoc/>
    public void Use()
    {
        if (_s is null)
        {
            return;
        }
        _s.State.Rest();
        if (_s.Level is UndercityLevel level)
        {
            level.SaveTo("auto");
            _s.State.Say("Saved.");
        }
    }
}
