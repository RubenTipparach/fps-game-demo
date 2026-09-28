// When the runner may save, which slots exist, and when quitting warns about lost play
// (data/saves.json).
//
// It lives in the core because the pause menu's greyed button, the quicksave key and the
// refusal itself must agree: they all ask these rules, and a save tool or a test can too
// (openspec/specs/title-and-pause, CLAUDE.md 5.1).

using Undercity.Core.Data;

namespace Undercity.Core;

/// <summary>data/saves.json: the slots and the save rules' numbers.</summary>
public sealed class SavesTable : IValidated
{
    /// <summary>The quicksave slot (F5, F9).</summary>
    public const string Quick = "quick";

    /// <summary>The slot the game writes on every level change and in the capsule bed.</summary>
    public const string Auto = "auto";

    /// <summary>How many named slots the pause menu offers: slot_1 to slot_N.</summary>
    public required int NamedSlots { get; init; }

    /// <summary>Quit to title asks once when the newest save is older than this, seconds.</summary>
    public required double QuitWarnAfterS { get; init; }

    /// <summary>A hostile NPC that can see the runner within this range refuses a save, metres.</summary>
    public required double HostileWatchM { get; init; }

    /// <summary>Every slot in menu order: quick, auto, then the named slots.</summary>
    public IReadOnlyList<string> Slots =>
        new[] { Quick, Auto }.Concat(Enumerable.Range(1, NamedSlots).Select(i => $"slot_{i}")).ToArray();

    /// <summary>True when the player may write the slot from the pause menu: any slot but auto, which is the game's.</summary>
    public bool Writable(string slot) => slot != Auto && Slots.Contains(slot);

    /// <summary>
    /// True when quitting to the title should ask first: there is no save, or the newest is older
    /// than <see cref="QuitWarnAfterS"/>.
    /// </summary>
    public bool WarnBeforeQuit(DateTime? newestWrittenUtc, DateTime nowUtc) =>
        newestWrittenUtc is not { } newest || (nowUtc - newest).TotalSeconds > QuitWarnAfterS;

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        if (NamedSlots is < 1 or > 9)
        {
            errors.Add("named_slots must be 1 to 9");
        }
        if (!double.IsFinite(QuitWarnAfterS) || QuitWarnAfterS < 0)
        {
            errors.Add("quit_warn_after_s must be a finite number of seconds, zero or more");
        }
        if (!double.IsFinite(HostileWatchM) || HostileWatchM <= 0)
        {
            errors.Add("hostile_watch_m must be a finite distance above zero");
        }
    }
}

/// <summary>The one save rule.</summary>
public static class SaveRules
{
    /// <summary>
    /// No saving during a conversation or while a hostile can see the runner. The pause menu
    /// greys its buttons with this reason, and the quicksave key is refused with it.
    /// </summary>
    public static bool CanSave(SaveSituation situation, out string reason)
    {
        reason = situation.InConversation ? "Not during a conversation."
            : situation.HostileWatching ? "Not while hostiles can see you."
            : "";
        return reason.Length == 0;
    }
}

/// <summary>What the level knows at the moment of a save.</summary>
/// <param name="InConversation">A conversation is open.</param>
/// <param name="HostileWatching">A hostile NPC can see the runner within <see cref="SavesTable.HostileWatchM"/>.</param>
public sealed record SaveSituation(bool InConversation, bool HostileWatching);

/// <summary>One slot as the save lists show it, read from the save itself.</summary>
/// <param name="Slot">The slot name.</param>
/// <param name="Exists">A file is in the slot.</param>
/// <param name="Damaged">The file isn't a readable save; it can't be loaded.</param>
/// <param name="LevelId">Where the run was, from the save's own world state; empty when there is none.</param>
/// <param name="PlayTimeS">Seconds played, from the save.</param>
/// <param name="WrittenUtc">When the file was written; <see cref="DateTime.MinValue"/> when empty.</param>
public sealed record SaveSummary(string Slot, bool Exists, bool Damaged, string LevelId, double PlayTimeS, DateTime WrittenUtc)
{
    /// <summary>True when the slot holds a save that can be loaded.</summary>
    public bool Loadable => Exists && !Damaged;
}
