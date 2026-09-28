// The level as its entities see it: its data, the player, travel, and finding things by stable id.
//
// It lives here as an interface so entity scripts can be tested and reused without the level
// root's scene (CLAUDE.md 6.3).

#nullable enable
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>A node with a stable id (see openspec/changes/undercity-architecture: persistent objects have stable ids).</summary>
public interface IStable
{
    /// <summary>"&lt;level&gt;:&lt;id&gt;", such as "hub:kessler_safe".</summary>
    string StableId { get; }
}

/// <summary>Something a dialog effect can open ("open": "hub:checkpoint_barrier").</summary>
public interface IOpenable : IStable
{
    /// <summary>Opens it, as if its lock had been opened.</summary>
    void Open();
}

/// <summary>The level being played.</summary>
public interface ILevelHost
{
    /// <summary>The level id, such as "hub".</summary>
    string Id { get; }

    /// <summary>The level's data (containers, doors, terminals, exits, zones, triggers).</summary>
    LevelDef Def { get; }

    /// <summary>The level's water: where it is and how deep a body is in it.</summary>
    LevelWater Water { get; }

    /// <summary>The player's body.</summary>
    Brushfire.PlayerController Player { get; }

    /// <summary>The player's eye position.</summary>
    Vector3 PlayerEye { get; }

    /// <summary>Takes an exit: another level, or a spawn point in this one.</summary>
    void Travel(ExitDef exit);

    /// <summary>Puts items on the floor at the player's feet (a full pack, a dropped item).</summary>
    void DropAtPlayer(string itemId, int count, string? stolenFrom);

    /// <summary>Seconds the runner has been in a restricted zone they aren't allowed in (0 outside one).</summary>
    double RestrictedS { get; }

    /// <summary>Called by a restricted zone each frame: how long the runner has been in it unallowed (0 when out or allowed).</summary>
    void SetRestricted(string zoneId, double seconds);

    /// <summary>
    /// True when someone who would report a crime can see the player now: a resident or MerSec
    /// within their sight range, facing the player, with a clear line.
    /// </summary>
    bool CrimeWitnessed(out string witness);

    /// <summary>
    /// Why the runner can't save right now (the one save rule, <see cref="Undercity.Core.SaveRules.CanSave"/>),
    /// or empty when a save is allowed. The pause menu greys its save buttons with this.
    /// </summary>
    string SaveRefusal();

    /// <summary>Saves the run to a slot unless the save rule refuses. Returns false with the reason.</summary>
    bool TrySave(string slot, out string reason);
}
