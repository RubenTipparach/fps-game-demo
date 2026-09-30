// The placement check (scenes/undercity/tests/placement_test.tscn): loads a level's real sector
// glbs, with the NPCs, civilians and spawn points the importer placed in them, and tests every
// person with their own collider against the level's physics (openspec/specs/level-geometry,
// "People stand clear of the level"). A person passes when their capsule, lifted just off the
// floor, overlaps no world collider and no other person, and the floor is right under their feet.
// Every stop on an NPC's patrol is tested the same way. Every ladder out of the water is tested
// with the player's collider: its foot at least 0.5 m under the surface, room to climb its whole
// height, and room to stand on the floor at its top (openspec/changes/archive/2026-09-29-water-and-swimming). Every
// accessory a civilian's role may give them is tested in its mount's pose, on every body of the
// role's pool at both ends of the height range, against the level: an umbrella held up into a
// wall, or a bag hanging into a counter, fails (openspec/changes/archive/2026-09-29-crowd-variety, task 3.3). From
// 1 m outside every exterior door of an enterable building (the level data's "approaches"), the
// level's baked navmesh must reach the runner's spawn (openspec/changes/hub-doorways, "Every
// door opens onto ground a person can reach"). Every parked vehicle in the level data (the plan's
// list) stands in the built level as a static mesh of the sector that owns its ground, where and as
// the plan put it, with its collision, baked in that sector's lightmap (openspec/changes/vehicle-fixes).
// Prints PASS or FAIL per check and quits with 1 on any failure.
//
//   flock /tmp/undercity-godot.lock timeout 900 godot --headless --path game res://scenes/undercity/tests/placement_test.tscn
//
// It lives beside the entity scripts because it loads the real level, the real NPC scene and the
// real player scene rather than copies of their sizes (CLAUDE.md 5.6). The layout's own check
// (tools/levels/city_plan.py, check_standing_room) catches most of this before a build, against
// the plan's boxes; this one also covers what isn't a box: stalls, lamps, bollards, stairs, props.

#nullable enable
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Brushfire;
using Godot;
using Undercity.Core;
using GArray = Godot.Collections.Array<Godot.Rid>;

namespace Undercity.Client;

/// <summary>The headless placement check.</summary>
public partial class PlacementTest : Node3D
{
    /// <summary>The level folder whose sector glbs are loaded.</summary>
    [Export] public string LevelDir { get; set; } = "res://levels/undercity/hub";

    /// <summary>How far the body is lifted off the floor for the overlap test, metres: the floor
    /// itself touches the capsule's foot and isn't an overlap.</summary>
    [Export] public float LiftM { get; set; } = 0.03f;

    /// <summary>How far the floor may be from a person's feet, metres, above or below.</summary>
    [Export] public float FloorToleranceM { get; set; } = 0.05f;

    /// <summary>How high above a patrol stop the floor search starts, metres over the NPC's own
    /// floor (patrols walk the streets, under the canopies).</summary>
    [Export] public float PatrolProbeM { get; set; } = 1.5f;

    private const string PlayerScene = "res://scenes/undercity/player.tscn";

    private int _people;
    private int _fail;

    /// <inheritdoc/>
    public override async void _Ready()
    {
        try
        {
            var glbs = DirAccess.GetFilesAt(LevelDir).Where(f => f.EndsWith(".glb", StringComparison.Ordinal))
                .Order(StringComparer.Ordinal).ToArray();
            if (glbs.Length == 0)
            {
                throw new InvalidOperationException($"{LevelDir} has no sector glbs");
            }
            foreach (var f in glbs)
            {
                // Named after its file (hub_streets): every sector glb's root is the level's name,
                // and the car checks tell sectors apart by it (SectorOf).
                var sector = GD.Load<PackedScene>($"{LevelDir}/{f}").Instantiate();
                sector.Name = f.GetBaseName();
                AddChild(sector);
            }
            // The level's trimeshes are one-sided, and a query ignores a face it sees from
            // behind, so a body whose centre is inside a solid (a counter, a hull) would touch
            // nothing. In this test only, every face counts from both sides.
            foreach (var shape in FindChildren("*", nameof(CollisionShape3D), true, false).OfType<CollisionShape3D>()
                         .Select(c => c.Shape).OfType<ConcavePolygonShape3D>())
            {
                shape.BackfaceCollision = true;
            }
            // The colliders join the physics space on the next physics frames.
            for (var i = 0; i < 3; i++)
            {
                await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
            }
            var npcs = People("ent_npc").Concat(People("ent_civ")).ToList();
            foreach (var npc in npcs)
            {
                CheckNpc(npc);
            }
            CheckSpawns();
            CheckLadders();
            CheckParkedCars();
            await CheckApproaches();
            await CheckAccessories();
        }
        catch (Exception e)
        {
            GD.PrintErr($"FAIL [placement_test] {e}");
            _fail++;
        }
        GD.Print($"[placement_test] {_people - _fail} of {_people} placements passed");
        GetTree().Quit(_fail > 0 ? 1 : 0);
    }

