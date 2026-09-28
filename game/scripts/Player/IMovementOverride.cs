using Godot;

namespace Brushfire;

/// <summary>
/// Moves the player's body in place of the ground and air rules while it applies: Undercity's
/// swimming, ladders and mantling (game/scripts/Undercity/Player/PlayerWater.cs). The controller
/// asks it first every physics tick, so the controller itself stays the Quake-style walker it
/// was (CLAUDE.md 13) and gains only this hand-off (openspec/changes/water-and-swimming).
/// </summary>
public interface IMovementOverride
{
    /// <summary>Called first on every physics tick. True when it moved the body this tick.</summary>
    bool Drive(PlayerController body, float dt);

    /// <summary>Ground speed is multiplied by this (wading); 1 when nothing slows the body.</summary>
    float GroundSpeedFactor { get; }

    /// <summary>False while sprinting isn't allowed (wading).</summary>
    bool SprintAllowed { get; }
}
