// The UI size check (ui_size_test.tscn, CLAUDE.md 8): opens every screen on a staged run, writes
// an overlong string into every visible Label and Button, waits two frames, and checks that every
// panel kept its size and every pinned panel still has its pinned size. Prints PASS or FAIL per
// panel and quits with 1 on any failure.
//
//   flock /tmp/undercity-godot.lock timeout 600 godot --headless --path game res://ui/undercity/ui_size_test.tscn
//
// It lives beside the screens because it loads the real scenes and the real theme: it checks the
// artifact, not a copy of its sizes (CLAUDE.md 5.6).

#nullable enable
using System;
using System.Linq;
using System.Threading.Tasks;
using Godot;

namespace Undercity.Client;

/// <summary>The headless panel-size check.</summary>
public partial class UiSizeTest : Node
{
    /// <summary>The UI under test.</summary>
    [Export] public PackedScene ScreensScene { get; set; } = null!;

    private static readonly string Overlong = string.Concat(Enumerable.Repeat("An overlong runtime string that must never resize a panel ", 8));

    private Screens _screens = null!;
    private int _pass;
    private int _fail;

    /// <inheritdoc/>
    public override async void _Ready()
    {
        try
        {
            await Run();
        }
        catch (Exception e)
        {
            GD.PrintErr($"FAIL [ui_size_test] {e}");
            GetTree().Quit(1);
        }
    }

    private async Task Run()
    {
        _screens = ScreensScene.Instantiate<Screens>();
        AddChild(_screens);
        var services = UiFixture.NewServices(_screens);
        _screens.Wire(services);
        UiFixture.Stage(services.State);
        for (var i = 0; i < 8; i++)
        {
            services.State.Say($"Feed line {i}: {Overlong}");
        }

        await Check("hud", () => UiFixture.StageHud(services));
        await Check("deck/inventory", () =>
        {
            _screens.OpenDeck(DeckTab.Inventory);
            Callable.From(SelectFirstItem).CallDeferred();
        });
        await Check("deck/skills", () => _screens.OpenDeck(DeckTab.Skills));
        await Check("deck/journal", () => _screens.OpenDeck(DeckTab.Journal));
        await Check("dialog", () => _screens.OpenDialog(
            services.State.Talk(services.Data.Dialogs["tank"], new Undercity.Core.Dialog.Speaker("hub:tank", "tank")),
            new SpeakerView("Tank", "The Anchor's bouncer", null)));
        await Check("terminal", () => _screens.OpenTerminal("hub:capsule_terminal", UiFixture.BusyTerminal(services.Data)));

        GD.Print($"[ui_size_test] {_pass} passed, {_fail} failed");
        GetTree().Quit(_fail > 0 ? 1 : 0);
    }

    private void SelectFirstItem()
    {
        var tile = UiFixture.Descendants(_screens).OfType<PackItemView>().FirstOrDefault(t => t.IsVisibleInTree());
        tile?.EmitSignal(BaseButton.SignalName.Pressed);
    }

    private async Task Check(string screen, Action open)
    {
        open();
        await Frames(3);
        var panels = UiFixture.Descendants(_screens).OfType<Control>().Where(c => c.IsVisibleInTree() && IsPanel(c)).ToList();
        var before = panels.ToDictionary(p => p, p => p.Size);
        foreach (var label in UiFixture.Descendants(_screens).OfType<Label>().Where(l => l.IsVisibleInTree()))
        {
            label.Text = Overlong;
        }
        foreach (var button in UiFixture.Descendants(_screens).OfType<Button>().Where(b => b.IsVisibleInTree()))
        {
            button.Text = Overlong;
        }
        await Frames(2);
        foreach (var p in panels.Where(IsInstanceValid))
        {
            var path = _screens.GetPathTo(p);
            var pinned = IsPinned(p);
            var ok = p.Size == before[p] && (!pinned || p.Size == p.CustomMinimumSize);
            if (ok)
            {
                _pass++;
                GD.Print($"PASS {screen} {path} {Fmt(p.Size)}");
            }
            else
            {
                _fail++;
                GD.PrintErr($"FAIL {screen} {path}: was {Fmt(before[p])}, now {Fmt(p.Size)}" + (pinned ? $", pinned {Fmt(p.CustomMinimumSize)}" : ""));
            }
        }
        _screens.CloseAll();
        await Frames(1);
    }

    private static bool IsPanel(Control c) => c is Panel or PanelContainer || IsPinned(c);

    private static bool IsPinned(Control c) =>
        c.CustomMinimumSize.X > 0 && c.CustomMinimumSize.Y > 0 && c.CustomMinimumSize == c.CustomMaximumSize;

    private static string Fmt(Vector2 v) => UiText.Invariant($"{v.X:0}x{v.Y:0}");

    private async Task Frames(int n)
    {
        for (var i = 0; i < n; i++)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        }
    }
}
