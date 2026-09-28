namespace Brushfire;

/// <summary>
/// Where a weapon's rounds come from when the WeaponManager's own counts don't apply: Undercity
/// keeps rounds in each firearm's magazine and the pack (Undercity.Core's Magazines), so its
/// weapons fire through this (openspec/changes/hub-combat, design section 1). Brushfire's
/// reference maps leave it unset and keep their counts.
/// </summary>
public interface IAmmoSource
{
    /// <summary>False while the weapon can't fire at all (reloading): the trigger does nothing.</summary>
    bool CanFire(Weapon w);

    /// <summary>True when a round is loaded.</summary>
    bool HasRound(Weapon w);

    /// <summary>Takes the round for one shot. False when there wasn't one.</summary>
    bool TakeRound(Weapon w);

    /// <summary>The trigger was pulled on nothing loaded (a reload can start).</summary>
    void DryFired(Weapon w);
}