    private IEnumerable<CollisionObject3D> People(string group) =>
        GetTree().GetNodesInGroup(group).OfType<CollisionObject3D>().OrderBy(n => n.Name.ToString(), StringComparer.Ordinal);

    private static CollisionShape3D ColliderOf(Node body) =>
        body.GetChildren().OfType<CollisionShape3D>().FirstOrDefault()
        ?? throw new InvalidOperationException($"{body.Name} has no CollisionShape3D");

    private void CheckNpc(CollisionObject3D npc)
    {
        var col = ColliderOf(npc);
        var feet = npc.GlobalTransform;
        Check($"{npc.Name}", col.Shape, feet, col.Transform, new[] { npc.GetRid() }, Layers.World | Layers.Enemy);
        var patrol = npc.HasMeta("patrol") ? npc.GetMeta("patrol").AsString() : "";
        var stops = patrol.Split(';', StringSplitOptions.RemoveEmptyEntries);
        for (var i = 0; i < stops.Length; i++)
        {
            // Layout metres, x east and y south: Godot's x and z.
            var xy = stops[i].Split(',');
            var x = float.Parse(xy[0], CultureInfo.InvariantCulture);
            var z = float.Parse(xy[1], CultureInfo.InvariantCulture);
            var floor = FloorBelow(new Vector3(x, feet.Origin.Y + PatrolProbeM, z), PatrolProbeM * 2, Array.Empty<Rid>());
            if (floor is not { } y)
            {
                Fail($"{npc.Name} patrol stop {i} ({xy[0]}, {xy[1]}): no floor under it");
                continue;
            }
            // Against the world only: whoever stands on a stop now will have walked on.
            Check($"{npc.Name} patrol stop {i}", col.Shape, new Transform3D(feet.Basis, new Vector3(x, y, z)),
                col.Transform, new[] { npc.GetRid() }, Layers.World);
        }
    }

    // The player's own collider at every spawn marker (the game drops the player 0.05 m above it).
    private void CheckSpawns()
    {
        var player = GD.Load<PackedScene>(PlayerScene).Instantiate<Node3D>();
        var col = ColliderOf(player);
        foreach (var spawn in GetTree().GetNodesInGroup("ent_spawn").OfType<Node3D>()
                     .OrderBy(n => n.Name.ToString(), StringComparer.Ordinal))
        {
            Check($"{spawn.Name}", col.Shape, spawn.GlobalTransform, col.Transform, Array.Empty<Rid>(), Layers.World | Layers.Enemy);
        }
        player.Free();
    }

    /// <summary>A walk ends at the spawn when the navmesh path's last point is this near it, metres.</summary>
    private const float ReachedM = 1.0f;

    /// <summary>The frames the navmesh has to reach the navigation map before the walks give up.</summary>
    private const int NavSyncFrames = 600;

    // Every exterior door's approach reaches the runner's spawn on the level's baked navmesh: the
    // walk starts 1 m outside the door, on the navmesh there, and must end at the spawn.
    /// <summary>How far a parked vehicle may stand from its place in the level data, metres.</summary>
    private const float CarPlaceToleranceM = 0.05f;

    /// <summary>How far a parked vehicle's heading may be from the level data's, degrees.</summary>
    private const float CarHeadingToleranceDeg = 1f;

    /// <summary>A parked car's lightmap texel over the level's (city_plan.py, CAR_EXTRAS): 0.1 m against 0.4 m.</summary>
    private const float CarTexelScale = 4f;

