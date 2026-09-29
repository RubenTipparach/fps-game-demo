// The conversation rig: a soft warm key and two district gels around the speaker's head, lighting
// characters only, ramped in when a conversation opens and out when it closes
// (openspec/changes/character-lighting, design section 4, after the owner's portrait reference:
// loop lighting with a rim light and coloured gels).
//
// It lives in the Godot layer: the scene (scenes/undercity/conversation_rig.tscn) holds the three
// lights; where they go, their colours and energies come from data/character_lighting.json, and
// which side the key takes and which gels a district wears are the core's
// (CharacterLightingTable.KeySide, RoleFor).

#nullable enable
using System;
using System.Linq;
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>Three lights around a speaker.</summary>
public partial class ConversationRig : Node3D
{
    /// <summary>The group the face-box instrument finds the rig in.</summary>
    public const string Group = "conversation_rig";

    private (Light3D Light, float Energy)[] _lights = Array.Empty<(Light3D, float)>();

    /// <summary>The side the key is on: "left" or "right" of the camera.</summary>
    public string KeySide { get; private set; } = "left";

    /// <summary>
    /// Places the lights around <paramref name="head"/> as seen from <paramref name="cam"/>, the key
    /// on <paramref name="keySide"/>, the gels those of <paramref name="district"/>, and ramps them in.
    /// </summary>
    public void Light(CharacterLightingTable t, Vector3 head, Camera3D cam, string keySide, string district)
    {
        KeySide = keySide;
        SetMeta("key_side", keySide);
        AddToGroup(Group);
        // Azimuth 0 is toward the camera; positive runs toward the key side.
        var toCam = cam.GlobalPosition - head;
        toCam.Y = 0;
        toCam = toCam.LengthSquared() > 1e-6f ? toCam.Normalized() : Vector3.Back;
        var right = cam.GlobalBasis.X;
        right.Y = 0;
        right = right.LengthSquared() > 1e-6f ? right.Normalized() : Vector3.Right;
        var keyward = keySide == "right" ? right : -right;
        var c = t.Conversation;
        var mask = 1u << (t.CharactersLayer - 1);
        _lights = new[] { ("Key", c.Key), ("Rim", c.Rim), ("Accent", c.Accent) }.Select(p =>
        {
            var light = GetNode<Light3D>(p.Item1);
            var def = p.Item2;
            var az = Mathf.DegToRad((float)def.AzimuthDeg);
            var el = Mathf.DegToRad((float)def.ElevationDeg);
            var flat = toCam * Mathf.Cos(az) + keyward * Mathf.Sin(az);
            var dir = flat * Mathf.Cos(el) + Vector3.Up * Mathf.Sin(el);
            var at = head + dir * (float)def.DistanceM;
            var (r, g, b) = t.Rgb(t.RoleFor(def, district));
            light.LightColor = new Color((float)r, (float)g, (float)b);
            light.LightCullMask = mask;
            light.LightSize = (float)def.SizeM;
            light.ShadowEnabled = def.Shadow;
            light.LightBakeMode = Light3D.BakeMode.Disabled;
            light.LightEnergy = 0;
            light.GlobalPosition = at;
            if (light is SpotLight3D spot)
            {
                spot.SpotAngle = (float)def.SpotAngleDeg / 2;     // Godot's is the half-angle
                spot.SpotRange = (float)def.DistanceM + 1;
                spot.LookAt(head, Mathf.Abs(dir.Y) > 0.99f ? Vector3.Forward : Vector3.Up);
            }
            else if (light is OmniLight3D omni)
            {
                omni.OmniRange = (float)def.DistanceM + 0.8f;
            }
            return (light, (float)def.Energy);
        }).ToArray();
        Ramp(1, c.RampS, free: false);
    }

    /// <summary>Ramps the lights out over <paramref name="seconds"/>, then frees the rig.</summary>
    public void FadeOut(double seconds) => Ramp(0, seconds, free: true);

    private void Ramp(float to, double seconds, bool free)
    {
        var tween = CreateTween().SetParallel();
        foreach (var (light, energy) in _lights)
        {
            tween.TweenProperty(light, "light_energy", energy * to, Math.Max(seconds, 0.01));
        }
        if (free)
        {
            tween.Chain().TweenCallback(Callable.From(QueueFree));
        }
    }
}
