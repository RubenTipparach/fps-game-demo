using Godot;

namespace Brushfire;

/// <summary>End-of-level tally screen, Doom/Quake style.</summary>
public partial class Intermission : CanvasLayer
{
    public override void _Ready()
    {
        Layer = 30;
        ProcessMode = ProcessModeEnum.Always;
        PauseMenu.Blocked = true;
        GetTree().Paused = true;
        Input.MouseMode = Input.MouseModeEnum.Visible;

        var game = Game.Instance;
        var s = game.Stats;
        var root = new Control { Theme = UiTheme.Get() };
        root.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        AddChild(root);
        var dim = new ColorRect { Color = new Color(0.02f, 0.015f, 0.01f, 0.85f) };
        dim.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        root.AddChild(dim);
        var center = new CenterContainer();
        center.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        root.AddChild(center);
        var v = new VBoxContainer();
        v.AddThemeConstantOverride("separation", 14);
        center.AddChild(v);

        string title = game.CurrentLevel >= 0 ? Game.Levels[game.CurrentLevel].Title : "Level";
        v.AddChild(UiTheme.MakeLabel(title.ToUpperInvariant(), 36, UiTheme.TextDim, HorizontalAlignment.Center));
        v.AddChild(UiTheme.MakeLabel("COMPLETE", 84, UiTheme.Accent, HorizontalAlignment.Center));

        int secs = (int)s.Time;
        float acc = s.ShotsFired > 0 ? 100f * s.ShotsHit / s.ShotsFired : 0f;
        var grid = new GridContainer { Columns = 2 };
        grid.AddThemeConstantOverride("h_separation", 60);
        v.AddChild(grid);
        void Row(string k, string val)
        {
            grid.AddChild(UiTheme.MakeLabel(k, 34));
            grid.AddChild(UiTheme.MakeLabel(val, 34, UiTheme.Accent, HorizontalAlignment.Right));
        }
        Row("KILLS", s.TotalEnemies > 0 ? $"{100 * s.Kills / s.TotalEnemies}%  ({s.Kills}/{s.TotalEnemies})" : "-");
        Row("SECRETS", s.TotalSecrets > 0 ? $"{s.Secrets}/{s.TotalSecrets}" : "-");
        Row("ACCURACY", $"{acc:0}%");
        Row("TIME", $"{secs / 60:00}:{secs % 60:00}");

        bool last = game.CurrentLevel >= Game.Levels.Length - 1;
        var next = UiTheme.MakeButton(last ? "BACK TO MENU" : "NEXT LEVEL", () => game.NextLevel());
        v.AddChild(next);
        v.AddChild(UiTheme.MakeButton("REPLAY", () => game.RestartLevel()));
        if (!last)
            v.AddChild(UiTheme.MakeButton("MAIN MENU", () => game.GoToMainMenu()));
        next.CallDeferred(Control.MethodName.GrabFocus);
    }

    public override void _ExitTree() => PauseMenu.Blocked = false;
}
