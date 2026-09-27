// Item icons: ItemDef.Icon names a drawing on the design page, exported to
// res://ui/undercity/icons/<icon>.svg by tools/design/export_icons.py.
//
// It lives in the UI layer because it maps a core id to an engine texture, once, for every screen
// that draws an item: the HUD belt, the pack grid and the detail panel (CLAUDE.md 5.1).

#nullable enable
using System;
using System.Collections.Generic;
using Godot;
using Undercity.Core.Items;

namespace Undercity.Client;

/// <summary>Loads and caches item icon textures.</summary>
public static class ItemIcons
{
    private const string Folder = "res://ui/undercity/icons/";
    private static readonly Dictionary<string, Texture2D?> Cache = new(StringComparer.Ordinal);

    /// <summary>The icon for an item, or null when its drawing is missing (export_icons.py fails the export if one is).</summary>
    public static Texture2D? For(ItemDef def)
    {
        if (!Cache.TryGetValue(def.Icon, out var tex))
        {
            var path = Folder + def.Icon + ".svg";
            tex = ResourceLoader.Exists(path) ? GD.Load<Texture2D>(path) : null;
            if (tex is null)
            {
                GD.PushWarning($"[Undercity] no icon '{path}' for item '{def.Id}'");
            }
            Cache[def.Icon] = tex;
        }
        return tex;
    }
}
