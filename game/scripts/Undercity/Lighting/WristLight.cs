// The runner's wrist-deck glow: an omni light low and to the left of the view, lighting characters
// and nothing else (openspec/changes/character-lighting, design section 3). At 2 m it is a cool
// fill of about a third of the conversation key. It is always on (owner I9), and perception
// doesn't count it: it lights no world surface.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): the player scene holds the light;
// its colour, energy, reach and place come from data/character_lighting.json.

#nullable enable
using Godot;

namespace Undercity.Client;

/// <summary>The wrist-deck glow on the runner's camera.</summary>
public partial class WristLight : OmniLight3D, IWired
{
    /// <inheritdoc/>
    public void Wire(Services services)
    {
        var t = services.Data.CharacterLighting;
        var w = t.Wrist;
        var (r, g, b) = t.Rgb(w.Color);
        LightColor = new Color((float)r, (float)g, (float)b);
        LightEnergy = (float)w.Energy;
        OmniRange = (float)w.RangeM;
        OmniAttenuation = (float)w.Attenuation;
        Position = new Vector3((float)w.OffsetM[0], (float)w.OffsetM[1], (float)w.OffsetM[2]);
        LightCullMask = 1u << (t.CharactersLayer - 1);
        ShadowEnabled = false;
        LightBakeMode = BakeMode.Disabled;
        Visible = true;
    }
}
