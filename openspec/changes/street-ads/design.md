# Design: a street full of ads, Hong Kong at night

## Context

The owner, 2026-09-29, asked for more advertisement signs, and answered survey M4 to M7 the same
day: every kind of sign, food, casino, shops and lingerie among the ads, Hong Kong's night streets
as the reference; dense on the market streets; one ad in eight pointing to the hub's own places,
with lots of signs on rooftops and building sides; some animated, some not.

## 1. Today

Measured on the committed plan at seed 7 (a counting instrument over `city_plan.build("hub")`):

| Sign | Count | Built by |
|---|---|---|
| Building name over a door | 15 | `City.put_sign`: extruded text in `neon_pink`, `neon_cyan` or `lamp_glow`, and a light |
| Blade (vertical word) | 12, 24 faces | `City.building_details`: a 0.24 m steel blade 1.3 m out, a letter stack from `BLADE_WORDS`, a neon border, a light; one feature per building, by the style's `blade` share |
| Holo billboard | 1 | `City.foundation_geometry`: a 26 x 11 m panel on the Spire's foundation wall |
| Skyline crowns | per tower | `skyline.py` |

| Sector | Buildings | Street frontage | Roofs facing a street, 6 m up or more |
|---|---|---|---|
| Lantern Row | 27 | 477 m | 24 |
| Tin Stacks | 268 | 454 m | 51 |
| Kiln | 40 | 399 m | 26 |
| Sump Market | 15 | 202 m | 6 |
| Drydock | 7 | 109 m | 6 |
| **All** | 357 | **1,641 m** | 113 |

The hub has 225 lights.

## 2. The reference: Hong Kong's night streets

