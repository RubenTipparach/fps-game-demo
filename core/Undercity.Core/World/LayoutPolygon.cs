// A polygon in layout metres (x east, y south, the engine's x and z): the one containment rule
// for a level's water bodies and districts.
//
// It lives in the core because everything that asks "is this point in it" must agree (CLAUDE.md
// 5.1): the swim motor and the placement check for water, the conversation rig for districts.

namespace Undercity.Core.World;

/// <summary>Containment and validation for [x, y] outlines in layout metres.</summary>
public static class LayoutPolygon
{
    /// <summary>True when the point (x, y) lies inside <paramref name="poly"/> (even-odd rule).</summary>
    public static bool Contains(IReadOnlyList<IReadOnlyList<double>> poly, double x, double y)
    {
        var inside = false;
        for (int i = 0, j = poly.Count - 1; i < poly.Count; j = i++)
        {
            double xi = poly[i][0], yi = poly[i][1], xj = poly[j][0], yj = poly[j][1];
            if ((yi > y) != (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi)
            {
                inside = !inside;
            }
        }
        return inside;
    }

    /// <summary>How far the point (x, y) is from <paramref name="poly"/>, metres: 0 inside, else to its nearest edge.</summary>
    public static double Distance(IReadOnlyList<IReadOnlyList<double>> poly, double x, double y)
    {
        if (Contains(poly, x, y))
        {
            return 0;
        }
        var best = double.MaxValue;
        for (int i = 0, j = poly.Count - 1; i < poly.Count; j = i++)
        {
            double ax = poly[j][0], ay = poly[j][1], bx = poly[i][0], by = poly[i][1];
            double dx = bx - ax, dy = by - ay, len2 = dx * dx + dy * dy;
            var t = len2 > 0 ? Math.Clamp(((x - ax) * dx + (y - ay) * dy) / len2, 0, 1) : 0;
            double px = ax + t * dx - x, py = ay + t * dy - y;
            best = Math.Min(best, Math.Sqrt(px * px + py * py));
        }
        return best;
    }

    /// <summary>True when <paramref name="poly"/> has 3 or more [x, y] points of finite metres.</summary>
    public static bool IsValid(IReadOnlyList<IReadOnlyList<double>> poly) =>
        poly.Count >= 3 && poly.All(p => p.Count == 2 && double.IsFinite(p[0]) && double.IsFinite(p[1]));
}
