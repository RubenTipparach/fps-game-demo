// Finds and loads the real game/data for tests, once per test run.
//
// It lives with the tests because every rule test runs against the shipped tables, not a
// hand-written copy of them (CLAUDE.md 5.6, "validate the real artifact").

using Undercity.Core.Data;

namespace Undercity.Core.Tests;

/// <summary>The shipped data, loaded once.</summary>
public static class TestData
{
    /// <summary>game/data, found by walking up from the test binaries.</summary>
    public static FolderDataSource Source { get; } = new(FindDataFolder());

    private static readonly Lazy<GameData> Loaded = new(() => GameData.Load(Source));

    /// <summary>Every table, loaded and cross-checked.</summary>
    public static GameData Data => Loaded.Value;

    /// <summary>A new run with the shipped start kit and a fixed seed.</summary>
    public static GameState NewGame(ulong seed = 7) => GameState.NewGame(Data, seed);

    private static string FindDataFolder()
    {
        for (var dir = new DirectoryInfo(AppContext.BaseDirectory); dir is not null; dir = dir.Parent)
        {
            var candidate = Path.Combine(dir.FullName, "game", "data");
            if (File.Exists(Path.Combine(candidate, "items.json")))
            {
                return candidate;
            }
        }
        throw new DirectoryNotFoundException("game/data not found above " + AppContext.BaseDirectory);
    }
}
