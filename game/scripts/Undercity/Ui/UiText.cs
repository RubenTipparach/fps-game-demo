// Display names and number formatting shared by the Undercity screens: a faction's or an NPC's
// name from its id, and invariant-culture formatting so a German locale never prints "1,5 s".
//
// It lives in the UI layer because it only turns data ids into the names the tables already hold.

#nullable enable
using System;
using System.Globalization;
using System.Linq;
using Godot;
using Undercity.Core;

namespace Undercity.Client;

/// <summary>Text helpers for the screens.</summary>
public static class UiText
{
    /// <summary>A faction's display name, or "" for null.</summary>
    public static string Faction(GameData data, string? id) =>
        id is null ? "" : data.Factions.Factions.FirstOrDefault(f => f.Id == id)?.Name ?? id;

    /// <summary>A named NPC's display name, or the id when it isn't one.</summary>
    public static string Npc(GameData data, string id) => data.Npcs.Find(id)?.Name ?? id;

    /// <summary>
    /// Sizes a clipped label to its text, up to <paramref name="maxPx"/>: a name sits next to what
    /// follows it, and an overlong one ends in an ellipsis instead of pushing the row (CLAUDE.md 8).
    /// </summary>
    public static void FitWidth(Label label, float maxPx)
    {
        var text = label.Uppercase ? label.Text.ToUpperInvariant() : label.Text;
        var font = label.GetThemeFont("font");
        var width = font.GetStringSize(text, HorizontalAlignment.Left, -1, label.GetThemeFontSize("font_size")).X;
        label.CustomMinimumSize = new Vector2(Mathf.Min(Mathf.Ceil(width) + 2, maxPx), label.CustomMinimumSize.Y);
    }

    /// <summary>A level's title from the level index, such as "Low Harbor"; "" for an unknown id.</summary>
    public static string Place(GameData data, string levelId) => data.LevelIndex.Find(levelId)?.Title ?? "";

    /// <summary>Play time as the save lists show it: "1 h 42 m".</summary>
    public static string PlayTime(double seconds)
    {
        var minutes = (long)Math.Floor(Math.Max(0, seconds) / 60);
        return Invariant($"{minutes / 60} h {minutes % 60:00} m");
    }

    /// <summary>A save slot's name as the lists show it: "quick", "auto", "slot 1".</summary>
    public static string Slot(string slot) => slot.Replace('_', ' ');

    /// <summary>When a save was written, in local time: "21:12" today, "26 Sep" before.</summary>
    public static string Written(DateTime writtenUtc, DateTime nowUtc)
    {
        var local = writtenUtc.ToLocalTime();
        return local.Date == nowUtc.ToLocalTime().Date
            ? local.ToString("HH:mm", CultureInfo.InvariantCulture)
            : local.ToString("d MMM", CultureInfo.InvariantCulture);
    }

    /// <summary>Formats with the invariant culture.</summary>
    public static string Invariant(FormattableString s) => s.ToString(CultureInfo.InvariantCulture);
}