    // Every parked vehicle in the level data is a static mesh of the level, car_<id>, built into the
    // sector that owns the ground under it (openspec/changes/vehicle-fixes, design section 2.2): where
    // and as the plan put it, beside its ENT_car marker, with its static body, the ground a ray finds
    // under it belonging to its own sector, and a user of that sector's baked lightmap, at the car's
    // texel scale. The lightmap is read from the level's committed .lmbake, so the check holds after
    // a bake, not before one.
    private void CheckParkedCars()
    {
        var level = LevelDir.TrimEnd('/').Split('/')[^1];
        var def = GameData.Load(new GodotDataSource()).Levels.GetValueOrDefault(level);
        if (def is null)
        {
            return;
        }
        var markers = GetTree().GetNodesInGroup("ent_car").OfType<Node3D>()
            .ToDictionary(n => n.GetMeta("id", "").AsString(), StringComparer.Ordinal);
        foreach (var extra in markers.Keys.Where(id => def.Cars.All(c => c.Id != id)).Order(StringComparer.Ordinal))
        {
            _people++;
            Fail($"car_{extra}: in the built level, not in the level data");
        }
        var lightmaps = new Dictionary<string, HashSet<string>>(StringComparer.Ordinal);
        foreach (var car in def.Cars)
        {
            _people++;
            var who = $"car_{car.Id} ({car.Model})";
            var mesh = FindChildren($"car_{car.Id}", nameof(MeshInstance3D), true, false).OfType<MeshInstance3D>().FirstOrDefault();
            var body = FindChildren($"car_{car.Id}_box", nameof(StaticBody3D), true, false).OfType<StaticBody3D>()
                .FirstOrDefault(b => b.GetChildren().OfType<CollisionShape3D>().Any());
            if (!markers.TryGetValue(car.Id, out var marker) || mesh is null)
            {
                Fail($"{who}: {(mesh is null ? "no static mesh" : "no ENT_car marker")} in the built level");
                continue;
            }
            var sector = SectorOf(mesh);
            var at = mesh.GlobalPosition;
            var off = new Vector2(at.X - (float)car.At[0], at.Z - (float)car.At[1]).Length();
            var front = -mesh.GlobalBasis.Z;
            var heading = Mathf.PosMod(Mathf.RadToDeg(Mathf.Atan2(front.X, -front.Z)), 360f);
            var turn = Mathf.Abs(Mathf.PosMod(heading - (float)car.HeadingDeg + 180f, 360f) - 180f);
            var material = mesh.GetActiveMaterial(0)?.ResourceName ?? "";
            var ground = body is null ? null : GroundSector(at, body.GetRid());
            var users = sector is null ? null : LightmapUsers(level, sector, lightmaps);
            if (marker.GetMeta("model", "").AsString() != car.Model || material != $"veh_psx_{car.Model}")
            {
                Fail($"{who}: the built level has model '{marker.GetMeta("model", "")}', material '{material}'");
            }
            else if (off > CarPlaceToleranceM || marker.GlobalPosition.DistanceTo(at) > CarPlaceToleranceM)
            {
                Fail($"{who}: stands {off:0.00} m from ({car.At[0]}, {car.At[1]}), its marker {marker.GlobalPosition.DistanceTo(at):0.00} m from it");
            }
            else if (turn > CarHeadingToleranceDeg)
            {
                Fail($"{who}: faces {heading:0.#} degrees, not {car.HeadingDeg:0.#}");
            }
            else if (body is null)
            {
                Fail($"{who}: has no static body (car_{car.Id}_box)");
            }
            else if (ground != sector)
            {
                Fail($"{who}: stands in the {sector} sector on the {ground ?? "(no)"} sector's ground");
            }
            else if (mesh.GIMode != GeometryInstance3D.GIModeEnum.Static || !Mathf.IsEqualApprox(mesh.GILightmapTexelScale, CarTexelScale))
            {
                Fail($"{who}: bakes as {mesh.GIMode} at texel scale {mesh.GILightmapTexelScale}, not static at {CarTexelScale}");
            }
            else if (users is null || !users.Contains($"../Geometry/{mesh.Name}"))
            {
                Fail($"{who}: not a user of the {sector} sector's lightmap ({level}_{sector}.lmbake)");
            }
            else
            {
                GD.Print($"PASS [placement_test] {who} at ({at.X:0.#}, {at.Z:0.#}) facing {heading:0.#}: a static mesh of the "
                         + $"{sector} sector on its ground, with its body, in its lightmap");
            }
        }
    }

