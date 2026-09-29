// How characters are lit: the wrist-deck glow on the runner, and the conversation rig of a key
// and two gels around the speaker's head (openspec/changes/character-lighting, design sections 2
// to 5 and 7), with the targets the captures are measured against.
//
// It lives in the core with the other tables because it is tuning (CLAUDE.md 5.5): committed,
// validated on load and by a core test, one source for each number. The Godot layer places the
// lights; the numbers and the colour roles are here.

using System.Globalization;
using Undercity.Core.Data;

namespace Undercity.Core.World;

/// <summary>The runner's wrist-deck glow: an omni light on the camera rig that lights characters only.</summary>
public sealed class WristLightDef
{
    /// <summary>A colour role in <see cref="CharacterLightingTable.Colors"/>.</summary>
    public required string Color { get; init; }

    /// <summary>The light's energy.</summary>
    public required double Energy { get; init; }

    /// <summary>How far it reaches, metres.</summary>
    public required double RangeM { get; init; }

    /// <summary>Its falloff curve (Godot's omni attenuation).</summary>
    public required double Attenuation { get; init; }

    /// <summary>Where it sits from the camera: right, up, back, metres (x, y, z in the camera's frame).</summary>
    public required IReadOnlyList<double> OffsetM { get; init; }
}

/// <summary>One light of the conversation rig, placed around the speaker's head.</summary>
public sealed class RigLightDef
{
    /// <summary>A colour role, or "gel" (the district's rim gel) or "gel_accent" (its accent).</summary>
    public required string Color { get; init; }

    /// <summary>The light's energy.</summary>
    public required double Energy { get; init; }

    /// <summary>Around the head from the camera's line, degrees: 0 is the camera's side, positive toward the key side.</summary>
    public required double AzimuthDeg { get; init; }

    /// <summary>Above the head's height, degrees.</summary>
    public required double ElevationDeg { get; init; }

    /// <summary>From the head, metres.</summary>
    public required double DistanceM { get; init; }

    /// <summary>The light's size, metres: large is soft, small is hard.</summary>
    public required double SizeM { get; init; }

    /// <summary>A spot's cone, degrees; 0 for an omni light.</summary>
    public double SpotAngleDeg { get; init; }

    /// <summary>True when it casts shadows.</summary>
    public bool Shadow { get; init; }
}

/// <summary>The conversation rig: a key and two gels, ramped in when a conversation opens.</summary>
public sealed class ConversationRigDef
{
    /// <summary>The key sides the data may name.</summary>
    public static readonly IReadOnlyList<string> KeySides = ["motivated", "left", "right"];

    /// <summary>The rig fades in over this long, seconds.</summary>
    public required double RampS { get; init; }

    /// <summary>"motivated" (the brighter side of the scene), "left" or "right".</summary>
    public required string KeySide { get; init; }

    /// <summary>The level's lights within this range of the speaker decide the motivated side, metres.</summary>
    public required double MotivationRadiusM { get; init; }

    /// <summary>The key: a soft spot, with shadows.</summary>
    public required RigLightDef Key { get; init; }

    /// <summary>The rim gel, behind on the far side.</summary>
    public required RigLightDef Rim { get; init; }

    /// <summary>The accent gel, behind on the key's side.</summary>
    public required RigLightDef Accent { get; init; }
}

/// <summary>What a conversation shot is measured against (tools/measure/face_luma.py).</summary>
public sealed class LightingTargets
{
    /// <summary>The face box's mean luma, lowest and highest.</summary>
    public required IReadOnlyList<double> FaceMeanLuma { get; init; }

    /// <summary>The key side's half over the other half, lowest and highest.</summary>
    public required IReadOnlyList<double> KeyToShadow { get; init; }

    /// <summary>The rim strip is at least this much brighter than the background beside it, luma.</summary>
    public required double RimOverBackgroundLuma { get; init; }

    /// <summary>The frame outside the face changes by less than this with the rig on, percent.</summary>
    public required double WorldLumaChangePct { get; init; }
}

/// <summary>How a conversation is framed (mockup D9, approved by the owner, survey I11).</summary>
public sealed class FramingDef
{
    /// <summary>The field of view narrows to this, degrees (vertical).</summary>
    public required double FovDeg { get; init; }

    /// <summary>Over this long, and back on close, seconds.</summary>
    public required double TimeS { get; init; }

