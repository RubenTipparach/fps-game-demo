// Save slots on disk (openspec/changes/undercity-architecture, task 3.3).

using Undercity.Core.Data;

namespace Undercity.Core.Tests;

public sealed class SaveStoreTests : IDisposable
{
    private readonly string _folder = Path.Combine(Path.GetTempPath(), "undercity-saves-" + Guid.NewGuid().ToString("N"));

    public void Dispose() => Directory.Delete(_folder, recursive: true);

    [Fact]
    public void A_written_slot_reads_back_the_same_save()
    {
        var store = new SaveStore(_folder);
        var save = TestData.NewGame().Save();
        store.Write("quick", save);
        Assert.Equal(save.ToJson(), store.Read("quick")!.ToJson());
        Assert.False(File.Exists(Path.Combine(_folder, "quick.json.tmp")), "the temp file is renamed, never left behind");
    }

    [Fact]
    public void An_empty_slot_reads_as_null()
    {
        Assert.Null(new SaveStore(_folder).Read("auto"));
    }

    [Fact]
    public void A_file_that_isnt_a_save_names_itself_in_the_error()
    {
        var store = new SaveStore(_folder);
        File.WriteAllText(Path.Combine(_folder, "auto.json"), "not json");
        var ex = Assert.Throws<DataException>(() => store.Read("auto"));
        Assert.Contains("auto.json", ex.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_slot_name_cannot_leave_the_folder()
    {
        Assert.Throws<ArgumentException>(() => new SaveStore(_folder).Write("../escape", TestData.NewGame().Save()));
    }
}
