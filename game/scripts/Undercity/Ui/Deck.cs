// The wrist-deck (deck.tscn), after the approved F6 mockup: the frame, the Inventory, Skills and
// Journal tabs, and the header with credits, level, XP and unspent points.
//
// It lives in the UI layer as a thin view: it switches tabs and prints the header from the state;
// each tab's page binds its own part of the state (CLAUDE.md 6.2, 6.3).

#nullable enable
using System;
using Godot;

namespace Undercity.Client;

/// <summary>The deck.</summary>
public partial class Deck : Control, IWired
{
    private Services? _services;
    private Button _tabInventory = null!;
    private Button _tabSkills = null!;
    private Button _tabJournal = null!;
    private InventoryPage _inventory = null!;
    private SkillsPage _skills = null!;
    private JournalPage _journal = null!;
    private Label _credits = null!;
    private Label _level = null!;
    private Label _xp = null!;
    private Label _points = null!;

    /// <summary>Raised when the deck closes.</summary>
    public event Action? Closed;

    /// <summary>The tab showing.</summary>
    public DeckTab Tab { get; private set; }

    /// <inheritdoc/>
    public override void _Ready()
    {
        _tabInventory = GetNode<Button>("%TabInventory");
        _tabSkills = GetNode<Button>("%TabSkills");
        _tabJournal = GetNode<Button>("%TabJournal");
        _inventory = GetNode<InventoryPage>("%Inventory");
        _skills = GetNode<SkillsPage>("%Skills");
        _journal = GetNode<JournalPage>("%Journal");
        _credits = GetNode<Label>("%Credits");
        _level = GetNode<Label>("%Level");
        _xp = GetNode<Label>("%Xp");
        _points = GetNode<Label>("%Points");
        _tabInventory.Pressed += () => ShowTab(DeckTab.Inventory);
        _tabSkills.Pressed += () => ShowTab(DeckTab.Skills);
        _tabJournal.Pressed += () => ShowTab(DeckTab.Journal);
        ShowTab(DeckTab.Inventory);
    }

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _services = services;
        _inventory.Wire(services);
        _skills.Wire(services);
        _journal.Wire(services);
        services.State.Inventory.Changed += RefreshHeader;
        services.State.Character.Changed += RefreshHeader;
        RefreshHeader();
    }

    /// <inheritdoc/>
    public override void _ExitTree()
    {
        if (_services is not null)
        {
            _services.State.Inventory.Changed -= RefreshHeader;
            _services.State.Character.Changed -= RefreshHeader;
        }
    }

    /// <summary>Opens the deck on <paramref name="tab"/>, or switches to it when already open.</summary>
    public void Open(DeckTab tab)
    {
        ShowTab(tab);
        Show();
    }

    /// <summary>Closes the deck.</summary>
    public void Close()
    {
        if (!Visible)
        {
            return;
        }
        Hide();
        Closed?.Invoke();
    }

    /// <summary>Shows a tab's page.</summary>
    public void ShowTab(DeckTab tab)
    {
        Tab = tab;
        _inventory.Visible = tab == DeckTab.Inventory;
        _skills.Visible = tab == DeckTab.Skills;
        _journal.Visible = tab == DeckTab.Journal;
        _tabInventory.SetPressedNoSignal(tab == DeckTab.Inventory);
        _tabSkills.SetPressedNoSignal(tab == DeckTab.Skills);
        _tabJournal.SetPressedNoSignal(tab == DeckTab.Journal);
    }

    /// <inheritdoc/>
    public override void _UnhandledInput(InputEvent e)
    {
        if (!Visible || e is not InputEventKey { Pressed: true, Echo: false } k)
        {
            return;
        }
        DeckTab? tab = k.PhysicalKeycode switch
        {
            Key.F1 => DeckTab.Inventory,
            Key.F2 => DeckTab.Skills,
            Key.F3 => DeckTab.Journal,
            _ => null,
        };
        if (tab is { } t)
        {
            ShowTab(t);
            GetViewport().SetInputAsHandled();
        }
    }

    private void RefreshHeader()
    {
        if (_services is null)
        {
            return;
        }
        var c = _services.State.Character;
        _credits.Text = UiText.Invariant($"{_services.State.Inventory.Credits}");
        _level.Text = UiText.Invariant($"{c.Level}");
        _xp.Text = c.XpToNext > 0 ? UiText.Invariant($"{c.Xp} / {c.XpToNext}") : "MAX";
        _points.Text = UiText.Invariant($"{c.SkillPoints}");
    }
}
