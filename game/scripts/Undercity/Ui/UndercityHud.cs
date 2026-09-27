// The Undercity HUD (hud.tscn), after the approved F11 mockup: the compass, the objective, the
// vitals with the disguise chip, the belt, the weapon line, the feed, barks, the law alert, and
// the crosshair with its prompt and hold bar.
//
// It lives in the UI layer as a thin view: health, the belt, the drawn weapon, quests and the
// feed come from the game state's own values and events; the prompt, hold, disguise, bark and
// alert come from the level through IScreens (CLAUDE.md 6.2). Named UndercityHud so it doesn't
// clash with Brushfire's Hud, which this doesn't extend (CLAUDE.md 13).

#nullable enable
using System;
using System.Linq;
using Godot;
using Undercity.Core;
using Undercity.Core.Perception;
using Undercity.Core.Quests;

namespace Undercity.Client;

/// <summary>What the HUD shows while a screen is open.</summary>
public enum HudMode
{
    /// <summary>Everything: nothing else is open.</summary>
    Full,

    /// <summary>Only the feed, beside a conversation.</summary>
    FeedOnly,

    /// <summary>Nothing, under the deck or a terminal.</summary>
    Hidden,
}

/// <summary>The HUD.</summary>
public partial class UndercityHud : Control, IWired
{
    /// <summary>The feed line scene.</summary>
    [Export] public PackedScene FeedLineScene { get; set; } = null!;

    /// <summary>Feed lines shown at most; the oldest goes first.</summary>
    [Export] public int FeedMax { get; set; } = 6;

    /// <summary>Seconds a bark subtitle stays.</summary>
    [Export] public double BarkS { get; set; } = 4.0;

    /// <summary>Seconds a law alert stays unless the level clears it first.</summary>
    [Export] public double AlertS { get; set; } = 6.0;

