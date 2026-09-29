// What a node in an Undercity level may use, handed to it once by the level loader.
//
// It lives here because nodes are wired, not self-locating (CLAUDE.md 5.3): nothing in the
// Undercity layer reaches through a static singleton for its collaborators.

#nullable enable
using Undercity.Core;

namespace Undercity.Client;

/// <summary>A node that needs services. The level loader calls <see cref="Wire"/> once, after the node's _Ready.</summary>
public interface IWired
{
    /// <summary>Receives the services. Do setup that needs the game state here, not in _Ready.</summary>
    void Wire(Services services);
}

/// <summary>The services of one level visit.</summary>
/// <param name="State">The run: character, inventory, quests, world. The rules live here.</param>
/// <param name="Level">The level being played.</param>
/// <param name="Screens">The UI: dialog, terminal, deck and HUD.</param>
/// <param name="Saves">The save slots.</param>
/// <param name="Shell">The application: new game, load, the title screen, quit, options.</param>
public sealed record Services(GameState State, ILevelHost Level, IScreens Screens, SaveStore Saves, IShell Shell)
{
    /// <summary>The data tables.</summary>
    public GameData Data => State.Data;
}
