using Godot;

namespace Brushfire;

/// <summary>User options persisted to user://settings.cfg.</summary>
public class GameSettings
{
    const string Path = "user://settings.cfg";

    public float MouseSensitivity = 1.0f;   // multiplier on 0.1 degrees per mouse count
    public float GamepadSensitivity = 1.0f;
    public bool InvertY;
    public float Fov = 100f;               // horizontal degrees at 16:9
    public bool HeadBob = true;
    public float MasterVolume = 0.9f;
    public float SfxVolume = 1.0f;
    public float MusicVolume = 0.7f;
    public bool Fullscreen;
    public bool RetroFiltering;            // nearest-neighbour texture sampling, like software Quake
    public bool ShowFps;

    public void Load()
    {
        var cfg = new ConfigFile();
        if (cfg.Load(Path) != Error.Ok)
            return;
        MouseSensitivity = (float)cfg.GetValue("input", "mouse_sensitivity", MouseSensitivity);
        GamepadSensitivity = (float)cfg.GetValue("input", "gamepad_sensitivity", GamepadSensitivity);
        InvertY = (bool)cfg.GetValue("input", "invert_y", InvertY);
        Fov = (float)cfg.GetValue("video", "fov", Fov);
        HeadBob = (bool)cfg.GetValue("video", "head_bob", HeadBob);
        Fullscreen = (bool)cfg.GetValue("video", "fullscreen", Fullscreen);
        RetroFiltering = (bool)cfg.GetValue("video", "retro_filtering", RetroFiltering);
        ShowFps = (bool)cfg.GetValue("video", "show_fps", ShowFps);
        MasterVolume = (float)cfg.GetValue("audio", "master", MasterVolume);
        SfxVolume = (float)cfg.GetValue("audio", "sfx", SfxVolume);
        MusicVolume = (float)cfg.GetValue("audio", "music", MusicVolume);
    }

    public void Save()
    {
        var cfg = new ConfigFile();
        cfg.SetValue("input", "mouse_sensitivity", MouseSensitivity);
        cfg.SetValue("input", "gamepad_sensitivity", GamepadSensitivity);
        cfg.SetValue("input", "invert_y", InvertY);
        cfg.SetValue("video", "fov", Fov);
        cfg.SetValue("video", "head_bob", HeadBob);
        cfg.SetValue("video", "fullscreen", Fullscreen);
        cfg.SetValue("video", "retro_filtering", RetroFiltering);
        cfg.SetValue("video", "show_fps", ShowFps);
        cfg.SetValue("audio", "master", MasterVolume);
        cfg.SetValue("audio", "sfx", SfxVolume);
        cfg.SetValue("audio", "music", MusicVolume);
        cfg.Save(Path);
    }

    public void Apply()
    {
        SetBusVolume("Master", MasterVolume);
        SetBusVolume("SFX", SfxVolume);
        SetBusVolume("Music", MusicVolume);
        if (!OS.HasFeature("editor_hint") && DisplayServer.GetName() != "headless")
        {
            var mode = Fullscreen ? DisplayServer.WindowMode.Fullscreen : DisplayServer.WindowMode.Windowed;
            if (DisplayServer.WindowGetMode() != mode)
                DisplayServer.WindowSetMode(mode);
        }
    }

    static void SetBusVolume(string bus, float linear)
    {
        int idx = AudioServer.GetBusIndex(bus);
        if (idx < 0)
            return;
        AudioServer.SetBusVolumeDb(idx, Mathf.LinearToDb(Mathf.Max(linear, 0.0001f)));
        AudioServer.SetBusMute(idx, linear <= 0.001f);
    }
}
