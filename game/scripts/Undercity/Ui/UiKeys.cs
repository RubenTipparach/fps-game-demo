// The number keys as the numbered rows of a menu: 1 to 9, then 0 for the tenth. The belt, the
// deck's belt assignment and the dialog choices all read them the same way.
//
// It lives in the UI layer because it only turns a key event into a row index; what the row does
// belongs to the screen that owns it.

#nullable enable
using Godot;

namespace Undercity.Client;

/// <summary>Key helpers shared by the Undercity screens.</summary>
public static class UiKeys
{
    /// <summary>
    /// The row a number key picks: key 1 is row 0, key 9 is row 8 and key 0 is row 9. Null for any
    /// other event, a release or an echo.
    /// </summary>
    public static int? Row(InputEvent e)
    {
        if (e is not InputEventKey { Pressed: true, Echo: false } k)
        {
            return null;
        }
        return k.PhysicalKeycode switch
        {
            Key.Key0 => 9,
            >= Key.Key1 and <= Key.Key9 => (int)(k.PhysicalKeycode - Key.Key1),
            _ => null,
        };
    }

    /// <summary>The label of row <paramref name="row"/>: "1" to "9", then "0".</summary>
    public static string RowLabel(int row) => ((row + 1) % 10).ToString(System.Globalization.CultureInfo.InvariantCulture);
}
