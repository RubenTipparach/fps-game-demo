using System.Collections.Generic;
using Godot;

namespace Brushfire;

/// <summary>
/// In-game HUD, built in code: health/armor/ammo status bar, dynamic crosshair with hit
/// markers, damage vignette + direction indicator, pickup feed, centre messages, level stats.
/// </summary>
public partial class Hud : CanvasLayer
{
    PlayerController _player;
    Label _health, _armor, _ammo, _weaponName, _ammoList, _stats, _fps, _centerTitle, _centerSub;
    Control _center;
    VBoxContainer _feed;
    Crosshair _crosshair;
    ColorRect _vignette;
    ShaderMaterial _vignetteMat;
    DamageIndicator _indicator;
    float _damageFlash;
    float _centerTimer;
    float _healthPulse;
    readonly List<(Label label, float time)> _feedItems = new();

    public override void _Ready()
    {
        _player = GetParent<PlayerController>();
        var root = new Control { MouseFilter = Control.MouseFilterEnum.Ignore };
        root.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        root.Theme = UiTheme.Get();
        AddChild(root);

        // Damage vignette (full screen, shader driven).
        _vignetteMat = new ShaderMaterial { Shader = new Shader { Code = VignetteShader } };
        _vignette = new ColorRect { Material = _vignetteMat, MouseFilter = Control.MouseFilterEnum.Ignore };
        _vignette.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        root.AddChild(_vignette);

        _indicator = new DamageIndicator();
        _indicator.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        root.AddChild(_indicator);

        _crosshair = new Crosshair();
        _crosshair.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        root.AddChild(_crosshair);

        // Bottom status bar.
        var bar = new HBoxContainer { MouseFilter = Control.MouseFilterEnum.Ignore };
        bar.SetAnchorsPreset(Control.LayoutPreset.BottomWide);
        bar.OffsetTop = -150;
        bar.OffsetBottom = -24;
        bar.OffsetLeft = 48;
        bar.OffsetRight = -48;
        bar.AddThemeConstantOverride("separation", 64);
        root.AddChild(bar);

        _health = AddStat(bar, "HEALTH");
        _armor = AddStat(bar, "ARMOR");
        bar.AddChild(new Control { SizeFlagsHorizontal = Control.SizeFlags.ExpandFill, MouseFilter = Control.MouseFilterEnum.Ignore });
        var ammoBox = new VBoxContainer { MouseFilter = Control.MouseFilterEnum.Ignore, Alignment = BoxContainer.AlignmentMode.End };
        _weaponName = UiTheme.MakeLabel("", 24, UiTheme.TextDim, HorizontalAlignment.Right);
        _ammo = UiTheme.MakeLabel("0", 88, UiTheme.Accent, HorizontalAlignment.Right);
        ammoBox.AddChild(_weaponName);
        ammoBox.AddChild(_ammo);
        bar.AddChild(ammoBox);
        _ammoList = UiTheme.MakeLabel("", 20, UiTheme.TextDim, HorizontalAlignment.Right);
        _ammoList.VerticalAlignment = VerticalAlignment.Bottom;
        bar.AddChild(_ammoList);

        _stats = UiTheme.MakeLabel("", 22, UiTheme.TextDim, HorizontalAlignment.Right);
        _stats.SetAnchorsPreset(Control.LayoutPreset.TopRight);
        _stats.OffsetLeft = -420;
        _stats.OffsetRight = -32;
        _stats.OffsetTop = 24;
        root.AddChild(_stats);

        _fps = UiTheme.MakeLabel("", 18, UiTheme.TextDim);
        _fps.Position = new Vector2(24, 20);
        root.AddChild(_fps);

        _feed = new VBoxContainer { Position = new Vector2(32, 64), MouseFilter = Control.MouseFilterEnum.Ignore };
        root.AddChild(_feed);

        _center = new VBoxContainer { MouseFilter = Control.MouseFilterEnum.Ignore, Alignment = BoxContainer.AlignmentMode.Center };
        _center.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        _center.OffsetTop = -260;
        _centerTitle = UiTheme.MakeLabel("", 64, UiTheme.Accent, HorizontalAlignment.Center);
        _centerSub = UiTheme.MakeLabel("", 28, UiTheme.Text, HorizontalAlignment.Center);
        _center.AddChild(_centerTitle);
        _center.AddChild(_centerSub);
        _center.Modulate = new Color(1, 1, 1, 0);
        root.AddChild(_center);

        Events.Message += ShowPickup;
    }

    public override void _ExitTree() => Events.Message -= ShowPickup;

