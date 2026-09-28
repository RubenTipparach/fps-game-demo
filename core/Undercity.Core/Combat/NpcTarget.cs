// Who an NPC is, for a hit: the key their status and health are kept under, their faction and
// their body (openspec/changes/hub-combat, design sections 4 and 6).
//
// It lives in the core because the key is saved. A named NPC is kept under their NPC id, which
// dialog and quests read; a civilian under their own stable id. Every civilian was once kept under
// the one id "civ", so killing one killed none of them in the world's memory.

using Undercity.Core.World;

namespace Undercity.Core.Combat;

/// <summary>An NPC as a target.</summary>
/// <param name="Key">The key their status and health are kept under.</param>
/// <param name="NpcId">A named NPC's id (their quests fail when they die), or null for a civilian.</param>
/// <param name="Name">Their name, for the feed.</param>
/// <param name="Faction">Their faction: violence against them costs its reputation.</param>
/// <param name="MaxHealth">Their health when unhurt.</param>
/// <param name="ResistPct">Their resistance by damage type, percent.</param>
public sealed record NpcTarget(string Key, string? NpcId, string Name, string Faction, double MaxHealth,
    IReadOnlyDictionary<string, double> ResistPct)
{
    /// <summary>A named NPC.</summary>
    public static NpcTarget For(NpcDef def) => new(def.Id, def.Id, def.Name, def.Faction, def.Health, def.ResistPct);

    /// <summary>A civilian, by their stable id ("hub:civ_07").</summary>
    public static NpcTarget Civilian(CivilianPool pool, string stableId, string faction, string name) =>
        new(stableId, null, name, faction, pool.Health, pool.ResistPct);
}

/// <summary>What a hit did.</summary>
/// <param name="Damage">The damage dealt.</param>
/// <param name="HealthLeft">Their health after it (0 or less when killed).</param>
/// <param name="Killed">True when this hit killed them.</param>
public readonly record struct NpcHit(double Damage, double HealthLeft, bool Killed);
