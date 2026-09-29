// Deterministic randomness for everything that is allowed to be random: civilian small talk,
// rumours, loot variation. Skill checks never use it (CLAUDE.md 5.4).
//
// It lives in the core because a save and a replay must reproduce the same choices, and
// System.Random's sequence isn't guaranteed across .NET versions. SplitMix64 is small, fast and
// the same everywhere.

namespace Undercity.Core.Data;

/// <summary>A seeded random stream. Same seed, same numbers, on every platform and version.</summary>
public sealed class SeededRandom
{
    private ulong _state;

    /// <summary>Creates a stream from a 64-bit seed.</summary>
    public SeededRandom(ulong seed) => _state = seed;

    /// <summary>
    /// A stream for one purpose on one object: the save's seed, the object's stable id and what
    /// the numbers are for, so two purposes never share a sequence.
    /// </summary>
    public static SeededRandom For(ulong saveSeed, string stableId, string purpose) =>
        new(saveSeed ^ Hash($"{stableId}|{purpose}"));

    /// <summary>The next 64 random bits.</summary>
    public ulong NextULong()
    {
        _state += 0x9E3779B97F4A7C15UL;
        var z = _state;
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9UL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBUL;
        return z ^ (z >> 31);
    }

    /// <summary>A number in [0, <paramref name="max"/>). Returns 0 when max is 0 or less.</summary>
    public int Next(int max) => max <= 0 ? 0 : (int)(NextULong() % (ulong)max);

    /// <summary>A number in [0, 1).</summary>
    public double NextDouble() => (NextULong() >> 11) * (1.0 / (1UL << 53));

    /// <summary>A stable 64-bit FNV-1a hash of a string, the same on every platform.</summary>
    public static ulong Hash(string text)
    {
        var h = 0xCBF29CE484222325UL;
        foreach (var c in text)
        {
            h ^= c;
            h *= 0x100000001B3UL;
        }
        return h;
    }
}
