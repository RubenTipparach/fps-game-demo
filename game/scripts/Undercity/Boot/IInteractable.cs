// What the use key can do with a thing: a prompt, whether it's possible now, and how long to hold.
//
// It lives here because every interactable shares the one use key and the one prompt
// (openspec/changes/world-interaction: one use key, one rule per object). The prompt comes from
// the same rule as the outcome (CLAUDE.md 5.1): a lock's prompt is its LockPlan.

#nullable enable

namespace Undercity.Client;

/// <summary>What pressing use would do now.</summary>
/// <param name="Prompt">The prompt, such as "Pick door, tier 1 (hold 1.0 s)".</param>
/// <param name="Enabled">False when it can't be done now: the prompt shows greyed.</param>
/// <param name="HoldS">Seconds to hold use; 0 for a press.</param>
public readonly record struct Interaction(string Prompt, bool Enabled, double HoldS = 0)
{
    /// <summary>Nothing to do.</summary>
    public static readonly Interaction None = new("", false);
}

/// <summary>A thing the use key works on.</summary>
public interface IInteractable
{
    /// <summary>What use would do now. Called every frame the crosshair is on it.</summary>
    Interaction Describe();

    /// <summary>Does it (after the hold, if any). Only called when <see cref="Describe"/> says it's enabled.</summary>
    void Use();
}
