using Godot;

namespace Brushfire;

/// <summary>Use it to travel to another level of the campaign (storm drain, yard gate).</summary>
public partial class LevelExit : Node3D, IInteractable
{
    [Export] public string TargetLevel = "hub";
    [Export] public string TargetSpawn = "";
    [Export] public string Label = "Leave";
    /// <summary>Optional condition: flag that must be set (e.g. gate unlocked).</summary>
    [Export] public string RequireFlag = "";
    [Export] public string LockedText = "It's locked.";

    public override void _Ready()
    {
        foreach (var n in FindChildren("*", "CollisionObject3D", true, false))
            ((CollisionObject3D)n).CollisionLayer |= Layers.Interact;
        if (GetChildCount() == 0)
        {
            var area = new Area3D { CollisionLayer = Layers.Interact, CollisionMask = 0, Monitoring = false };
            area.AddChild(new CollisionShape3D { Position = new Vector3(0, 1.2f, 0), Shape = new BoxShape3D { Size = new Vector3(2.2f, 2.4f, 0.6f) } });
            AddChild(area);
        }
    }

    bool Allowed => string.IsNullOrEmpty(RequireFlag) || Game.Instance.State.Flag(RequireFlag);
    public string Prompt(PlayerController p) => Allowed ? Label : LockedText;
    public bool Blocked(PlayerController p) => !Allowed;

    public void Interact(PlayerController p)
    {
        if (!Allowed)
            return;
        Game.Instance.TravelTo(TargetLevel, TargetSpawn);
    }
}

/// <summary>
/// Area that fires story effects when the player walks in: flags, objectives, feed messages.
/// Optional conditions: RequireFlag / ForbidFlag.
/// </summary>
public partial class StoryTrigger : Area3D
{
    [Export] public Vector3 Size = new(3, 3, 3);
    [Export] public string SetFlag = "";
    [Export] public string RequireFlag = "";
    [Export] public string ForbidFlag = "";
    [Export] public string Objective = "";   // "quest/objective"
    [Export] public string Reveal = "";      // "quest/objective"
    [Export] public string Message = "";
    [Export] public bool Once = true;
    [Export] public int Xp;

    string _key;

    public override void _Ready()
    {
        _key = LevelRoot.PersistKey(this);
        if (Once && Game.Instance.State.Taken.Contains(_key))
        {
            QueueFree();
            return;
        }
        CollisionLayer = 0;
        CollisionMask = Layers.Player;
        AddChild(new CollisionShape3D { Position = new Vector3(0, Size.Y / 2, 0), Shape = new BoxShape3D { Size = Size } });
        BodyEntered += OnEnter;
    }

    void OnEnter(Node3D body)
    {
        if (body is not PlayerController)
            return;
        var s = Game.Instance.State;
        if (!string.IsNullOrEmpty(RequireFlag) && !s.Flag(RequireFlag))
            return;
        if (!string.IsNullOrEmpty(ForbidFlag) && s.Flag(ForbidFlag))
            return;
        if (!string.IsNullOrEmpty(SetFlag))
            s.SetFlag(SetFlag);
        if (!string.IsNullOrEmpty(Reveal))
        {
            var p = Reveal.Split('/');
            s.Quests.Reveal(p[0], p[1]);
        }
        if (!string.IsNullOrEmpty(Objective))
        {
            var p = Objective.Split('/');
            s.CompleteObjective(p[0], p[1]);
        }
        if (!string.IsNullOrEmpty(Message))
            PlayerController.Instance?.Hud.ShowPickup(Message);
        if (Xp > 0)
            s.Character.AddXp(Xp, "discovery");
        if (Once)
        {
            s.Taken.Add(_key);
            SetDeferred(Area3D.PropertyName.Monitoring, false);
        }
    }
}

/// <summary>
/// A terminal: log in (instant, or hack it) to read its text; access can also unlock a door and
/// set a flag (e.g. learn a safe code).
/// </summary>
public partial class Terminal : Node3D, IInteractable
{
    [Export] public string Title = "TERMINAL";
    [Export(PropertyHint.MultilineText)] public string Text = "";
    [Export] public int HackTier;
    [Export] public string SetFlag = "";
    [Export] public string OpenDoor = "";

    LockSpec _lock;
    string _key;

    public override void _Ready()
    {
        _key = LevelRoot.PersistKey(this);
        _lock = new LockSpec { HackTier = HackTier };
        if (Game.Instance.State.Flag("unlocked:" + _key))
            _lock = new LockSpec();
        foreach (var n in FindChildren("*", "CollisionObject3D", true, false))
            ((CollisionObject3D)n).CollisionLayer |= Layers.Interact;
    }

    public string Prompt(PlayerController p) => _lock.Locked ? _lock.Prompt("terminal") : $"Use {Title}";
    public bool Blocked(PlayerController p) => _lock.Locked && !_lock.CanOpen;
    public float HoldTime(PlayerController p) => _lock.Locked ? _lock.HoldTime : 0f;

    public void Interact(PlayerController p)
    {
        var s = Game.Instance.State;
        if (_lock.Locked)
        {
            if (!_lock.Open())
                return;
            s.SetFlag("unlocked:" + _key);
        }
        if (!string.IsNullOrEmpty(SetFlag) && !s.Flag(SetFlag))
        {
            s.SetFlag(SetFlag);
            s.Say("Noted in your journal");
        }
        if (!string.IsNullOrEmpty(OpenDoor))
            Doorway.OpenById(OpenDoor);
        TextScreen.Show(Title, Text);
    }
}