    /// <summary>The sector a node was built into, from its sector glb's root, which _Ready names
    /// after the file ("hub_streets" for the streets).</summary>
    private string? SectorOf(Node node)
    {
        var level = LevelDir.TrimEnd('/').Split('/')[^1];
        for (var n = node; n is not null && n != this; n = n.GetParent())
        {
            if (n.GetParent() == this && n.Name.ToString().StartsWith(level + "_", StringComparison.Ordinal))
            {
                return n.Name.ToString()[(level.Length + 1)..];
            }
        }
        return null;
    }

    /// <summary>The sector of the world collider a ray finds under a point, the car's own body aside.</summary>
    private string? GroundSector(Vector3 at, Rid own)
    {
        var from = at + Vector3.Up * 1.0f;
        var q = PhysicsRayQueryParameters3D.Create(from, from + Vector3.Down * 2.0f, Layers.World, new GArray { own });
        var hit = GetWorld3D().DirectSpaceState.IntersectRay(q);
        return hit.Count > 0 && hit["collider"].AsGodotObject() is Node n ? SectorOf(n) : null;
    }

    /// <summary>The node paths a sector's baked lightmap lists as its users, from the LightmapGI (a
    /// sibling of the sector's "Geometry" in the level scene), or null when the sector has no bake.</summary>
    private HashSet<string>? LightmapUsers(string level, string sector, Dictionary<string, HashSet<string>> cache)
    {
        if (!cache.TryGetValue(sector, out var users))
        {
            var path = $"{LevelDir.TrimEnd('/')}/{level}_{sector}.lmbake";
            var data = ResourceLoader.Exists(path) ? GD.Load<LightmapGIData>(path) : null;
            users = data is null ? null! : Enumerable.Range(0, data.GetUserCount())
                .Select(i => data.GetUserPath(i).ToString()).ToHashSet(StringComparer.Ordinal);
            cache[sector] = users;
        }
        return users;
    }

    private async Task CheckApproaches()
    {
        var level = LevelDir.TrimEnd('/').Split('/')[^1];
        var def = GameData.Load(new GodotDataSource()).Levels.GetValueOrDefault(level);
        if (def is null || def.Approaches.Count == 0)
        {
            return;
        }
        var region = new NavigationRegion3D { NavigationMesh = GD.Load<NavigationMesh>($"{LevelDir}/{level}_navmesh.res") };
        AddChild(region);
        var map = GetWorld3D().NavigationMap;
        var spawn = GetTree().GetNodesInGroup("ent_spawn").OfType<Node3D>().FirstOrDefault(n => n.Name == "spawn_start")
                    ?? GetTree().GetNodesInGroup("ent_spawn").OfType<Node3D>().FirstOrDefault();
        if (spawn is null)
        {
            Fail("approaches: the level has no spawn to walk to");
            return;
        }
        // Godot syncs a region into its map on a worker thread, over several frames for a mesh this
        // size (12 for the hub's 5,000 polygons). Until then every query answers the origin, so wait
        // until the spawn's floor is on the map.
        var goal = Vector3.Zero;
        for (var i = 0; i < NavSyncFrames && goal.DistanceTo(spawn.GlobalPosition) > ReachedM; i++)
        {
            await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
            goal = NavigationServer3D.MapGetClosestPoint(map, spawn.GlobalPosition);
        }
        if (goal.DistanceTo(spawn.GlobalPosition) > ReachedM)
        {
            Fail($"approaches: after {NavSyncFrames} frames the navmesh is still {goal.DistanceTo(spawn.GlobalPosition):0.00} m from the spawn");
            return;
        }
        foreach (var a in def.Approaches)
        {
            _people++;
            var outside = new Vector3((float)a.At[0], 0, (float)a.At[1]);
            var floor = FloorBelow(outside + Vector3.Up * 2.0f, 3.0f, Array.Empty<Rid>()) ?? 0f;
            var from = outside with { Y = floor };
            var start = NavigationServer3D.MapGetClosestPoint(map, from);
            var off = new Vector2(start.X - from.X, start.Z - from.Z).Length();
            var path = NavigationServer3D.MapGetPath(map, start, goal, true);
            var at = $"({outside.X:0.#}, {outside.Z:0.#})";
            if (off > ReachedM)
            {
                Fail($"door {a.Door} ({a.Kind}): the navmesh is {off:0.00} m from {at}, 1 m outside the door");
            }
            else if (path.Length == 0 || path[^1].DistanceTo(goal) > ReachedM)
            {
                var end = path.Length == 0 ? "nowhere" : $"({path[^1].X:0.#}, {path[^1].Z:0.#})";
                Fail($"door {a.Door} ({a.Kind}): the navmesh from {at} ends at {end}, not the spawn");
            }
            else
            {
                GD.Print($"PASS [placement_test] door {a.Door} ({a.Kind}): {at} reaches the spawn in {path.Length} points");
            }
        }
        // Everyone stands on the navmesh: a person who fights, flees or cowers moves on it, and one
        // whose spot fell off it (Tank's aisle behind the Anchor's bar, once the door beside it was
        // framed) stands frozen. Where they can walk from there isn't asserted: the baked mesh
        // treats a locked door as a wall (Silk's back room), and the Pit's floor isn't joined to the
        // street (docs/validation/2026-09-29-hub-doorways.md, found while building).
        foreach (var npc in People("ent_npc").Concat(People("ent_civ")))
        {
            _people++;
            var feet = npc.GlobalPosition;
            var on = NavigationServer3D.MapGetClosestPoint(map, feet);
            var off = new Vector2(on.X - feet.X, on.Z - feet.Z).Length();
            if (off > NavStandM)
            {
                Fail($"{npc.Name} at ({feet.X:0.#}, {feet.Z:0.#}): the navmesh is {off:0.00} m away, at ({on.X:0.#}, {on.Z:0.#})");
            }
        }
    }

