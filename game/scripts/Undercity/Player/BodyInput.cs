// What the player asks of their body on one physics tick, read once from the keys so the swim,
// ladder and mantle motors all see the same tick's input (and a scripted test drives them all
// through the same actions).
//
// It lives in the Godot layer because it reads Godot's input actions.

#nullable enable
using Godot;

namespace Undercity.Client;

/// <summary>The movement keys on one tick.</summary>
/// <param name="Move">move_left/right and move_forward/back, as Input.GetVector gives them: y below 0 is forward.</param>
/// <param name="Jump">Jump held.</param>
/// <param name="JumpPressed">Jump pressed this tick.</param>
/// <param name="Crouch">Crouch held.</param>
public readonly record struct BodyInput(Vector2 Move, bool Jump, bool JumpPressed, bool Crouch)
{
    /// <summary>Forward held (more than a third of the stick).</summary>
    public bool Forward => Move.Y < -0.3f;

    /// <summary>Back held.</summary>
    public bool Back => Move.Y > 0.3f;

    /// <summary>The keys now, or nothing while gameplay input is off (a menu has the mouse).</summary>
    public static BodyInput Read() => Brushfire.PlayerController.InputEnabled
        ? new BodyInput(Input.GetVector("move_left", "move_right", "move_forward", "move_back"),
            Input.IsActionPressed("jump"), Input.IsActionJustPressed("jump"), Input.IsActionPressed("crouch"))
        : default;
}
