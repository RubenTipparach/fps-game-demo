// The title screen (title.tscn, approved mockup D5), the game's main scene: Continue (the newest
// save, with where and how long), New game, Load, Options and Quit, over the city at night.
//
// It lives in the UI layer as a thin view: which save is newest and what it says come from
// SaveStore, and starting, loading and quitting are the application's (IShell), which the Game
// autoload hands over before _Ready (CLAUDE.md 5.3).

#nullable enable
using Godot;
using Undercity.Core;

namespace Undercity.Client;

/// <summary>The title screen.</summary>
public partial class TitleScreen : Control
{
    private IShell? _shell;
    private SaveStore? _saves;
    private GameData? _data;
    private Button _continue = null!;
    private Label _continueLine = null!;
    private Button _newGame = null!;
    private Button _load = null!;
    private Control _loadPanel = null!;
    private SaveListView _list = null!;
    private Button _loadSlot = null!;
    private OptionsScreen _options = null!;
    private SaveSummary? _newest;

    /// <summary>
    /// Called by the composition root as the screen enters the tree, before _Ready. The first call
    /// wins, so a UI check that hands over a stub before adding the screen keeps it.
    /// </summary>
    public void Begin(IShell shell, SaveStore saves, GameData data)
    {
        if (_shell is not null)
        {
            return;
        }
        _shell = shell;
        _saves = saves;
        _data = data;
    }

    /// <inheritdoc/>
    public override void _Ready()
    {
        _continue = GetNode<Button>("%ContinueItem");
        _continueLine = GetNode<Label>("%ContinueLine");
        _newGame = GetNode<Button>("%NewGameItem");
        _load = GetNode<Button>("%LoadItem");
        _loadPanel = GetNode<Control>("%LoadPanel");
        _list = GetNode<SaveListView>("%SaveList");
        _loadSlot = GetNode<Button>("%LoadSlot");
        _options = GetNode<OptionsScreen>("%Options");

        _continue.Pressed += () => Load(_newest?.Slot);
        _newGame.Pressed += () => _shell?.NewGame();
        _load.Pressed += OpenLoad;
        GetNode<Button>("%OptionsItem").Pressed += () =>
        {
            if (_shell is not null)
            {
                _options.Open(_shell.Settings);
            }
        };
        GetNode<Button>("%QuitItem").Pressed += () => _shell?.Quit();
        _loadSlot.Pressed += () => Load(_list.Selected?.Slot);
        GetNode<Button>("%LoadBack").Pressed += CloseLoad;
        _list.SelectionChanged += RefreshLoad;
        _options.Closed += () => FocusFirst();

        if (_shell is null)
        {
            GD.PushError("[Undercity] the title screen started without the shell; is the Game autoload missing?");
            return;
        }
        Input.MouseMode = Input.MouseModeEnum.Visible;
        Refresh();
    }

    /// <summary>Reads the save folder: Continue and Load show only when there is a save to load.</summary>
    public void Refresh()
    {
        if (_saves is null || _data is null)
        {
            return;
        }
        _newest = _saves.Newest();
        _continue.Visible = _load.Visible = _newest is not null;
        _continueLine.Text = _newest is null
            ? ""
            : $"{UiText.Slot(_newest.Slot)} · {UiText.Place(_data, _newest.LevelId)} · {UiText.PlayTime(_newest.PlayTimeS)}";
        FocusFirst();
    }

    /// <inheritdoc/>
    public override void _UnhandledInput(InputEvent e)
    {
        if (_loadPanel.Visible && e.IsActionPressed("ui_cancel"))
        {
            CloseLoad();
            GetViewport().SetInputAsHandled();
        }
    }

    private void FocusFirst() => (_continue.Visible ? _continue : _newGame).GrabFocus();

    private void OpenLoad()
    {
        if (_saves is null || _data is null)
        {
            return;
        }
        _list.Show(_saves, _data, _newest?.Slot);
        _loadPanel.Visible = true;
        RefreshLoad();
        _loadSlot.GrabFocus();
    }

    private void RefreshLoad() => _loadSlot.Disabled = _list.Selected is not { Loadable: true };

    private void CloseLoad()
    {
        _loadPanel.Visible = false;
        FocusFirst();
    }

    private void Load(string? slot)
    {
        if (slot is not null && _shell is not null && !_shell.Load(slot))
        {
            Refresh();
        }
    }
}
