using System.Collections.Generic;
using Godot;

namespace Brushfire;

/// <summary>
/// Fire-and-forget sound playback. Sounds are referenced by name ("shotgun_fire") and resolve to
/// res://audio/sfx/NAME.wav, or to a random variant NAME_1.wav, NAME_2.wav ... when those exist.
/// </summary>
public static class Audio
{
    const string Dir = "res://audio/sfx/";
    static readonly Dictionary<string, AudioStream[]> Cache = new();

    public static AudioStream Pick(string name)
    {
        if (!Cache.TryGetValue(name, out var streams))
        {
            var list = new List<AudioStream>();
            string single = Dir + name + ".wav";
            if (ResourceLoader.Exists(single))
                list.Add(GD.Load<AudioStream>(single));
            for (int i = 1; i < 16; i++)
            {
                string variant = $"{Dir}{name}_{i}.wav";
                if (!ResourceLoader.Exists(variant))
                    break;
                list.Add(GD.Load<AudioStream>(variant));
            }
            if (list.Count == 0)
                GD.PushWarning($"Missing sound '{name}'");
            streams = list.ToArray();
            Cache[name] = streams;
        }
        return streams.Length == 0 ? null : streams[GD.RandRange(0, streams.Length - 1)];
    }

    /// <summary>Non-positional sound (player weapons, UI, pickups).</summary>
    public static AudioStreamPlayer Play2D(Node context, string name, float volumeDb = 0f, float pitchVariance = 0.05f,
        string bus = "SFX")
    {
        var stream = Pick(name);
        if (stream == null || !context.IsInsideTree())
            return null;
        var p = new AudioStreamPlayer
        {
            Stream = stream,
            VolumeDb = volumeDb,
            PitchScale = 1f + (float)GD.RandRange(-pitchVariance, pitchVariance),
            Bus = bus,
            ProcessMode = Node.ProcessModeEnum.Always,
        };
        context.GetTree().Root.AddChild(p);
        p.Finished += p.QueueFree;
        p.Play();
        return p;
    }

    /// <summary>Positional sound in the level (enemies, impacts, explosions).</summary>
    public static AudioStreamPlayer3D Play3D(Node context, string name, Vector3 position, float volumeDb = 0f,
        float pitchVariance = 0.07f, float unitSize = 10f, float maxDistance = 80f)
    {
        var stream = Pick(name);
        if (stream == null || !context.IsInsideTree())
            return null;
        var p = new AudioStreamPlayer3D
        {
            Stream = stream,
            VolumeDb = volumeDb,
            PitchScale = 1f + (float)GD.RandRange(-pitchVariance, pitchVariance),
            UnitSize = unitSize,
            MaxDistance = maxDistance,
            Bus = "World",
            AttenuationFilterCutoffHz = 6000f,
            AttenuationFilterDb = -18f,
        };
        var parent = context.GetTree().CurrentScene ?? context.GetTree().Root;
        parent.AddChild(p);
        p.GlobalPosition = position;
        p.Finished += p.QueueFree;
        p.Play();
        return p;
    }
}
