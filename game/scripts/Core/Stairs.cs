using Godot;

namespace Brushfire;

/// <summary>
/// Stair stepping for CharacterBody3D (player and walking enemies). Uses body test-motions:
/// when horizontal movement is blocked by something that is not a walkable slope, try
/// "up, forward, down" and accept the move if we land on walkable ground within MaxStep.
/// </summary>
public static class Stairs
{
    static bool Test(CharacterBody3D body, Transform3D from, Vector3 motion, PhysicsTestMotionResult3D result)
    {
        var p = new PhysicsTestMotionParameters3D { From = from, Motion = motion, Margin = 0.001f };
        return PhysicsServer3D.BodyTestMotion(body.GetRid(), p, result);
    }

    /// <summary>Returns the height climbed (0 if no step was taken). Moves the body when it succeeds.</summary>
    public static float TryStepUp(CharacterBody3D body, float dt, float maxStep)
    {
        Vector3 v = body.Velocity;
        if (v.Y > 0.01f)
            return 0f;
        var move = new Vector3(v.X, 0, v.Z) * dt;
        if (move.LengthSquared() < 1e-6f)
            return 0f;

        Transform3D from = body.GlobalTransform;
        var blocked = new PhysicsTestMotionResult3D();
        if (!Test(body, from, move, blocked))
            return 0f;
        if (blocked.GetCollisionNormal().AngleTo(Vector3.Up) <= body.FloorMaxAngle)
            return 0f; // walkable slope: move_and_slide handles it

        var up = new PhysicsTestMotionResult3D();
        Vector3 rise = Vector3.Up * maxStep;
        Transform3D raised = from.Translated(Test(body, from, rise, up) ? up.GetTravel() : rise);
        var fwd = new PhysicsTestMotionResult3D();
        Vector3 fwdTravel = Test(body, raised, move, fwd) ? fwd.GetTravel() : move;
        if (fwdTravel.Length() < move.Length() * 0.3f)
            return 0f; // still blocked when raised: a wall, not a step
        Transform3D moved = raised.Translated(fwdTravel);
        var down = new PhysicsTestMotionResult3D();
        if (!Test(body, moved, Vector3.Down * (raised.Origin.Y - from.Origin.Y + 0.02f), down))
            return 0f;
        if (down.GetCollisionNormal().AngleTo(Vector3.Up) > body.FloorMaxAngle)
            return 0f;
        Vector3 target = moved.Origin + down.GetTravel();
        float height = target.Y - from.Origin.Y;
        if (height < 0.02f || height > maxStep + 0.01f)
            return 0f;
        body.GlobalPosition = target;
        body.ApplyFloorSnap();
        return height;
    }

    /// <summary>Keeps the body glued to stairs when walking down. Returns the (negative) drop.</summary>
    public static float TryStepDown(CharacterBody3D body, float maxStep)
    {
        if (body.IsOnFloor() || body.Velocity.Y > 0f)
            return 0f;
        var down = new PhysicsTestMotionResult3D();
        if (!Test(body, body.GlobalTransform, Vector3.Down * maxStep, down))
            return 0f;
        if (down.GetCollisionNormal().AngleTo(Vector3.Up) > body.FloorMaxAngle)
            return 0f;
        float dy = down.GetTravel().Y;
        body.GlobalPosition += new Vector3(0, dy, 0);
        body.ApplyFloorSnap();
        return dy;
    }
}