    /// <summary>A person stands on the navmesh when it is this near their feet, metres: the mesh
    /// keeps its agent's 0.4 m off walls, and a person may stand closer.</summary>
    private const float NavStandM = 0.5f;

    /// <summary>How far under the water's surface a ladder's foot must reach, metres: a floating
    /// swimmer's hands are there (openspec/changes/archive/2026-09-29-water-and-swimming, task 4.2).</summary>
    private const float LadderUnderM = 0.5f;

    // Each ladder, with the player's own collider: its foot under the water, the climb clear from
    // a floating swimmer's feet to over the top, and the floor at the top where the climb ends.
    private void CheckLadders()
    {
        var player = GD.Load<PackedScene>(PlayerScene).Instantiate<Node3D>();
        var col = ColliderOf(player);
        var radius = col.Shape is CylinderShape3D c ? c.Radius : 0.4f;
        var data = Session.Data;
        var level = LevelId;
        var water = new LevelWater(data.Levels[level].Water, data.Water);
        var ladders = GetTree().GetNodesInGroup("ladders").OfType<Ladder>().OrderBy(n => n.Name.ToString(), StringComparer.Ordinal).ToList();
        if (ladders.Count == 0 && data.Levels[level].Water.Count > 0)
        {
            Fail($"{level} has water and no ladders");
        }
        foreach (var l in ladders)
        {
            var hold = l.HoldPoint(radius, 0);
            if (water.SurfaceAt(hold) is not { } surface)
            {
                Fail($"{l.Name}: no water under the ladder");
                continue;
            }
            _people++;
            if (l.BottomM > surface - LadderUnderM)
            {
                Fail($"{l.Name}: its foot is at {l.BottomM:0.00} m, less than {LadderUnderM} m under the surface ({surface:0.00} m)");
            }
            else
            {
                GD.Print($"PASS [placement_test] {l.Name} reaches {surface - l.BottomM:0.00} m under the surface");
            }
            var eye = 1.62f;
            for (var y = surface + (float)data.Water.FloatEyeAboveM - eye; y < l.TopM + 0.06f; y += 0.25f)
            {
                var feet = l.HoldPoint(radius, Math.Min(y, l.TopM + 0.05f));
                if (!Clear($"{l.Name} climb at {feet.Y:0.00} m", col.Shape, new Transform3D(Basis.Identity, feet), col.Transform))
                {
                    break;
                }
            }
            Clear($"{l.Name} step in over the top", col.Shape, new Transform3D(Basis.Identity,
                new Vector3(l.Landing.X, l.TopM + 0.02f, l.Landing.Z)), col.Transform);
            Check($"{l.Name} landing", col.Shape, new Transform3D(Basis.Identity, l.Landing), col.Transform, Array.Empty<Rid>(), Layers.World | Layers.Enemy);
        }
        player.Free();
    }

