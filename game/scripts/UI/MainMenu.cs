using Godot;

namespace Brushfire;

/// <summary>Title screen: pick one of the three levels (one per level-design tool), options, quit.</summary>
public partial class MainMenu : Control
{
    VBoxContainer _main;
    SettingsPanel _settings;

    public override void _Ready()
    {
        Theme = UiTheme.Get();
        SetAnchorsPreset(LayoutPreset.FullRect);
        Input.MouseMode = Input.MouseModeEnum.Visible;
        GetTree().Paused = false;

        var bg = new ColorRect { Material = new ShaderMaterial { Shader = new Shader { Code = BackgroundShader } } };
        bg.SetAnchorsPreset(LayoutPreset.FullRect);
        AddChild(bg);

        var margin = new MarginContainer();
        margin.SetAnchorsPreset(LayoutPreset.FullRect);
        foreach (var side in new[] { "left", "right" })
            margin.AddThemeConstantOverride("margin_" + side, 120);
        margin.AddThemeConstantOverride("margin_top", 90);
        margin.AddThemeConstantOverride("margin_bottom", 60);
        AddChild(margin);

        var columns = new HBoxContainer();
        columns.AddThemeConstantOverride("separation", 80);
        margin.AddChild(columns);

        _main = new VBoxContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill };
        _main.AddThemeConstantOverride("separation", 16);
        columns.AddChild(_main);

        _main.AddChild(UiTheme.MakeLabel("BRUSHFIRE", 132, UiTheme.Accent));
        _main.AddChild(UiTheme.MakeLabel("An old-school shooter, built three ways.", 30, UiTheme.TextDim));
        _main.AddChild(new Control { CustomMinimumSize = new Vector2(0, 30) });

        Button first = null;
        for (int i = 0; i < Game.Levels.Length; i++)
        {
            int index = i;
            var info = Game.Levels[i];
            var card = new VBoxContainer();
            card.AddThemeConstantOverride("separation", 2);
            var b = UiTheme.MakeButton($"{info.Title}", () => Game.Instance.StartLevel(index), 640);
            b.Alignment = HorizontalAlignment.Left;
            first ??= b;
            card.AddChild(b);
            var desc = UiTheme.MakeLabel($"Made with {info.Tool}. {info.Description}", 20, UiTheme.TextDim);
            desc.AutowrapMode = TextServer.AutowrapMode.WordSmart;
            desc.CustomMinimumSize = new Vector2(640, 0);
            card.AddChild(desc);
            _main.AddChild(card);
        }
        _main.AddChild(new Control { CustomMinimumSize = new Vector2(0, 16) });
        var row = new HBoxContainer();
        row.AddThemeConstantOverride("separation", 16);
        row.AddChild(UiTheme.MakeButton("OPTIONS", ShowSettings, 250));
        row.AddChild(UiTheme.MakeButton("QUIT", () => GetTree().Quit(), 250));
        _main.AddChild(row);

        var help = UiTheme.MakeLabel(
            "WASD move   MOUSE look   SPACE jump   CTRL crouch   SHIFT sprint\n" +
            "LMB fire   1-3 / wheel weapons   F flashlight   ESC pause   F11 fullscreen",
            20, UiTheme.TextDim);
        help.SizeFlagsVertical = SizeFlags.ExpandFill;
        help.VerticalAlignment = VerticalAlignment.Bottom;
        _main.AddChild(help);

        var right = new CenterContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill };
        columns.AddChild(right);
        _settings = new SettingsPanel { Visible = false };
        _settings.Closed += () =>
        {
            _settings.Visible = false;
            first?.GrabFocus();
        };
        right.AddChild(_settings);
        first?.CallDeferred(Control.MethodName.GrabFocus);
    }

    void ShowSettings() => _settings.Visible = !_settings.Visible;

    const string BackgroundShader = @"
shader_type canvas_item;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
void fragment() {
    vec2 uv = UV;
    float t = TIME * 0.05;
    float n = noise(uv * 3.0 + vec2(t, -t * 2.0)) * 0.6 + noise(uv * 9.0 - vec2(0.0, t * 6.0)) * 0.4;
    float glow = smoothstep(0.3, 1.0, uv.y) * (0.6 + 0.4 * n);
    vec3 col = mix(vec3(0.03, 0.03, 0.035), vec3(0.35, 0.12, 0.02), glow * 0.55);
    // embers
    vec2 g = uv * vec2(60.0, 34.0) + vec2(0.0, TIME * 1.5);
    float e = step(0.985, hash(floor(g))) * smoothstep(0.5, 0.0, length(fract(g) - 0.5));
    col += vec3(1.0, 0.5, 0.1) * e * smoothstep(0.1, 0.9, uv.y);
    // scanline grit
    col *= 0.92 + 0.08 * sin(uv.y * 900.0);
    COLOR = vec4(col, 1.0);
}";
}
