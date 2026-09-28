// Save slots on disk: one JSON file per slot, written to a temp file and renamed, so a crash
// mid-write leaves the old save whole. The save lists (title, pause) read their summaries here.
//
// It lives in the core because the file format and its safety are rules every build must agree
// on; the game only supplies the folder (user://saves) (openspec/changes/undercity-architecture,
// design section 5).

using System.Text.RegularExpressions;
using Undercity.Core.Data;

namespace Undercity.Core;

/// <summary>One save file as a listing shows it.</summary>
/// <param name="Slot">The slot name: auto, quick, or a name.</param>
/// <param name="WrittenUtc">When it was written.</param>
public sealed record SaveSlot(string Slot, DateTime WrittenUtc);

/// <summary>The save folder.</summary>
public sealed partial class SaveStore
{
    private readonly string _folder;

    /// <summary>Uses <paramref name="folder"/>, creating it when needed.</summary>
    public SaveStore(string folder)
    {
        _folder = folder;
        Directory.CreateDirectory(folder);
    }

    [GeneratedRegex("^[a-z0-9_]{1,32}$")]
    private static partial Regex SlotPattern();

    private string PathOf(string slot) => SlotPattern().IsMatch(slot)
        ? Path.Combine(_folder, slot + ".json")
        : throw new ArgumentException($"bad save slot '{slot}': use a-z, 0-9 and _", nameof(slot));

    /// <summary>True when the slot has a save.</summary>
    public bool Exists(string slot) => File.Exists(PathOf(slot));

    /// <summary>Writes a save: to a temp file first, then renamed over the old one.</summary>
    public void Write(string slot, SaveGame save)
    {
        var path = PathOf(slot);
        var temp = path + ".tmp";
        File.WriteAllText(temp, save.ToJson());
        File.Move(temp, path, overwrite: true);
    }

    /// <summary>
    /// Reads a slot, or null when it's empty. A file that isn't a save at all throws
    /// <see cref="DataException"/> naming the file; a save with damaged contents loads and is
    /// repaired by <see cref="GameState.Load"/>.
    /// </summary>
    public SaveGame? Read(string slot)
    {
        var path = PathOf(slot);
        if (!File.Exists(path))
        {
            return null;
        }
        return JsonData.Parse<SaveGame>(File.ReadAllText(path), path);
    }

    /// <summary>Every save, newest first. Files whose names aren't slot names are ignored.</summary>
    public IReadOnlyList<SaveSlot> List() => Directory.GetFiles(_folder, "*.json")
        .Where(f => SlotPattern().IsMatch(Path.GetFileNameWithoutExtension(f)))
        .Select(f => new SaveSlot(Path.GetFileNameWithoutExtension(f), File.GetLastWriteTimeUtc(f)))
        .OrderByDescending(s => s.WrittenUtc).ThenBy(s => s.Slot, StringComparer.Ordinal)
        .ToList();

    /// <summary>
    /// A slot as the save lists show it: where and how long, read from the save itself so nothing
    /// is stored twice. A file that isn't a save reads as damaged rather than throwing.
    /// </summary>
    public SaveSummary Summary(string slot)
    {
        var path = PathOf(slot);
        if (!File.Exists(path))
        {
            return new SaveSummary(slot, false, false, "", 0, DateTime.MinValue);
        }
        var written = File.GetLastWriteTimeUtc(path);
        try
        {
            var save = JsonData.Parse<SaveGame>(File.ReadAllText(path), path);
            return new SaveSummary(slot, true, false, save.World.CurrentLevel, save.World.PlayTimeS, written);
        }
        catch (DataException)
        {
            return new SaveSummary(slot, true, true, "", 0, written);
        }
    }

    /// <summary>
    /// The save list: the slots that hold a save, newest first, then the empty ones in the order
    /// given (openspec/specs/title-and-pause).
    /// </summary>
    public IReadOnlyList<SaveSummary> Summaries(IEnumerable<string> slots)
    {
        var all = slots.Select(Summary).ToList();
        return all.Where(s => s.Exists)
            .OrderByDescending(s => s.WrittenUtc).ThenBy(s => s.Slot, StringComparer.Ordinal)
            .Concat(all.Where(s => !s.Exists))
            .ToList();
    }

    /// <summary>The newest save that can be loaded, of any slot, or null: what Continue loads.</summary>
    public SaveSummary? Newest() => List().Select(s => Summary(s.Slot)).FirstOrDefault(s => s.Loadable);
}
