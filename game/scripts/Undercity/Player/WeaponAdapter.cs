// The runner's weapons in Undercity: draws the belt's firearm into Brushfire's WeaponManager,
// holsters it, feeds it rounds from the core's magazines, and reloads it (openspec/changes/archive/
// 2026-09-28-hub-combat, design section 1).
//
// It lives in the Godot layer as the seam between the two games' halves. What is drawn, the
// rounds, the reload time and every number the weapon fires with belong to the core and to
// data/weapons.json; Brushfire's Weapon aims, shoots, recoils and flashes, one implementation for
// the reference maps and Undercity alike (CLAUDE.md 5.1). The belt is the only way to draw:
// Brushfire's own weapon keys have nothing to switch to.

#nullable enable
using Brushfire;
using Godot;
using Undercity.Core.Combat;

namespace Undercity.Client;

/// <summary>Draws, feeds and reloads the runner's firearm.</summary>
public partial class WeaponAdapter : Node, IWired, IAmmoSource
{
    private Services? _s;
    private WeaponManager? _manager;
    private Weapon? _held;
    private string? _heldItem;
    private WeaponDef? _def;

    /// <summary>The weapon in hand, or null.</summary>
    public Weapon? Held => _held;

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _s = services;
        _manager = GetParent().GetNodeOrNull<WeaponManager>("CameraRig/Camera3D/WeaponManager");
        if (_manager is null)
        {
            GD.PushError("[Undercity] WeaponAdapter: the player has no CameraRig/Camera3D/WeaponManager");
            return;
        }
        _manager.AmmoSource = this;
        services.State.LoadoutChanged += OnLoadout;
        services.State.ReloadChanged += OnReload;
        OnLoadout();
    }

    public override void _ExitTree()
    {
        if (_s is not null)
        {
            _s.State.LoadoutChanged -= OnLoadout;
            _s.State.ReloadChanged -= OnReload;
        }
    }

    public override void _Process(double delta)
    {
        if (_s is null || _held is null || _def is null)
        {
            return;
        }
        if (Input.IsActionJustPressed("reload") && PlayerController.InputEnabled && !_s.Screens.Blocking)
        {
            _s.State.StartReload();
        }
        // The weapon dips and rolls out of the way while it reloads, and comes back as it ends.
        var k = _s.State.Reloading ? Mathf.Sin(Mathf.Pi * (float)(1 - _s.State.ReloadLeftS / _def.ReloadS)) : 0f;
        _held.Rotation = new Vector3(-0.7f * k, 0, 0.5f * k);
    }

    private void OnLoadout()
    {
        var s = _s!.State;
        if (s.Drawn == _heldItem)
        {
            return;
        }
        if (_held is not null)
        {
            _manager!.Release(_held);
            _held = null;
            _heldItem = null;
            _def = null;
        }
        if (s.Drawn is not { } item || s.Data.Items.Get(item).Weapon is not { } weaponId
            || s.Data.Weapons.Find(weaponId) is not { Scene: { } scene } def)
        {
            return;
        }
        if (!ResourceLoader.Exists(scene))
        {
            GD.PushWarning($"[Undercity] {weaponId}: no weapon scene {scene}");
            return;
        }
        var w = GD.Load<PackedScene>(scene).Instantiate<Weapon>();
        Configure(w, weaponId, def);
        _manager!.Adopt(w);
        foreach (var g in w.FindChildren("*", "GeometryInstance3D", true, false))
        {
            ((GeometryInstance3D)g).CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
        }
        _held = w;
        _heldItem = item;
        _def = def;
    }

    /// <summary>Sets the weapon's numbers from data/weapons.json: the scene holds its parts, the data what it does.</summary>
    private static void Configure(Weapon w, string id, WeaponDef def)
    {
        w.WeaponId = id;
        w.DisplayName = def.Name;
        w.Slot = 0;
        w.Owned = true;
        w.Damage = (float)def.Damage;
        w.Pellets = def.Pellets;
        w.FireInterval = (float)(1 / def.RatePerS);
        w.SpreadDegrees = (float)def.SpreadDeg;
        w.NoiseRadius = (float)def.NoiseM;
        w.FireSound = def.FireSound ?? "";
    }

    private void OnReload()
    {
        if (_s!.State.Reloading && _def?.ReloadSound is { } sound)
        {
            Audio.Play2D(this, sound, -3f);
        }
    }

    // ------------------------------------------------------------------ IAmmoSource

    /// <inheritdoc/>
    public bool CanFire(Weapon w) => _s is { State.Reloading: false, State.Dead: false };

    /// <inheritdoc/>
    public bool HasRound(Weapon w) => _s?.State.Rounds is not { } r || r.Loaded > 0;

    /// <inheritdoc/>
    public bool TakeRound(Weapon w)
    {
        if (_s is null || !_s.State.FireDrawn())
        {
            return false;
        }
        var p = _s.Level.Player;
        _s.Level.ShotHeard(p.EyePosition, w.NoiseRadius, byRunner: true);
        return true;
    }

    /// <inheritdoc/>
    public void DryFired(Weapon w) => _s?.State.StartReload();
}
