using Godot;

namespace Brushfire;

/// <summary>
/// An item lying in the world. Use it to pick it up into the grid inventory. Taken items are
/// remembered in GameState.Taken so they don't come back when you return to the level.
/// The visual is the item's model (res://models/items/&lt;id&gt;.glb), or a labelled crate.
/// </summary>
public partial class WorldItem : Area3D, IInteractable
{
    [Export] public string ItemId = "medkit";
    [Export] public int Count = 1;
    /// <summary>Dropped by the player at runtime: not persisted.</summary>
    [Export] public bool Dropped;

    ItemDef _def;
    string _key;

    public override void _Ready()
    {
        _def = ItemDb.Get(ItemId);
        _key = Dropped ? "" : LevelRoot.PersistKey(this);
        if (_def == null || (!Dropped && Game.Instance.State.Taken.Contains(_key)))
        {
            QueueFree();
            return;
        }
        CollisionLayer = Layers.Interact;
        CollisionMask = 0;
        Monitoring = false;
        if (GetNodeOrNull("Visual") == null)
            AddChild(BuildVisual(_def));
        if (GetNodeOrNull<CollisionShape3D>("Shape") == null)
            AddChild(new CollisionShape3D
            {
                Name = "Shape",
                Position = new Vector3(0, 0.15f, 0),
                Shape = new BoxShape3D { Size = new Vector3(0.18f * _def.W + 0.25f, 0.35f, 0.18f * _def.H + 0.25f) },
            });
    }

    public static Node3D BuildVisual(ItemDef def)
    {
        Node3D vis;
        if (!string.IsNullOrEmpty(def.Model) && ResourceLoader.Exists(def.Model))
            vis = GD.Load<PackedScene>(def.Model).Instantiate<Node3D>();
        else
        {
            // Fallback: a small crate with the item name, so missing models are obvious but usable.
            vis = new Node3D();
            var box = new MeshInstance3D
            {
                Mesh = new BoxMesh { Size = new Vector3(0.12f * def.W + 0.15f, 0.12f, 0.12f * def.H + 0.15f) },
                Position = new Vector3(0, 0.06f, 0),
                MaterialOverride = new StandardMaterial3D { AlbedoColor = new Color(0.35f, 0.3f, 0.22f), Roughness = 0.8f },
            };
            vis.AddChild(box);
            vis.AddChild(new Label3D
            {
                Text = def.Name, FontSize = 32, PixelSize = 0.004f, Position = new Vector3(0, 0.25f, 0),
                Billboard = BaseMaterial3D.BillboardModeEnum.Enabled, Modulate = UiTheme.Accent, OutlineSize = 6,
            });
        }
        vis.Name = "Visual";
        foreach (var n in vis.FindChildren("*", "GeometryInstance3D", true, false))
            ((GeometryInstance3D)n).GIMode = GeometryInstance3D.GIModeEnum.Dynamic;
        return vis;
    }

    public string Prompt(PlayerController p)
    {
        if (_def == null)
            return null;
        string n = Count > 1 ? $"{_def.Name} ×{Count}" : _def.Name;
        return Game.Instance.State.Inventory.RoomFor(_def, 1) < 1 ? $"{n}: no room in inventory" : $"Take {n}";
    }

    public bool Blocked(PlayerController p) => Game.Instance.State.Inventory.RoomFor(_def, 1) < 1;

    public void Interact(PlayerController p)
    {
        var s = Game.Instance.State;
        int left = s.Inventory.Add(_def, Count);
        int got = Count - left;
        if (got <= 0)
            return;
        s.Say(got > 1 ? $"{_def.Name} ×{got}" : _def.Name);
        Audio.Play2D(p, _def.Cat == ItemCategory.Weapon ? "pickup_weapon" : "pickup_ammo", -4f);
        Count = left;
        if (Count <= 0)
        {
            if (!string.IsNullOrEmpty(_key))
                s.Taken.Add(_key);
            QueueFree();
        }
    }

