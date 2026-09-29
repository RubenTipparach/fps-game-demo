using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using Godot;

namespace Brushfire;

// ---------------------------------------------------------------------------- data model
// Written by tools/dialog/build_dialogs.py (which validates every link) into res://data/dialog/*.json.

public class DialogCond
{
    public string Flag { get; set; }
    public string NotFlag { get; set; }
    public string Item { get; set; }
    public string NoItem { get; set; }
    public int Count { get; set; } = 1;
    public int? Credits { get; set; }
    public string Skill { get; set; }
    public int Min { get; set; }
    public string Disguise { get; set; }
    public string Quest { get; set; }
    public string State { get; set; }
    public string Objective { get; set; }
    public string NotObjective { get; set; }
    public string Npc { get; set; }
    public string Status { get; set; }
}

public class DialogCheck
{
    /// <summary>Skill name, or "cover" for Deception + disguise quality.</summary>
    public string Skill { get; set; }
    public int Dc { get; set; }
    public int Xp { get; set; } = 50;
}

public class DialogEffect
{
    public string Flag { get; set; }
    public string Unflag { get; set; }
    public string Give { get; set; }
    public string Take { get; set; }
    public int Count { get; set; } = 1;
    public int Credits { get; set; }
    public int Xp { get; set; }
    public string Why { get; set; }
    public string StartQuest { get; set; }
    public string Objective { get; set; }   // "quest/objective"
    public string Reveal { get; set; }      // "quest/objective"
    public string CompleteQuest { get; set; }
    public string FailQuest { get; set; }
    public string Trade { get; set; }       // shop id
    public int Heal { get; set; }
    /// <summary>A verb for an NPC: "hostile", "leave", "calm", "surrender", "free", "follow". Npc = null means the speaker.</summary>
    public string Npc { get; set; }
    public string Do { get; set; }
    public string Open { get; set; }        // InteractDoor id to unlock + open
    public string Say { get; set; }         // feed message
}

public class DialogChoice
{
    public string Text { get; set; } = "";
    public List<DialogCond> If { get; set; }
    public DialogCheck Check { get; set; }
    public string Next { get; set; }
    public string Pass { get; set; }
    public string Fail { get; set; }
    public List<DialogEffect> Do { get; set; }
    public bool Once { get; set; }
    public bool Exit { get; set; }
}

public class DialogNode
{
    public string Speaker { get; set; }
    /// <summary>One or more variants; one is picked at random each visit.</summary>
    public List<string> Say { get; set; } = new();
    public List<DialogEffect> Do { get; set; }
    public string Next { get; set; }
    public List<DialogChoice> Choices { get; set; }
}

public class DialogStart
{
    public List<DialogCond> If { get; set; }
    public string Node { get; set; }
}

public class DialogTree
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public string Start { get; set; } = "start";
    /// <summary>Conditional entry points, checked in order before Start.</summary>
    public List<DialogStart> Starts { get; set; }
    public Dictionary<string, DialogNode> Nodes { get; set; } = new();
    /// <summary>Ambient one-liners shown over the NPC's head.</summary>
    public List<string> Barks { get; set; }
}

/// <summary>What the dialog system needs from whoever it is talking to.</summary>
public interface IDialogSpeaker
{
    string NpcId { get; }
    string DisplayName { get; }
    Node3D Body { get; }
    Vector3 HeadPosition { get; }
    void OnTalkStart();
    void OnTalkEnd();
    void DialogVerb(string verb);
}

// ---------------------------------------------------------------------------- runtime

public static class DialogDb
{
    static readonly Dictionary<string, DialogTree> _cache = new();

    public static DialogTree Get(string id)
    {
        if (string.IsNullOrEmpty(id))
            return null;
        if (_cache.TryGetValue(id, out var t))
            return t;
        string path = $"res://data/dialog/{id}.json";
        string text = FileAccess.FileExists(path) ? FileAccess.GetFileAsString(path) : null;
        if (string.IsNullOrEmpty(text))
        {
            GD.PushWarning($"[Dialog] missing tree {path}");
            return null;
        }
        t = JsonSerializer.Deserialize<DialogTree>(text, ItemDb.Json);
        _cache[id] = t;
        return t;
    }
}

/// <summary>A choice as the UI should show it.</summary>
public record ChoiceView(DialogChoice Choice, int Index, string Label, bool Enabled, string Requirement);

/// <summary>Evaluates conditions, checks and effects against the GameState.</summary>
public static class DialogLogic
{
    static GameState S => Game.Instance.State;

    public static int SkillValue(string skill)
    {
        if (string.Equals(skill, "cover", StringComparison.OrdinalIgnoreCase))
            return Disguise.Cover;
        return Enum.TryParse<Skill>(skill, true, out var s) ? S.Character.Get(s) : 0;
    }

    public static string SkillLabel(string skill) =>
        string.Equals(skill, "cover", StringComparison.OrdinalIgnoreCase) ? "Cover"
        : Enum.TryParse<Skill>(skill, true, out var s) ? Character.Info(s).Name : skill;

    /// <summary>True when a condition is about the player's build (shown greyed out) rather than the story (hidden).</summary>
    static bool IsBuildCond(DialogCond c) => c.Skill != null || c.Credits != null;

