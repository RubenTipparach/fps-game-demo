// The options screen (options.tscn, approved mockup D7): Controls, Video and Audio tabs, one row
// per setting, a label and a control. Opened from the title screen and from the pause menu, so it
// always processes (the tree is paused under the pause menu).
//
// It lives in the UI layer as a view over Brushfire's GameSettings: the values, their ranges
// (GameSettings.*Range) and the settings file are Brushfire's and stay unchanged; this screen
// only shows them in Undercity's theme (openspec/specs/title-and-pause; design in openspec/changes/archive/2026-09-28-title-and-pause, section 3).

#nullable enable
using System;
using System.Collections.Generic;
using System.Globalization;
using Brushfire;
using Godot;

namespace Undercity.Client;

/// <summary>The options screen.</summary>
public partial class OptionsScreen : Control
{
    private readonly List<(HSlider Slider, Label Value, string Format, Func<GameSettings, float> Get)> _sliders = new();
    private readonly List<(CheckButton Toggle, Func<GameSettings, bool> Get)> _toggles = new();
    private GameSettings? _settings;
    private Control[] _pages = Array.Empty<Control>();
    private Button[] _tabs = Array.Empty<Button>();

    /// <summary>Raised when the screen closes; the settings are saved by then.</summary>
    public event Action? Closed;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _pages = new[] { GetNode<Control>("%ControlsPage"), GetNode<Control>("%VideoPage"), GetNode<Control>("%AudioPage") };
        _tabs = new[] { GetNode<Button>("%ControlsTab"), GetNode<Button>("%VideoTab"), GetNode<Button>("%AudioTab") };
        for (var i = 0; i < _tabs.Length; i++)
        {
            var page = i;
            _tabs[i].Pressed += () => ShowPage(page);
        }
        GetNode<Button>("%OptionsBack").Pressed += Close;

        Slider("MouseSensitivity", GameSettings.MouseSensitivityRange, "0.00", s => s.MouseSensitivity, (s, v) => s.MouseSensitivity = v);
        Toggle("InvertLook", s => s.InvertY, (s, v) => s.InvertY = v);
        Slider("Fov", GameSettings.FovRange, "0°", s => s.Fov, (s, v) => s.Fov = v);
        Toggle("HeadBob", s => s.HeadBob, (s, v) => s.HeadBob = v);
        Slider("PadSensitivity", GameSettings.GamepadSensitivityRange, "0.00", s => s.GamepadSensitivity, (s, v) => s.GamepadSensitivity = v);
        Toggle("Fullscreen", s => s.Fullscreen, (s, v) =>
        {
            s.Fullscreen = v;
            s.Apply();
        });
        Toggle("RetroFiltering", s => s.RetroFiltering, (s, v) =>
        {
            s.RetroFiltering = v;
            MaterialFilter.Apply(v);
        });
        Slider("MasterVolume", GameSettings.VolumeRange, "0.00", s => s.MasterVolume, (s, v) =>
        {
            s.MasterVolume = v;
            s.Apply();
        });
        Slider("MusicVolume", GameSettings.VolumeRange, "0.00", s => s.MusicVolume, (s, v) =>
        {
            s.MusicVolume = v;
            s.Apply();
        });
        Slider("EffectsVolume", GameSettings.VolumeRange, "0.00", s => s.SfxVolume, (s, v) =>
        {
            s.SfxVolume = v;
            s.Apply();
        });
    }

    /// <summary>Opens the screen on the Controls tab, showing <paramref name="settings"/>.</summary>
    public void Open(GameSettings settings)
    {
        _settings = settings;
        foreach (var (slider, value, format, get) in _sliders)
        {
            slider.SetValueNoSignal(get(settings));
            value.Text = slider.Value.ToString(format, CultureInfo.InvariantCulture);
        }
        foreach (var (toggle, get) in _toggles)
        {
            toggle.SetPressedNoSignal(get(settings));
        }
        Visible = true;
        ShowPage(0);
        _tabs[0].GrabFocus();
    }

    /// <summary>Saves the settings and closes.</summary>
    public void Close()
    {
        if (!Visible)
        {
            return;
        }
        _settings?.Save();
        Visible = false;
        Closed?.Invoke();
    }

    /// <summary>Shows one tab: 0 Controls, 1 Video, 2 Audio.</summary>
    public void ShowPage(int page)
    {
        for (var i = 0; i < _pages.Length; i++)
        {
            _pages[i].Visible = i == page;
            _tabs[i].SetPressedNoSignal(i == page);
        }
    }

    /// <inheritdoc/>
    public override void _Input(InputEvent e)
    {
        if (Visible && e.IsActionPressed("ui_cancel"))
        {
            Close();
            GetViewport().SetInputAsHandled();
        }
    }

    private void Slider(string name, SettingRange range, string format, Func<GameSettings, float> get, Action<GameSettings, float> set)
    {
        var slider = GetNode<HSlider>($"%{name}");
        var value = GetNode<Label>($"%{name}Value");
        slider.MinValue = range.Min;
        slider.MaxValue = range.Max;
        slider.Step = range.Step;
        slider.ValueChanged += v =>
        {
            if (_settings is not null)
            {
                set(_settings, (float)v);
            }
            value.Text = v.ToString(format, CultureInfo.InvariantCulture);
        };
        _sliders.Add((slider, value, format, get));
    }

    private void Toggle(string name, Func<GameSettings, bool> get, Action<GameSettings, bool> set)
    {
        var toggle = GetNode<CheckButton>($"%{name}");
        toggle.Toggled += v =>
        {
            if (_settings is not null)
            {
                set(_settings, v);
            }
        };
        _toggles.Add((toggle, get));
    }
}