    private Services? _services;
    private Control _compass = null!;
    private CompassStrip _strip = null!;
    private Label _alert = null!;
    private Control _objective = null!;
    private Label _questTitle = null!;
    private Label _objectiveText = null!;
    private Label _prompt = null!;
    private ProgressBar _hold = null!;
    private VBoxContainer _feed = null!;
    private Label _bark = null!;
    private Label _health = null!;
    private Label _healthMax = null!;
    private ProgressBar _healthBar = null!;
    private PanelContainer _chip = null!;
    private Label _chipMain = null!;
    private Label _chipSub = null!;
    private BeltSlotView[] _belt = Array.Empty<BeltSlotView>();
    private Label _weapon = null!;
    private double _barkLeftS;
    private double _alertLeftS;
    private Control _frame = null!;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _frame = GetNode<Control>("%Frame");
        _compass = GetNode<Control>("%Compass");
        _strip = GetNode<CompassStrip>("%Strip");
        _alert = GetNode<Label>("%Alert");
        _objective = GetNode<Control>("%Objective");
        _questTitle = GetNode<Label>("%QuestTitle");
        _objectiveText = GetNode<Label>("%ObjectiveText");
        _prompt = GetNode<Label>("%Prompt");
        _hold = GetNode<ProgressBar>("%Hold");
        _feed = GetNode<VBoxContainer>("%Feed");
        _bark = GetNode<Label>("%Bark");
        _health = GetNode<Label>("%Health");
        _healthMax = GetNode<Label>("%HealthMax");
        _healthBar = GetNode<ProgressBar>("%HealthBar");
        _chip = GetNode<PanelContainer>("%Chip");
        _chipMain = GetNode<Label>("%ChipMain");
        _chipSub = GetNode<Label>("%ChipSub");
        _belt = GetNode<Control>("%Belt").GetChildren().OfType<BeltSlotView>().ToArray();
        _weapon = GetNode<Label>("%Weapon");
        ShowPrompt("", false);
        ShowHold(-1);
        ShowDisguise(null);
        ShowAlert("");
        _bark.Visible = false;
    }

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _services = services;
        var s = services.State;
        s.Feed += OnFeed;
        s.LoadoutChanged += RefreshKit;
        s.Inventory.Changed += RefreshKit;
        s.Health.Changed += RefreshHealth;
        s.Character.Changed += RefreshHealth;
        s.Quests.Updated += OnQuestUpdated;
        RefreshKit();
        RefreshHealth();
        RefreshObjective();
    }

    /// <inheritdoc/>
    public override void _ExitTree()
    {
        if (_services is null)
        {
            return;
        }
        var s = _services.State;
        s.Feed -= OnFeed;
        s.LoadoutChanged -= RefreshKit;
        s.Inventory.Changed -= RefreshKit;
        s.Health.Changed -= RefreshHealth;
        s.Character.Changed -= RefreshHealth;
        s.Quests.Updated -= OnQuestUpdated;
    }

    /// <summary>Shows all of the HUD, only the feed, or nothing, as the open screen needs.</summary>
    public void SetMode(HudMode mode)
    {
        _frame.Visible = mode == HudMode.Full;
        _feed.Visible = mode != HudMode.Hidden;
    }

    /// <inheritdoc/>
    public override void _Process(double delta)
    {
        if (_services?.Level.Player is { } player && IsInstanceValid(player))
        {
            // Godot's yaw is 0 facing -Z (north) and grows turning left; a compass heading grows turning right.
            _strip.Face(Mathf.PosMod(-Mathf.RadToDeg(player.Yaw), 360f), _compass.Size.X);
        }
        if (_barkLeftS > 0 && (_barkLeftS -= delta) <= 0)
        {
            _bark.Visible = false;
        }
        if (_alertLeftS > 0 && (_alertLeftS -= delta) <= 0)
        {
            _alert.Visible = false;
        }
    }

    // ------------------------------------------------------------------ what the level drives (IScreens)

    /// <summary>The prompt under the crosshair: accent when it can be done, greyed when not; empty hides it.</summary>
    public void ShowPrompt(string text, bool enabled)
    {
        _prompt.Text = text;
        _prompt.Visible = text.Length > 0;
        _prompt.AddThemeColorOverride("font_color", GetThemeColor(enabled ? "accent" : "disabled", "Palette"));
    }

    /// <summary>The hold bar, 0 to 1; negative hides it.</summary>
    public void ShowHold(double progress)
    {
        _hold.Value = Math.Clamp(progress, 0, 1);
        _hold.Visible = progress >= 0;
    }

    /// <summary>A subtitle above the belt for <see cref="BarkS"/> seconds.</summary>
    public void Bark(string speaker, string line)
    {
        _bark.Text = speaker.Length > 0 ? $"{speaker}: \"{line}\"" : line;
        _bark.Visible = true;
        _barkLeftS = BarkS;
    }

    /// <summary>The law warning under the compass; empty hides it.</summary>
    public void ShowAlert(string text)
    {
        _alert.Text = text;
        _alert.Visible = text.Length > 0;
        _alertLeftS = text.Length > 0 ? AlertS : 0;
    }

    /// <summary>The disguise chip, coloured by the verdict; null hides it.</summary>
    public void ShowDisguise(DisguiseView? view)
    {
        _chip.Visible = view is not null;
        if (view is null)
        {
            return;
        }
        var j = view.Judgement;
        _chipMain.Text = UiText.Invariant($"{view.Faction.ToUpperInvariant()}  Q {j.Quality}  COVER {j.Cover}");
        _chipSub.Text = view.Observer.Length > 0
            ? UiText.Invariant($"vs I {view.Intelligence} · {view.Observer} · {view.DistanceM:0} m")
            : j.Reason;
        var (style, role) = VerdictStyle(j.Verdict);
        _chip.ThemeTypeVariation = style;
        var colour = GetThemeColor(role, "Palette");
        _chipMain.AddThemeColorOverride("font_color", colour);
        _chipSub.AddThemeColorOverride("font_color", colour);
    }

    /// <summary>The chip style and colour role for a verdict: ok accepted, tech suspicious, danger blown.</summary>
    public static (string Style, string Role) VerdictStyle(Verdict verdict) => verdict switch
    {
        Verdict.Accepted => ("ChipOk", "ok"),
        Verdict.Suspicious => ("ChipTech", "tech"),
        Verdict.Blown => ("ChipDanger", "danger"),
        _ => ("ChipNone", "text_dim"),
    };

    // ------------------------------------------------------------------ what the state drives

    private void OnFeed(string line)
    {
        if (!IsInsideTree())
        {
            return;
        }
        var feedLine = FeedLineScene.Instantiate<FeedLine>();
        feedLine.Text = line;
        _feed.AddChild(feedLine);
        var lines = _feed.GetChildren();
        for (var i = 0; i < lines.Count - FeedMax; i++)
        {
            lines[i].QueueFree();
            _feed.RemoveChild(lines[i]);
        }
    }

    private void OnQuestUpdated(QuestDef quest, string line) => RefreshObjective();

    private void RefreshHealth()
    {
        if (_services is null)
        {
            return;
        }
        var h = _services.State.Health;
        _health.Text = UiText.Invariant($"{Math.Ceiling(h.Value):0}");
        _healthMax.Text = UiText.Invariant($"/ {h.Max:0}");
        _healthBar.MaxValue = h.Max;
        _healthBar.Value = h.Value;
    }

    private void RefreshObjective()
    {
        if (_services is null)
        {
            return;
        }
        var log = _services.State.Quests;
        var quest = log.Active.FirstOrDefault();
        var objective = quest?.Objectives.FirstOrDefault(o => log.IsVisible(quest.Id, o) && !log.IsDone($"{quest.Id}/{o.Id}"));
        _questTitle.Text = quest?.Title ?? "";
        _objectiveText.Text = objective?.Text ?? "";
        _objective.Visible = quest is not null;
    }

    private void RefreshKit()
    {
        if (_services is null)
        {
            return;
        }
        var s = _services.State;
        for (var i = 0; i < _belt.Length; i++)
        {
            var id = i < s.Inventory.Belt.Count ? s.Inventory.Belt[i] : null;
            var def = id is null ? null : s.Data.Items.Get(id);
            _belt[i].Bind(i, def, id is null ? 0 : s.Inventory.Pack.Count(id), id is not null && id == s.Drawn);
        }
        if (s.Drawn is { } drawn)
        {
            _weapon.Text = $"{s.Data.Items.Get(drawn).Name.ToUpperInvariant()} · DRAWN";
            _weapon.AddThemeColorOverride("font_color", GetThemeColor("text", "Palette"));
        }
        else
        {
            _weapon.Text = "HOLSTERED";
            _weapon.AddThemeColorOverride("font_color", GetThemeColor("text_dim", "Palette"));
        }
    }
}
