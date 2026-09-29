using Godot;

namespace Brushfire;

public enum DisguiseVerdict
{
    /// <summary>Not wearing this observer's colours: normal faction stance applies.</summary>
    NotDisguised,
    /// <summary>They take you for one of their own.</summary>
    Accepted,
    /// <summary>Something's off (wrong armour, creeping about): their suspicion meter fills.</summary>
    Suspicious,
    /// <summary>They see through it, or you gave yourself away.</summary>
    Blown,
}

/// <summary>
/// Disguise rules (docs/design/immersive_sim.md section 5):
///   Q = matching pieces worn (body 2, head 1, face 1); Cover = Deception + Q.
///   Outside an observer's scrutiny range (2 + 2 x I metres) a matching outfit passes at a glance.
///   Inside it (and always when talking) the observer accepts you only if Cover >= I.
///   A drawn weapon, a restricted zone or a fight blow any disguise; foreign armour is suspicious.
/// </summary>
public static class Disguise
{
    static GameState S => Game.Instance?.State;

    public static string Faction => S?.Inventory.DisguiseFaction ?? "";
    public static int Quality => S?.Inventory.DisguiseQuality ?? 0;
    public static int Deception => S?.Character.Get(Skill.Deception) ?? 0;
    public static int Cover => Deception + Quality;

    public static float ScrutinyRange(int intelligence) => (2f + 2f * intelligence) * (Deception >= 5 ? 0.5f : 1f);

    /// <summary>How long a drawn weapon is tolerated (Master of Disguise, Deception 3).</summary>
    public static float WeaponGrace => Deception >= 3 ? 2f : 0f;

    public static bool WeaponGivesAway
    {
        get
        {
            var w = PlayerController.Instance?.Weapons;
            return w != null && w.DrawnTime > WeaponGrace;
        }
    }

    /// <summary>The player is in a zone this faction keeps even its own members out of.</summary>
    public static bool InRestrictedZone(string faction)
    {
        var p = PlayerController.Instance;
        if (p == null)
            return false;
        foreach (var n in p.GetTree().GetNodesInGroup("restricted"))
            if (n is RestrictedZone z && z.Faction == faction && z.Contains(p.GlobalPosition))
                return true;
        return false;
    }

    public static DisguiseVerdict Judge(string observerFaction, int intelligence, float distance, bool talking = false)
    {
        if (string.IsNullOrEmpty(observerFaction) || Faction != observerFaction || Quality <= 0)
            return DisguiseVerdict.NotDisguised;
        if (WeaponGivesAway || InRestrictedZone(observerFaction))
            return DisguiseVerdict.Blown;
        bool close = talking || distance <= ScrutinyRange(intelligence);
        if (close && Cover < intelligence)
            return DisguiseVerdict.Blown;
        if (S.Inventory.ArmorClashes)
            return DisguiseVerdict.Suspicious;
        var p = PlayerController.Instance;
        // Creeping or sprinting around guards up close is not how their people move.
        if (close && p != null && (p.Crouched || p.Sprinting))
            return DisguiseVerdict.Suspicious;
        return DisguiseVerdict.Accepted;
    }
}

/// <summary>An area a faction keeps everyone out of (boss offices, hostage cages). Box-shaped.</summary>
public partial class RestrictedZone : Node3D
{
    [Export] public string Faction = "";
    [Export] public Vector3 Size = new(4, 3, 4);

    public override void _Ready() => AddToGroup("restricted");

    public bool Contains(Vector3 p)
    {
        Vector3 local = GlobalTransform.AffineInverse() * p;
        return Mathf.Abs(local.X) <= Size.X / 2 && local.Y >= 0 && local.Y <= Size.Y && Mathf.Abs(local.Z) <= Size.Z / 2;
    }
}
