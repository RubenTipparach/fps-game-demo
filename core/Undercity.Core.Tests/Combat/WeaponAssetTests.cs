// The files data/weapons.json names exist: its scenes, sounds and hand models, checked against the
// real files under game/ (CLAUDE.md 5.6, "validate the real artifact"). A misspelt sound would
// otherwise fire in silence.

namespace Undercity.Core.Tests.Combat;

public class WeaponAssetTests
{
    private static string Game => Path.Combine(TestData.RepoRoot, "game");

    private static bool ResExists(string res) =>
        res.StartsWith("res://", StringComparison.Ordinal) && File.Exists(Path.Combine(Game, res["res://".Length..]));

    private static bool SoundExists(string name)
    {
        var dir = Path.Combine(Game, "audio", "sfx");
        return File.Exists(Path.Combine(dir, name + ".wav")) || File.Exists(Path.Combine(dir, name + "_1.wav"));
    }

    [Fact]
    public void Every_sound_a_weapon_names_is_in_game_audio_sfx()
    {
        foreach (var (id, w) in TestData.Data.Weapons.Weapons)
        {
            foreach (var sound in new[] { w.FireSound, w.ReloadSound }.OfType<string>())
            {
                Assert.True(SoundExists(sound), $"{id}: no game/audio/sfx/{sound}.wav (tools/sfx/generate_sfx.py)");
            }
        }
    }

    [Fact]
    public void Every_scene_and_hand_model_a_weapon_names_exists()
    {
        foreach (var (id, w) in TestData.Data.Weapons.Weapons)
        {
            foreach (var res in new[] { w.Scene, w.HandModel }.OfType<string>())
            {
                Assert.True(ResExists(res), $"{id}: {res} doesn't exist");
            }
        }
    }

    [Fact]
    public void Every_firearm_with_a_scene_has_its_shot_and_reload_sounds()
    {
        foreach (var (id, w) in TestData.Data.Weapons.Weapons.Where(p => p.Value.Scene is not null))
        {
            Assert.True(w.FireSound is not null && (w.Melee || w.ReloadSound is not null), $"{id} fires in silence");
        }
    }
}
