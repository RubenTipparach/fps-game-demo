using Godot;

namespace Brushfire;

/// <summary>
/// Root of every level scene. Spawns the player at the node in group "player_start",
/// counts enemies/secrets, runs ambience and music, and handles pause and level completion.
/// </summary>
public partial class LevelRoot : Node3D
{
    public static LevelRoot Current { get; private set; }

    [Export] public string LevelTitle = "";
    [Export] public PackedScene PlayerScene = GD.Load<PackedScene>("res://scenes/player/player.tscn");
    [Export] public string Ambience = "ambience_industrial";
    [Export] public bool Music = true;

    public PlayerController Player { get; private set; }
    bool _complete;

    public override void _EnterTree()
    {
        Current = this;
        Events.Clear(); // before children subscribe in their _Ready
        Fx.ClearDecals();
    }

    public override void _ExitTree()
    {
        if (Current == this)
            Current = null;
    }

    public override void _Ready()
    {
        // Level sources that only matter in the editor (e.g. the CSG brushes that were baked
        // into the level mesh) are dropped immediately, before CSG gets a chance to rebuild.
        foreach (var n in GetTree().GetNodesInGroup("editor_only"))
            n.Free();

        var stats = Game.Instance.Stats;
        stats.TotalEnemies = GetTree().GetNodesInGroup("enemies").Count;
        stats.TotalSecrets = GetTree().GetNodesInGroup("secrets").Count;

        Node3D start = null;
        foreach (var n in GetTree().GetNodesInGroup("player_start"))
            if (n is Node3D s)
            {
                start = s;
                break;
            }
        Player = PlayerScene.Instantiate<PlayerController>();
        // Place the player before it enters the tree, so it never touches anything at the origin.
        if (start != null)
            Player.Transform = new Transform3D(Basis.FromEuler(new Vector3(0, start.GlobalRotation.Y, 0)), start.GlobalPosition + Vector3.Up * 0.05f);
        AddChild(Player);
        Player.ResetPhysicsInterpolation();

        if (!string.IsNullOrEmpty(Ambience))
            AddLoop(Ambience, "SFX", -12f);
        if (Music)
            AddLoop("music_loop", "Music", -9f);

        AddChild(new PauseMenu());
        MaterialFilter.Apply(Game.Instance.Settings.RetroFiltering);
        Input.MouseMode = Input.MouseModeEnum.Captured;
        Events.EnemyKilled += _ => CheckAllDead();
        var title = string.IsNullOrEmpty(LevelTitle) && Game.Instance.CurrentLevel >= 0
            ? Game.Levels[Game.Instance.CurrentLevel].Title
            : LevelTitle;
        Player.Hud.ShowCenterMessage(title, "Find the exit. Kill everything in your way.", 3.5f);
    }

    void AddLoop(string sound, string bus, float db)
    {
        var stream = Audio.Pick(sound);
        if (stream is AudioStreamWav wav)
        {
            wav.LoopMode = AudioStreamWav.LoopModeEnum.Forward;
            wav.LoopEnd = (int)(wav.GetLength() * wav.MixRate);
        }
        var p = new AudioStreamPlayer { Stream = stream, Bus = bus, VolumeDb = db, Autoplay = true };
        AddChild(p);
    }

    void CheckAllDead()
    {
        var stats = Game.Instance.Stats;
        if (stats.Kills >= stats.TotalEnemies && stats.TotalEnemies > 0)
            Player?.Hud.ShowPickup("All enemies destroyed!");
    }

    public override void _Process(double delta)
    {
        if (!_complete && !GetTree().Paused && Player is { IsDead: false })
            Game.Instance.Stats.Time += delta;
    }

    public void CompleteLevel()
    {
        if (_complete)
            return;
        _complete = true;
        Audio.Play2D(this, "level_complete", 0f, 0f, "Music");
        AddChild(new Intermission());
    }
}

/// <summary>Switches every level material between smooth and "software renderer" nearest filtering.</summary>
public static class MaterialFilter
{
    public static void Apply(bool retro)
    {
        var mode = retro
            ? BaseMaterial3D.TextureFilterEnum.NearestWithMipmapsAnisotropic
            : BaseMaterial3D.TextureFilterEnum.LinearWithMipmapsAnisotropic;
        foreach (var file in DirAccess.GetFilesAt("res://materials"))
        {
            string name = file.TrimSuffix(".remap");
            if (!name.EndsWith(".tres"))
                continue;
            if (ResourceLoader.Load("res://materials/" + name) is BaseMaterial3D m)
                m.TextureFilter = mode;
        }
    }
}
