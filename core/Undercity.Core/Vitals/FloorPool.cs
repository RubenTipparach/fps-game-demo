// A pool that regenerates only up to a floor: health and augmentation energy.
//
// It lives in the core because the owner's rule (survey B1: "health minimal regen is 25%") is
// shared by health and energy, and CLAUDE.md 5.1 wants one implementation of a shared rule.
// Above the floor, only items and healers restore it.

namespace Undercity.Core.Vitals;

/// <summary>The tuning of a floor-regenerating pool, from data/progression.json or data/augs.json.</summary>
/// <param name="FloorPct">The floor as a percentage of the maximum, 0 to 100.</param>
/// <param name="RatePerS">Points restored per second while below the floor.</param>
/// <param name="DelayS">Seconds after the last loss or use before regeneration starts.</param>
public sealed record FloorRegen(double FloorPct, double RatePerS, double DelayS);

/// <summary>A value between 0 and a maximum that regenerates only up to a floor.</summary>
public sealed class FloorPool
{
    private readonly FloorRegen _regen;
    private double _sinceLoss;

    /// <summary>Creates a full pool.</summary>
    public FloorPool(double max, FloorRegen regen)
    {
        if (!double.IsFinite(max) || max <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(max), max, "must be a positive number");
        }
        Max = max;
        Value = max;
        _regen = regen;
        _sinceLoss = regen.DelayS;
    }

    /// <summary>The current value, 0 to <see cref="Max"/>.</summary>
    public double Value { get; private set; }

    /// <summary>The maximum.</summary>
    public double Max { get; private set; }

    /// <summary>The value regeneration stops at.</summary>
    public double Floor => Max * _regen.FloorPct / 100.0;

    /// <summary>True when the value is 0.</summary>
    public bool Empty => Value <= 0;

    /// <summary>Raises when the value changes.</summary>
    public event Action? Changed;

    /// <summary>Removes <paramref name="amount"/> and restarts the regeneration delay. Non-finite or negative amounts are ignored.</summary>
    public void Lose(double amount)
    {
        if (!double.IsFinite(amount) || amount <= 0)
        {
            return;
        }
        Value = Math.Max(0, Value - amount);
        _sinceLoss = 0;
        Changed?.Invoke();
    }

    /// <summary>Adds up to <paramref name="amount"/>, capped at the maximum. Returns what was added.</summary>
    public double Restore(double amount)
    {
        if (!double.IsFinite(amount) || amount <= 0 || Value >= Max)
        {
            return 0;
        }
        var before = Value;
        Value = Math.Min(Max, Value + amount);
        Changed?.Invoke();
        return Value - before;
    }

    /// <summary>Sets a new maximum, keeping the same fraction full.</summary>
    public void SetMax(double max)
    {
        if (!double.IsFinite(max) || max <= 0)
        {
            return;
        }
        var fraction = Value / Max;
        Max = max;
        Value = Math.Clamp(fraction * max, 0, max);
        Changed?.Invoke();
    }

    /// <summary>Sets the value directly (loading a save), clamped to the legal range.</summary>
    public void Set(double value)
    {
        Value = double.IsFinite(value) ? Math.Clamp(value, 0, Max) : Max;
        Changed?.Invoke();
    }

    /// <summary>Advances time: regenerates toward the floor once the delay has passed.</summary>
    public void Tick(double dt)
    {
        if (!double.IsFinite(dt) || dt <= 0)
        {
            return;
        }
        _sinceLoss += dt;
        if (_sinceLoss < _regen.DelayS || Value >= Floor || Value <= 0 && _regen.RatePerS <= 0)
        {
            return;
        }
        var before = Value;
        Value = Math.Min(Floor, Value + _regen.RatePerS * dt);
        if (Value != before)
        {
            Changed?.Invoke();
        }
    }
}
