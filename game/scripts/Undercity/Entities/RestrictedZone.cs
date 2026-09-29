// A restricted zone (the checkpoint, the depot, Precinct 9): the owning faction keeps even its
// own out. Seen inside without leave, the runner is warned, then MerSec turns hostile or the
// trespass is reported as a crime.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): who may be here is data
// (ZoneDef.Allow), and the warning time and the disguise verdict are the core's.

#nullable enable
using Godot;
using Undercity.Core.Perception;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>A restricted zone placed by the level's entity layout.</summary>
public partial class RestrictedZone : Area3D, IWired, IStable
{
    /// <summary>How far a zone's guard notices a trespasser, metres.</summary>
    [Export] public float SightM = 20f;

    private Services? _s;
    private ZoneDef? _def;
    private bool _inside;
    private double _seenS;
    private bool _warned;
    private bool _punished;

    /// <inheritdoc/>
    public string StableId => Entity.StableIdOf(this);

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _s = services;
        if (!services.Level.Def.Zones.TryGetValue(StableId, out _def))
        {
            GD.PushError($"[Undercity] {StableId}: no zone in data/levels/{services.Level.Id}.json");
            return;
        }
        BodyEntered += b => _inside |= b is Brushfire.PlayerController;
        BodyExited += b =>
        {
            if (b is Brushfire.PlayerController)
            {
                _inside = false;
                _seenS = 0;
                _warned = false;
                services.Level.SetRestricted(StableId, 0);
            }
        };
    }

    /// <summary>True when the runner may be here: the zone's conditions hold, or their disguise as its faction holds up.</summary>
    private bool Allowed(NpcActor? guard)
    {
        if (_s!.State.Holds(_def!.Allow))
        {
            return true;
        }
        return guard is not null && _s.State.Inventory.OutfitFaction == _def.Faction
            && guard.Judge(guard.GlobalPosition.DistanceTo(_s.Level.Player.GlobalPosition), talking: false).Verdict
                is Verdict.Accepted or Verdict.Suspicious;
    }

    public override void _Process(double delta)
    {
        if (_s is null || _def is null || !_inside || _punished)
        {
            return;
        }
        var level = _s.Level as UndercityLevel;
        var guard = level?.Seer(n => n.Faction == _def.Faction && n.Alive, SightM);
        if (guard is null || Allowed(guard))
        {
            _s.Level.SetRestricted(StableId, 0);
            return;
        }
        _seenS += delta;
        _s.Level.SetRestricted(StableId, _seenS);
        if (!_warned)
        {
            _warned = true;
            guard.Say("zone_warning", "You can't be here.");
            _s.Screens.ShowAlert($"{guard.DisplayName}: you can't be here.");
        }
        else if (_seenS > _s.Data.Perception.Disguise.RestrictedWarningS)
        {
            _punished = true;
            if (guard.IsLaw)
            {
                level!.TurnLawHostile(guard);
            }
            else
            {
                _s.State.ReportCrime(guard.DisplayName);
            }
        }
    }
}
