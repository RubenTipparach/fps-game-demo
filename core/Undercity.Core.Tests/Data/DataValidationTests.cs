// The shipped data files load, validate and agree with each other.
//
// It lives here because a misspelt key or a dangling id in game/data must fail `dotnet test`, not
// a playtest (CLAUDE.md 5.5, 5.6).

using Undercity.Core.Data;

namespace Undercity.Core.Tests.Data;

public class DataValidationTests
{
    [Fact]
    public void The_shipped_data_loads_and_cross_checks()
    {
        var data = TestData.Data;
        Assert.NotEmpty(data.Items.Items);
        Assert.True(data.Levels.ContainsKey("hub"), "the hub is built, so its level file must load");
    }

    [Fact]
    public void Every_hub_npc_has_a_dialog_tree()
    {
        foreach (var npc in TestData.Data.Npcs.Npcs)
        {
            Assert.True(TestData.Data.Dialogs.ContainsKey(npc.Dialog), $"{npc.Id} names dialog '{npc.Dialog}'");
        }
    }

    [Fact]
    public void Every_npc_placed_in_the_hub_is_a_known_npc()
    {
        foreach (var (sid, npc) in TestData.Data.Levels["hub"].Npcs)
        {
            Assert.True(npc == "civ" || TestData.Data.Npcs.Find(npc) is not null, $"{sid} places unknown npc '{npc}'");
        }
    }

    [Fact]
    public void Every_dialog_open_names_a_door_container_or_exit_in_the_hub()
    {
        var hub = TestData.Data.Levels["hub"];
        var opens = TestData.Data.Dialogs.Values
            .SelectMany(t => t.Nodes.Values.SelectMany(n => n.Do.Concat(n.Choices.SelectMany(c => c.Do))))
            .Select(e => e.Open).OfType<string>().Distinct();
        foreach (var id in opens)
        {
            Assert.True(hub.Doors.ContainsKey(id) || hub.Containers.ContainsKey(id) || hub.Exits.ContainsKey(id),
                $"a dialog opens '{id}', which the hub doesn't place");
        }
    }

    [Fact]
    public void A_misspelt_key_is_an_error_naming_the_file_and_the_key()
    {
        var real = TestData.Source.Read("factions.json");
        var misspelt = real.Replace("\"liked_at_least\"", "\"prise_mult\": 1, \"liked_at_least\"", StringComparison.Ordinal);
        Assert.NotEqual(real, misspelt);
        var ex = Assert.Throws<DataException>(() => JsonData.Parse<Undercity.Core.Factions.FactionTable>(misspelt, "factions.json"));
        Assert.Contains("factions.json", ex.Message, StringComparison.Ordinal);
        Assert.True(ex.Message.Contains("prise_mult", StringComparison.Ordinal), "the message must name the knob that does nothing");
    }
}
