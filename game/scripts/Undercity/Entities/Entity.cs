// Stable ids and lock use for level entities: the one place an entity's stable id is derived, and
// the one lock prompt and open path shared by doors, containers, terminals and exits.
//
// It lives here because every interactable with a lock must show the prompt the core's LockRules
// gives and open through GameState.OpenLock (CLAUDE.md 5.1): a door and a safe never differ in how
// a lock resolves, only in what happens after.

#nullable enable
using Godot;
using Undercity.Core.Locks;
using Undercity.Core.Perception;

namespace Undercity.Client;

/// <summary>Helpers for entities placed by a level's entity layout.</summary>
public static class Entity
{
    /// <summary>
    /// The stable id of an entity: its level's id and the "id" the importer copied from the layout,
    /// as "&lt;level&gt;:&lt;id&gt;". Empty when the node isn't in an Undercity level.
    /// </summary>
    public static string StableIdOf(Node node)
    {
        var id = node.HasMeta("id") ? node.GetMeta("id").AsString() : "";
        for (var p = node.GetParent(); p is not null; p = p.GetParent())
        {
            if (p is UndercityLevel level)
            {
                return id.Length == 0 ? "" : $"{level.LevelId}:{id}";
            }
        }
        return "";
    }

    /// <summary>A string extra from the layout, or <paramref name="fallback"/>.</summary>
    public static string Meta(Node node, string key, string fallback = "") =>
        node.HasMeta(key) ? node.GetMeta(key).AsString() : fallback;

    /// <summary>
    /// What use does on a thing behind <paramref name="lk"/>: the lock's plan while it's locked,
    /// otherwise <paramref name="whenOpen"/> (an empty prompt means nothing to do).
    /// </summary>
    public static Interaction DescribeLock(Services s, string stableId, LockDef? lk, string whenOpen)
    {
        if (lk is null || s.State.IsOpened(s.Level.Id, stableId))
        {
            return new Interaction(whenOpen, whenOpen.Length > 0);
        }
        var plan = s.State.PlanLock(lk);
        return new Interaction(plan.Prompt, plan.CanOpen, plan.HoldS);
    }

    /// <summary>True while the lock is shut.</summary>
    public static bool IsLocked(Services s, string stableId, LockDef? lk) =>
        lk is not null && !s.State.IsOpened(s.Level.Id, stableId);

    /// <summary>
    /// Opens a lock by its plan. Picking or hacking something that belongs to someone, in view of a
    /// resident or trooper, is a crime. Returns true when it opened.
    /// </summary>
    public static bool OpenLock(Services s, string stableId, LockDef lk, string? owner)
    {
        var way = s.State.PlanLock(lk).Way;
        if (!s.State.OpenLock(lk, s.Level.Id, stableId))
        {
            return false;
        }
        if (owner is not null && way is LockWay.Pick or LockWay.Hack)
        {
            Witness(s);
        }
        return true;
    }

    /// <summary>Reports a crime if anyone who would report it can see the runner now.</summary>
    public static void Witness(Services s)
    {
        if (s.Level.CrimeWitnessed(out var who) && s.State.ReportCrime(who) == LawResponse.Hostile
            && s.Level is UndercityLevel level)
        {
            foreach (var npc in level.Npcs())
            {
                if (npc.IsLaw)
                {
                    level.TurnLawHostile(npc);
                    break;
                }
            }
        }
    }
}
