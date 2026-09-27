// The terminal screen (terminal_screen.tscn): a logged-in terminal's messages and actions, styled
// as a variant of the approved deck and dialog screens (no mockup of its own).
//
// It lives in the UI layer as a thin view: pages come from the level's TerminalDef, and an action
// runs its effects through GameState.Apply with a stable source id, so its XP pays once.

#nullable enable
using System;
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>The terminal screen.</summary>
public partial class TerminalScreen : Control, IWired
{
    /// <summary>One message in the list (page_row.tscn).</summary>
    [Export] public PackedScene PageRowScene { get; set; } = null!;

    /// <summary>One action button (terminal_action.tscn).</summary>
    [Export] public PackedScene ActionScene { get; set; } = null!;

    private Services? _services;
    private Label _title = null!;
    private VBoxContainer _pages = null!;
    private Label _pagesEmpty = null!;
    private Control _page = null!;
    private Label _subject = null!;
    private Label _from = null!;
    private Label _body = null!;
    private ScrollContainer _bodyScroll = null!;
    private Control _actionBar = null!;
    private HBoxContainer _actions = null!;
    private string _stableId = "";
    private TerminalDef? _terminal;
    private int _selected;

    /// <summary>Raised when the terminal closes.</summary>
    public event Action? Closed;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _title = GetNode<Label>("%Title");
        _pages = GetNode<VBoxContainer>("%PageRows");
        _pagesEmpty = GetNode<Label>("%PagesEmpty");
        _page = GetNode<Control>("%PageBody");
        _subject = GetNode<Label>("%Subject");
        _from = GetNode<Label>("%From");
        _body = GetNode<Label>("%Body");
        _bodyScroll = GetNode<ScrollContainer>("%BodyScroll");
        _actionBar = GetNode<Control>("%Actions");
        _actions = GetNode<HBoxContainer>("%ActionRow");
        GetNode<Button>("%Close").Pressed += Close;
    }

    /// <inheritdoc/>
    public void Wire(Services services) => _services = services;

    /// <summary>Shows <paramref name="terminal"/>, whose stable id is <paramref name="stableId"/>.</summary>
    public void Open(string stableId, TerminalDef terminal)
    {
        _stableId = stableId;
        _terminal = terminal;
        _selected = 0;
        _title.Text = terminal.Title;
        foreach (var old in _actions.GetChildren())
        {
            _actions.RemoveChild(old);
            old.QueueFree();
        }
        for (var i = 0; i < terminal.Actions.Count; i++)
        {
            var action = terminal.Actions[i];
            var index = i;
            var button = ActionScene.Instantiate<Button>();
            button.Text = action.Label;
            button.Pressed += () => Run(index);
            _actions.AddChild(button);
        }
        _actionBar.Visible = terminal.Actions.Count > 0;
        Show();
        ShowPages();
    }

    /// <summary>Closes the terminal.</summary>
    public void Close()
    {
        if (!Visible)
        {
            return;
        }
        Hide();
        _terminal = null;
        Closed?.Invoke();
    }

    private void Run(int index)
    {
        if (_services is null || _terminal is null || index >= _terminal.Actions.Count)
        {
            return;
        }
        _services.State.Apply(_terminal.Actions[index].Do, $"{_stableId}:action:{index}");
    }

    private void Pick(int index)
    {
        _selected = index;
        Callable.From(ShowPages).CallDeferred();
    }

    private void ShowPages()
    {
        foreach (var old in _pages.GetChildren())
        {
            _pages.RemoveChild(old);
            old.QueueFree();
        }
        if (_terminal is null)
        {
            return;
        }
        var pages = _terminal.Pages;
        for (var i = 0; i < pages.Count; i++)
        {
            var row = PageRowScene.Instantiate<PageRowView>();
            _pages.AddChild(row);
            row.Bind(i, pages[i], i == _selected);
            row.Picked += Pick;
        }
        _pagesEmpty.Visible = pages.Count == 0;
        _page.Visible = _selected < pages.Count;
        if (_selected < pages.Count)
        {
            var page = pages[_selected];
            _subject.Text = page.Subject;
            _from.Text = page.From;
            _body.Text = page.Body;
            _bodyScroll.ScrollVertical = 0;
        }
    }
}
