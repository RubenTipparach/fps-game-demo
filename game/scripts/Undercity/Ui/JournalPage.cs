// The deck's Journal tab: active quests, then finished ones; the selected quest's summary and its
// visible objectives, ticked when done and marked when optional.
//
// It lives in the UI layer as a thin view: quest states, which objectives show and which are done
// come from the QuestLog (CLAUDE.md 6.2).

#nullable enable
using System.Linq;
using Godot;
using Undercity.Core.Quests;

namespace Undercity.Client;

/// <summary>The Journal tab.</summary>
public partial class JournalPage : HBoxContainer, IWired
{
    /// <summary>One quest in the list (quest_row.tscn).</summary>
    [Export] public PackedScene QuestRowScene { get; set; } = null!;

    /// <summary>One objective (objective_row.tscn).</summary>
    [Export] public PackedScene ObjectiveRowScene { get; set; } = null!;

    private Services? _services;
    private VBoxContainer _activeRows = null!;
    private VBoxContainer _finishedRows = null!;
    private Label _activeTitle = null!;
    private Label _finishedTitle = null!;
    private Label _empty = null!;
    private Control _questBody = null!;
    private Label _title = null!;
    private Label _state = null!;
    private Label _summary = null!;
    private VBoxContainer _objectives = null!;
    private string? _selected;

    /// <inheritdoc/>
    public override void _Ready()
    {
        _activeRows = GetNode<VBoxContainer>("%ActiveRows");
        _finishedRows = GetNode<VBoxContainer>("%FinishedRows");
        _activeTitle = GetNode<Label>("%ActiveTitle");
        _finishedTitle = GetNode<Label>("%FinishedTitle");
        _empty = GetNode<Label>("%JournalEmpty");
        _questBody = GetNode<Control>("%QuestBody");
        _title = GetNode<Label>("%QuestTitle");
        _state = GetNode<Label>("%QuestState");
        _summary = GetNode<Label>("%QuestSummary");
        _objectives = GetNode<VBoxContainer>("%ObjectiveRows");
    }

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _services = services;
        services.State.Quests.Updated += OnUpdated;
        Refresh();
    }

    /// <inheritdoc/>
    public override void _ExitTree()
    {
        if (_services is not null)
        {
            _services.State.Quests.Updated -= OnUpdated;
        }
    }

    private void OnUpdated(QuestDef quest, string line) => Callable.From(Refresh).CallDeferred();

    /// <summary>Rebuilds the list and the selected quest from the journal.</summary>
    public void Refresh()
    {
        if (_services is null || !IsInstanceValid(this))
        {
            return;
        }
        var log = _services.State.Quests;
        var active = log.Active.ToList();
        var finished = log.Finished.ToList();
        if (_selected is null || log.State(_selected) == QuestState.NotStarted)
        {
            _selected = active.Concat(finished).FirstOrDefault()?.Id;
        }
        Fill(_activeRows, active);
        Fill(_finishedRows, finished);
        _activeTitle.Visible = active.Count > 0;
        _finishedTitle.Visible = finished.Count > 0;
        _empty.Visible = active.Count + finished.Count == 0;
        ShowQuest();
    }

    private void Fill(VBoxContainer rows, System.Collections.Generic.List<QuestDef> quests)
    {
        foreach (var old in rows.GetChildren())
        {
            rows.RemoveChild(old);
            old.QueueFree();
        }
        foreach (var q in quests)
        {
            var row = QuestRowScene.Instantiate<QuestRowView>();
            rows.AddChild(row);
            row.Bind(q, q.Id == _selected);
            row.Picked += Pick;
        }
    }

    private void Pick(string questId)
    {
        _selected = questId;
        Callable.From(Refresh).CallDeferred();
    }

    private void ShowQuest()
    {
        foreach (var old in _objectives.GetChildren())
        {
            _objectives.RemoveChild(old);
            old.QueueFree();
        }
        _questBody.Visible = _selected is not null;
        if (_selected is null || _services is null)
        {
            return;
        }
        var log = _services.State.Quests;
        var quest = log.Table.Get(_selected);
        _title.Text = quest.Title;
        _state.Text = $"{log.State(quest.Id)} · {UiText.Npc(_services.Data, quest.Giver)}";
        _summary.Text = quest.Summary;
        foreach (var o in quest.Objectives.Where(o => log.IsVisible(quest.Id, o)))
        {
            var row = ObjectiveRowScene.Instantiate<ObjectiveRowView>();
            _objectives.AddChild(row);
            row.Bind(o, log.IsDone($"{quest.Id}/{o.Id}"));
        }
    }
}
