using Godot;

namespace Brushfire;

/// <summary>Shared look for all menus and the HUD: dark steel panels with a molten-orange accent.</summary>
public static class UiTheme
{
    public static readonly Color Accent = new(1f, 0.62f, 0.18f);
    public static readonly Color AccentDim = new(0.75f, 0.42f, 0.1f);
    public static readonly Color Text = new(0.92f, 0.9f, 0.86f);
    public static readonly Color TextDim = new(0.62f, 0.6f, 0.57f);
    public static readonly Color Panel = new(0.07f, 0.075f, 0.08f, 0.92f);
    public static readonly Color Danger = new(0.95f, 0.22f, 0.15f);

    static Theme _theme;
    static Font _font;

    public static Font Font => _font ??= MakeFont();

    static Font MakeFont()
    {
        var f = new SystemFont
        {
            FontNames = new[] { "Impact", "Haettenschweiler", "Oswald", "DejaVu Sans Condensed", "Liberation Sans Narrow", "Arial Narrow", "sans-serif" },
            FontWeight = 700,
            Antialiasing = TextServer.FontAntialiasing.Gray,
        };
        return f;
    }

    public static Theme Get()
    {
        if (_theme != null)
            return _theme;
        var t = new Theme { DefaultFont = Font, DefaultFontSize = 26 };

        StyleBoxFlat Box(Color bg, Color border, int borderWidth = 2)
        {
            var sb = new StyleBoxFlat
            {
                BgColor = bg,
                BorderColor = border,
                ContentMarginLeft = 22, ContentMarginRight = 22, ContentMarginTop = 10, ContentMarginBottom = 10,
            };
            sb.SetBorderWidthAll(borderWidth);
            sb.SetCornerRadiusAll(2);
            return sb;
        }

        t.SetStylebox("normal", "Button", Box(new Color(0.12f, 0.12f, 0.13f, 0.95f), new Color(0.3f, 0.3f, 0.32f)));
        t.SetStylebox("hover", "Button", Box(new Color(0.2f, 0.14f, 0.08f, 0.95f), Accent));
        t.SetStylebox("pressed", "Button", Box(new Color(0.35f, 0.2f, 0.06f, 0.95f), Accent));
        t.SetStylebox("focus", "Button", Box(new Color(0, 0, 0, 0), Accent, 3));
        t.SetStylebox("disabled", "Button", Box(new Color(0.08f, 0.08f, 0.08f, 0.8f), new Color(0.2f, 0.2f, 0.2f)));
        t.SetColor("font_color", "Button", Text);
        t.SetColor("font_hover_color", "Button", Accent);
        t.SetColor("font_pressed_color", "Button", Colors.White);
        t.SetColor("font_focus_color", "Button", Accent);
        t.SetFontSize("font_size", "Button", 28);

        t.SetStylebox("panel", "PanelContainer", Box(Panel, new Color(0.25f, 0.25f, 0.27f)));
        t.SetColor("font_color", "Label", Text);
        t.SetColor("font_outline_color", "Label", new Color(0, 0, 0, 0.9f));
        t.SetConstant("outline_size", "Label", 6);

        var grabber = new StyleBoxFlat { BgColor = Accent };
        grabber.SetCornerRadiusAll(2);
        t.SetStylebox("slider", "HSlider", new StyleBoxFlat { BgColor = new Color(0.2f, 0.2f, 0.22f), ContentMarginTop = 4, ContentMarginBottom = 4 });
        t.SetStylebox("grabber_area", "HSlider", new StyleBoxFlat { BgColor = AccentDim, ContentMarginTop = 4, ContentMarginBottom = 4 });
        t.SetStylebox("grabber_area_highlight", "HSlider", new StyleBoxFlat { BgColor = Accent, ContentMarginTop = 4, ContentMarginBottom = 4 });
        t.SetColor("font_color", "CheckButton", Text);
        t.SetColor("font_hover_color", "CheckButton", Accent);
        t.SetFontSize("font_size", "CheckButton", 24);
        _theme = t;
        return t;
    }

    public static Label MakeLabel(string text, int size, Color? color = null, HorizontalAlignment align = HorizontalAlignment.Left)
    {
        var l = new Label { Text = text, HorizontalAlignment = align };
        l.AddThemeFontSizeOverride("font_size", size);
        l.AddThemeColorOverride("font_color", color ?? Text);
        l.AddThemeConstantOverride("outline_size", Mathf.Max(4, size / 8));
        l.AddThemeColorOverride("font_outline_color", new Color(0, 0, 0, 0.85f));
        return l;
    }

    public static Button MakeButton(string text, System.Action onPressed, int minWidth = 360)
    {
        var b = new Button { Text = text, CustomMinimumSize = new Vector2(minWidth, 60), FocusMode = Control.FocusModeEnum.All };
        b.Pressed += () =>
        {
            Audio.Play2D(b, "ui_click", -6f, 0f);
            onPressed();
        };
        b.MouseEntered += () => Audio.Play2D(b, "ui_hover", -14f, 0f);
        return b;
    }
}
