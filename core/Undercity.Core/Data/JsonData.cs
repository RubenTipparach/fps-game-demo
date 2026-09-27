// Loads Undercity's data files (game/data/*.json) into typed tables, and refuses bad ones.
//
// It lives in the core because every rule reads its numbers from these tables, and a test must
// be able to load the real files without Godot (CLAUDE.md 5.5, 5.6). Authored data fails
// loudly: an unknown key, a parse error or a failed validation stops startup with the file and
// the field. Nothing silently falls back to a default.

using System.Text.Json;
using System.Text.Json.Serialization;

namespace Undercity.Core.Data;

/// <summary>Where data files come from: the Godot resource system in the game, the disk in tests.</summary>
public interface IDataSource
{
    /// <summary>Reads a data file by its path relative to the data root, such as <c>items.json</c>.</summary>
    string Read(string relativePath);

    /// <summary>True when the file exists.</summary>
    bool Exists(string relativePath);

    /// <summary>Lists the files in a data folder, sorted by name, such as the dialog trees.</summary>
    IReadOnlyList<string> List(string relativeFolder);
}

/// <summary>A data source reading from a folder on disk. Used by tests and tools.</summary>
public sealed class FolderDataSource : IDataSource
{
    private readonly string _root;

    /// <summary>Creates a source rooted at <paramref name="root"/>, the game's data folder.</summary>
    public FolderDataSource(string root) => _root = root;

    /// <inheritdoc/>
    public string Read(string relativePath) => File.ReadAllText(Path.Combine(_root, relativePath));

    /// <inheritdoc/>
    public bool Exists(string relativePath) => File.Exists(Path.Combine(_root, relativePath));

    /// <inheritdoc/>
    public IReadOnlyList<string> List(string relativeFolder)
    {
        var dir = Path.Combine(_root, relativeFolder);
        if (!Directory.Exists(dir))
        {
            return Array.Empty<string>();
        }
        return Directory.GetFiles(dir)
            .Select(f => Path.GetRelativePath(_root, f).Replace('\\', '/'))
            .OrderBy(f => f, StringComparer.Ordinal)
            .ToArray();
    }
}

/// <summary>A data file that failed to load or validate. The message names the file and the field.</summary>
public sealed class DataException : Exception
{
    /// <summary>Creates the exception for <paramref name="file"/>.</summary>
    public DataException(string file, string message)
        : base($"{file}: {message}") => File = file;

    /// <summary>Creates the exception with the underlying parse error.</summary>
    public DataException(string file, string message, Exception inner)
        : base($"{file}: {message}", inner) => File = file;

    /// <summary>The data file that failed.</summary>
    public string File { get; }
}

/// <summary>A table that can check itself after loading and report every problem it finds.</summary>
public interface IValidated
{
    /// <summary>Adds a message to <paramref name="errors"/> for every value out of range or reference that doesn't resolve.</summary>
    void Validate(ICollection<string> errors);
}

/// <summary>The one JSON configuration every data file and save uses.</summary>
public static class JsonData
{
    /// <summary>
    /// snake_case keys, enums as strings, comments and trailing commas allowed, and unknown keys
    /// rejected, because a misspelt knob that silently does nothing is the worst kind of bug.
    /// </summary>
    public static readonly JsonSerializerOptions Options = CreateOptions();

    private static JsonSerializerOptions CreateOptions()
    {
        var o = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            DictionaryKeyPolicy = null,
            ReadCommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
            UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
            WriteIndented = true,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        };
        o.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseLower));
        return o;
    }

    /// <summary>
    /// Loads and validates <paramref name="relativePath"/>. Throws <see cref="DataException"/>
    /// naming the file and the problem when it can't be read, parsed or validated.
    /// </summary>
    public static T Load<T>(IDataSource source, string relativePath)
        where T : class, IValidated
    {
        string text;
        try
        {
            text = source.Read(relativePath);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            throw new DataException(relativePath, "can't be read", e);
        }
        var value = Parse<T>(text, relativePath);
        var errors = new List<string>();
        value.Validate(errors);
        if (errors.Count > 0)
        {
            throw new DataException(relativePath, string.Join("; ", errors));
        }
        return value;
    }

    /// <summary>Parses JSON text as <typeparamref name="T"/>, naming <paramref name="file"/> on failure.</summary>
    public static T Parse<T>(string text, string file)
        where T : class
    {
        try
        {
            return JsonSerializer.Deserialize<T>(text, Options)
                ?? throw new DataException(file, "is empty");
        }
        catch (JsonException e)
        {
            throw new DataException(file, $"{e.Message} (path {e.Path})", e);
        }
    }

    /// <summary>Serializes <paramref name="value"/> with the shared options.</summary>
    public static string Write<T>(T value) => JsonSerializer.Serialize(value, Options);
}
