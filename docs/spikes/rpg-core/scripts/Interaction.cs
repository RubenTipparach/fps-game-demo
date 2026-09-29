using System;
using Godot;

namespace Brushfire;

/// <summary>Anything the player can use with the use key: pickups, containers, doors, NPCs, exits.</summary>
public interface IInteractable
{
    /// <summary>Text for the HUD prompt, or null when there is nothing to do right now.</summary>
    string Prompt(PlayerController player);
    /// <summary>Seconds the use key must be held (lockpicking, hacking). 0 = instant.</summary>
    float HoldTime(PlayerController player) => 0f;
    /// <summary>True when the action can't be performed (the prompt explains why).</summary>
    bool Blocked(PlayerController player) => false;
    void Interact(PlayerController player);
}

/// <summary>
/// Lock data shared by doors, containers and terminals. Opening options, in order:
/// the key item, a known code (flag), lockpicking (skill >= tier, uses a lockpick),
/// hacking (skill >= tier, uses a multitool).
/// </summary>
public class LockSpec
{
    public int PickTier;
    public int HackTier;
    public string Key = "";
    public string CodeFlag = "";
    public bool Locked => PickTier > 0 || HackTier > 0 || !string.IsNullOrEmpty(Key) || !string.IsNullOrEmpty(CodeFlag);

    enum Way { None, Key, Code, Pick, Hack }

    Way Best(out string why)
    {
        var s = Game.Instance.State;
        why = "";
        if (!string.IsNullOrEmpty(Key) && s.Inventory.Has(Key))
            return Way.Key;
        if (!string.IsNullOrEmpty(CodeFlag) && s.Flag(CodeFlag))
            return Way.Code;
        int lp = s.Character.Get(Skill.Lockpicking), hk = s.Character.Get(Skill.Hacking);
        if (PickTier > 0 && lp >= PickTier && s.Inventory.Has("lockpick"))
            return Way.Pick;
        if (HackTier > 0 && hk >= HackTier && s.Inventory.Has("multitool"))
            return Way.Hack;
        var needs = new System.Collections.Generic.List<string>();
        if (!string.IsNullOrEmpty(Key)) needs.Add(ItemDb.Get(Key)?.Name ?? Key);
        if (PickTier > 0) needs.Add(lp >= PickTier ? "a lockpick" : $"Lockpicking {PickTier}");
        if (HackTier > 0) needs.Add(hk >= HackTier ? "a multitool" : $"Hacking {HackTier}");
        if (!string.IsNullOrEmpty(CodeFlag)) needs.Add("the code");
        why = "needs " + string.Join(" or ", needs);
        return Way.None;
    }

    public string Prompt(string noun)
    {
        return Best(out string why) switch
        {
            Way.Key => $"Unlock {noun} ({ItemDb.Get(Key)?.Name})",
            Way.Code => $"Enter code ({noun})",
            Way.Pick => $"Pick lock · tier {PickTier} (hold)",
            Way.Hack => $"Hack lock · tier {HackTier} (hold)",
            _ => $"Locked {noun}: {why}",
        };
    }

    public bool CanOpen => Best(out _) != Way.None;

    public float HoldTime
    {
        get
        {
            var c = Game.Instance.State.Character;
            return Best(out _) switch
            {
                Way.Pick => 1.2f * PickTier * (c.Get(Skill.Lockpicking) >= 3 ? 0.5f : 1f),
                Way.Hack => 1.5f * HackTier,
                _ => 0f,
            };
        }
    }

    /// <summary>Consumes the tool, pays XP. Returns true when the lock opened.</summary>
    public bool Open()
    {
        var s = Game.Instance.State;
        switch (Best(out _))
        {
            case Way.Key:
            case Way.Code:
                break;
            case Way.Pick:
                s.Inventory.Remove("lockpick");
                s.Character.AddXp(20 * PickTier, "lock picked");
                break;
            case Way.Hack:
                s.Inventory.Remove("multitool");
                s.Character.AddXp(20 * HackTier, "system hacked");
                break;
            default:
                return false;
        }
        PickTier = HackTier = 0;
        Key = CodeFlag = "";
        return true;
    }
}

/// <summary>
/// Player component: finds the interactable under the crosshair, drives the HUD prompt and
/// handles tap/hold of the use key.
/// </summary>
public partial class Interactor : Node
{
    public const float Reach = 2.6f;
    public const uint Mask = Layers.World | Layers.Enemy | Layers.Pickup | Layers.Interact;

    PlayerController _player;
    public IInteractable Target { get; private set; }
    public string PromptText { get; private set; }
    public bool TargetBlocked { get; private set; }
    public float HoldProgress { get; private set; } = -1f;
    float _held;
    IInteractable _holding;

    public override void _Ready() => _player = GetParent<PlayerController>();

    public static IInteractable FindInteractable(Node n)
    {
        while (n != null)
        {
            if (n is IInteractable i)
                return i;
            n = n.GetParent();
        }
        return null;
    }

    public override void _PhysicsProcess(double delta)
    {
        Target = null;
        PromptText = null;
        if (_player.IsDead || !PlayerController.InputEnabled || DialogScreen.Current != null)
        {
            HoldProgress = -1f;
            return;
        }
        var cam = _player.Camera;
        Vector3 from = cam.GlobalPosition;
        Vector3 to = from - cam.GlobalBasis.Z * Reach;
        var q = PhysicsRayQueryParameters3D.Create(from, to, Mask, new Godot.Collections.Array<Rid> { _player.GetRid() });
        q.CollideWithAreas = true;
        var hit = _player.GetWorld3D().DirectSpaceState.IntersectRay(q);
        if (hit.Count > 0 && hit["collider"].AsGodotObject() is Node node)
        {
            Target = FindInteractable(node);
            if (Target != null)
            {
                PromptText = Target.Prompt(_player);
                TargetBlocked = Target.Blocked(_player);
                if (PromptText == null)
                    Target = null;
            }
        }

        // Hold-to-use (lockpicking, hacking) or tap.
        float dt = (float)delta;
        bool down = Input.IsActionPressed("use");
        if (Target != null && !TargetBlocked && down && (_holding == null || _holding == Target))
        {
            float need = Target.HoldTime(_player);
            _holding = Target;
            if (need <= 0f)
            {
                if (Input.IsActionJustPressed("use"))
                {
                    _holding = null;
                    Target.Interact(_player);
                }
                HoldProgress = -1f;
                return;
            }
            if (_held == 0f)
                Audio.Play2D(_player, "ui_click", -12f);
            _held += dt;
            HoldProgress = Mathf.Clamp(_held / need, 0f, 1f);
            if (_held >= need)
            {
                _held = 0f;
                HoldProgress = -1f;
                _holding = null;
                Target.Interact(_player);
            }
            return;
        }
        if (!down)
            _holding = null;
        _held = 0f;
        HoldProgress = -1f;
    }
}
