// Quests and objectives (data/quests.json), and the journal's state.
//
// It lives in the core because dialog conditions, triggers, XP and the journal all read and move
// quest state, and a save must restore it exactly.

using Undercity.Core.Data;

namespace Undercity.Core.Quests;

/// <summary>A quest's state.</summary>
public enum QuestState
{
    /// <summary>Not given yet.</summary>
    NotStarted,

    /// <summary>In the journal.</summary>
    Active,

    /// <summary>Completed.</summary>
    Done,

    /// <summary>Failed.</summary>
    Failed,
}

/// <summary>One objective.</summary>
public sealed class ObjectiveDef
{
    /// <summary>The id within its quest.</summary>
    public required string Id { get; init; }

    /// <summary>The journal line.</summary>
    public required string Text { get; init; }

    /// <summary>XP paid on completion.</summary>
    public int Xp { get; init; }

    /// <summary>Optional objectives don't block completing the quest.</summary>
    public bool Optional { get; init; }

    /// <summary>Hidden until revealed (by dialog, a terminal or a trigger).</summary>
    public bool Hidden { get; init; }
}

/// <summary>One quest.</summary>
public sealed class QuestDef
{
    /// <summary>The id, such as <c>s3_mouses_debt</c>.</summary>
    public required string Id { get; init; }

    /// <summary>The journal title.</summary>
    public required string Title { get; init; }

    /// <summary>Who gives it (an NPC id).</summary>
    public required string Giver { get; init; }

    /// <summary>The journal summary.</summary>
    public required string Summary { get; init; }

    /// <summary>The level it's played in.</summary>
    public required string Level { get; init; }

    /// <summary>Its objectives, in journal order.</summary>
    public required IReadOnlyList<ObjectiveDef> Objectives { get; init; }

    /// <summary>XP on completion.</summary>
    public int Xp { get; init; }

    /// <summary>Credits on completion.</summary>
    public int Credits { get; init; }
}

/// <summary>data/quests.json.</summary>
public sealed class QuestTable : IValidated
{
    /// <summary>The quests.</summary>
    public required IReadOnlyList<QuestDef> Quests { get; init; }

    /// <summary>The quest with this id.</summary>
    public QuestDef Get(string id) => Quests.First(q => q.Id == id);

    /// <summary>True when the quest exists.</summary>
    public bool Exists(string id) => Quests.Any(q => q.Id == id);

    /// <summary>True when "quest/objective" names an existing objective.</summary>
    public bool ObjectiveExists(string path)
    {
        var (q, o) = Split(path);
        return Exists(q) && Get(q).Objectives.Any(x => x.Id == o);
    }

    /// <summary>Splits "quest/objective".</summary>
    public static (string Quest, string Objective) Split(string path)
    {
        var i = path.IndexOf('/', StringComparison.Ordinal);
        return i < 0 ? (path, "") : (path[..i], path[(i + 1)..]);
    }

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        foreach (var dup in Quests.GroupBy(q => q.Id).Where(g => g.Count() > 1))
        {
            errors.Add($"quests: '{dup.Key}' appears twice");
        }
        foreach (var q in Quests)
        {
            if (q.Objectives.Count == 0)
            {
                errors.Add($"quests.{q.Id}: needs at least one objective");
            }
            foreach (var dup in q.Objectives.GroupBy(o => o.Id).Where(g => g.Count() > 1))
            {
                errors.Add($"quests.{q.Id}: objective '{dup.Key}' appears twice");
            }
        }
    }
}

/// <summary>The journal: which quests are active or done, and which objectives are complete or revealed.</summary>
public sealed class QuestLog
{
    private readonly QuestTable _table;
    private readonly SortedDictionary<string, QuestState> _states = new(StringComparer.Ordinal);
    private readonly SortedSet<string> _done = new(StringComparer.Ordinal);
    private readonly SortedSet<string> _revealed = new(StringComparer.Ordinal);

    /// <summary>Creates an empty journal.</summary>
    public QuestLog(QuestTable table) => _table = table;

    /// <summary>The quest table.</summary>
    public QuestTable Table => _table;

    /// <summary>Raises with the quest and a journal line when anything moves.</summary>
    public event Action<QuestDef, string>? Updated;

    /// <summary>A quest's state.</summary>
    public QuestState State(string quest) => _states.TryGetValue(quest, out var s) ? s : QuestState.NotStarted;