    /// <summary>Spawn a dropped item in front of the player.</summary>
    public static void Drop(PlayerController p, ItemDef def, int count)
    {
        var w = new WorldItem { ItemId = def.Id, Count = count, Dropped = true, Name = "Dropped_" + def.Id };
        Vector3 fwd = p.LookDirection with { Y = 0 };
        Vector3 at = p.GlobalPosition + fwd.Normalized() * 0.9f + Vector3.Up * 0.3f;
        // Settle it on the floor below.
        var q = PhysicsRayQueryParameters3D.Create(at, at + Vector3.Down * 3f, Layers.World);
        var hit = p.GetWorld3D().DirectSpaceState.IntersectRay(q);
        if (hit.Count > 0)
            at = (Vector3)hit["position"];
        LevelRoot.Current.AddChild(w);
        w.GlobalPosition = at;
    }
}

/// <summary>
/// Lockers, crates and safes. Use to search: everything inside goes to the inventory (what
/// doesn't fit stays inside). Locks use <see cref="LockSpec"/>.
/// </summary>
public partial class LootContainer : Node3D, IInteractable
{
    [Export] public string Noun = "locker";
    /// <summary>"item:count,item:count".</summary>
    [Export] public string Items = "";
    [Export] public int PickTier;
    [Export] public int HackTier;
    [Export] public string Key = "";
    [Export] public string CodeFlag = "";
    /// <summary>Owning faction: searching it in front of them blows a disguise.</summary>
    [Export] public string Owner = "";

    LockSpec _lock;
    string _key;
    readonly System.Collections.Generic.List<(string id, int n)> _contents = new();

    public override void _Ready()
    {
        _key = LevelRoot.PersistKey(this);
        var s = Game.Instance.State;
        _lock = new LockSpec { PickTier = PickTier, HackTier = HackTier, Key = Key, CodeFlag = CodeFlag };
        if (s.Flag("unlocked:" + _key))
            _lock = new LockSpec();
        if (!s.Taken.Contains(_key))
            foreach (var part in Items.Split(',', System.StringSplitOptions.RemoveEmptyEntries | System.StringSplitOptions.TrimEntries))
            {
                var kv = part.Split(':');
                if (ItemDb.Exists(kv[0]))
                    _contents.Add((kv[0], kv.Length > 1 && int.TryParse(kv[1], out int n) ? n : 1));
            }
        foreach (var n in FindChildren("*", "CollisionObject3D", true, false))
            ((CollisionObject3D)n).CollisionLayer |= Layers.Interact;
    }

    public string Prompt(PlayerController p)
    {
        if (_lock.Locked)
            return _lock.Prompt(Noun);
        return _contents.Count == 0 ? $"{Capitalize(Noun)} (empty)" : $"Search {Noun}";
    }

    static string Capitalize(string s) => string.IsNullOrEmpty(s) ? s : char.ToUpper(s[0]) + s[1..];

    public bool Blocked(PlayerController p) => _lock.Locked ? !_lock.CanOpen : _contents.Count == 0;
    public float HoldTime(PlayerController p) => _lock.Locked ? _lock.HoldTime : 0f;

    public void Interact(PlayerController p)
    {
        var s = Game.Instance.State;
        if (_lock.Locked)
        {
            if (!_lock.Open())
                return;
            s.SetFlag("unlocked:" + _key);
            Audio.Play2D(p, "door_open", -6f);
            s.Say($"{Capitalize(Noun)} unlocked");
            return;
        }
        Events.EmitNoise(GlobalPosition, 4f);
        for (int i = _contents.Count - 1; i >= 0; i--)
        {
            var (id, n) = _contents[i];
            var def = ItemDb.Get(id);
            int left = s.Inventory.Add(def, n);
            if (left < n)
                s.Say(n - left > 1 ? $"{def.Name} ×{n - left}" : def.Name);
            if (left == 0)
                _contents.RemoveAt(i);
            else
                _contents[i] = (id, left);
        }
        if (_contents.Count == 0)
            s.Taken.Add(_key);
        else
            s.Say("Inventory full");
        Audio.Play2D(p, "pickup_ammo", -6f);
    }
}
