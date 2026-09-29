// The compass strip inside the HUD's compass (hud.tscn): the bearing labels are authored along it
// at 45 degree steps from -180 to 540, and this draws the tick marks between them and slides the
// strip so the player's heading sits under the needle.
//
// It lives in the UI layer because it only presents the heading the level's player already has.

#nullable enable
using Godot;

namespace Undercity.Client;

/// <summary>The sliding compass strip.</summary>
public partial class CompassStrip : Control
{
    /// <summary>Pixels per degree of heading. The labels in hud.tscn are placed 45 degrees (240 px) apart to match.</summary>
    [Export] public float PixelsPerDegree { get; set; } = 240f / 45f;

    /// <summary>Degrees between minor ticks.</summary>
    [Export] public float TickDeg { get; set; } = 9f;

    /// <summary>The heading at the strip's left edge, degrees.</summary>
    [Export] public float StartDeg { get; set; } = -180f;

    /// <summary>The span the strip covers, degrees.</summary>
    [Export] public float SpanDeg { get; set; } = 720f;

    /// <summary>Slides the strip so <paramref name="headingDeg"/> (0 to 360, 0 north, clockwise) sits at the centre of a <paramref name="viewWidth"/>-pixel window.</summary>
    public void Face(double headingDeg, float viewWidth) =>
        Position = new Vector2(viewWidth / 2f - (float)(headingDeg - StartDeg) * PixelsPerDegree, Position.Y);

    /// <inheritdoc/>
    public override void _Draw()
    {
        var minor = GetThemeColor("faint", "Palette");
        var major = GetThemeColor("text_dim", "Palette");
        var h = Size.Y;
        var steps = (int)(SpanDeg / TickDeg);
        for (var i = 0; i <= steps; i++)
        {
            var deg = i * TickDeg;
            var x = deg * PixelsPerDegree;
            var isMajor = Mathf.IsZeroApprox(Mathf.PosMod(deg, 45f));
            DrawLine(new Vector2(x, h - (isMajor ? 12 : 8)), new Vector2(x, h - 2), isMajor ? major : minor, 2f);
        }
    }
}