    static Label AddStat(Container parent, string caption)
    {
        var box = new VBoxContainer { MouseFilter = Control.MouseFilterEnum.Ignore, Alignment = BoxContainer.AlignmentMode.End };
        box.AddChild(UiTheme.MakeLabel(caption, 24, UiTheme.TextDim));
        var value = UiTheme.MakeLabel("100", 88);
        box.AddChild(value);
        parent.AddChild(box);
        return value;
    }

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        var w = _player.Weapons;
        int hp = Mathf.CeilToInt(_player.Health);
        _health.Text = hp.ToString();
        _healthPulse += dt * (hp <= 25 ? 6f : 0f);
        Color hc = hp <= 25 ? UiTheme.Danger.Lerp(UiTheme.Text, 0.5f + 0.5f * Mathf.Sin(_healthPulse)) : UiTheme.Text;
        _health.AddThemeColorOverride("font_color", hp > 100 ? new Color(0.5f, 0.8f, 1f) : hc);
        _armor.Text = Mathf.CeilToInt(_player.Armor).ToString();
        _armor.AddThemeColorOverride("font_color", _player.Armor > 0 ? new Color(0.55f, 0.85f, 0.55f) : UiTheme.TextDim);

        if (w.Current != null)
        {
            _weaponName.Text = w.Current.DisplayName.ToUpperInvariant();
            int ammo = w.GetAmmo(w.Current.Ammo);
            _ammo.Text = ammo.ToString();
            _ammo.AddThemeColorOverride("font_color", ammo == 0 ? UiTheme.Danger : UiTheme.Accent);
            _crosshair.Spread = w.Current.CurrentSpread;
        }
        _ammoList.Text = $"SHELLS {w.GetAmmo(AmmoType.Shells),3}\nBULLETS {w.GetAmmo(AmmoType.Bullets),3}\nROCKETS {w.GetAmmo(AmmoType.Rockets),3}";

        var s = Game.Instance.Stats;
        int secs = (int)s.Time;
        _stats.Text = $"KILLS {s.Kills}/{s.TotalEnemies}\nSECRETS {s.Secrets}/{s.TotalSecrets}\nTIME {secs / 60:00}:{secs % 60:00}";
        _fps.Visible = Game.Instance.Settings.ShowFps;
        if (_fps.Visible)
            _fps.Text = $"{Engine.GetFramesPerSecond()} FPS";

        _damageFlash = Mathf.Max(_damageFlash - dt * 1.8f, 0f);
        float lowHealth = _player.IsDead ? 0.8f : Mathf.Clamp((35f - _player.Health) / 35f, 0f, 1f) * 0.45f;
        _vignetteMat.SetShaderParameter("intensity", Mathf.Max(_damageFlash, lowHealth));

        if (_centerTimer > 0f)
        {
            _centerTimer -= dt;
            _center.Modulate = new Color(1, 1, 1, Mathf.Clamp(_centerTimer / 0.6f, 0f, 1f));
        }

        for (int i = _feedItems.Count - 1; i >= 0; i--)
        {
            var (label, time) = _feedItems[i];
            time -= dt;
            _feedItems[i] = (label, time);
            label.Modulate = new Color(1, 1, 1, Mathf.Clamp(time / 0.5f, 0f, 1f));
            if (time <= 0f)
            {
                label.QueueFree();
                _feedItems.RemoveAt(i);
            }
        }
        _crosshair.Visible = !_player.IsDead;
    }

    public void OnDamaged(DamageInfo info, PlayerController player)
    {
        _damageFlash = Mathf.Clamp(_damageFlash + info.Amount / 40f, 0.25f, 0.9f);
        if (info.Source != null && info.Source != player)
        {
            Vector3 to = info.Source.GlobalPosition - player.GlobalPosition;
            // Angle relative to view: 0 = in front, positive = to the right.
            float angle = Mathf.Atan2(to.X, -to.Z) + player.Yaw;
            _indicator.Show(angle);
        }
    }

    public void ShowHitMarker(bool kill)
    {
        _crosshair.Hit(kill);
        Audio.Play2D(this, kill ? "kill_marker" : "hit_marker", kill ? -6f : -12f, 0.05f);
    }

    public void ShowPickup(string text)
    {
        var l = UiTheme.MakeLabel(text, 26, UiTheme.Accent);
        _feed.AddChild(l);
        _feedItems.Add((l, 3f));
        if (_feedItems.Count > 5)
        {
            _feedItems[0].label.QueueFree();
            _feedItems.RemoveAt(0);
        }
    }

    public void ShowCenterMessage(string title, string subtitle, float duration = 999f)
    {
        _centerTitle.Text = title;
        _centerSub.Text = subtitle;
        _centerTimer = duration;
        _center.Modulate = Colors.White;
    }

    const string VignetteShader = @"
shader_type canvas_item;
uniform float intensity = 0.0;
void fragment() {
    vec2 p = UV * 2.0 - 1.0;
    float d = length(p * vec2(1.0, 0.8));
    float v = smoothstep(0.55, 1.35, d);
    COLOR = vec4(0.6, 0.02, 0.0, v * intensity);
}";
}
