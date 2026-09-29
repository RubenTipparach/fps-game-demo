using System.Collections.Generic;
using System.Linq;
using Godot;

namespace Brushfire;

public enum AmmoType { Shells, Bullets, Rockets }

/// <summary>
/// Owns the player's weapons and ammo, handles switching, and animates the viewmodel:
/// look sway, movement bob, sprint pose, recoil springs, raise/lower on switch.
///
/// The viewmodel is drawn at 1/4 scale, 1/4 as far from the eye. It looks identical in
/// perspective but sits inside the player's collision cylinder, so it never clips into walls.
/// </summary>
public partial class WeaponManager : Node3D
{
    public const float ViewmodelScale = 0.25f;

    static readonly Dictionary<AmmoType, int> MaxAmmo = new()
    {
        [AmmoType.Shells] = 60, [AmmoType.Bullets] = 300, [AmmoType.Rockets] = 30,
    };

    readonly Dictionary<AmmoType, int> _ammo = new()
    {
        [AmmoType.Shells] = 24, [AmmoType.Bullets] = 0, [AmmoType.Rockets] = 0,
    };

    PlayerController _player;
    Node3D _root;
    readonly List<Weapon> _weapons = new();
    Weapon _current, _pending;
    float _switchT;
    enum SwitchState { Ready, Lowering, Raising }
    SwitchState _state = SwitchState.Raising;

    float _lastYaw, _lastPitch;
    Vector2 _sway, _swayVel;
    Vector3 _kickPos, _kickPosVel;
    Vector3 _kickRot, _kickRotVel;
    float _sprintBlend;
    float _landDip;
    bool _wasOnFloor = true;

    /// <summary>
    /// Where rounds come from, when not the manager's own counts: Undercity's pack and magazines
    /// (openspec/changes/archive/2026-09-28-hub-combat). Null for Brushfire's reference maps.
    /// </summary>
    public IAmmoSource AmmoSource { get; set; }

    public Weapon Current => _current;
    public IReadOnlyList<Weapon> All => _weapons;
    public int GetAmmo(AmmoType t) => _ammo[t];
    public int GetMaxAmmo(AmmoType t) => MaxAmmo[t];
    public PlayerController Player => _player;

    public override void _Ready()
    {
        _player = GetParent().GetParent().GetParent<PlayerController>();
        _root = GetNode<Node3D>("ViewmodelRoot");
        _root.Scale = Vector3.One * ViewmodelScale;
        foreach (var w in _root.GetChildren().OfType<Weapon>().OrderBy(w => w.Slot))
        {
            w.Manager = this;
            w.Visible = false;
            _weapons.Add(w);
        }
        _current = _weapons.FirstOrDefault(w => w.Owned);
        if (_current != null)
            _current.Visible = true;
        _switchT = 0f;
        _lastYaw = _player.Yaw;
        _lastPitch = _player.Pitch;
    }

    /// <summary>Takes a weapon made at runtime into the hand (Undercity draws from its belt), raising it.</summary>
    public void Adopt(Weapon w)
    {
        if (w.GetParent() != _root)
            _root.AddChild(w);
        w.Manager = this;
        w.Owned = true;
        if (!_weapons.Contains(w))
            _weapons.Add(w);
        _current?.OnHolster();
        if (_current != null && _current != w)
            _current.Visible = false;
        _current = w;
        _pending = null;
        w.Visible = true;
        _state = SwitchState.Raising;
        _switchT = 0f;
    }

    /// <summary>Puts away and frees a weapon taken with <see cref="Adopt"/>.</summary>
    public void Release(Weapon w)
    {
        _weapons.Remove(w);
        if (_current == w)
            _current = null;
        if (_pending == w)
            _pending = null;
        w.OnHolster();
        w.QueueFree();
    }

    public bool TakeAmmo(AmmoType t, int amount)
    {
        if (_ammo[t] < amount)
            return false;
        _ammo[t] -= amount;
        return true;
    }

    public bool GiveAmmo(AmmoType t, int amount)
    {
        if (_ammo[t] >= MaxAmmo[t])
            return false;
        _ammo[t] = Mathf.Min(_ammo[t] + amount, MaxAmmo[t]);
        return true;
    }

    /// <summary>Give a weapon (and some ammo). Switches to it when it is new.</summary>
    public bool GiveWeapon(int slot, int ammo)
    {
        var w = _weapons.FirstOrDefault(x => x.Slot == slot);
        if (w == null)
            return false;
        bool isNew = !w.Owned;
        bool gotAmmo = GiveAmmo(w.Ammo, ammo);
        w.Owned = true;
        if (isNew)
            SwitchTo(w);
        return isNew || gotAmmo;
    }

    public void SwitchTo(Weapon w)
    {
        if (w == null || !w.Owned || w == _current && _state != SwitchState.Lowering)
            return;
        _pending = w;
        if (_current == null)
        {
            _current = w;
            _current.Visible = true;
            _state = SwitchState.Raising;
            _switchT = 0f;
            return;
        }
        if (_state != SwitchState.Lowering)
        {
            _state = SwitchState.Lowering;
            _switchT = 0f;
            Audio.Play2D(this, "weapon_switch", -10f);
        }
    }

    void Cycle(int dir)
    {
        if (_weapons.Count == 0)
            return;
        int start = _weapons.IndexOf(_pending ?? _current);
        for (int i = 1; i <= _weapons.Count; i++)
        {
            var w = _weapons[((start + dir * i) % _weapons.Count + _weapons.Count) % _weapons.Count];
            if (w.Owned && (w.HasAmmo || w == _current))
            {
                SwitchTo(w);
                return;
            }
        }
    }

