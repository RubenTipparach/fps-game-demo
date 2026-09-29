// The application around a run: start one, load one, leave it, and the options. The Game autoload
// (the composition root) implements it and hands it to the title screen and to each level.
//
// It lives here as an interface so the title, the pause menu and the options screen never reach
// through Game.Instance for their collaborators (CLAUDE.md 5.3), and so the UI checks can hand
// them a stub.

#nullable enable
using Brushfire;

namespace Undercity.Client;

/// <summary>What the menus can ask of the application.</summary>
public interface IShell
{
    /// <summary>The options, persisted to user://settings.cfg (Brushfire's file, unchanged).</summary>
    GameSettings Settings { get; }

    /// <summary>Starts a new run in capsule 12 with a new seed.</summary>
    void NewGame();

    /// <summary>Loads a save slot and goes to its level. Returns false when the slot can't be loaded.</summary>
    bool Load(string slot);

    /// <summary>Leaves the run for the title screen.</summary>
    void ToTitle();

    /// <summary>Quits the game.</summary>
    void Quit();
}
