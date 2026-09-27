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
