// The Undercity UI (screens.tscn): a CanvasLayer holding the HUD, the deck, the dialog screen,
// the terminal screen, the pause menu and options, and the one IScreens the level talks to.
//
// It lives in the UI layer as the screens' composition point: the level instances this scene and
// calls Wire once; this passes the services down and routes IScreens calls to the right screen.
// Only the pause menu pauses the tree (the deck is part of play); the pause and options screens
// process while paused, and everything else reads Blocking to stop the player's input.

#nullable enable
using Godot;
using Undercity.Core.Dialog;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>The UI layer.</summary>
public partial class Screens : CanvasLayer, IScreens, IWired
{
    private const string DeckAction = "deck";

    private UndercityHud _hud = null!;
    private Deck _deck = null!;
    private DialogScreen _dialog = null!;
    private TerminalScreen _terminal = null!;
    private PauseScreen _pause = null!;
    private OptionsScreen _options = null!;
    private Services? _services;
    private bool _wasBlocking;

    /// <inheritdoc/>
    public bool Blocking => _deck.Visible || _dialog.Visible || _terminal.Visible || _pause.Visible || _options.Visible;

    /// <inheritdoc/>
    public bool InConversation => _dialog.Visible;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _hud = GetNode<UndercityHud>("%Hud");
        _deck = GetNode<Deck>("%Deck");
        _dialog = GetNode<DialogScreen>("%Dialog");
        _terminal = GetNode<TerminalScreen>("%Terminal");
        _pause = GetNode<PauseScreen>("%Pause");
        _options = GetNode<OptionsScreen>("%Options");
        _deck.Closed += OnScreenChanged;
        _dialog.Closed += OnScreenChanged;
        _terminal.Closed += OnScreenChanged;
        _pause.Closed += () =>
        {
            _options.Close();
            GetTree().Paused = false;
            OnScreenChanged();
        };
        _pause.OptionsRequested += () =>
        {
            if (_services is not null)
            {
                _options.Open(_services.Shell.Settings);
            }
        };
        _options.Closed += OnScreenChanged;
        if (!InputMap.HasAction(DeckAction))
        {
            GD.PushWarning($"[Undercity] no '{DeckAction}' input action in project.godot: the deck can't be opened by key");
        }
    }

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _services = services;
        _pause.Wire(services);
        _hud.Wire(services);
        _deck.Wire(services);
        _dialog.Wire(services);
        _terminal.Wire(services);
    }

    /// <inheritdoc/>
    public override void _Input(InputEvent e)
    {
        if (InputMap.HasAction(DeckAction) && e.IsActionPressed(DeckAction))
        {
            if (_deck.Visible)
            {
                CloseAll();
            }
            else if (!Blocking)
            {
                OpenDeck(_deck.Tab);
            }
            GetViewport().SetInputAsHandled();
        }
        else if (Blocking && e.IsActionPressed("ui_cancel"))
        {
            CloseAll();
            GetViewport().SetInputAsHandled();
        }
        else if (!Blocking && e.IsActionPressed("pause"))
        {
            OpenPause();
            GetViewport().SetInputAsHandled();
        }
    }

    /// <inheritdoc/>
    public void OpenPause()
    {
        CloseAll();
        _pause.Open();
        GetTree().Paused = true;
        OnScreenChanged();
    }

    /// <inheritdoc/>
    public void OpenDialog(DialogSession session, SpeakerView speaker)
    {
        CloseAll();
        _dialog.Open(session, speaker);
        OnScreenChanged();
    }

    /// <inheritdoc/>
    public void OpenTerminal(string stableId, TerminalDef terminal)
    {
        CloseAll();
        _terminal.Open(stableId, terminal);
        OnScreenChanged();
    }

    /// <inheritdoc/>
    public void OpenDeck(DeckTab tab)
    {
        if (!_deck.Visible)
        {
            CloseAll();
        }
        _deck.Open(tab);
        OnScreenChanged();
    }

    /// <inheritdoc/>
    public void CloseAll()
    {
        _deck.Close();
        _dialog.Close();
        _terminal.Close();
        _options.Close();
        _pause.Close();
        OnScreenChanged();
    }

    /// <inheritdoc/>
    public void ShowPrompt(string text, bool enabled) => _hud.ShowPrompt(text, enabled);

    /// <inheritdoc/>
    public void ShowHold(double progress) => _hud.ShowHold(progress);

    /// <inheritdoc/>
    public void Bark(string speaker, string line) => _hud.Bark(speaker, line);

    /// <inheritdoc/>
    public void ShowDisguise(DisguiseView? view) => _hud.ShowDisguise(view);

    /// <inheritdoc/>
    public void ShowAlert(string text) => _hud.ShowAlert(text);

    /// <inheritdoc/>
    public void ShowHitMarker(bool killed) => _hud.ShowHitMarker(killed);

    /// <inheritdoc/>
    public void FadeToBlack(double seconds) => _hud.FadeToBlack(seconds);

    // The mouse is free while a screen is open, and captured again when the last one closes.
    private void OnScreenChanged()
    {
        var blocking = Blocking;
        _hud.SetMode(_dialog.Visible ? HudMode.FeedOnly : blocking ? HudMode.Hidden : HudMode.Full);
        if (blocking)
        {
            Input.MouseMode = Input.MouseModeEnum.Visible;
        }
        else if (_wasBlocking)
        {
            Input.MouseMode = Input.MouseModeEnum.Captured;
        }
        _wasBlocking = blocking;
    }
}
