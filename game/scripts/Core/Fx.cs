using System.Collections.Generic;
using Godot;

namespace Brushfire;

/// <summary>
/// Visual effects built at runtime from a handful of shared materials: sparks, dust, smoke,
/// explosions, tracers and bullet-hole decals. Everything is dynamic (lit by light probes,
/// never baked) and cleans itself up.
/// </summary>
public static class Fx
{
    static StandardMaterial3D _additive, _smoke, _tracer;
    static QuadMesh _sparkMesh, _dustMesh, _fireMesh, _smokeMesh;
    static Texture2D _holeAlbedo, _holeNormal, _scorch;
    static readonly Queue<Decal> Decals = new();
    const int MaxDecals = 80;

    static Node Root(Node context) => context.GetTree().CurrentScene ?? context.GetTree().Root;

    static void Init()
    {
        if (_additive != null)
            return;
        var soft = GD.Load<Texture2D>("res://textures/fx/soft_particle.png");
        _additive = new StandardMaterial3D
        {
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
            Transparency = BaseMaterial3D.TransparencyEnum.Alpha,
            BlendMode = BaseMaterial3D.BlendModeEnum.Add,
            BillboardMode = BaseMaterial3D.BillboardModeEnum.Particles,
            VertexColorUseAsAlbedo = true,
            AlbedoTexture = soft,
            DisableReceiveShadows = true,
        };
        _smoke = new StandardMaterial3D
        {
            ShadingMode = BaseMaterial3D.ShadingModeEnum.PerVertex,
            Transparency = BaseMaterial3D.TransparencyEnum.Alpha,
            BillboardMode = BaseMaterial3D.BillboardModeEnum.Particles,
            VertexColorUseAsAlbedo = true,
            AlbedoTexture = GD.Load<Texture2D>("res://textures/fx/smoke_puff.png"),
            DisableReceiveShadows = true,
            Roughness = 1f,
        };
        _tracer = new StandardMaterial3D
        {
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
            Transparency = BaseMaterial3D.TransparencyEnum.Alpha,
            BlendMode = BaseMaterial3D.BlendModeEnum.Add,
            AlbedoColor = new Color(1f, 0.8f, 0.45f, 0.8f),
            DisableReceiveShadows = true,
        };
        _sparkMesh = new QuadMesh { Size = new Vector2(0.05f, 0.05f), Material = _additive };
        _dustMesh = new QuadMesh { Size = new Vector2(0.3f, 0.3f), Material = _smoke };
        _fireMesh = new QuadMesh { Size = new Vector2(1.2f, 1.2f), Material = _additive };
        _smokeMesh = new QuadMesh { Size = new Vector2(1.6f, 1.6f), Material = _smoke };
        _holeAlbedo = GD.Load<Texture2D>("res://textures/fx/bullet_hole.png");
        _holeNormal = GD.Load<Texture2D>("res://textures/fx/bullet_hole_normal.png");
        _scorch = GD.Load<Texture2D>("res://textures/fx/scorch.png");
    }

    static Gradient Ramp(params (float t, Color c)[] stops)
    {
        var offsets = new float[stops.Length];
        var colors = new Color[stops.Length];
        for (int i = 0; i < stops.Length; i++)
            (offsets[i], colors[i]) = stops[i];
        return new Gradient { Offsets = offsets, Colors = colors };
    }

    static CpuParticles3D Burst(Node context, Vector3 pos, Vector3 normal, Mesh mesh, int amount, float lifetime,
        float speedMin, float speedMax, float spread, Vector3 gravity, Gradient ramp, float scaleMin = 0.5f,
        float scaleMax = 1f, float damping = 0f)
    {
        var p = new CpuParticles3D
        {
            Emitting = false,
            OneShot = true,
            Amount = amount,
            Lifetime = lifetime,
            Explosiveness = 1f,
            Randomness = 0.5f,
            Mesh = mesh,
            Direction = Vector3.Up,
            Spread = spread,
            InitialVelocityMin = speedMin,
            InitialVelocityMax = speedMax,
            Gravity = gravity,
            ScaleAmountMin = scaleMin,
            ScaleAmountMax = scaleMax,
            ColorRamp = ramp,
            DampingMin = damping,
            DampingMax = damping,
            CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            LocalCoords = false,
        };
        Root(context).AddChild(p);
        p.GlobalTransform = new Transform3D(BasisFromUp(normal), pos);
        p.Emitting = true;
        p.Finished += p.QueueFree;
        return p;
    }