    /// <summary>The pitch recentres so the face sits this far from the top of the screen, 0 to 1.</summary>
    public required double FaceFromTop { get; init; }
}

/// <summary>A light of the level near a speaker, as the motivated key side weighs it.</summary>
/// <param name="Side">How far to the camera's right of the speaker it is, metres (negative: left).</param>
/// <param name="DistanceM">How far from the speaker's head it is, metres.</param>
/// <param name="Energy">Its energy.</param>
public readonly record struct NearbyLight(double Side, double DistanceM, double Energy);

/// <summary>data/character_lighting.json.</summary>
public sealed class CharacterLightingTable : IValidated
{
    /// <summary>The rim and accent colours the rig reads from the district.</summary>
    public const string Gel = "gel";

    /// <summary>The district's accent gel.</summary>
    public const string GelAccent = "gel_accent";

    /// <summary>The visual layer characters render on besides the world's, and the only one the new lights reach (1-based).</summary>
    public required int CharactersLayer { get; init; }

    /// <summary>Colour roles: name to "#rrggbb".</summary>
    public required IReadOnlyDictionary<string, string> Colors { get; init; }

    /// <summary>The wrist-deck glow.</summary>
    public required WristLightDef Wrist { get; init; }

    /// <summary>The conversation rig.</summary>
    public required ConversationRigDef Conversation { get; init; }

    /// <summary>Each district's gels: [rim, accent], colour roles.</summary>
    public required IReadOnlyDictionary<string, IReadOnlyList<string>> Gels { get; init; }

    /// <summary>What the captures are measured against.</summary>
    public required LightingTargets Targets { get; init; }

    /// <summary>How a conversation is framed.</summary>
    public required FramingDef Framing { get; init; }

    /// <summary>How characters wet in the rain and dry under a roof (design section 9).</summary>
    public required WetnessDef Wetness { get; init; }

    /// <summary>
    /// The side the key goes on: the data's, or when it says "motivated", the side where the
    /// level's lights within the motivation radius sum the most energy / distance², so the face
    /// agrees with the scene it sits in (design section 4). A tie goes left.
    /// </summary>
    public string KeySide(IEnumerable<NearbyLight> lights)
    {
        if (Conversation.KeySide != "motivated")
        {
            return Conversation.KeySide;
        }
        double left = 0, right = 0;
        foreach (var l in lights.Where(l => l.DistanceM <= Conversation.MotivationRadiusM && double.IsFinite(l.Energy)))
        {
            var w = l.Energy / Math.Max(l.DistanceM * l.DistanceM, 0.01);
            if (l.Side > 0)
            {
                right += w;
            }
            else
            {
                left += w;
            }
        }
        return right > left ? "right" : "left";
    }

    /// <summary>A colour role's red, green and blue, 0 to 1 (sRGB, as the data writes it).</summary>
    public (double R, double G, double B) Rgb(string role)
    {
        if (!Colors.TryGetValue(role, out var hex) || ParseHex(hex) is not { } rgb)
        {
            throw new KeyNotFoundException($"character_lighting.json: no colour role '{role}'");
        }
        return rgb;
    }

    /// <summary>The colour role a rig light uses in <paramref name="district"/>: its own, or the district's gel.</summary>
    public string RoleFor(RigLightDef light, string district)
    {
        var pair = Gels.TryGetValue(district, out var p) ? p : null;
        return light.Color switch
        {
            Gel => pair?[0] ?? throw new KeyNotFoundException($"character_lighting.json: no gels for '{district}'"),
            GelAccent => pair?[1] ?? throw new KeyNotFoundException($"character_lighting.json: no gels for '{district}'"),
            _ => light.Color,
        };
    }

    private static (double R, double G, double B)? ParseHex(string hex)
    {
        if (hex.Length != 7 || hex[0] != '#'
            || !int.TryParse(hex.AsSpan(1), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var v))
        {
            return null;
        }
        return (((v >> 16) & 0xff) / 255.0, ((v >> 8) & 0xff) / 255.0, (v & 0xff) / 255.0);
    }

