// The crowd: which body, outfit palette, accessories, height and idle each civilian takes, and the
// rule that no two nearby civilians look alike (openspec/changes/crowd-variety, design sections 2
// to 5). The level says where each civilian stands (LevelDef.Crowd); data/crowd.json says what
// they may wear by role; CrowdPicker.Assign decides the whole crowd at once.
//
// It lives in the core because who looks like whom is a rule a save and a replay must agree on
// (CLAUDE.md 5.2, 5.4): the same world seed gives the same crowd, and nothing rests on hash order.
// The Godot layer loads the body and applies the rest.

using Undercity.Core.Data;

namespace Undercity.Core.World;

/// <summary>Where a civilian stands (data/levels/&lt;id&gt;.json "crowd").</summary>
public sealed class CrowdPlace
{
    /// <summary>[x, y] in layout metres (x east, y south).</summary>
    public required IReadOnlyList<double> At { get; init; }

    /// <summary>The district it stands in; null between districts.</summary>
    public string? District { get; init; }

    /// <summary>True inside a named building: no umbrella there.</summary>
    public bool Indoors { get; init; }
}

/// <summary>An outfit palette: how the clothes' colours shift. Skin, hair and eyes never shift.</summary>
public sealed class PaletteDef
{
    /// <summary>Hue shift, degrees.</summary>
    public required double HueDeg { get; init; }

    /// <summary>Saturation multiplier, 0-2.</summary>
    public required double Sat { get; init; }
}

/// <summary>An accessory a civilian may carry: the bone it hangs from and the slot it fills.</summary>
public sealed class AccessoryDef
{
    /// <summary>The humanoid bone it attaches to (Godot's SkeletonProfileHumanoid names).</summary>
    public required string Bone { get; init; }

    /// <summary>What it occupies (hat, face, ears, hand_r...): one accessory per slot.</summary>
    public required string Slot { get; init; }

    /// <summary>The idle it forces (an open umbrella is held up), or null.</summary>
    public string? Idle { get; init; }
}

/// <summary>What a role may look like.</summary>
public sealed class CrowdRoleDef
{
    /// <summary>The body pool it draws from (a key of <see cref="CrowdTable.BodyPools"/>).</summary>
    public required string Bodies { get; init; }

    /// <summary>The accessories it may carry.</summary>
    public required IReadOnlyList<string> Accessories { get; init; }

    /// <summary>The idles it plays (states of data/npc_bodies.json).</summary>
    public required IReadOnlyList<string> Idles { get; init; }
}

/// <summary>data/crowd.json.</summary>
public sealed class CrowdTable : IValidated
{
    /// <summary>Within this distance no two civilians share both body and palette, metres.</summary>
    public required double LookalikeRadiusM { get; init; }

    /// <summary>No body is used by more civilians than this.</summary>
    public required int MaxPerBody { get; init; }

    /// <summary>A civilian's height scale is drawn in [lo, hi].</summary>
    public required IReadOnlyList<double> ScaleRange { get; init; }

    /// <summary>How many accessories a civilian carries at most.</summary>
    public required int MaxAccessories { get; init; }

    /// <summary>The share of outdoor civilians who carry an open umbrella (the hub always rains), 0-1.</summary>
    public required double RainUmbrellaShare { get; init; }

    /// <summary>The accessory that is the umbrella.</summary>
    public required string Umbrella { get; init; }

    /// <summary>Body pools: name to body ids.</summary>
    public required IReadOnlyDictionary<string, IReadOnlyList<string>> BodyPools { get; init; }

    /// <summary>Palettes by name.</summary>
    public required IReadOnlyDictionary<string, PaletteDef> Palettes { get; init; }

    /// <summary>Accessories by id.</summary>
    public required IReadOnlyDictionary<string, AccessoryDef> Accessories { get; init; }

    /// <summary>Roles by name.</summary>
    public required IReadOnlyDictionary<string, CrowdRoleDef> Roles { get; init; }

    /// <summary>The role of a civilian standing in each district.</summary>
    public required IReadOnlyDictionary<string, string> DistrictRoles { get; init; }

    /// <summary>The role of a civilian between districts.</summary>
    public required string DefaultRole { get; init; }

