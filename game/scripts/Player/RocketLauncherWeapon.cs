using Godot;

namespace Brushfire;

/// <summary>Rocket launcher: fires a projectile that converges on the crosshair.</summary>
public partial class RocketLauncherWeapon : Weapon
{
    [Export] public PackedScene ProjectileScene;

    protected override void Fire()
    {
        PlayFireEffects();
        var player = Player;
        Vector3 eye = player.EyePosition;
        Basis aim = Basis.FromEuler(new Vector3(player.Pitch, player.Yaw, 0f));
        Vector3 forward = -aim.Z;
        var space = player.GetWorld3D().DirectSpaceState;
        var exclude = new Godot.Collections.Array<Rid> { player.GetRid() };

        // Where is the crosshair pointing?
        var aimQuery = PhysicsRayQueryParameters3D.Create(eye, eye + forward * 300f, Layers.World | Layers.Enemy);
        aimQuery.Exclude = exclude;
        var aimHit = space.IntersectRay(aimQuery);
        Vector3 target = aimHit.Count > 0 ? (Vector3)aimHit["position"] : eye + forward * 300f;

        // Spawn slightly right/below the eye, like it leaves the tube; if a wall is in the way,
        // detonate right there (point-blank rockets hurt, as they should).
        Vector3 spawn = eye + forward * 0.55f + aim.X * 0.14f - aim.Y * 0.12f;
        var block = PhysicsRayQueryParameters3D.Create(eye, spawn, Layers.World | Layers.Enemy);
        block.Exclude = exclude;
        var blockHit = space.IntersectRay(block);
        if (blockHit.Count > 0)
            spawn = (Vector3)blockHit["position"] - forward * 0.05f;

        Vector3 dir = (target - spawn).Normalized();
        if (dir.Dot(forward) < 0.8f)
            dir = forward;
        var rocket = ProjectileScene.Instantiate<Projectile>();
        GetTree().CurrentScene.AddChild(rocket);
        rocket.Launch(spawn, dir, player, Layers.World | Layers.Enemy);
        if (blockHit.Count > 0)
            rocket.ForceImpact(spawn, -forward, blockHit["collider"].AsGodotObject());
    }
}
