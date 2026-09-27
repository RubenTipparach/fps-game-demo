using Godot;

namespace Brushfire;

/// <summary>Dynamic crosshair: gap follows weapon spread, flashes an X on hits.</summary>
public partial class Crosshair : Control
{
    public float Spread;
    float _gap = 8f;
    float _hitTimer;
    bool _kill;

    public Crosshair() => MouseFilter = MouseFilterEnum.Ignore;

    public void Hit(bool kill)
    {
        _hitTimer = kill ? 0.35f : 0.18f;
        _kill = kill;
    }

    public override void _Process(double delta)
    {
        float target = 7f + Spread * 5.5f;
        _gap = Mathf.Lerp(_gap, target, 1f - Mathf.Exp(-18f * (float)delta));
        _hitTimer -= (float)delta;
        QueueRedraw();
    }

    public override void _Draw()
    {
        Vector2 c = Size / 2f;
        var col = new Color(1f, 1f, 1f, 0.9f);
        var shadow = new Color(0, 0, 0, 0.6f);
        const float len = 9f;
        foreach (var d in new[] { Vector2.Up, Vector2.Down, Vector2.Left, Vector2.Right })
        {
            DrawLine(c + d * _gap, c + d * (_gap + len), shadow, 4f);
            DrawLine(c + d * _gap, c + d * (_gap + len), col, 2f);
        }
        DrawCircle(c, 1.6f, col);
        if (_hitTimer > 0f)
        {
            var hc = _kill ? new Color(1f, 0.25f, 0.2f, 1f) : new Color(1f, 1f, 1f, 1f);
            float a = 10f, b = 20f;
            foreach (var d in new[] { new Vector2(1, 1), new Vector2(-1, 1), new Vector2(1, -1), new Vector2(-1, -1) })
                DrawLine(c + d.Normalized() * a, c + d.Normalized() * b, hc, 3f);
        }
    }
}