    public override void _UnhandledInput(InputEvent e)
    {
        if (_player.IsDead || !PlayerController.InputEnabled)
            return;
        for (int i = 1; i <= 3; i++)
            if (e.IsActionPressed($"weapon_{i}"))
                SwitchTo(_weapons.FirstOrDefault(w => w.Slot == i));
        if (e.IsActionPressed("weapon_next"))
            Cycle(1);
        else if (e.IsActionPressed("weapon_prev"))
            Cycle(-1);
    }

    /// <summary>Called by weapons when they fire, to kick the viewmodel and camera.</summary>
    public void Kick(Vector3 push, float pitchDegrees, float viewKick)
    {
        _kickPosVel += push * 60f;
        _kickRotVel += new Vector3(Mathf.DegToRad(pitchDegrees), (float)GD.RandRange(-0.03, 0.03), 0) * 60f;
        _player.AddRecoil(viewKick, (float)GD.RandRange(-viewKick, viewKick) * 0.25f);
    }

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        if (dt <= 0f)
            return;
        bool canUse = !_player.IsDead && PlayerController.InputEnabled && !GetTree().Paused;

        // --- switching
        float lower = 0f;
        switch (_state)
        {
            case SwitchState.Lowering:
                _switchT += dt / 0.16f;
                lower = Mathf.Clamp(_switchT, 0f, 1f);
                if (_switchT >= 1f)
                {
                    _current.Visible = false;
                    _current.OnHolster();
                    _current = _pending ?? _current;
                    _current.Visible = true;
                    _state = SwitchState.Raising;
                    _switchT = 0f;
                    lower = 1f;
                }
                break;
            case SwitchState.Raising:
                _switchT += dt / 0.22f;
                lower = 1f - Mathf.SmoothStep(0f, 1f, Mathf.Clamp(_switchT, 0f, 1f));
                if (_switchT >= 1f)
                {
                    _state = SwitchState.Ready;
                    _pending = null;
                }
                break;
        }

        if (_current != null)
        {
            bool trigger = canUse && _state == SwitchState.Ready && Input.IsActionPressed("fire");
            _current.Tick(dt, trigger, Input.IsActionJustPressed("fire") && canUse && _state == SwitchState.Ready);
            // Out of ammo: pick the best weapon that still has some (Brushfire's own counts only).
            if (AmmoSource == null && _state == SwitchState.Ready && !_current.HasAmmo && _current.ReadyToFire && trigger)
            {
                var next = _weapons.Where(w => w.Owned && w.HasAmmo).OrderByDescending(w => w.Slot).FirstOrDefault();
                if (next != null)
                    SwitchTo(next);
            }
        }

        AnimateViewmodel(dt, lower);
    }

    void AnimateViewmodel(float dt, float lower)
    {
        // Look sway: the weapon lags behind camera rotation.
        float dYaw = Mathf.AngleDifference(_lastYaw, _player.Yaw);
        float dPitch = _player.Pitch - _lastPitch;
        _lastYaw = _player.Yaw;
        _lastPitch = _player.Pitch;
        Vector2 target = new Vector2(-dYaw, -dPitch) / Mathf.Max(dt, 1f / 240f) * 0.012f;
        target = target.LimitLength(0.12f);
        Springs.Step(ref _sway, ref _swayVel, target, 90f, 14f, dt);

        // Recoil springs.
        Springs.Step(ref _kickPos, ref _kickPosVel, Vector3.Zero, 260f, 22f, dt);
        Springs.Step(ref _kickRot, ref _kickRotVel, Vector3.Zero, 200f, 18f, dt);

        // Landing dip.
        bool onFloor = _player.IsOnFloor();
        if (onFloor && !_wasOnFloor)
            _landDip = Mathf.Min(_landDip + 0.04f, 0.08f);
        _wasOnFloor = onFloor;
        _landDip = Mathf.Lerp(_landDip, 0f, 1f - Mathf.Exp(-8f * dt));

        // Movement bob (figure-eight), sprint pose.
        float weight = _player.BobWeight;
        float phase = _player.BobPhase;
        Vector3 bob = new(Mathf.Sin(phase * 0.5f) * 0.018f * weight, -Mathf.Abs(Mathf.Sin(phase)) * 0.016f * weight, 0f);
        _sprintBlend = Mathf.Lerp(_sprintBlend, _player.Sprinting && weight > 0.8f ? 1f : 0f, 1f - Mathf.Exp(-8f * dt));
        float breathe = Mathf.Sin(Time.GetTicksMsec() / 1000f * 1.6f) * 0.004f;

        Vector3 pos = bob + new Vector3(0, breathe - _landDip - lower * 0.35f, 0) + _kickPos;
        pos += new Vector3(-0.04f, -0.05f, 0.02f) * _sprintBlend;
        Vector3 rot = new Vector3(_sway.Y + _kickRot.X - lower * 0.6f + _sprintBlend * -0.25f,
            _sway.X + _kickRot.Y + _sprintBlend * 0.5f,
            _sway.X * 0.6f + bob.X * 2f);

        // ViewmodelRoot holds weapons in "full size" units; scale its offsets to match.
        _root.Position = pos * ViewmodelScale;
        _root.Rotation = rot;
    }
}
