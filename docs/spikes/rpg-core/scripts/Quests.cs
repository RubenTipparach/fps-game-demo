using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using Godot;

namespace Brushfire;

public enum QuestState { Inactive, Active, Completed, Failed }

public class ObjectiveDef
{
    public string Id { get; set; } = "";
    public string Text { get; set; } = "";
    public bool Optional { get; set; }
    public int Xp { get; set; }
}

/// <summary>A mission, loaded from res://data/quests.json (tools/rpg/build_quests.py).</summary>
public class QuestDef
{
    public string Id { get; set; } = "";
    public string Title { get; set; } = "";
    public string Giver { get; set; } = "";
    public string Summary { get; set; } = "";
    public string Level { get; set; } = "";
    public List<ObjectiveDef> Objectives { get; set; } = new();
    public int Xp { get; set; }
    public int Credits { get; set; }
}

/// <summary>Quest states and completed objectives for the current run.</summary>
public class QuestLog
{
    static Dictionary<string, QuestDef> _defs;

    readonly Dictionary<string, QuestState> _state = new();
    readonly HashSet<string> _done = new(); // "quest/objective"
    readonly HashSet<string> _revealed = new();

    public event Action<QuestDef, string> Updated; // (quest, message)

    public static IReadOnlyDictionary<string, QuestDef> Defs
    {
        get
        {
            if (_defs == null)
            {
                _defs = new Dictionary<string, QuestDef>();
                string text = FileAccess.GetFileAsString("res://data/quests.json");
                if (!string.IsNullOrEmpty(text))
                    foreach (var q in JsonSerializer.Deserialize<List<QuestDef>>(text, ItemDb.Json))
                        _defs[q.Id] = q;
            }
            return _defs;
        }
    }

    public static QuestDef Def(string id) => Defs.TryGetValue(id, out var d) ? d : null;

    public QuestState State(string id) => _state.TryGetValue(id, out var s) ? s : QuestState.Inactive;
    public bool IsActive(string id) => State(id) == QuestState.Active;
    public bool IsDone(string quest, string objective) => _done.Contains(quest + "/" + objective);
    public bool IsRevealed(string quest, string objective) => _revealed.Contains(quest + "/" + objective);

    public IEnumerable<QuestDef> Active => Defs.Values.Where(q => IsActive(q.Id));
    public IEnumerable<QuestDef> Finished => Defs.Values.Where(q => State(q.Id) is QuestState.Completed or QuestState.Failed);

    /// <summary>Objectives shown in the tracker: required ones, plus optional ones once revealed or done.</summary>
    public IEnumerable<ObjectiveDef> Visible(QuestDef q) =>
        q.Objectives.Where(o => !o.Optional || IsRevealed(q.Id, o.Id) || IsDone(q.Id, o.Id));

    public void Start(string id)
    {
        var q = Def(id);
        if (q == null || State(id) != QuestState.Inactive)
            return;
        _state[id] = QuestState.Active;
        Updated?.Invoke(q, "New contract: " + q.Title);
    }

    public void Reveal(string quest, string objective) => _revealed.Add(quest + "/" + objective);

    /// <summary>Completes an objective (starting the quest if needed). Returns the XP it pays.</summary>
    public int CompleteObjective(string quest, string objective)
    {
        var q = Def(quest);
        var o = q?.Objectives.FirstOrDefault(x => x.Id == objective);
        if (o == null || IsDone(quest, objective) || State(quest) is QuestState.Completed or QuestState.Failed)
            return 0;
        if (State(quest) == QuestState.Inactive)
            _state[quest] = QuestState.Active;
        _done.Add(quest + "/" + objective);
        Updated?.Invoke(q, (o.Optional ? "Bonus: " : "Objective: ") + o.Text + " ✓");
        return o.Xp;
    }

    /// <summary>Marks the quest complete. Returns (xp, credits) to pay out.</summary>
    public (int xp, int credits) Complete(string quest)
    {
        var q = Def(quest);
        if (q == null || State(quest) == QuestState.Completed)
            return (0, 0);
        _state[quest] = QuestState.Completed;
        Updated?.Invoke(q, "Contract complete: " + q.Title);
        return (q.Xp, q.Credits);
    }

    public void Fail(string quest)
    {
        var q = Def(quest);
        if (q == null || State(quest) is QuestState.Completed or QuestState.Failed)
            return;
        _state[quest] = QuestState.Failed;
        Updated?.Invoke(q, "Contract failed: " + q.Title);
    }
}
