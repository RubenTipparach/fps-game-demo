// One Undercity run in this process: the data, the game state and the save folder. The Game
// autoload (the composition root) owns it and hands it to each level as it loads.
//
// It lives in the Godot layer because it is where the core meets Godot's paths (res://data,
// user://saves); everything it holds is core state.

#nullable enable
using System;
using Godot;
using Undercity.Core;

namespace Undercity.Client;

/// <summary>The current run.</summary>
public sealed class Session
{
    private static GameData? _data;

    private Session(GameState state, SaveStore saves)
    {
        State = state;
        Saves = saves;
    }

    /// <summary>The data tables, loaded once per process. A bad data file stops the game here with its path (CLAUDE.md 5.6).</summary>
    public static GameData Data => _data ??= GameData.Load(new GodotDataSource());

    /// <summary>The run.</summary>
    public GameState State { get; }

    /// <summary>The save slots, in user://saves.</summary>
    public SaveStore Saves { get; }

    /// <summary>The save folder, user://saves.</summary>
    public static SaveStore OpenSaves() => new(ProjectSettings.GlobalizePath("user://saves"));

    /// <summary>A new run with <paramref name="seed"/>, starting in the hub.</summary>
    public static Session NewGame(ulong seed)
    {
        var state = GameState.NewGame(Data, seed);
        state.World.CurrentLevel = "hub";
        state.World.Spawn = "start";
        return new Session(state, OpenSaves());
    }

    /// <summary>The run in a save slot, repaired where damaged (each repair is logged), or null when the slot is empty.</summary>
    public static Session? Load(string slot)
    {
        var saves = OpenSaves();
        var save = saves.Read(slot);
        if (save is null)
        {
            return null;
        }
        var (state, repairs) = GameState.Load(Data, save);
        foreach (var r in repairs)
        {
            GD.PushWarning($"[Undercity] save '{slot}' repaired: {r}");
        }
        return new Session(state, saves);
    }

    /// <summary>Writes the run to a slot.</summary>
    public void Save(string slot) => Saves.Write(slot, State.Save());

    /// <summary>The scene of a built level.</summary>
    public static string SceneOf(string levelId) =>
        Data.LevelIndex.Find(levelId) is { Built: true } entry
            ? entry.Scene
            : throw new InvalidOperationException($"level '{levelId}' isn't built");

    /// <summary>A seed for a new game: the clock, unless BRUSHFIRE_SEED fixes it (tests, captures).</summary>
    public static ulong NewSeed() =>
        ulong.TryParse(OS.GetEnvironment("BRUSHFIRE_SEED"), out var s) ? s : (ulong)DateTime.UtcNow.Ticks;
}
