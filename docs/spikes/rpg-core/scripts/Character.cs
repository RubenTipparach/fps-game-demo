using System;
using Godot;

namespace Brushfire;

public enum Skill { Firearms, Melee, Stealth, Hacking, Lockpicking, Deception, Persuasion }

/// <summary>A skill and its five rank perks (the skill's tree). See docs/design/immersive_sim.md.</summary>
public record SkillInfo(Skill Id, string Name, string Blurb, string[] Perks, string[] PerkText,
    (Skill skill, int rank)[] Requires);

/// <summary>
/// The runner: level, XP, skill ranks (0-5), skill points and credits. Checks are deterministic:
/// a check passes when the skill rank (plus situational bonuses) reaches the difficulty.
/// </summary>
public class Character
{
    public const int MaxRank = 5;
    public int Level { get; private set; } = 1;
    public int Xp { get; private set; }
    public int SkillPoints { get; private set; } = 4;
    public int Credits { get; set; } = 150;
    readonly int[] _ranks = new int[Enum.GetValues<Skill>().Length];

    public event Action Changed;
    public event Action<int> LeveledUp;
    public event Action<int, string> XpGained;

    public int XpToNext => Level * 500;
    public int MaxHealth => 100 + (Level - 1) * 10;

    public int Get(Skill s) => _ranks[(int)s];

    public static readonly SkillInfo[] Skills =
    {
        new(Skill.Firearms, "Firearms", "Spread, recoil and reload speed with guns.",
            new[] { "Steady Hands", "Quick Reload", "Headhunter", "Recoil Control", "Deadeye" },
            new[] { "-15% spread", "Faster weapon handling", "+50% headshot damage", "-30% recoil", "-40% spread when still" },
            Array.Empty<(Skill, int)>()),
        new(Skill.Melee, "Melee", "Baton damage and takedowns.",
            new[] { "Clubber", "Silent Takedown", "Fast Takedown", "Heavy Hitter", "One-Punch" },
            new[] { "+25% baton damage", "Knock out unaware targets from behind in one hit", "Takedowns are faster", "+50% baton damage", "Knock out anyone in one hit" },
            Array.Empty<(Skill, int)>()),
        new(Skill.Stealth, "Stealth", "Noise and visibility.",
            new[] { "Soft Steps", "Low Profile", "Shadow", "Ghost", "Vanish" },
            new[] { "-25% footstep noise", "Faster crouch-walking", "-30% visibility in shadow", "Sprinting makes no noise", "Enemies lose track of you twice as fast" },
            Array.Empty<(Skill, int)>()),
        new(Skill.Hacking, "Hacking", "Terminals, cameras and turrets.",
            new[] { "Script Kiddie", "Cracker", "Camera Loop", "Turret Control", "Ghost Login" },
            new[] { "Hack tier-1 terminals", "Hack tier-2 terminals", "Hacked cameras stop watching", "Turn turrets on their owners", "Hack tier-3 terminals, no trace" },
            Array.Empty<(Skill, int)>()),
        new(Skill.Lockpicking, "Lockpicking", "Doors, lockers and safes.",
            new[] { "Rake", "Tension", "Fast Picks", "Pin Master", "Safecracker" },
            new[] { "Pick tier-1 locks", "Pick tier-2 locks", "Picking takes half the time", "Pick tier-3 locks", "Open safes without a code" },
            Array.Empty<(Skill, int)>()),
        new(Skill.Deception, "Deception", "Disguises and lies. Cover = Deception + disguise quality.",
            new[] { "Passing Glance", "Fast Talk", "Master of Disguise", "Silver Tongue", "Doppelganger" },
            new[] { "A matching outfit passes at a glance outside scrutiny range", "Lie options in dialog", "Drawing a weapon gives you 2 seconds before your cover breaks", "Bluff bosses", "Halves every observer's scrutiny range" },
            new[] { (Skill.Stealth, 2) }),
        new(Skill.Persuasion, "Persuasion", "Charm, intimidation and prices.",
            new[] { "Friendly", "Haggler", "Intimidate", "Negotiator", "Kingmaker" },
            new[] { "Charm options in dialog", "-15% shop prices", "Threaten weaker NPCs", "Talk down hostage-takers", "Turn gang lieutenants" },
            Array.Empty<(Skill, int)>()),
    };

    public static SkillInfo Info(Skill s) => Skills[(int)s];

    public Character()
    {
        _ranks[(int)Skill.Deception] = 1; // the runner's trade
    }

    /// <summary>Skill points needed for the next rank: ranks 1-2 cost 1, ranks 3-5 cost 2.</summary>
    public static int Cost(int nextRank) => nextRank <= 2 ? 1 : 2;

    /// <summary>Why the next rank can't be bought, or null when it can.</summary>
    public string WhyNot(Skill s)
    {
        int next = Get(s) + 1;
        if (next > MaxRank)
            return "Mastered";
        // Cross-tree requirements only gate the upper half of a tree.
        if (next >= 3)
            foreach (var (req, rank) in Info(s).Requires)
                if (Get(req) < rank)
                    return $"Needs {Info(req).Name} {rank}";
        if (SkillPoints < Cost(next))
            return $"Needs {Cost(next)} skill point{(Cost(next) > 1 ? "s" : "")}";
        return null;
    }

    public bool Raise(Skill s)
    {
        if (WhyNot(s) != null)
            return false;
        int next = Get(s) + 1;
        SkillPoints -= Cost(next);
        _ranks[(int)s] = next;
        Changed?.Invoke();
        return true;
    }

    public void AddXp(int amount, string reason)
    {
        if (amount <= 0)
            return;
        Xp += amount;
        XpGained?.Invoke(amount, reason);
        while (Xp >= XpToNext)
        {
            Xp -= XpToNext;
            Level++;
            SkillPoints += 2;
            LeveledUp?.Invoke(Level);
        }
        Changed?.Invoke();
    }

    public bool Spend(int credits)
    {
        if (Credits < credits)
            return false;
        Credits -= credits;
        Changed?.Invoke();
        return true;
    }

    public void Earn(int credits)
    {
        Credits += credits;
        Changed?.Invoke();
    }

    /// <summary>Debug/autotest helper.</summary>
    public void SetRank(Skill s, int rank)
    {
        _ranks[(int)s] = Mathf.Clamp(rank, 0, MaxRank);
        Changed?.Invoke();
    }
}