    public static bool Eval(DialogCond c, IDialogSpeaker speaker = null)
    {
        var s = S;
        if (c.Flag != null && !s.Flag(c.Flag)) return false;
        if (c.NotFlag != null && s.Flag(c.NotFlag)) return false;
        if (c.Item != null && s.Inventory.Count(c.Item) < c.Count && !s.Inventory.Has(c.Item)) return false;
        if (c.NoItem != null && s.Inventory.Has(c.NoItem)) return false;
        if (c.Credits != null && s.Character.Credits < c.Credits) return false;
        if (c.Skill != null && SkillValue(c.Skill) < c.Min) return false;
        if (c.Disguise != null && !(Disguise.Faction == c.Disguise && Disguise.Quality > 0)) return false;
        if (c.Quest != null)
        {
            var st = s.Quests.State(c.Quest).ToString().ToLowerInvariant();
            if (c.State != null ? st != c.State : st == "inactive") return false;
        }
        if (c.Objective != null)
        {
            var parts = c.Objective.Split('/');
            if (!s.Quests.IsDone(parts[0], parts[1])) return false;
        }
        if (c.NotObjective != null)
        {
            var parts = c.NotObjective.Split('/');
            if (s.Quests.IsDone(parts[0], parts[1])) return false;
        }
        if (c.Npc != null && s.Npc(c.Npc) != (c.Status ?? "")) return false;
        return true;
    }

    public static string EntryNode(DialogTree tree, IDialogSpeaker speaker)
    {
        if (tree.Starts != null)
            foreach (var st in tree.Starts)
                if (st.If == null || st.If.All(c => Eval(c, speaker)))
                    return st.Node;
        return tree.Start;
    }

    static string OnceFlag(DialogTree tree, string node, int index) => $"dlg:{tree.Id}:{node}:{index}";

    public static List<ChoiceView> Choices(DialogTree tree, string nodeId, IDialogSpeaker speaker)
    {
        var node = tree.Nodes[nodeId];
        var list = new List<ChoiceView>();
        if (node.Choices == null)
            return list;
        for (int i = 0; i < node.Choices.Count; i++)
        {
            var ch = node.Choices[i];
            if (ch.Once && S.Flag(OnceFlag(tree, nodeId, i)))
                continue;
            var conds = ch.If ?? new List<DialogCond>();
            // Story conditions hide the choice; build conditions grey it out with the requirement shown.
            if (conds.Where(c => !IsBuildCond(c)).Any(c => !Eval(c, speaker)))
                continue;
            var build = conds.Where(IsBuildCond).ToList();
            bool enabled = build.All(c => Eval(c, speaker));
            var tags = new List<string>();
            foreach (var c in build)
            {
                if (c.Skill != null) tags.Add($"{SkillLabel(c.Skill)} {c.Min}");
                if (c.Credits != null) tags.Add($"{c.Credits} cr");
            }
            if (ch.Check != null)
                tags.Add($"{SkillLabel(ch.Check.Skill)} {ch.Check.Dc}");
            string label = (tags.Count > 0 ? "[" + string.Join(" · ", tags) + "] " : "") + ch.Text;
            list.Add(new ChoiceView(ch, i, label, enabled, enabled ? null : string.Join(", ", tags)));
        }
        return list;
    }

    /// <summary>Resolve a picked choice: effects, check, next node (null = end).</summary>
    public static string Pick(DialogTree tree, string nodeId, ChoiceView view, IDialogSpeaker speaker, out bool passed)
    {
        var ch = view.Choice;
        passed = true;
        if (ch.Once)
            S.SetFlag(OnceFlag(tree, nodeId, view.Index));
        string next = ch.Next;
        if (ch.Check != null)
        {
            passed = SkillValue(ch.Check.Skill) >= ch.Check.Dc;
            next = passed ? ch.Pass : ch.Fail;
            if (passed && ch.Check.Xp > 0)
                S.Character.AddXp(ch.Check.Xp, $"{SkillLabel(ch.Check.Skill)} check");
        }
        if (ch.Do != null && passed)
            foreach (var e in ch.Do)
                Apply(e, speaker);
        return ch.Exit ? null : next;
    }

    public static void Enter(DialogNode node, IDialogSpeaker speaker)
    {
        if (node.Do != null)
            foreach (var e in node.Do)
                Apply(e, speaker);
    }

    public static void Apply(DialogEffect e, IDialogSpeaker speaker)
    {
        var s = S;
        if (e.Flag != null) s.SetFlag(e.Flag);
        if (e.Unflag != null) s.ClearFlag(e.Unflag);
        if (e.Give != null) s.Give(e.Give, e.Count);
        if (e.Take != null)
        {
            int n = s.Inventory.Remove(e.Take, e.Count);
            if (n > 0) s.Say($"−{ItemDb.Get(e.Take)?.Name}{(n > 1 ? " ×" + n : "")}");
        }
        if (e.Credits > 0) { s.Character.Earn(e.Credits); s.Say($"+{e.Credits} credits"); }
        if (e.Credits < 0) { s.Character.Spend(-e.Credits); s.Say($"−{-e.Credits} credits"); }
        if (e.StartQuest != null) s.Quests.Start(e.StartQuest);
        if (e.Reveal != null) { var p = e.Reveal.Split('/'); s.Quests.Reveal(p[0], p[1]); }
        if (e.Objective != null) { var p = e.Objective.Split('/'); s.CompleteObjective(p[0], p[1]); }
        if (e.CompleteQuest != null) s.CompleteQuest(e.CompleteQuest);
        if (e.FailQuest != null) s.Quests.Fail(e.FailQuest);
        if (e.Xp > 0) s.Character.AddXp(e.Xp, e.Why ?? "dialog");
        if (e.Heal > 0) PlayerController.Instance?.GiveHealth(e.Heal);
        if (e.Say != null) s.Say(e.Say);
        if (e.Open != null) InteractDoor.OpenById(e.Open);
        if (e.Do != null)
        {
            if (string.IsNullOrEmpty(e.Npc) || e.Npc == speaker?.NpcId)
                speaker?.DialogVerb(e.Do);
            else
                Npc.Find(e.Npc)?.DialogVerb(e.Do);
        }
        if (e.Trade != null) DialogScreen.Current?.OpenTrade(e.Trade);
    }
}
