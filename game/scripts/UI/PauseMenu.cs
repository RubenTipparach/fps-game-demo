using Godot;

namespace Brushfire;

/// <summary>Esc / Start: pauses the tree and shows resume/restart/options/quit.</summary>
public partial class PauseMenu : CanvasLayer
{
    Control _root;
    VBoxContainer _buttons;
    SettingsPanel _settings;
    public static bool Blocked; // set while the intermission screen owns the pause state

    public override void _Ready()
    {
        Layer = 20;
        ProcessMode = ProcessModeEnum.Always;
        _root = new Control { Theme = UiTheme.Get(), Visible = false };
        _root.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        AddChild(_root);
        var dim = new ColorRect { Color = new Color(0, 0, 0, 0.6f) };
        dim.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        _root.AddChild(dim);

        var center = new CenterContainer();
        center.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        _root.AddChild(center);
        _buttons = new VBoxContainer();
        _buttons.AddThemeConstantOverride("separation", 12);
        center.AddChild(_buttons);
        _buttons.AddChild(UiTheme.MakeLabel("PAUSED", 72, UiTheme.Accent, HorizontalAlignment.Center));
        _buttons.AddChild(UiTheme.MakeButton("RESUME", () => SetPaused(false)));
        _buttons.AddChild(UiTheme.MakeButton("RESTART LEVEL", () => Game.Instance.RestartLevel()));
        _buttons.AddChild(UiTheme.MakeButton("OPTIONS", ShowSettings));
        _buttons.AddChild(UiTheme.MakeButton("MAIN MENU", () => Game.Instance.GoToMainMenu()));
        _buttons.AddChild(UiTheme.MakeButton("QUIT TO DESKTOP", () => GetTree().Quit()));

        _settings = new SettingsPanel { Visible = false };
        _settings.Closed += () =>
        {
            _settings.Visible = false;
            _buttons.Visible = true;
            ((Control)_buttons.GetChild(1)).GrabFocus();
        };
        center.AddChild(_settings);
        Blocked = false;
    }

    void ShowSettings()
    {
        _buttons.Visible = false;
        _settings.Visible = true;
    }

    public override void _UnhandledInput(InputEvent e)
    {
        if (!e.IsActionPressed("pause") || Blocked)
            return;
        GetViewport().SetInputAsHandled();
        if (_settings.Visible)
        {
            _settings.Visible = false;
            _buttons.Visible = true;
            return;
        }
        SetPaused(!_root.Visible);
    }

    public override void _Notification(int what)
    {
        // Losing focus (alt-tab) pauses, like it should.
        if (what == NotificationApplicationFocusOut && !_root.Visible && !Blocked && !OS.HasFeature("editor"))
            SetPaused(true);
    }

    void SetPaused(bool paused)
    {
        _root.Visible = paused;
        GetTree().Paused = paused;
        Input.MouseMode = paused ? Input.MouseModeEnum.Visible : Input.MouseModeEnum.Captured;
        if (paused)
            ((Control)_buttons.GetChild(1)).GrabFocus();
        else
            Game.Instance.Settings.Save();
    }
}
