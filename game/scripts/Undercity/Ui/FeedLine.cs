// One line of the HUD's message feed (feed_line.tscn): it shows for a while, fades and frees itself.
//
// It lives in the UI layer because the feed's text comes from GameState.Feed; only how long a line
// stays on screen is decided here.

#nullable enable
using Godot;

namespace Undercity.Client;

/// <summary>A feed line.</summary>
public partial class FeedLine : Label
{
    /// <summary>Seconds the line stays fully visible.</summary>
    [Export] public double LifeS { get; set; } = 6.0;

    /// <summary>Seconds the fade takes, after <see cref="LifeS"/>.</summary>
    [Export] public double FadeS { get; set; } = 0.8;

    /// <inheritdoc/>
    public override void _Ready()
    {
        var tween = CreateTween();
        tween.TweenInterval(LifeS);
        tween.TweenProperty(this, "modulate:a", 0.0, FadeS);
        tween.TweenCallback(Callable.From(QueueFree));
    }
}
