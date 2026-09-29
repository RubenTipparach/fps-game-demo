# Proposal: a street full of ads, Hong Kong at night

## Why

The owner, 2026-09-29: "I also want to generate more advertisement signs on the streets."
Answered in the survey the same day:
- M4 (which kinds): "food, casino, shops, lingerie, look at pictures of hong kong streets at night.
  also do recommended": every kind of sign at street level, advertising food, casinos, shops and
  lingerie among the rest, with Hong Kong's night streets as the reference;
- M5 (how dense): "recommended": dense on the market streets, sparse elsewhere;
- M6 (what they say): "recommended, I would say 1 in 8, lots of random signs on rooftops, and sides
  of buildings": one ad in eight points to a real hub place, vendor or faction; many signs on
  rooftops and on the sides of buildings;
- M7 (do they animate): "yup, some do, some dont".

**Measured** on the committed plan at seed 7:

| | Today |
|---|---|
| Building-name signs (`City.put_sign`, neon text over a door) | 15 |
| Blade signs (`City.building_details`, a vertical word from 20 `BLADE_WORDS`) | 12 (24 faces) |
| Other ads | 1 holo billboard on the Spire's foundation wall; the skyline towers' crowns |
| Street-facing frontage (walls 4 m or longer facing a street) | 1,641 m on 357 buildings |
| ... on the market streets (Lantern Row, Sump Market) | 679 m |
| Lights in the hub | 225 |

So a 240 x 170 m neon slum has 27 street signs: one per 61 m of frontage. Hong Kong's streets were
the model for this look, and more than 4,000 neon signs were counted there in a single
crowdsourced survey in 2014 ([Hyperallergic](https://hyperallergic.com/152810/saving-the-memory-of-hong-kongs-neon-before-it-goes-dark/)).

## What Changes

- **One sign builder, seven kinds.** Today's name signs and blade signs become two kinds of one
  `City.sign()` (CLAUDE.md 5.1), joined by projecting lightboxes on steel arms over the pavement,
  wall panels on the sides of buildings, rooftop billboards on frames, stall banners and posters,
  and holo screens.
- **An ad catalogue.** `tools/levels/ads.json` holds invented brands: name, a short Chinese-script
  name, category, colour roles, an icon and a tagline. Categories include the owner's food,
  casino, shops and lingerie, and Hong Kong's pawn, mahjong, sauna, karaoke and noodle shops. One
  in eight placed ads names a real hub place, vendor or faction (M6).
- **Placed by rule, by district.** Market streets: one street-level sign per 5 m of frontage and a
  rooftop billboard on one roof in two facing a street. Elsewhere: one per 15 m, one roof in six.
  About 230 signs in all, placed from a seeded stream of their own so nothing else in the hub
  moves.
- **Some animate** (M7): about one lit sign in three flickers, chases or scrolls, through a sign
  shader; the rest are steady neon. The lightmap bakes each at its mean brightness.
- **Real type:** three pinned fonts under the Open Font License (a condensed sans, a neon script,
  and a Chinese-script face), used at build time only; the meshes and textures ship, not the fonts.
- **Checks:** every sign registered with the z-fighting check; nothing below 2.6 m over walkable
  ground except flat posters and banners; signs never overlap each other, a window, an awning, a
  fire escape, a lamp or a door frame; density and the one-in-eight share within tolerance; every
  brand from the catalogue.

## Capabilities

### New Capabilities

- `street-signs`: signs in city levels are one family, placed by rule from an ad catalogue.

## Impact

- `tools/levels/city_plan.py`: `City.sign()` in place of `put_sign` and the blade code; sign spots
  per kind; `check_signs`; `BLADE_WORDS` moves into the catalogue.
- `tools/levels/ads.json` (new) with its schema and test in `tools/levels`.
- `tools/deps/fonts.json` (new): the three OFL fonts, pinned by SHA-256 like the character packs,
  fetched by the same fetcher.
- `tools/blender/build_undercity.py`: text in a named font, a `tube` primitive (a polyline swept
  into a neon tube), and the ad atlas.
- `tools/blender/build_ad_atlas.py` (new): renders the billboard, holo and poster faces from the
  catalogue into `game/textures/ads/`.
- `game/shaders/sign.gdshader` (new): flicker, chase and scroll; its numbers in `materials.json`.
- `tools/godot/import_presets.py`: the sign materials.
- The design map draws the signs; the hub's sectors are rebuilt and baked.
