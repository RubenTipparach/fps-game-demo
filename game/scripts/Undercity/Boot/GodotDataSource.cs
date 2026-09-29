// Reads game/data through Godot's file API, so the same tables load in the editor and in an
// exported build (where res:// is a pack, not a folder).
//
// It lives in the Godot layer because it is the one place the core's IDataSource meets the
// engine's file system (CLAUDE.md 5.2).

#nullable enable
using System.Collections.Generic;
using Godot;
using Undercity.Core.Data;

namespace Undercity.Client;

/// <summary>game/data as res://data.</summary>
public sealed class GodotDataSource : IDataSource
{
    private const string Root = "res://data/";

    /// <inheritdoc/>
    public string Read(string relativePath)
    {
        using var f = FileAccess.Open(Root + relativePath, FileAccess.ModeFlags.Read);
        if (f is null)
        {
            throw new DataException(relativePath, $"can't open ({FileAccess.GetOpenError()})");
        }
        return f.GetAsText();
    }

    /// <inheritdoc/>
    public bool Exists(string relativePath) => FileAccess.FileExists(Root + relativePath);

    /// <inheritdoc/>
    public IReadOnlyList<string> List(string relativeFolder)
    {
        var files = new List<string>();
        foreach (var name in DirAccess.GetFilesAt(Root + relativeFolder))
        {
            files.Add(relativeFolder.TrimEnd('/') + "/" + name.TrimSuffix(".remap"));
        }
        files.Sort(System.StringComparer.Ordinal);
        return files;
    }
}
