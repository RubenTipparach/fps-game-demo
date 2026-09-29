// Screenshots of every Undercity screen (ui_capture.tscn) over a flat backdrop, on a staged run,
// for the owner to check against the approved mockups (CLAUDE.md 9). Needs a renderer, so run it
// under Xvfb with Vulkan (lavapipe in a cloud session), at 1920 x 1080:
//
//   Xvfb :97 -screen 0 1920x1080x24 &
//   DISPLAY=:97 flock /tmp/undercity-godot.lock timeout 600 godot --path game --resolution 1920x1080 res://ui/undercity/ui_capture.tscn
//
// Writes docs/screenshots/undercity_ui/<shot>.png. It lives beside the screens because it opens
// the real scenes with the real theme.

#nullable enable
using System;
using System.Linq;
using System.Threading.Tasks;
using Godot;
using Undercity.Core.Dialog;

namespace Undercity.Client;

/// <summary>The screenshot pass.</summary>
public partial class UiCapture : Node
{
    /// <summary>The UI to capture.</summary>
    [Export] public PackedScene ScreensScene { get; set; } = null!;

    /// <summary>The title screen, captured last over its own backdrop.</summary>
    [Export] public PackedScene TitleScene { get; set; } = null!;

    /// <summary>Where the PNGs go, relative to the project folder.</summary>
    [Export] public string OutDir { get; set; } = "../docs/screenshots/undercity_ui";

    private Screens _screens = null!;

    /// <inheritdoc/>
    public override async void _Ready()
    {
        try
        {
            await Run();
        }
        catch (Exception e)
        {
            GD.PrintErr($"[ui_capture] {e}");
            GetTree().Quit(1);
        }
    }

    private async Task Run()
    {
        var backdrop = GetNode<ColorRect>("Backdrop");
        backdrop.Color = backdrop.GetThemeColor("panel2", "Palette");
        _screens = ScreensScene.Instantiate<Screens>();
        AddChild(_screens);
        var services = UiFixture.NewServices(_screens);
        _screens.Wire(services);
        UiFixture.Stage(services.State);
        var dir = ProjectSettings.GlobalizePath("res://" + OutDir);
        DirAccess.MakeDirRecursiveAbsolute(dir);

        UiFixture.StageHud(services);
        await Shot(dir, "hud");
        _screens.OpenDeck(DeckTab.Inventory);
        await Frames(2);
        var tile = UiFixture.Descendants(_screens).OfType<PackItemView>()
            .FirstOrDefault(t => t.Stack?.Def.Id == "rat_goggles");
        tile?.EmitSignal(BaseButton.SignalName.Pressed);
        await Shot(dir, "deck_inventory");
        _screens.OpenDeck(DeckTab.Skills);
        await Shot(dir, "deck_skills");
        _screens.OpenDeck(DeckTab.Journal);
        await Shot(dir, "deck_journal");
        var session = services.State.Talk(services.Data.Dialogs["tank"], new Speaker("hub:tank", "tank"));
        var tank = services.Data.Npcs.Find("tank");
        _screens.OpenDialog(session, new SpeakerView(tank?.Name ?? "Tank", tank?.Role ?? "", null));
        await Shot(dir, "dialog");
        _screens.OpenTerminal("hub:capsule_terminal", services.Data.Levels["hub"].Terminals["hub:capsule_terminal"]);
        await Shot(dir, "terminal");
        _screens.OpenTerminal("hub:capsule_terminal", UiFixture.BusyTerminal(services.Data));
        await Shot(dir, "terminal_actions");

        // Title and pause (mockups D5-D7), with saves like the D6 mockup's.
        _screens.CloseAll();
        UiFixture.StageSaves(services);
        var pause = _screens.GetNode<PauseScreen>("%Pause");
        _screens.OpenPause();
        await Shot(dir, "pause");
        pause.GetNode<Button>("%LoadItem").EmitSignal(BaseButton.SignalName.Pressed);
        await Shot(dir, "pause_load");
        _screens.CloseAll();
        ((StubLevelHost)services.Level).Refusal = "Not while hostiles can see you.";
        _screens.OpenPause();
        await Shot(dir, "pause_refused");
        ((StubLevelHost)services.Level).Refusal = "";
        pause.GetNode<Button>("%OptionsItem").EmitSignal(BaseButton.SignalName.Pressed);
        var options = _screens.GetNode<OptionsScreen>("%Options");
        foreach (var (page, name) in new[] { (0, "options_controls"), (1, "options_video"), (2, "options_audio") })
        {
            options.ShowPage(page);
            await Shot(dir, name);
        }
        _screens.CloseAll();

        _screens.Visible = false;
        var title = TitleScene.Instantiate<TitleScreen>();
        title.Begin(new StubShell(), services.Saves, services.Data);
        AddChild(title);
        await Shot(dir, "title");
        title.GetNode<Button>("%LoadItem").EmitSignal(BaseButton.SignalName.Pressed);
        await Shot(dir, "title_load");
        GetTree().Quit();
    }

    private async Task Shot(string dir, string name)
    {
        await Frames(6);
        var image = GetViewport().GetTexture().GetImage();
        var path = System.IO.Path.Combine(dir, name + ".png");
        var err = image.SavePng(path);
        GD.Print($"[ui_capture] {name}: {image.GetWidth()}x{image.GetHeight()} -> {path} ({err})");
    }

    private async Task Frames(int n)
    {
        for (var i = 0; i < n; i++)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        }
    }
}
