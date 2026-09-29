// The pause menu (pause.tscn, approved mockup D6): Resume, Save, Load, Options, Quit to title and
// Quit game on the left; where the runner is, the current objective and the save slots on the
// right. The game is paused under it (Screens pauses the tree), so this node always processes.
//
// It lives in the UI layer as a thin view: whether a save is allowed and why not, which slots the
// player may write, the objective shown and when quitting asks first are all core rules, reached
// through the level and the data (CLAUDE.md 5.1, 6.2). The greyed button and the refused save
// read the same rule.

#nullable enable
using System;
using System.Linq;
using Godot;
using Undercity.Core;

namespace Undercity.Client;

/// <summary>The pause menu.</summary>
public partial class PauseScreen : Control, IWired
{
    private enum Mode
    {
        Save,
        Load,
    }

    private Services? _services;
    private Button _resume = null!;
    private Button _quitTitle = null!;
    private Button _quitGame = null!;
    private Label _place = null!;
    private Label _placeLine = null!;
    private Label _questTitle = null!;
    private Label _objective = null!;
    private SaveListView _list = null!;
    private Button _saveHere = null!;
    private Button _overwrite = null!;
    private Button _loadSlot = null!;
    private Label _status = null!;
    private Mode _mode;
    private bool _quitArmed;

    /// <summary>Raised when the menu closes (Resume or Esc).</summary>
    public event Action? Closed;

    /// <summary>Raised when the player asks for the options screen.</summary>
    public event Action? OptionsRequested;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _resume = GetNode<Button>("%ResumeItem");
        _quitTitle = GetNode<Button>("%QuitTitleItem");
        _quitGame = GetNode<Button>("%QuitGameItem");
        _place = GetNode<Label>("%Place");
        _placeLine = GetNode<Label>("%PlaceLine");
        _questTitle = GetNode<Label>("%QuestTitle");
        _objective = GetNode<Label>("%ObjectiveText");
        _list = GetNode<SaveListView>("%SaveList");
        _saveHere = GetNode<Button>("%SaveHere");
        _overwrite = GetNode<Button>("%Overwrite");
        _loadSlot = GetNode<Button>("%LoadSlot");
        _status = GetNode<Label>("%Status");

        _resume.Pressed += Close;
        GetNode<Button>("%SaveItem").Pressed += () => SetMode(Mode.Save);
        GetNode<Button>("%LoadItem").Pressed += () => SetMode(Mode.Load);
        GetNode<Button>("%OptionsItem").Pressed += () => OptionsRequested?.Invoke();
        _quitTitle.Pressed += () => Quit(toTitle: true);
        _quitGame.Pressed += () => Quit(toTitle: false);
        _saveHere.Pressed += Save;
        _overwrite.Pressed += Save;
        _loadSlot.Pressed += Load;
        _list.SelectionChanged += () => Refresh(keepStatus: false);
    }

    /// <inheritdoc/>
    public void Wire(Services services) => _services = services;

    /// <summary>Opens the menu in save mode with Resume focused.</summary>
    public void Open()
    {
        _mode = Mode.Save;
        _quitArmed = false;
        _quitTitle.Text = "QUIT TO TITLE";
        _quitGame.Text = "QUIT GAME";
        _status.Text = "";
        Visible = true;
        Refresh(keepStatus: false);
        _resume.GrabFocus();
    }

    /// <summary>Closes the menu.</summary>
    public void Close()
    {
        if (!Visible)
        {
            return;
        }
        Visible = false;
        Closed?.Invoke();
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

    private void SetMode(Mode mode)
    {
        _mode = mode;
        Refresh(keepStatus: false);
    }

    /// <summary>Reads everything shown from the run, the level and the save folder.</summary>
    private void Refresh(bool keepStatus)
    {
        if (_services is null)
        {
            return;
        }
        var s = _services.State;
        _place.Text = UiText.Place(s.Data, _services.Level.Id);
        _placeLine.Text = UiText.Invariant($"{UiText.PlayTime(s.World.PlayTimeS)} · {s.Inventory.Credits} cr");
        var current = s.Quests.Current();
        _questTitle.Text = current?.Quest.Title ?? "";
        _objective.Text = current?.Objective?.Text ?? (current is null ? "No active contract." : "");

        _list.Show(_services.Saves, s.Data, _list.Selected?.Slot);
        var selected = _list.Selected;
        var refusal = _services.Level.SaveRefusal();
        var writable = selected is not null && s.Data.Saves.Writable(selected.Slot);
        _saveHere.Visible = _overwrite.Visible = _mode == Mode.Save;
        _loadSlot.Visible = _mode == Mode.Load;
        _saveHere.Disabled = refusal.Length > 0 || !writable || selected!.Exists;
        _overwrite.Disabled = refusal.Length > 0 || !writable || !selected!.Exists;
        _loadSlot.Disabled = selected is not { Loadable: true };
        if (!keepStatus)
        {
            _status.Text = _mode == Mode.Save ? refusal : "";
        }
    }

    private void Save()
    {
        if (_services is null || _list.Selected is not { } selected)
        {
            return;
        }
        _status.Text = _services.Level.TrySave(selected.Slot, out var reason)
            ? $"Saved: {UiText.Slot(selected.Slot)}."
            : reason;
        Refresh(keepStatus: true);
    }

    private void Load()
    {
        if (_services is null || _list.Selected is not { Loadable: true } selected)
        {
            return;
        }
        if (!_services.Shell.Load(selected.Slot))
        {
            _status.Text = $"{UiText.Slot(selected.Slot)} can't be loaded.";
        }
    }

    /// <summary>Quitting asks once when the newest save is older than the data's limit (SavesTable.WarnBeforeQuit).</summary>
    private void Quit(bool toTitle)
    {
        if (_services is null)
        {
            return;
        }
        var newest = _services.Saves.List().FirstOrDefault()?.WrittenUtc;
        var now = DateTime.UtcNow;
        if (!_quitArmed && _services.Data.Saves.WarnBeforeQuit(newest, now))
        {
            _quitArmed = true;
            (toTitle ? _quitTitle : _quitGame).Text = "QUIT ANYWAY";
            _status.Text = newest is { } t
                ? UiText.Invariant($"Last save {(int)(now - t).TotalMinutes} m ago.")
                : "No save yet.";
            return;
        }
        if (toTitle)
        {
            _services.Shell.ToTitle();
        }
        else
        {
            _services.Shell.Quit();
        }
    }
}
