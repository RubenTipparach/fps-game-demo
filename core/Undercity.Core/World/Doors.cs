// How the hub's public entrances slide open (openspec/changes/hub-doorways, design section 3.3; the
// owner, survey K2: "automatic opening sliding doors"): how near the runner and a person come
// before the leaves part, how long they wait once nobody is near, and how fast they move.
//
// It lives in the core with the other tables because it is tuning (CLAUDE.md 5.5): committed,
// validated on load and by a core test, one source for each number. The door itself is E1M3's
// (Brushfire.Doorway and Brushfire.Door); Undercity.Client.SlidingDoorway sets it from here.

using Undercity.Core.Data;

namespace Undercity.Core.World;

/// <summary>A sliding entrance's timings.</summary>
public sealed class SlidingDoorDef
{
    /// <summary>The leaves part when the runner comes this near the doorway, metres.</summary>
    public required double TriggerRadiusM { get; init; }

    /// <summary>The leaves part when a person comes this near, metres.</summary>
    public required double NpcTriggerRadiusM { get; init; }

    /// <summary>They close this long after the last one leaves, seconds.</summary>
    public required double WaitS { get; init; }

    /// <summary>How fast each leaf slides, metres a second.</summary>
    public required double SpeedMps { get; init; }
}

/// <summary>data/doors.json.</summary>
public sealed class DoorsTable : IValidated
{
    /// <summary>The public entrances' sliding doors.</summary>
    public required SlidingDoorDef Sliding { get; init; }

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        void Positive(string at, double v)
        {
            if (!double.IsFinite(v) || v <= 0)
            {
                errors.Add($"sliding.{at} must be a finite number above zero");
            }
        }
        Positive("trigger_radius_m", Sliding.TriggerRadiusM);
        Positive("npc_trigger_radius_m", Sliding.NpcTriggerRadiusM);
        Positive("speed_mps", Sliding.SpeedMps);
        if (!double.IsFinite(Sliding.WaitS) || Sliding.WaitS < 0)
        {
            errors.Add("sliding.wait_s must be a finite number, zero or more");
        }
    }
}
