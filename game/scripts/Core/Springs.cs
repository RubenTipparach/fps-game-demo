using Godot;

namespace Brushfire;

/// <summary>
/// Damped springs for camera/viewmodel motion. Integrated with semi-implicit Euler in fixed
/// sub-steps, so they stay stable through frame hitches instead of exploding.
/// </summary>
public static class Springs
{
    const float MaxStep = 1f / 120f;

    static int Steps(ref float dt)
    {
        dt = Mathf.Min(dt, 0.1f);
        int n = Mathf.Max(1, Mathf.CeilToInt(dt / MaxStep));
        dt /= n;
        return n;
    }

    public static void Step(ref float x, ref float v, float target, float stiffness, float damping, float dt)
    {
        int n = Steps(ref dt);
        for (int i = 0; i < n; i++)
        {
            v += ((target - x) * stiffness - v * damping) * dt;
            x += v * dt;
        }
    }

    public static void Step(ref Vector2 x, ref Vector2 v, Vector2 target, float stiffness, float damping, float dt)
    {
        int n = Steps(ref dt);
        for (int i = 0; i < n; i++)
        {
            v += ((target - x) * stiffness - v * damping) * dt;
            x += v * dt;
        }
    }

    public static void Step(ref Vector3 x, ref Vector3 v, Vector3 target, float stiffness, float damping, float dt)
    {
        int n = Steps(ref dt);
        for (int i = 0; i < n; i++)
        {
            v += ((target - x) * stiffness - v * damping) * dt;
            x += v * dt;
        }
    }
}
