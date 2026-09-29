using Godot;

namespace Brushfire;

/// <summary>A playable level and the tool it was built with.</summary>
public record LevelInfo(string Id, string Title, string Tool, string Description, string ScenePath);

/// <summary>
/// Global game state (autoload "Game"): level list, settings, level flow and run statistics. For
/// Undercity it is the composition root: it owns the run and is the shell the menus call.
/// </summary>
public partial class Game : Node, Undercity.Client.IShell
{
    /// <summary>Undercity's title screen, the project's main scene.</summary>
    const string UndercityTitle = "res://ui/undercity/title.tscn";

    public static Game Instance { get; private set; }

    public static readonly LevelInfo[] Levels =
    {
        new("csg", "E1M1: Pump Station", "Godot CSG",
            "Blocked out entirely with CSG nodes inside the Godot editor, then baked to a UV-mapped mesh for lightmapping.",
            "res://levels/csg/level_csg.tscn"),
        new("trenchbroom", "E1M2: Slag Works", "TrenchBroom",
            "Brushwork authored as a Quake .map for TrenchBroom and built into Godot with func_godot.",
            "res://levels/trenchbroom/level_trenchbroom.tscn"),
        new("blender", "E1M3: The Cistern", "Blender",
            "Modelled in Blender with non-destructive boolean (CSG) brushes, exported as glTF.",
            "res://levels/blender/level_blender.tscn"),
    };

    public GameSettings Settings { get; } = new();

    /// <summary>The Undercity run, if one is in progress. Only this composition root reads it; levels receive it.</summary>
    Undercity.Client.Session _undercity;
    public int CurrentLevel { get; private set; } = -1;
    public LevelStats Stats { get; } = new();

    public override void _EnterTree()
    {
        Instance = this;
        ProcessMode = ProcessModeEnum.Always;
        // Here, not in _Ready: at startup the main scene enters the tree right after the autoloads
        // and before any _Ready, and it must be handed the shell or the run as it enters.
        GetTree().NodeAdded += OnNodeAdded;
    }

    public override void _Ready()
    {
        Settings.Load();
        Settings.Apply();
        Input.UseAccumulatedInput = false; // every mouse event, not one per frame: precise aim
        if (!string.IsNullOrEmpty(OS.GetEnvironment("BRUSHFIRE_AUTOTEST")))
            AddChild(new AutoTest());
    }

    // ------------------------------------------------------------------ Undercity

    /// <summary>
    /// Hands the shell to the title screen, and the run to an Undercity level, as they enter the
    /// tree, before their _Ready. A level opened directly (F6 in the editor) starts a new game.
    /// </summary>
    void OnNodeAdded(Node node)
    {
        if (node is Undercity.Client.TitleScreen title)
        {
            _undercity = null;
            title.Begin(this, Undercity.Client.Session.OpenSaves(), Undercity.Client.Session.Data);
            return;
        }
        if (node is not Undercity.Client.UndercityLevel level)
            return;
        _undercity ??= Undercity.Client.Session.NewGame(Undercity.Client.Session.NewSeed());
        CurrentLevel = -1;
        level.Begin(_undercity, TravelUndercity, this);
    }

    /// <inheritdoc/>
    public void NewGame()
    {
        _undercity = Undercity.Client.Session.NewGame(Undercity.Client.Session.NewSeed());
        TravelUndercity(_undercity.State.World.CurrentLevel);
    }

    /// <inheritdoc/>
    public bool Load(string slot)
    {
        Undercity.Client.Session loaded;
        try
        {
            loaded = Undercity.Client.Session.Load(slot);
        }
        catch (Undercity.Core.Data.DataException e)
        {
            GD.PushError($"[Undercity] save '{slot}' can't be loaded: {e.Message}");
            return false;
        }
        if (loaded == null)
            return false;
        _undercity = loaded;
        TravelUndercity(loaded.State.World.CurrentLevel);
        return true;
    }

    /// <inheritdoc/>
    public void ToTitle()
    {
        _undercity = null;
        GetTree().Paused = false;
        Input.MouseMode = Input.MouseModeEnum.Visible;
        GetTree().CallDeferred(SceneTree.MethodName.ChangeSceneToFile, UndercityTitle);
    }

    /// <inheritdoc/>
    public void Quit() => GetTree().Quit();

    /// <summary>Changes to another Undercity level; the run has already recorded where to spawn.</summary>
    void TravelUndercity(string levelId)
    {
        GetTree().Paused = false;
        GetTree().CallDeferred(SceneTree.MethodName.ChangeSceneToFile, Undercity.Client.Session.SceneOf(levelId));
    }

    public void StartLevel(int index)
    {
        if (index < 0 || index >= Levels.Length)
        {
            GoToMainMenu();
            return;
        }
        CurrentLevel = index;
        Stats.Reset();
        GetTree().Paused = false;
        GetTree().CallDeferred(SceneTree.MethodName.ChangeSceneToFile, Levels[index].ScenePath);
    }

    public void RestartLevel() => StartLevel(CurrentLevel);

    public void NextLevel() => StartLevel(CurrentLevel + 1 < Levels.Length ? CurrentLevel + 1 : -1);

    public void GoToMainMenu()
    {
        CurrentLevel = -1;
        GetTree().Paused = false;
        Input.MouseMode = Input.MouseModeEnum.Visible;
        GetTree().CallDeferred(SceneTree.MethodName.ChangeSceneToFile, "res://scenes/ui/main_menu.tscn");
    }

    public override void _UnhandledInput(InputEvent e)
    {
        if (e is InputEventKey { Pressed: true, Keycode: Key.F11 })
        {
            Settings.Fullscreen = !Settings.Fullscreen;
            Settings.Apply();
            Settings.Save();
        }
    }
}

/// <summary>Per-level run statistics shown on the intermission screen.</summary>
public class LevelStats
{
    public int Kills;
    public int TotalEnemies;
    public int Secrets;
    public int TotalSecrets;
    public int ShotsFired;
    public int ShotsHit;
    public double Time;

    public void Reset()
    {
        Kills = TotalEnemies = Secrets = TotalSecrets = ShotsFired = ShotsHit = 0;
        Time = 0;
    }
}
