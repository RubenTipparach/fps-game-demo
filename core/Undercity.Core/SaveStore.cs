// Save slots on disk: one JSON file per slot, written to a temp file and renamed, so a crash
// mid-write leaves the old save whole.
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

    /// <summary>Every save, newest first.</summary>
    public IReadOnlyList<SaveSlot> List() => Directory.GetFiles(_folder, "*.json")
        .Select(f => new SaveSlot(Path.GetFileNameWithoutExtension(f), File.GetLastWriteTimeUtc(f)))
        .OrderByDescending(s => s.WrittenUtc).ThenBy(s => s.Slot, StringComparer.Ordinal)
        .ToList();
}
