// The characters' shader globals: dry skin's roughness add, and soaked cloth's roughness and
// brightness (openspec/changes/archive/2026-09-29-character-lighting, design section 9). The skin and outfit shaders
// read them; project.godot declares them with neutral values, and this sets them from
// data/character_lighting.json "wetness" when a level starts.
//
// It lives in the Godot layer as a thin adapter (CLAUDE.md 6.2): the numbers are data and the
// rule is the core's (Undercity.Core.World.Wetness); this only hands them to the renderer.

#nullable enable
using Godot;
using Undercity.Core.World;

namespace Undercity.Client;

/// <summary>Sets the character shaders' globals from the wetness table.</summary>
public static class CharacterShading
{
    /// <summary>The skin shader's dry add over the wet roughness mask.</summary>
    public const string SkinDryRoughnessAdd = "character_skin_dry_roughness_add";

    /// <summary>The outfit shader's soaked cloth roughness.</summary>
    public const string ClothWetRoughness = "character_cloth_wet_roughness";

    /// <summary>The outfit shader's soaked cloth brightness.</summary>
    public const string ClothWetBrightness = "character_cloth_wet_brightness";

    /// <summary>Hands the table's numbers to every character material at once.</summary>
    public static void Apply(WetnessDef wetness)
    {
        RenderingServer.GlobalShaderParameterSet(SkinDryRoughnessAdd, (float)wetness.SkinDryRoughnessAdd);
        RenderingServer.GlobalShaderParameterSet(ClothWetRoughness, (float)wetness.ClothWetRoughness);
        RenderingServer.GlobalShaderParameterSet(ClothWetBrightness, (float)wetness.ClothWetBrightness);
    }
}