We take the shape, never the text (CLAUDE.md 12). Sources, each opened 2026-09-29:
- More than 4,000 neon signs were documented in one 2014 crowdsourced survey. They advertised
  pawn shops, night clubs, restaurants, mahjong schools, saunas and even funeral homes, often
  with a picture: an animal or a dish; funeral homes used blue and white
  ([Hyperallergic, on the M+ neonsigns.hk project](https://hyperallergic.com/152810/saving-the-memory-of-hong-kongs-neon-before-it-goes-dark/)).
- "By 1970, entire building facades were covered in neon"
  ([Google Arts & Culture, West Kowloon Cultural District](https://artsandculture.google.com/story/hong-kong%E2%80%99s-neon-signs-%E2%80%93%E2%80%93-then-and-now-west-kowloon-cultural-district-authority-%E8%A5%BF%E4%B9%9D%E6%96%87%E5%8C%96%E5%8D%80/ogWRMXUKqUGzJg?hl=en)).
- Signboards hang from buildings' columns and beams over the pavement: a 3 m wide gaming
  centre's signboard in Yau Ma Tei fell and hurt people below. A validation scheme has governed
  them since 2013. "Colourful neon signs and eye-catching billboards have long been a defining
  characteristic of Hong Kong's cityscape"
  ([Hong Kong Free Press, 2018](https://hongkongfp.com/2018/12/08/sign-sign-off-regulation-poses-threat-hong-kong-s-iconic-signboards/)).
- A picture to work from: Nathan Road's neon in the 1960s, photographed by the sign makers Nam Wah
  Neonlight ([M+ collection](https://www.mplus.org.hk/en/collection/objects/photograph-neon-signs-on-nathan-road-hong-kong-ca13-4-4/)).

What we take:
- **Projection:** signs on arms, reaching out over the pavement at many heights, overlapping in
  the view down the street. This is what makes the "canyon" read.
- **Stacking:** several signs up one facade, staggered.
- **Two scripts:** a short Latin name and a Chinese-script name on the same sign.
- **Pictures:** an icon beside the words (a bowl, a fish, a cow, dice, a mahjong tile).
- **Colour:** saturated pinks, reds, cyans and ambers, with the odd blue-and-white.

## 3. One sign builder, seven kinds

`City.sign(sector, kind, spot, ad)` builds every sign. Today's two builders (`put_sign` and the
blade branch of `building_details`) become its `name` and `blade` kinds, with their geometry kept,
so there is one sign builder (CLAUDE.md 5.1).

| Kind | Where | Size | Height of its bottom | Light |
|---|---|---|---|---|
| `name` (today's) | over a named building's door | text 0.4-1.0 m high | 3.2 m or above the door | one baked light |
| `blade` (today's, extended) | a street front's end, 1.3 m out | 0.24 x 1.3 m, 1.6-6 m tall | the ground floor's height + 0.5 m | one baked light |
| `lightbox` (new) | on a steel arm off a street front, reaching 0.6-2.4 m over the pavement | 1.2-3.0 x 0.6-1.4 m, 0.3 m deep | 4.0 m or more, then every 1.8 m up, staggered | a light if the face is 1.5 m² or more |
| `panel` (new) | flat on a building's side wall or upper front, 0.05 m off it | up to 6 x 8 m | 3.5 m or more | a light if 1.5 m² or more |
| `billboard` (new) | on a roof, on a steel frame 1-3 m tall, facing the nearest street or square | 4-12 x 2-5 m | on the roof | one baked light |
| `banner` and `poster` (new) | a stall's front; clusters of 2-6 posters on blank ground-floor walls | banner 1.5-3 x 0.4 m; poster 0.6 x 0.9 m | banner on its stall; posters 1.2-2.2 m | none |
| `holo` (new) | the market's main corners | 2-4 m wide | 3.5 m or more | one baked light |

Heights clear what is already on a facade: shop fronts end at 3.05 m, wall lamps sit 3.1-3.5 m,
the string course at 3.55 m (`city_plan.py`, `WALL_LAMP_Z`), and awnings project below 3.05 m.

### 3.1 Geometry

- **Letters:** the existing `text` primitive, given a `font` (section 5). Neon letters are
  extruded 0.05 m.
- **Neon tubes:** a new `tube` primitive, a polyline swept by an 8-sided circle of 0.02-0.035 m
  radius. It draws icon outlines and borders as tubes, like real neon.
- **Lightboxes, panels, billboards and holos:** bevelled boxes with an emissive face textured
  from the ad atlas (section 5.3), a steel frame and brackets.
- **Banners and posters:** thin boxes 0.01 m off their surface, textured from the atlas.

Every box is registered with the plan's z-fighting check. Tubes and letters stand at least 0.01 m
off their backing, by construction (CLAUDE.md 7.2).

### 3.2 Triangle budgets

Letters can be heavy; Chinese-script glyphs especially. Per sign: 600 triangles for letters and
tubes, the whole sign 900. Over that, the plan drops the Chinese-script line first, then the icon,
and records it. The total is counted and recorded at the first build.

## 4. Where they go

### 4.1 Density by district (M5)

| District | Kind of street | Street-level signs | Rooftop billboards | Posters |
|---|---|---|---|---|
| Lantern Row, Sump Market | market | one per 5 m of street frontage | one roof in two facing a street | a cluster on one blank ground-floor wall in three |
| Tin Stacks, Kiln, Drydock | the rest | one per 15 m | one roof in six | one wall in ten |
| Spire Foundations | wall | the existing holo billboard only | none | none |

Expected from section 1: 136 street-level signs on the market streets, 64 elsewhere, 15 + 14
rooftop billboards, and 4 holos: **about 230 signs**, against 27 today. "Street-level" is split
between the kinds by a table in `ads.json` (proposed: lightbox 45 %, blade 25 %, panel 20 %,
banner 10 %). Panels go first to the side walls the owner asked for (M6), which `city_plan.py`
already knows as a building's edges facing a side passage or an open lot.

### 4.2 Rules

- Spots come from `city_plan.py`'s own facade edges and roofs; the draws take a stream of their
  own, `f"{seed}:signs:{building}:{edge}"`, so nothing else in the hub moves.
- **Never:** below 2.6 m over walkable ground (except posters and banners, flat on their surface);
  over a door's frame, lintel or lamp; over a window (the existing sign zone keeps window cutters
  out, as it does for name signs); into an awning, a fire escape, a wall lamp, the Skyway's deck,
  a walkway or another sign; a billboard outside its roof's parapet.
- A lightbox's arm reaches no further than 2.4 m, and never past the kerb line onto a road.
- A sign below 2.6 m registers its footprint as a solid for the people-placement check
  (CLAUDE.md 7.4); above that, people walk under it.

### 4.3 Which ad goes where

- Each spot draws an ad from the catalogue, weighted by category and by district: food and shops
  everywhere; casinos, karaoke, lingerie and saunas thicker on Lantern Row; pawn, repair and
  noodles in the Tin Stacks and the Kiln.
- **One in eight** (M6) names a real hub place, vendor or faction: Golden Carp Capsules, Neon Koi
  Karaoke, Pachinko Sunrise, the Rusty Anchor, Kessler's Pawn, Doc Vo's Clinic, the Harbor Fish
  Hall, the Kings' Garage, the Tsang Shrine, and faction ads (a MerSec recruiting poster, a
  Scrap Kings "we buy scrap" board). These carry a `place` extra, so a quest or a dialog line can
  point at them later. The rest are invented brands.
- No brand on neighbouring spots of one facade repeats.

## 5. Content

### 5.1 The catalogue: `tools/levels/ads.json`

```json
{
  "density": {"market": {"street_per_m": 0.2, "roof_share": 0.5, "poster_wall_share": 0.33},
              "rest": {"street_per_m": 0.0667, "roof_share": 0.167, "poster_wall_share": 0.1}},
  "kind_mix": {"lightbox": 0.45, "blade": 0.25, "panel": 0.2, "banner": 0.1},
  "story_share": 0.125,
  "animation": {"share": 0.33, "flicker_hz": [0.2, 1.5], "chase_step_s": 0.18, "scroll_mps": 0.4},
  "icons": {"bowl": [[...polyline in metres...]], "fish": [...], "dice": [...]},
  "brands": [
    {"id": "lucky_ox_noodle", "name": "LUCKY OX", "cjk": "...", "category": "food",
     "colours": ["neon_red", "neon_amber"], "icon": "bowl", "tagline": "NOODLES 24H"},
    {"id": "neon_koi", "name": "NEON KOI", "category": "karaoke", "place": "neon_koi"}
  ]
}
```

- Validated on load by the plan and by a unit test: unknown keys are errors, every `place` names
  a building or faction id in the hub's layout, every icon and colour exists, shares sum to 1.
- Categories: food (noodles, dumplings, fish, barbecue, tea), casino (pachinko, mahjong, cards,
  dice), shops (electronics, repair, pawn, tailor, pharmacy), lingerie, and bar, club, karaoke,
  hotel, sauna, tattoo, clinic. About 60 brands, all invented. Lingerie signs use a silhouette
  (a slip, lips), never a body.
- `BLADE_WORDS` moves in as brands, so today's blade signs read from the catalogue too.
- **Invented names only.** Nothing checks a name against real trademarks automatically; the
  catalogue is reviewed by eye, and a name that is a real brand is renamed.

### 5.2 Fonts

Pinned by SHA-256 in `tools/deps/fonts.json` and fetched by `fetch_character_tools.py`'s fetcher
(one implementation of a pin):

| Role | Font | Licence |
|---|---|---|
| Condensed sans (most signs) | Oswald | OFL 1.1 |
| Neon script (bars, clubs, lingerie) | a script face from Google Fonts, chosen on the look sheet | OFL 1.1 |
| Chinese script | Noto Sans TC | OFL 1.1 |

The fonts are read at build time into meshes and atlas pixels; no font file ships in the game.

### 5.3 The ad atlas

`tools/blender/build_ad_atlas.py` renders every lightbox, panel, billboard, holo, banner and
poster face in the catalogue orthographically in Blender (Cycles, emission only, so it runs
headless), from the same text, icons and colours as the neon, into
`game/textures/ads/ads_atlas.png` (2,048 px, each face padded 8 px) and a layout JSON the plan
reads for UVs. It is seeded, so the same catalogue gives the same pixels. A poster's wear (tears,
fading, rain streaks) is a seeded mask.

## 6. Animation (M7: "some do, some dont")

`game/shaders/sign.gdshader` (emissive; `emission_operator` 1, CLAUDE.md 11) drives the animated
ones. About one lit sign in three (`animation.share`) takes one mode:

| Mode | What | Numbers (in `ads.json`) |
|---|---|---|
| Flicker | a tube stutters and drops out, seeded per sign | 0.2-1.5 stutters a second |
| Chase | letters or tube segments light in sequence, then all | 0.18 s a step |
| Scroll | a holo's or panel's picture scrolls | 0.4 m a second |

The steady signs keep today's `neon_*` materials. The lightmap bakes an animated sign at its mean
emission, so the light it throws doesn't flicker with it; the corona follows the shader's value.

## 7. Lights

Emissive surfaces already light the bake (README, "Lighting"), so not every sign needs a light.
A sign gets one baked light and a corona only if its lit face is 1.5 m² or more, or it is a name,
blade, billboard or holo sign. Expected: about 70 new lights, 225 to about 295 (+31 %). The bake
time is recorded against the last bake at the first sector.

## 8. Checks

| Check | Where | Wanted |
|---|---|---|
| No z-fighting | the plan's `assert_no_zfighting`, every sign box registered | clean |
| People stand clear | `city_plan.py` standing checks; `placement_test.tscn` | clean |
| Signs overlap nothing listed in 4.2 | `city_plan.check_signs` | clean |
| Density per district within 20 % of section 4.1's target | `check_signs` | within |
| Story share 1 in 8, within one sign per 40 | `check_signs` | within |
| Every sign's ad is in the catalogue; catalogue valid | the catalogue test in `tools/levels` | passes |
| A lightbox forced over a door lamp, or one reaching over the road, is refused | `test_city_plan.py` | refused, named |
| Fonts match their pins | `fetch_character_tools.py --verify` | OK |

## 9. Captures

- Before and after stills at seed 7: down Lantern Row from its west end (the canyon view), Market
  Street at the station, the Sump Market square, a Tin Stacks lane, and a rooftop view.
- A 10 s night video down Lantern Row, for the animated signs (CLAUDE.md 9: motion).
- A contact sheet of the seven kinds and a page of the catalogue's faces.
- Lavapipe: proof of the look, not of frame time.

## Risks / Trade-offs

- **Clutter.** 230 signs could turn to noise. The market/rest contrast is the answer; the first
  sector is captured before the rest are built.
- **Legibility.** Small text at 20 m aliases; sign text is sized from a minimum of 0.25 m letter
  height at street level.
- **Triangles and draw calls.** About 230 signs at up to 900 triangles is up to about 200,000,
  more than the hub's static geometry. Signs go into their sector's 40 m chunks, and the budget
  per sign may tighten after the first measurement. Unmeasured on a GPU.
- **Bake time** grows with the lights (+31 %).
- **Trademarks.** Invented names, reviewed by eye.

## Owner decisions (survey M4 to M7, 2026-09-29)

- **M4** "food, casino, shops, ingerie, look at pictures of hong kong streets at night. also do
  recommended" (lingerie): all the kinds; those categories; Hong Kong as the reference (section 2).
- **M5** "recommended": dense on the market streets, sparse elsewhere.
- **M6** "recommended, I would say 1 in 8, lots of random signs on rooftops, and sides of
  buildings": story share 1 in 8; rooftop billboards and side-wall panels.
- **M7** "yup, some do, some dont": about one lit sign in three animates.