    /// <inheritdoc/>
    public void Validate(ICollection<string> errors)
    {
        if (CharactersLayer is < 2 or > 20)
        {
            errors.Add("characters_layer must be 2 to 20 (layer 1 is the world's)");
        }
        foreach (var (role, hex) in Colors.Where(c => ParseHex(c.Value) is null))
        {
            errors.Add($"colors.{role}: '{hex}' isn't #rrggbb");
        }
        void Role(string at, string role, bool gelAllowed)
        {
            if (!Colors.ContainsKey(role) && !(gelAllowed && role is Gel or GelAccent))
            {
                errors.Add($"{at}: '{role}' isn't a colour role{(gelAllowed ? " or gel / gel_accent" : "")}");
            }
        }
        void Number(string at, double v, bool zeroAllowed)
        {
            if (!double.IsFinite(v) || v < 0 || (!zeroAllowed && v == 0))
            {
                errors.Add($"{at} must be a finite number{(zeroAllowed ? ", zero or more" : " above zero")}");
            }
        }
        var w = Wrist;
        Role("wrist.color", w.Color, false);
        Number("wrist.energy", w.Energy, true);
        Number("wrist.range_m", w.RangeM, false);
        Number("wrist.attenuation", w.Attenuation, false);
        if (w.OffsetM.Count != 3 || w.OffsetM.Any(v => !double.IsFinite(v)))
        {
            errors.Add("wrist.offset_m must be three finite numbers");
        }
        var c = Conversation;
        Number("conversation.ramp_s", c.RampS, true);
        Number("conversation.motivation_radius_m", c.MotivationRadiusM, false);
        if (!ConversationRigDef.KeySides.Contains(c.KeySide))
        {
            errors.Add($"conversation.key_side '{c.KeySide}' isn't one of {string.Join(", ", ConversationRigDef.KeySides)}");
        }
        foreach (var (name, light) in new[] { ("key", c.Key), ("rim", c.Rim), ("accent", c.Accent) })
        {
            var at = $"conversation.{name}";
            Role($"{at}.color", light.Color, true);
            Number($"{at}.energy", light.Energy, true);
            Number($"{at}.distance_m", light.DistanceM, false);
            Number($"{at}.size_m", light.SizeM, true);
            if (!double.IsFinite(light.AzimuthDeg) || Math.Abs(light.AzimuthDeg) > 180
                || !double.IsFinite(light.ElevationDeg) || Math.Abs(light.ElevationDeg) > 90)
            {
                errors.Add($"{at}: azimuth_deg must be -180 to 180 and elevation_deg -90 to 90");
            }
            if (!double.IsFinite(light.SpotAngleDeg) || light.SpotAngleDeg is < 0 or >= 90)
            {
                errors.Add($"{at}.spot_angle_deg must be 0 (an omni light) to under 90");
            }
        }
        if (c.Key.SpotAngleDeg <= 0)
        {
            errors.Add("conversation.key is a spot: it needs spot_angle_deg");
        }
        foreach (var (district, pair) in Gels)
        {
            if (pair.Count != 2)
            {
                errors.Add($"gels.{district} must be [rim, accent]");
                continue;
            }
            Role($"gels.{district}[0]", pair[0], false);
            Role($"gels.{district}[1]", pair[1], false);
        }
        var t = Targets;
        if (t.FaceMeanLuma.Count != 2 || !(0 <= t.FaceMeanLuma[0] && t.FaceMeanLuma[0] < t.FaceMeanLuma[1] && t.FaceMeanLuma[1] <= 255))
        {
            errors.Add("targets.face_mean_luma must be [low, high] within 0-255");
        }
        if (t.KeyToShadow.Count != 2 || !(1 <= t.KeyToShadow[0] && t.KeyToShadow[0] < t.KeyToShadow[1]))
        {
            errors.Add("targets.key_to_shadow must be [low, high], low at least 1");
        }
        Number("targets.rim_over_background_luma", t.RimOverBackgroundLuma, true);
        Number("targets.world_luma_change_pct", t.WorldLumaChangePct, false);
        if (!double.IsFinite(Framing.FovDeg) || Framing.FovDeg is <= 1 or >= 179)
        {
            errors.Add("framing.fov_deg must be 1 to 179 degrees");
        }
        Number("framing.time_s", Framing.TimeS, true);
        if (!double.IsFinite(Framing.FaceFromTop) || Framing.FaceFromTop is <= 0 or >= 1)
        {
            errors.Add("framing.face_from_top must be between 0 and 1");
        }
        Wetness.Validate(errors);
    }
}
