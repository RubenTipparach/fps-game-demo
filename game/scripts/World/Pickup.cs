using Godot;

namespace Brushfire;

public enum PickupKind { Health, MegaHealth, Armor, HeavyArmor, Shells, Bullets, Rockets, Chaingun, RocketLauncher }

/// <summary>Spinning, bobbing pickup. Only consumed if the player can actually use it.</summary>
public partial class Pickup : Area3D
{
    [Export] public PickupKind Kind = PickupKind.Health;
    [Export] public int Amount = 25;
    [Export] public NodePath VisualPath = "Visual";
    /// <summary>Key/values from a TrenchBroom item_* entity (filled in by func_godot).</summary>
    [Export] public Godot.Collections.Dictionary func_godot_properties = new();

    Node3D _visual;
    float _time;
    Vector3 _base;

    public override void _Ready()
    {
        if (func_godot_properties.TryGetValue("amount", out var a) && a.AsInt32() > 0)
            Amount = a.AsInt32();
        CollisionLayer = Layers.Pickup;
        CollisionMask = Layers.Player;
        // deferred: drops are spawned by enemies that can die inside a physics callback (lava triggers)
        SetDeferred(Area3D.PropertyName.Monitorable, false);
        _visual = GetNodeOrNull<Node3D>(VisualPath);
        if (_visual != null)
            _base = _visual.Position;
        _time = GD.Randf() * 10f;
        BodyEntered += OnBodyEntered;
    }

    public override void _PhysicsProcess(double delta)
    {
        _time += (float)delta;
        if (_visual == null)
            return;
        _visual.Position = _base + new Vector3(0, Mathf.Sin(_time * 2.4f) * 0.08f, 0);
        _visual.Rotation = new Vector3(0, _time * 1.6f, 0);
    }

    void OnBodyEntered(Node3D body)
    {
        if (body is not PlayerController player || player.IsDead)
            return;
        var w = player.Weapons;
        bool taken;
        string sound;
        string message;
        switch (Kind)
        {
            case PickupKind.Health:
                taken = player.GiveHealth(Amount);
                sound = "pickup_health";
                message = $"+{Amount} health";
                break;
            case PickupKind.MegaHealth:
                taken = player.GiveHealth(Amount, overheal: true);
                sound = "pickup_health";
                message = "MEGA HEALTH";
                break;
            case PickupKind.Armor:
            case PickupKind.HeavyArmor:
                taken = player.GiveArmor(Amount);
                sound = "pickup_armor";
                message = Kind == PickupKind.HeavyArmor ? "Heavy armor" : $"+{Amount} armor";
                break;
            case PickupKind.Shells:
                taken = w.GiveAmmo(AmmoType.Shells, Amount);
                sound = "pickup_ammo";
                message = $"{Amount} shells";
                break;
            case PickupKind.Bullets:
                taken = w.GiveAmmo(AmmoType.Bullets, Amount);
                sound = "pickup_ammo";
                message = $"{Amount} bullets";
                break;
            case PickupKind.Rockets:
                taken = w.GiveAmmo(AmmoType.Rockets, Amount);
                sound = "pickup_ammo";
                message = $"{Amount} rockets";
                break;
            case PickupKind.Chaingun:
                taken = w.GiveWeapon(2, Amount);
                sound = "pickup_weapon";
                message = "You got the CHAINGUN!";
                break;
            case PickupKind.RocketLauncher:
                taken = w.GiveWeapon(3, Amount);
                sound = "pickup_weapon";
                message = "You got the ROCKET LAUNCHER!";
                break;
            default:
                return;
        }
        if (!taken)
            return;
        Audio.Play2D(this, sound, -2f, 0.02f);
        player.Hud.ShowPickup(message);
        QueueFree();
    }
}
