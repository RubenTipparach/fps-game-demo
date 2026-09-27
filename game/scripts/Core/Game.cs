using Godot;

namespace Brushfire;

/// <summary>A playable level and the tool it was built with.</summary>
public record LevelInfo(string Id, string Title, string Tool, string Description, string ScenePath);

/// <summary>
/// Global game state (autoload "Game"): level list, settings, level flow and run statistics.
/// </summary>
public partial class Game : Node
{
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
    public int CurrentLevel { get; private set; } = -1;
    public LevelStats Stats { get; } = new();

    public override void _EnterTree()
    {
        Instance = this;
        ProcessMode = ProcessModeEnum.Always;
    }

    public override void _Ready()
    {
        Settings.Load();
        Settings.Apply();
        Input.UseAccumulatedInput = false; // every mouse event, not one per frame: precise aim
        if (!string.IsNullOrEmpty(OS.GetEnvironment("BRUSHFIRE_AUTOTEST")))
            AddChild(new AutoTest());
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
