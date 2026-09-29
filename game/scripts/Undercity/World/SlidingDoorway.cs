// A public entrance's automatic sliding door (openspec/changes/hub-doorways, design section 3.3;
// the owner, survey K2: "automatic opening sliding doors"). It is E1M3's split door,
// Brushfire.Doorway with its two Brushfire.Door leaves, opening for the runner and for people (the
// "npcs" group NpcActor joins), so a civilian walking a navmesh path through a closed entrance
// opens it as they come. It never locks and holds nothing a save records.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): the door's behaviour is
// Brushfire's, and its radii, wait and speed come from data/doors.json.

#nullable enable
using Brushfire;

namespace Undercity.Client;

/// <summary>A sliding entrance, timed from data/doors.json.</summary>
public partial class SlidingDoorway : Doorway, IWired
{
    /// <summary>The group NpcActor joins: people open the hub's entrances.</summary>
    public const string PeopleGroup = "npcs";

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        var d = services.Data.Doors.Sliding;
        TriggerRadius = (float)d.TriggerRadiusM;
        GroupTriggerRadius = (float)d.NpcTriggerRadiusM;
        Wait = (float)d.WaitS;
        OpenForGroups = new[] { PeopleGroup };
        Locked = false;
        foreach (var leaf in Leaves)
        {
            leaf.Speed = (float)d.SpeedMps;
        }
    }
}