    /// <summary>True when "quest/objective" is complete.</summary>
    public bool IsDone(string path) => _done.Contains(path);

    /// <summary>True when an objective shows in the journal: not hidden, revealed, or done.</summary>
    public bool IsVisible(string quest, ObjectiveDef o) =>
        !o.Hidden || _revealed.Contains($"{quest}/{o.Id}") || _done.Contains($"{quest}/{o.Id}");

    /// <summary>Active quests, in table order.</summary>
    public IEnumerable<QuestDef> Active => _table.Quests.Where(q => State(q.Id) == QuestState.Active);

    /// <summary>Finished quests (done or failed), in table order.</summary>
    public IEnumerable<QuestDef> Finished => _table.Quests.Where(q => State(q.Id) is QuestState.Done or QuestState.Failed);

    /// <summary>Starts a quest. Returns false when it was already started.</summary>
    public bool Start(string quest)
    {
        if (State(quest) != QuestState.NotStarted)
        {
            return false;
        }
        _states[quest] = QuestState.Active;
        Updated?.Invoke(_table.Get(quest), "New quest");
        return true;
    }

    /// <summary>Reveals a hidden objective.</summary>
    public void Reveal(string path)
    {
        if (_revealed.Add(path))
        {
            var (q, _) = QuestTable.Split(path);
            Updated?.Invoke(_table.Get(q), "Journal updated");
        }
    }

    /// <summary>
    /// Completes an objective, starting its quest if needed. Returns the objective's XP, or 0 when it
    /// was already done or the quest is finished.
    /// </summary>
    public int CompleteObjective(string path)
    {
        var (q, o) = QuestTable.Split(path);
        if (State(q) is QuestState.Done or QuestState.Failed || !_done.Add(path))
        {
            return 0;
        }
        if (State(q) == QuestState.NotStarted)
        {
            _states[q] = QuestState.Active;
        }
        var def = _table.Get(q);
        var obj = def.Objectives.First(x => x.Id == o);
        Updated?.Invoke(def, $"Done: {obj.Text}");
        return obj.Xp;
    }

    /// <summary>Completes a quest. Returns its XP and credits, or zeros when it wasn't active.</summary>
    public (int Xp, int Credits) Complete(string quest)
    {
        if (State(quest) != QuestState.Active)
        {
            return (0, 0);
        }
        _states[quest] = QuestState.Done;
        var def = _table.Get(quest);
        Updated?.Invoke(def, "Quest complete");
        return (def.Xp, def.Credits);
    }

    /// <summary>Fails a quest.</summary>
    public void Fail(string quest)
    {
        if (State(quest) is QuestState.Done or QuestState.Failed)
        {
            return;
        }
        _states[quest] = QuestState.Failed;
        Updated?.Invoke(_table.Get(quest), "Quest failed");
    }

    /// <summary>A copy for a save.</summary>
    public QuestSave Save() => new()
    {
        States = new SortedDictionary<string, QuestState>(_states, StringComparer.Ordinal),
        Done = _done.ToList(),
        Revealed = _revealed.ToList(),
    };

    /// <summary>Restores a save, dropping unknown quests and objectives. Returns a message per repair.</summary>
    public IReadOnlyList<string> Load(QuestSave save)
    {
        var repairs = new List<string>();
        _states.Clear();
        _done.Clear();
        _revealed.Clear();
        foreach (var (q, s) in save.States)
        {
            if (_table.Exists(q))
            {
                _states[q] = s;
            }
            else
            {
                repairs.Add($"unknown quest '{q}' dropped");
            }
        }
        foreach (var p in save.Done.Where(_table.ObjectiveExists))
        {
            _done.Add(p);
        }
        foreach (var p in save.Revealed.Where(_table.ObjectiveExists))
        {
            _revealed.Add(p);
        }
        return repairs;
    }
}

/// <summary>The saved form of a <see cref="QuestLog"/>.</summary>
public sealed class QuestSave
{
    /// <summary>Quest states.</summary>
    public SortedDictionary<string, QuestState> States { get; set; } = new(StringComparer.Ordinal);

    /// <summary>Completed objectives, "quest/objective".</summary>
    public List<string> Done { get; set; } = new();

    /// <summary>Revealed objectives, "quest/objective".</summary>
    public List<string> Revealed { get; set; } = new();
}