    public static Basis BasisFromUp(Vector3 up)
    {
        up = up.Normalized();
        Vector3 reference = Mathf.Abs(up.Dot(Vector3.Forward)) > 0.95f ? Vector3.Right : Vector3.Forward;
        Vector3 x = reference.Cross(up).Normalized();
        Vector3 z = x.Cross(up).Normalized();
        return new Basis(x, up, z);
    }

    static void Flash(Node context, Vector3 pos, Color color, float energy, float range, float duration)
    {
        var light = new OmniLight3D
        {
            LightColor = color,
            LightEnergy = energy,
            OmniRange = range,
            ShadowEnabled = false,
            LightBakeMode = Light3D.BakeMode.Disabled,
        };
        Root(context).AddChild(light);
        light.GlobalPosition = pos;
        var tween = light.CreateTween();
        tween.TweenProperty(light, "light_energy", 0f, duration).SetEase(Tween.EaseType.Out).SetTrans(Tween.TransitionType.Quad);
        tween.TweenCallback(Callable.From(light.QueueFree));
    }

    // ------------------------------------------------------------------ public effects

    /// <summary>Bullet hitting level geometry: sparks, dust, decal, sound.</summary>
    public static void Impact(Node context, Vector3 pos, Vector3 normal, Node collider, bool sound = true)
    {
        Init();
        Burst(context, pos + normal * 0.02f, normal, _sparkMesh, 10, 0.35f, 3f, 9f, 55f, new Vector3(0, -15f, 0),
            Ramp((0f, new Color(1f, 0.95f, 0.7f)), (0.4f, new Color(1f, 0.55f, 0.15f)), (1f, new Color(0.6f, 0.1f, 0f, 0f))), 0.4f, 1f);
        Burst(context, pos + normal * 0.05f, normal, _dustMesh, 5, 0.9f, 0.5f, 1.6f, 35f, new Vector3(0, 0.4f, 0),
            Ramp((0f, new Color(0.55f, 0.52f, 0.48f, 0.55f)), (1f, new Color(0.5f, 0.48f, 0.45f, 0f))), 0.6f, 1.4f, 2f);
        SpawnDecal(context, pos, normal, collider, _holeAlbedo, _holeNormal, 0.14f);
        if (sound)
            Audio.Play3D(context, GD.Randf() < 0.5f ? "impact" : "impact_metal", pos, -6f, 0.12f, 6f, 40f);
    }

    /// <summary>Bullet hitting a robot: hot sparks and a spurt of black oil.</summary>
    public static void RobotHit(Node context, Vector3 pos, Vector3 normal)
    {
        Init();
        Burst(context, pos, normal, _sparkMesh, 14, 0.4f, 3f, 10f, 70f, new Vector3(0, -12f, 0),
            Ramp((0f, new Color(0.8f, 0.95f, 1f)), (0.3f, new Color(0.4f, 0.7f, 1f)), (1f, new Color(0.1f, 0.2f, 0.8f, 0f))), 0.4f, 1.1f);
        Burst(context, pos, normal, _dustMesh, 6, 0.6f, 1.5f, 3f, 40f, new Vector3(0, -9f, 0),
            Ramp((0f, new Color(0.05f, 0.05f, 0.05f, 0.9f)), (1f, new Color(0.02f, 0.02f, 0.02f, 0f))), 0.25f, 0.6f);
    }

    public static void MuzzleFlashLight(Node context, Vector3 pos, float energy = 3f)
    {
        Flash(context, pos, new Color(1f, 0.75f, 0.4f), energy, 7f, 0.07f);
    }

