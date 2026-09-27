// The use key: finds what the crosshair is on, shows its prompt, and uses it on a press or after
// its hold time. One interactor for every kind of object (openspec/changes/world-interaction).
//
// It lives in the Godot layer because it turns input and a ray into a core-backed action; the
// prompt and the hold time come from the object, which gets them from the core.

#nullable enable
using Godot;

namespace Undercity.Client;

/// <summary>The player's use key.</summary>
public partial class Interactor : Node, IWired
{
    /// <summary>How far the player can reach, metres.</summary>
    [Export] public float ReachM = 2.6f;

    private Services? _s;
    private Brushfire.PlayerController? _player;
    private IInteractable? _target;
    private double _held;

    /// <inheritdoc/>
    public void Wire(Services services)
    {
        _s = services;
        _player = GetParent<Brushfire.PlayerController>();
    }

    public override void _PhysicsProcess(double delta)
    {
        if (_s is null || _player is null)
        {
            return;
        }
        var target = _s.Screens.Blocking || _player.IsDead ? null : Find();
        if (!ReferenceEquals(target, _target))
        {
            _target = target;
            _held = 0;
            _s.Screens.ShowHold(-1);
        }
        if (_target is null)
        {
            _s.Screens.ShowPrompt("", false);
            return;
        }
        var what = _target.Describe();
        _s.Screens.ShowPrompt(what.Prompt, what.Enabled);
        if (!what.Enabled || !Brushfire.PlayerController.InputEnabled)
        {
            _held = 0;
            _s.Screens.ShowHold(-1);
            return;
        }
        if (what.HoldS <= 0)
        {
            if (Input.IsActionJustPressed("use"))
            {
                _target.Use();
            }
            return;
        }
        if (!Input.IsActionPressed("use"))
        {
            _held = 0;
            _s.Screens.ShowHold(-1);
            return;
        }
        _held += delta;
        _s.Screens.ShowHold(_held / what.HoldS);
        if (_held >= what.HoldS)
        {
            _held = 0;
            _s.Screens.ShowHold(-1);
            _target.Use();
        }
    }

    private IInteractable? Find()
    {
        var from = _player!.EyePosition;
        var query = PhysicsRayQueryParameters3D.Create(from, from + _player.LookDirection * ReachM,
            Brushfire.Layers.World | Brushfire.Layers.Enemy | Brushfire.Layers.Pickup);
        query.Exclude = new Godot.Collections.Array<Rid> { _player.GetRid() };
        var hit = _player.GetWorld3D().DirectSpaceState.IntersectRay(query);
        if (hit.Count == 0)
        {
            return null;
        }
        for (var n = hit["collider"].As<Node>(); n is not null; n = n.GetParent())
        {
            if (n is IInteractable i)
            {
                return i;
            }
            if (n is UndercityLevel)
            {
                break;
            }
        }
        return null;
    }
}
