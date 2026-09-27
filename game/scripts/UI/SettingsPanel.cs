using System;
using Godot;

namespace Brushfire;

/// <summary>Options screen shared by the main menu and pause menu. Changes apply live.</summary>
public partial class SettingsPanel : PanelContainer
{
    public event Action Closed;

    public override void _Ready()
    {
        Theme = UiTheme.Get();
        CustomMinimumSize = new Vector2(760, 0);
        var s = Game.Instance.Settings;
        var v = new VBoxContainer();
        v.AddThemeConstantOverride("separation", 10);
        AddChild(v);
        v.AddChild(UiTheme.MakeLabel("OPTIONS", 44, UiTheme.Accent));

        AddSlider(v, "Mouse sensitivity", 0.1, 4.0, 0.05, s.MouseSensitivity, x => s.MouseSensitivity = (float)x);
        AddSlider(v, "Gamepad sensitivity", 0.2, 3.0, 0.05, s.GamepadSensitivity, x => s.GamepadSensitivity = (float)x);
        AddCheck(v, "Invert mouse Y", s.InvertY, x => s.InvertY = x);
        AddSlider(v, "Field of view (horizontal)", 80, 130, 1, s.Fov, x => s.Fov = (float)x, "0");
        AddCheck(v, "Head bob", s.HeadBob, x => s.HeadBob = x);
        AddSlider(v, "Master volume", 0, 1, 0.01, s.MasterVolume, x => { s.MasterVolume = (float)x; s.Apply(); });
        AddSlider(v, "Effects volume", 0, 1, 0.01, s.SfxVolume, x => { s.SfxVolume = (float)x; s.Apply(); });
        AddSlider(v, "Music volume", 0, 1, 0.01, s.MusicVolume, x => { s.MusicVolume = (float)x; s.Apply(); });
        AddCheck(v, "Fullscreen (F11)", s.Fullscreen, x => { s.Fullscreen = x; s.Apply(); });
        AddCheck(v, "Retro texture filtering", s.RetroFiltering, x => { s.RetroFiltering = x; MaterialFilter.Apply(x); });
        AddCheck(v, "Show FPS", s.ShowFps, x => s.ShowFps = x);

        var back = UiTheme.MakeButton("BACK", () =>
        {
            s.Save();
            Closed?.Invoke();
        });
        back.SizeFlagsHorizontal = SizeFlags.ShrinkEnd;
        v.AddChild(back);
        back.CallDeferred(Control.MethodName.GrabFocus);
    }

    static void AddSlider(Container parent, string label, double min, double max, double step, double value,
        Action<double> onChanged, string format = "0.00")
    {
        var row = new HBoxContainer();
        var l = UiTheme.MakeLabel(label, 24);
        l.CustomMinimumSize = new Vector2(300, 0);
        row.AddChild(l);
        var slider = new HSlider
        {
            MinValue = min, MaxValue = max, Step = step, Value = value,
            SizeFlagsHorizontal = SizeFlags.ExpandFill, CustomMinimumSize = new Vector2(280, 32),
            SizeFlagsVertical = SizeFlags.ShrinkCenter,
        };
        var valueLabel = UiTheme.MakeLabel(value.ToString(format), 24, UiTheme.Accent, HorizontalAlignment.Right);
        valueLabel.CustomMinimumSize = new Vector2(90, 0);
        slider.ValueChanged += x =>
        {
            onChanged(x);
            valueLabel.Text = x.ToString(format);
        };
        row.AddChild(slider);
        row.AddChild(valueLabel);
        parent.AddChild(row);
    }

    static void AddCheck(Container parent, string label, bool value, Action<bool> onChanged)
    {
        var c = new CheckButton { Text = label, ButtonPressed = value };
        c.Toggled += x =>
        {
            Audio.Play2D(c, "ui_click", -8f, 0f);
            onChanged(x);
        };
        parent.AddChild(c);
    }
}
