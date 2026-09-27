// The UI as gameplay code sees it: open a conversation, a terminal or the deck, and drive the
// HUD's prompt, hold timer and disguise chip. The HUD reads everything else (health, belt,
// feed, quests) from the game state's own events.
//
// It lives here as an interface so level scripts never depend on a scene's layout (CLAUDE.md 5.3).

#nullable enable
using Undercity.Core.Dialog;
using Undercity.Core.Perception;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>The deck's tabs (the approved wrist-deck mockup, design page F6).</summary>
public enum DeckTab
{
    /// <summary>The pack, equipment and belt.</summary>
    Inventory,

    /// <summary>Skills and perks.</summary>
    Skills,

    /// <summary>Quests.</summary>
    Journal,
}

/// <summary>Who is on the other side of a conversation, for the dialog screen's header.</summary>
/// <param name="Name">Their name.</param>
/// <param name="Role">Their role or faction line, such as "MerSec sergeant".</param>
/// <param name="Disguise">The disguise verdict at talking range, when the runner is disguised as their faction; else null.</param>
public sealed record SpeakerView(string Name, string Role, Judgement? Disguise);

/// <summary>The disguise chip: the nearest observer of the runner's outfit faction.</summary>
/// <param name="Faction">The outfit's faction name.</param>
/// <param name="Judgement">The verdict for that observer now.</param>
/// <param name="Observer">The observer's name.</param>
/// <param name="Intelligence">The observer's intelligence.</param>
/// <param name="DistanceM">How far they are.</param>
public sealed record DisguiseView(string Faction, Judgement Judgement, string Observer, int Intelligence, double DistanceM);

/// <summary>The UI.</summary>
public interface IScreens
{
    /// <summary>True while a screen that takes the mouse is open (dialog, terminal, deck).</summary>
    bool Blocking { get; }

    /// <summary>Opens a conversation. The screen drives the session until it's over, then closes.</summary>
    void OpenDialog(DialogSession session, SpeakerView speaker);

    /// <summary>Opens a terminal that is already logged in.</summary>
    void OpenTerminal(string stableId, TerminalDef terminal);

    /// <summary>Opens the deck on a tab, or switches tab.</summary>
    void OpenDeck(DeckTab tab);

    /// <summary>Closes whatever screen is open.</summary>
    void CloseAll();

    /// <summary>The interaction prompt under the crosshair; an empty text hides it. A disabled prompt is greyed.</summary>
    void ShowPrompt(string text, bool enabled);

    /// <summary>The hold timer's progress, 0 to 1; a negative value hides it.</summary>
    void ShowHold(double progress);

    /// <summary>A spoken line as a subtitle: who, and what.</summary>
    void Bark(string speaker, string line);

    /// <summary>The disguise chip; null hides it.</summary>
    void ShowDisguise(DisguiseView? view);

    /// <summary>A warning line in the law colour, such as "MerSec: Put it away."; empty hides it.</summary>
    void ShowAlert(string text);
}
