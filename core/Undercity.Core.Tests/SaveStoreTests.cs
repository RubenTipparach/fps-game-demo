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
    public void The_save_list_puts_the_newest_save_first_and_empty_slots_last()
    {
        var store = new SaveStore(_folder);
        var state = TestData.NewGame();
        state.World.PlayTimeS = 6120;
        store.Write("auto", state.Save());
        store.Write("quick", state.Save());
        File.SetLastWriteTimeUtc(Path.Combine(_folder, "auto.json"), new DateTime(2026, 9, 27, 20, 53, 0, DateTimeKind.Utc));
        File.SetLastWriteTimeUtc(Path.Combine(_folder, "quick.json"), new DateTime(2026, 9, 27, 21, 12, 0, DateTimeKind.Utc));

        var list = store.Summaries(TestData.Data.Saves.Slots);

        Assert.Equal("quick,auto,slot_1,slot_2,slot_3", string.Join(',', list.Select(s => s.Slot)));
        Assert.Equal("hub", list[0].LevelId);
        Assert.Equal(6120, list[0].PlayTimeS);
        Assert.False(list[2].Exists, "an empty slot is listed so the player can save into it");
    }

    [Fact]
    public void Continue_picks_the_quicksave_when_it_is_newer_than_the_autosave()
    {
        var store = new SaveStore(_folder);
        store.Write("auto", TestData.NewGame().Save());
        store.Write("quick", TestData.NewGame().Save());
        File.SetLastWriteTimeUtc(Path.Combine(_folder, "auto.json"), new DateTime(2026, 9, 27, 20, 0, 0, DateTimeKind.Utc));
        File.SetLastWriteTimeUtc(Path.Combine(_folder, "quick.json"), new DateTime(2026, 9, 27, 21, 0, 0, DateTimeKind.Utc));

        Assert.Equal("quick", store.Newest()?.Slot);
    }

    [Fact]
    public void A_damaged_file_is_listed_as_damaged_and_never_continued()
    {
        var store = new SaveStore(_folder);
        store.Write("auto", TestData.NewGame().Save());
        File.SetLastWriteTimeUtc(Path.Combine(_folder, "auto.json"), new DateTime(2026, 9, 27, 20, 0, 0, DateTimeKind.Utc));
        File.WriteAllText(Path.Combine(_folder, "quick.json"), "not json");

        Assert.True(store.Summary("quick").Damaged, "the list shows the slot, but it can't be loaded");
        Assert.Equal("auto", store.Newest()?.Slot);
    }

    [Fact]
    public void With_no_saves_there_is_nothing_to_continue()
    {
        Assert.Null(new SaveStore(_folder).Newest());
    }

    [Fact]
    public void A_slot_name_cannot_leave_the_folder()
    {
        Assert.Throws<ArgumentException>(() => new SaveStore(_folder).Write("../escape", TestData.NewGame().Save()));
    }
}