    private string LevelId => LevelDir.TrimEnd('/').Split('/').Last();

    // Each civilian's accessories, as the crowd rule may give them (the umbrella only in the open),
    // in the pose of their mount, on each body of the role's pool at the smallest and largest
    // scale, turned as the civilian stands. The first placement that touches the level fails.
    private async Task CheckAccessories()
    {
        var data = Session.Data;
        var crowd = data.Crowd;
        var places = data.Levels[LevelId].Crowd;
        var shapes = crowd.Accessories.Keys.Order(StringComparer.Ordinal).ToDictionary(id => id, PropShapes, StringComparer.Ordinal);
        var mounts = new Dictionary<string, Dictionary<string, Transform3D>>(StringComparer.Ordinal);
        foreach (var body in crowd.BodyPools.Values.SelectMany(p => p).Distinct().Order(StringComparer.Ordinal))
        {
            mounts[body] = await MountsOf(body, data.NpcBodies);
        }
        var scales = crowd.ScaleRange.Select(s => (float)s).Distinct().ToArray();
        foreach (var civ in People("ent_civ"))
        {
            var sid = $"{LevelId}:{Entity.Meta(civ, "id")}";
            if (!places.TryGetValue(sid, out var place))
            {
                Fail($"{civ.Name}: the level's crowd block doesn't place {sid}");
                continue;
            }
            var role = crowd.Roles[crowd.RoleFor(place.District)];
            foreach (var id in role.Accessories.Where(a => a != crowd.Umbrella || !place.Sheltered))
            {
                _people++;
                var mount = crowd.Accessories[id].Mount;
                var hit = crowd.BodyPools[role.Bodies].SelectMany(b => scales.Select(s => (Body: b, Scale: s)))
                    .Select(v => (v.Body, v.Scale, Hits: Overlaps(shapes[id],
                        civ.GlobalTransform * new Transform3D(new Basis(Vector3.Up, Mathf.Pi).Scaled(Vector3.One * v.Scale), Vector3.Zero)
                        * mounts[v.Body][mount])))
                    .FirstOrDefault(v => v.Hits.Count > 0);
                if (hit.Hits is { Count: > 0 })
                {
                    Fail($"{civ.Name} with {id} ({hit.Body} at {hit.Scale:0.00}): it overlaps {string.Join(", ", hit.Hits)}");
                }
                else
                {
                    GD.Print($"PASS [placement_test] {civ.Name} with {id}");
                }
            }
        }
    }

    // A prop's convex parts, from its glb: one shape per mesh, with the mesh's place in the prop.
    private static List<(Shape3D Shape, Transform3D Local)> PropShapes(string id)
    {
        var prop = GD.Load<PackedScene>($"res://models/undercity/props/{id}.glb").Instantiate<Node3D>();
        var parts = prop.FindChildren("*", nameof(MeshInstance3D), true, false).OfType<MeshInstance3D>()
            .Select(m => ((Shape3D)m.Mesh.CreateConvexShape(), RelativeTo(prop, m))).ToList();
        prop.Free();
        return parts;
    }

    private static Transform3D RelativeTo(Node3D root, Node3D node)
    {
        var x = Transform3D.Identity;
        for (Node? n = node; n is Node3D n3 && n != root; n = n.GetParent())
        {
            x = n3.Transform * x;
        }
        return x;
    }

    // Where each mount is on a body, relative to the body's root, in the mount's pose (the idle
    // for a bone-aligned mount, which follows whatever the body plays).
    private async Task<Dictionary<string, Transform3D>> MountsOf(string body, Undercity.Core.World.NpcBodyTable table)
    {
        var model = GD.Load<PackedScene>($"res://scenes/undercity/npcs/{body}.tscn").Instantiate<Node3D>();
        AddChild(model);
        var anim = model.GetNode<AnimationPlayer>("Anim");
        var result = new Dictionary<string, Transform3D>(StringComparer.Ordinal);
        foreach (var group in table.Mounts.GroupBy(m => m.Value.Pose.Length > 0 ? m.Value.Pose : "idle").OrderBy(g => g.Key, StringComparer.Ordinal))
        {
            var clip = table.Clip(group.Key) ?? throw new InvalidOperationException($"no clip for the state '{group.Key}'");
            anim.Play(clip);
            anim.Seek(anim.CurrentAnimationLength, true);
            for (var i = 0; i < 2; i++)
            {
                await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
            }
            foreach (var (id, _) in group)
            {
                var node = model.FindChild(id, true, false) as Node3D
                    ?? throw new InvalidOperationException($"{body}.tscn has no mount '{id}'; run tools/godot/gen_npc_scenes.gd");
                result[id] = model.GlobalTransform.AffineInverse() * node.GlobalTransform;
            }
        }
        model.QueueFree();
        return result;
    }