    /// <summary>The role for a civilian in <paramref name="district"/>.</summary>
    public string RoleFor(string? district) =>
        district is not null && DistrictRoles.TryGetValue(district, out var r) ? r : DefaultRole;

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        if (!(LookalikeRadiusM >= 0) || !double.IsFinite(LookalikeRadiusM))
        {
            errors.Add("crowd.json lookalike_radius_m: a finite distance, 0 or more");
        }
        if (MaxPerBody < 1)
        {
            errors.Add("crowd.json max_per_body: 1 or more");
        }
        if (ScaleRange.Count != 2 || !ScaleRange.All(double.IsFinite) || !(ScaleRange[0] > 0) || ScaleRange[0] > ScaleRange[1])
        {
            errors.Add("crowd.json scale_range: [lo, hi], 0 < lo <= hi");
        }
        if (MaxAccessories < 0)
        {
            errors.Add("crowd.json max_accessories: 0 or more");
        }
        if (!(RainUmbrellaShare >= 0 && RainUmbrellaShare <= 1))
        {
            errors.Add("crowd.json rain_umbrella_share: 0-1");
        }
        if (!Accessories.ContainsKey(Umbrella))
        {
            errors.Add($"crowd.json umbrella: no accessory '{Umbrella}'");
        }
        if (Palettes.Count == 0)
        {
            errors.Add("crowd.json palettes: at least one");
        }
        foreach (var (name, p) in Palettes.Where(p => !double.IsFinite(p.Value.HueDeg) || !(p.Value.Sat >= 0 && p.Value.Sat <= 2)))
        {
            errors.Add($"crowd.json palettes.{name}: a finite hue_deg and a sat of 0-2");
        }
        foreach (var (name, pool) in BodyPools.Where(p => p.Value.Count == 0))
        {
            errors.Add($"crowd.json body_pools.{name}: at least one body");
        }
        foreach (var (name, role) in Roles)
        {
            if (!BodyPools.ContainsKey(role.Bodies))
            {
                errors.Add($"crowd.json roles.{name}.bodies: no body pool '{role.Bodies}'");
            }
            foreach (var a in role.Accessories.Where(a => !Accessories.ContainsKey(a)))
            {
                errors.Add($"crowd.json roles.{name}.accessories: no accessory '{a}'");
            }
            if (role.Idles.Count == 0)
            {
                errors.Add($"crowd.json roles.{name}.idles: at least one");
            }
        }
        foreach (var (district, role) in DistrictRoles.Append(new KeyValuePair<string, string>("(default)", DefaultRole)))
        {
            if (!Roles.ContainsKey(role))
            {
                errors.Add($"crowd.json district_roles.{district}: no role '{role}'");
            }
        }
    }
}

/// <summary>How one civilian looks.</summary>
/// <param name="Role">The role their place gave them.</param>
/// <param name="Body">The body (model) id.</param>
/// <param name="Palette">The outfit palette's name.</param>
/// <param name="Accessories">The accessories they carry, in the order drawn.</param>
/// <param name="Scale">Their height scale.</param>
/// <param name="Idle">The idle state they play.</param>
public sealed record CrowdLook(string Role, string Body, string Palette, IReadOnlyList<string> Accessories, double Scale, string Idle);

