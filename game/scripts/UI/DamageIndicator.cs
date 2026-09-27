using System.Collections.Generic;
using Godot;

namespace Brushfire;

/// <summary>Red arc around the crosshair pointing to whoever just hurt you.</summary>
public partial class DamageIndicator : Control
{
    readonly List<(float angle, float time)> _hits = new();

    public DamageIndicator() => MouseFilter = MouseFilterEnum.Ignore;

    public void Show(float angle)
    {
        _hits.Add((angle, 1.2f));
        if (_hits.Count > 6)
            _hits.RemoveAt(0);
    }

    public override void _Process(double delta)
    {
        for (int i = _hits.Count - 1; i >= 0; i--)
        {
            var h = _hits[i];
            h.time -= (float)delta;
            if (h.time <= 0f)
                _hits.RemoveAt(i);
            else
                _hits[i] = h;
        }
        QueueRedraw();
    }

    public override void _Draw()
    {
        Vector2 c = Size / 2f;
        foreach (var (angle, time) in _hits)
        {
            float a = angle - Mathf.Pi / 2f;
            var col = new Color(1f, 0.15f, 0.1f, Mathf.Clamp(time, 0f, 1f) * 0.85f);
            DrawArc(c, 150f, a - 0.35f, a + 0.35f, 24, col, 10f, true);
        }
    }
}
