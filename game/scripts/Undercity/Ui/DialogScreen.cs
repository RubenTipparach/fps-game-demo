// The dialog screen (dialog_screen.tscn), after the approved F8 mockup's lower third: who is
// speaking, their line, and the numbered choices with their requirements.
//
// It lives in the UI layer as a thin view that drives a core DialogSession: the line, the choices
// shown, which are greyed and why, and what a pick does all come from the session (CLAUDE.md 5.1).

#nullable enable
using System;
using System.Collections.Generic;
using Godot;
using Undercity.Core.Dialog;
using Undercity.Core.Perception;

namespace Undercity.Client;

/// <summary>The dialog screen.</summary>
public partial class DialogScreen : Control, IWired
{
    /// <summary>One choice (choice_row.tscn).</summary>
    [Export] public PackedScene ChoiceRowScene { get; set; } = null!;

    private const float MaxNamePx = 480;

    private Label _name = null!;
    private Label _role = null!;
    private Label _cover = null!;
    private Label _line = null!;
    private VBoxContainer _choices = null!;
    private DialogSession? _session;
    private IReadOnlyList<ChoiceView> _shown = Array.Empty<ChoiceView>();
    private ulong _openedFrame;

    /// <summary>Raised when the conversation ends or the screen is closed.</summary>
    public event Action? Closed;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _name = GetNode<Label>("%Name");
        _role = GetNode<Label>("%Role");
        _cover = GetNode<Label>("%Cover");
        _line = GetNode<Label>("%Line");
        _choices = GetNode<VBoxContainer>("%ChoiceRows");
    }

    /// <inheritdoc/>
    public void Wire(Services services)
    {
    }

    /// <summary>Shows <paramref name="session"/> with <paramref name="speaker"/> in the header.</summary>
    public void Open(DialogSession session, SpeakerView speaker)
    {
        _session = session;
        _openedFrame = Engine.GetProcessFrames();
        _name.Text = speaker.Name;
        UiText.FitWidth(_name, MaxNamePx);
        _role.Text = speaker.Role;
        _cover.Visible = speaker.Disguise is not null;
        if (speaker.Disguise is { } j)
        {
            // The core's own words for the verdict, such as "Cover 5 holds against I 3".
            _cover.Text = j.Reason.ToUpperInvariant();
            _cover.AddThemeColorOverride("font_color", GetThemeColor(UndercityHud.VerdictStyle(j.Verdict).Role, "Palette"));
        }
        Show();
        Render();
    }

    /// <summary>Closes the screen, ending nothing in the session.</summary>
    public void Close()
    {
        if (!Visible)
        {
            return;
        }
        Hide();
        _session = null;
        Closed?.Invoke();
    }

    /// <inheritdoc/>
    public override void _GuiInput(InputEvent e)
    {
        if (e is InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.Left })
        {
            Continue();
            AcceptEvent();
        }
    }

    /// <inheritdoc/>
    public override void _UnhandledInput(InputEvent e)
    {
        // The use press that opened the conversation must not also skip its first line.
        if (!Visible || _session is null || Engine.GetProcessFrames() == _openedFrame)
        {
            return;
        }
        if (UiKeys.Row(e) is { } row)
        {
            if (row < _shown.Count)
            {
                Choose(_shown[row].Index);
            }
            GetViewport().SetInputAsHandled();
        }
        else if (e.IsActionPressed("use") || e.IsActionPressed("jump") || e.IsActionPressed("ui_accept"))
        {
            Continue();
            GetViewport().SetInputAsHandled();
        }
    }

    /// <summary>Shows the next line, or moves on from a node without choices.</summary>
    public void Continue()
    {
        if (_session is null)
        {
            return;
        }
        if ((_session.MoreLines || _session.Choices().Count == 0) && _session.Advance())
        {
            Render();
        }
    }

    private void Choose(int index)
    {
        if (_session is not null && _session.Choose(index))
        {
            Render();
        }
    }

    private void Render()
    {
        foreach (var old in _choices.GetChildren())
        {
            _choices.RemoveChild(old);
            old.QueueFree();
        }
        if (_session is null || _session.Over)
        {
            Close();
            return;
        }
        _line.Text = _session.Line;
        _shown = _session.Choices();
        for (var i = 0; i < _shown.Count; i++)
        {
            var row = ChoiceRowScene.Instantiate<ChoiceRowView>();
            _choices.AddChild(row);
            row.Bind(i, _shown[i]);
            row.Chosen += index => Callable.From(() => Choose(index)).CallDeferred();
        }
    }
}