/// <summary>Decides how every civilian of a level looks.</summary>
public static class CrowdPicker
{
    /// <summary>
    /// Every civilian's look, by stable id. Civilians are taken in ordinal order of their stable
    /// ids; each draws from a stream seeded by the world seed and its id, shuffles its role's
    /// bodies and the palettes, and takes the first (body, palette) that keeps the rules: no
    /// civilian already placed within <see cref="CrowdTable.LookalikeRadiusM"/> has both, and the
    /// body isn't yet used <see cref="CrowdTable.MaxPerBody"/> times. When no pair keeps both, the
    /// cap gives way before the lookalike rule, and the least used body is taken.
    /// </summary>
    public static IReadOnlyDictionary<string, CrowdLook> Assign(ulong worldSeed, IReadOnlyDictionary<string, CrowdPlace> crowd, CrowdTable t)
    {
        var palettes = t.Palettes.Keys.OrderBy(p => p, StringComparer.Ordinal).ToArray();
        var used = new Dictionary<string, int>(StringComparer.Ordinal);
        var placed = new List<(CrowdPlace Place, CrowdLook Look)>();
        var looks = new Dictionary<string, CrowdLook>(StringComparer.Ordinal);
        foreach (var sid in crowd.Keys.OrderBy(k => k, StringComparer.Ordinal))
        {
            var place = crowd[sid];
            var roleName = t.RoleFor(place.District);
            var role = t.Roles[roleName];
            var rng = SeededRandom.For(worldSeed, sid, "crowd");
            var bodies = Shuffled(t.BodyPools[role.Bodies].OrderBy(b => b, StringComparer.Ordinal).ToArray(), rng);
            var shades = Shuffled(palettes, rng);
            (string Body, string Palette)? pick = null;
            foreach (var body in bodies)
            {
                if (used.GetValueOrDefault(body) >= t.MaxPerBody)
                {
                    continue;
                }
                foreach (var shade in shades)
                {
                    if (!Twin(place, body, shade, placed, t.LookalikeRadiusM))
                    {
                        pick = (body, shade);
                        break;
                    }
                }
                if (pick is not null)
                {
                    break;
                }
            }
            pick ??= (bodies.OrderBy(b => used.GetValueOrDefault(b)).First(), shades[0]);
            used[pick.Value.Body] = used.GetValueOrDefault(pick.Value.Body) + 1;

            var accessories = Accessories(t, role, place, rng);
            var lo = t.ScaleRange[0];
            var scale = Math.Round(lo + (t.ScaleRange[1] - lo) * rng.NextDouble(), 3);
            var forced = accessories.Select(a => t.Accessories[a].Idle).FirstOrDefault(i => i is not null);
            var idle = forced ?? role.Idles[rng.Next(role.Idles.Count)];
            var look = new CrowdLook(roleName, pick.Value.Body, pick.Value.Palette, accessories, scale, idle);
            looks[sid] = look;
            placed.Add((place, look));
        }
        return looks;
    }

    private static bool Twin(CrowdPlace place, string body, string palette, List<(CrowdPlace Place, CrowdLook Look)> placed, double radiusM) =>
        placed.Any(p => p.Look.Body == body && p.Look.Palette == palette && Distance(p.Place, place) <= radiusM);

    /// <summary>The distance between two places, metres.</summary>
    public static double Distance(CrowdPlace a, CrowdPlace b) =>
        Math.Sqrt(Math.Pow(a.At[0] - b.At[0], 2) + Math.Pow(a.At[1] - b.At[1], 2));

    // The umbrella first, outdoors, for rain_umbrella_share of them; then up to max_accessories in
    // all from the role's list in a seeded order, one per slot.
    private static List<string> Accessories(CrowdTable t, CrowdRoleDef role, CrowdPlace place, SeededRandom rng)
    {
        var count = rng.Next(t.MaxAccessories + 1);
        var umbrella = !place.Indoors && role.Accessories.Contains(t.Umbrella) && rng.NextDouble() < t.RainUmbrellaShare;
        var chosen = new List<string>();
        var slots = new HashSet<string>(StringComparer.Ordinal);
        if (umbrella && t.MaxAccessories > 0)
        {
            chosen.Add(t.Umbrella);
            slots.Add(t.Accessories[t.Umbrella].Slot);
        }
        foreach (var a in Shuffled(role.Accessories.Where(a => a != t.Umbrella).OrderBy(a => a, StringComparer.Ordinal).ToArray(), rng))
        {
            if (chosen.Count >= Math.Max(count, umbrella ? 1 : 0))
            {
                break;
            }
            if (slots.Add(t.Accessories[a].Slot))
            {
                chosen.Add(a);
            }
        }
        return chosen;
    }

    // Fisher-Yates over an ordinal-sorted copy, so the order depends only on the stream.
    private static T[] Shuffled<T>(T[] items, SeededRandom rng)
    {
        var a = (T[])items.Clone();
        for (var i = a.Length - 1; i > 0; i--)
        {
            var j = rng.Next(i + 1);
            (a[i], a[j]) = (a[j], a[i]);
        }
        return a;
    }
}