    public static void Explosion(Node context, Vector3 pos, float scale = 1f, bool sound = true)
    {
        Init();
        var fire = Burst(context, pos, Vector3.Up, _fireMesh, 28, 0.55f, 1.5f * scale, 6f * scale, 180f,
            new Vector3(0, 1.5f, 0),
            Ramp((0f, new Color(1f, 0.95f, 0.75f)), (0.25f, new Color(1f, 0.6f, 0.15f)),
                (0.6f, new Color(0.7f, 0.18f, 0.03f, 0.7f)), (1f, new Color(0.2f, 0.05f, 0f, 0f))), 0.6f * scale, 1.5f * scale, 4f);
        fire.ScaleAmountCurve = new Curve();
        fire.ScaleAmountCurve.AddPoint(new Vector2(0, 0.4f));
        fire.ScaleAmountCurve.AddPoint(new Vector2(0.3f, 1f));
        fire.ScaleAmountCurve.AddPoint(new Vector2(1, 1.2f));
        Burst(context, pos, Vector3.Up, _smokeMesh, 18, 2.2f, 0.6f * scale, 2.5f * scale, 180f, new Vector3(0, 1.2f, 0),
            Ramp((0f, new Color(0.15f, 0.13f, 0.12f, 0f)), (0.1f, new Color(0.18f, 0.16f, 0.15f, 0.8f)),
                (1f, new Color(0.3f, 0.3f, 0.3f, 0f))), 0.8f * scale, 1.8f * scale, 1.5f);
        Burst(context, pos, Vector3.Up, _sparkMesh, 40, 0.9f, 6f * scale, 16f * scale, 180f, new Vector3(0, -14f, 0),
            Ramp((0f, new Color(1f, 0.9f, 0.6f)), (0.5f, new Color(1f, 0.45f, 0.1f)), (1f, new Color(0.5f, 0.1f, 0f, 0f))), 0.5f, 1.2f);
        Flash(context, pos, new Color(1f, 0.6f, 0.25f), 10f * scale, 9f * scale, 0.45f);
        if (sound)
            Audio.Play3D(context, "explosion", pos, 4f, 0.1f, 18f, 140f);

        // Scorch mark on the nearest surface.
        var space = ((Node3D)context).GetWorld3D().DirectSpaceState;
        var q = PhysicsRayQueryParameters3D.Create(pos + Vector3.Up * 0.5f, pos + Vector3.Down * 2.5f, Layers.World);
        var hit = space.IntersectRay(q);
        if (hit.Count > 0)
            SpawnDecal(context, (Vector3)hit["position"], (Vector3)hit["normal"], hit["collider"].AsGodotObject() as Node,
                _scorch, null, 2.6f * scale);

        var player = PlayerController.Instance;
        if (player != null && !player.IsDead)
        {
            float d = player.GlobalPosition.DistanceTo(pos);
            player.AddTrauma(Mathf.Clamp(1f - d / (14f * scale), 0f, 1f) * 0.75f);
        }
    }

    public static void PlasmaImpact(Node context, Vector3 pos, Vector3 normal, Color color)
    {
        Init();
        Burst(context, pos, normal, _sparkMesh, 18, 0.45f, 2f, 7f, 80f, new Vector3(0, -4f, 0),
            Ramp((0f, Colors.White), (0.3f, color), (1f, new Color(color, 0f))), 0.6f, 1.6f);
        Flash(context, pos, color, 4f, 5f, 0.25f);
        Audio.Play3D(context, "plasma_impact", pos, -2f, 0.1f, 8f, 50f);
    }

    public static void Tracer(Node context, Vector3 from, Vector3 to)
    {
        Init();
        float len = from.DistanceTo(to);
        if (len < 1f)
            return;
        var mesh = new MeshInstance3D
        {
            Mesh = new BoxMesh { Size = new Vector3(0.012f, 0.012f, Mathf.Min(len, 6f)), Material = _tracer },
            CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
        };
        Root(context).AddChild(mesh);
        Vector3 dir = (to - from) / len;
        Vector3 start = from + dir * Mathf.Min(1.5f, len * 0.3f);
        mesh.GlobalTransform = new Transform3D(Basis.LookingAt(dir, Mathf.Abs(dir.Y) > 0.99f ? Vector3.Right : Vector3.Up), start);
        var tween = mesh.CreateTween();
        tween.TweenProperty(mesh, "global_position", to - dir * Mathf.Min(len, 6f) * 0.5f, 0.06f);
        tween.TweenCallback(Callable.From(mesh.QueueFree));
    }

    public static void SpawnDecal(Node context, Vector3 pos, Vector3 normal, Node collider, Texture2D albedo,
        Texture2D normalMap, float size)
    {
        var decal = new Decal
        {
            TextureAlbedo = albedo,
            TextureNormal = normalMap,
            Size = new Vector3(size, Mathf.Max(0.2f, size * 0.25f), size),
            UpperFade = 0.2f,
            LowerFade = 0.2f,
            NormalFade = 0.5f,
            DistanceFadeEnabled = true,
            DistanceFadeBegin = 40f,
            DistanceFadeLength = 10f,
            CullMask = 1, // world layer only: never paint on enemies or the viewmodel
        };
        // Parent to moving geometry (doors) so the hole moves with it.
        Node parent = collider is AnimatableBody3D ? collider : Root(context);
        parent.AddChild(decal);
        var basis = BasisFromUp(normal).Rotated(normal.Normalized(), (float)GD.RandRange(0, Mathf.Tau));
        decal.GlobalTransform = new Transform3D(basis, pos);
        Decals.Enqueue(decal);
        while (Decals.Count > MaxDecals)
        {
            var old = Decals.Dequeue();
            if (GodotObject.IsInstanceValid(old))
                old.QueueFree();
        }
    }

    public static void ClearDecals() => Decals.Clear();
}