    private List<string> Overlaps(List<(Shape3D Shape, Transform3D Local)> parts, Transform3D at)
    {
        var space = GetWorld3D().DirectSpaceState;
        return parts.SelectMany(p => space.IntersectShape(new PhysicsShapeQueryParameters3D
            {
                Shape = p.Shape,
                Transform = at * p.Local,
                CollisionMask = Layers.World,
            }, 8))
            .Select(h => h["collider"].As<Node>())
            .Where(n => n is not null)
            .Select(n => $"{n.GetParent()?.Name}/{n.Name}")
            .Distinct(StringComparer.Ordinal)
            .ToList();
    }

    // Overlap only: nothing in the level where the body is.
    private bool Clear(string who, Shape3D shape, Transform3D feet, Transform3D shapeLocal)
    {
        _people++;
        var q = new PhysicsShapeQueryParameters3D
        {
            Shape = shape,
            Transform = feet * shapeLocal,
            CollisionMask = Layers.World | Layers.Enemy,
        };
        var hits = GetWorld3D().DirectSpaceState.IntersectShape(q, 8).Select(h => h["collider"].As<Node>())
            .Where(n => n is not null).Select(n => $"{n.GetParent()?.Name}/{n.Name}").Distinct(StringComparer.Ordinal).ToList();
        if (hits.Count > 0)
        {
            Fail($"{who}: the body overlaps {string.Join(", ", hits)}");
            return false;
        }
        return true;
    }

    private void Check(string who, Shape3D shape, Transform3D feet, Transform3D shapeLocal, Rid[] exclude, uint mask)
    {
        _people++;
        var space = GetWorld3D().DirectSpaceState;
        var q = new PhysicsShapeQueryParameters3D
        {
            Shape = shape,
            Transform = new Transform3D(feet.Basis, feet.Origin + Vector3.Up * LiftM) * shapeLocal,
            CollisionMask = mask,
            Exclude = new GArray(exclude),
        };
        var hits = space.IntersectShape(q, 8)
            .Select(h => h["collider"].As<Node>())
            .Where(n => n is not null)
            .Select(n => $"{n.GetParent()?.Name}/{n.Name}")
            .Distinct(StringComparer.Ordinal)
            .ToList();
        var at = $"({feet.Origin.X:0.##}, {feet.Origin.Z:0.##}) at {feet.Origin.Y:0.##} m";
        if (hits.Count > 0)
        {
            Fail($"{who} {at}: the body overlaps {string.Join(", ", hits)}");
            return;
        }
        var floor = FloorBelow(feet.Origin + Vector3.Up * 0.5f, 1.0f, exclude);
        if (floor is not { } y)
        {
            Fail($"{who} {at}: no floor within 0.5 m under the feet");
            return;
        }
        var gap = feet.Origin.Y - y;
        if (Math.Abs(gap) > FloorToleranceM)
        {
            Fail($"{who} {at}: the floor is {gap:0.00} m {(gap > 0 ? "below" : "above")} the feet");
            return;
        }
        GD.Print($"PASS [placement_test] {who} {at}");
    }

    private float? FloorBelow(Vector3 from, float depth, Rid[] exclude)
    {
        var q = PhysicsRayQueryParameters3D.Create(from, from + Vector3.Down * depth, Layers.World, new GArray(exclude));
        var hit = GetWorld3D().DirectSpaceState.IntersectRay(q);
        return hit.Count > 0 ? hit["position"].AsVector3().Y : null;
    }

    private void Fail(string message)
    {
        GD.PrintErr($"FAIL [placement_test] {message}");
        _fail++;
    }
}
