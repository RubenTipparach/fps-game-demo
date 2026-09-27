# UNDERCITY: immersive sim design

Working title **Undercity**. It is a first-person immersive sim set in the flooded, neon-lit
lower levels of the megacity **Meridian**. The player is a freelance operator, a "runner". They
take contracts from a fixer in the Sump Market hub and carry them out in hostile territory:
the gang sewers, the scrapyards and, later, the corporate towers, malls and parks.

It is built on the Brushfire tech: Godot 4.7 C#, levels modelled in Blender, fully baked
lighting and Material Maker PBR materials. The three Brushfire arena maps stay in the project
as reference maps (main menu > Reference maps).

## 1. Pillars

1. **Every problem has three doors.** Each objective can be solved by force, by stealth or by
   social engineering (talk, lie, bribe, disguise), and usually by tech as well (hack, lockpick).
   Every level has at least three routes to its key rooms.
2. **Talk to anyone.** Every NPC in the hub has a dialog tree. Hostiles are talkable too if the
   player is disguised well enough to fool them.
3. **Smart enemies need smart answers.** Enemies differ in *intelligence* (who sees through a
   disguise, who searches properly) and in *senses* (sight, hearing, scent, sensors). Robot dogs
   can't be fooled by clothes. Bosses can't be fooled by cheap clothes.
4. **Deterministic checks.** Skill checks never roll dice: a check passes if the player's skill is
   high enough, and the dialog shows the requirement ("[Deception 3]"). There's no save-scumming;
   the player plans a build instead.
5. **Consequences stick.** Raise the alarm in the pump station and the hostage-taker executes a
   hostage. Kill a boss and his gang stays hostile to you in the hub. The state persists between
   levels.

## 2. Character

### Skills and skill trees

There are seven skills with ranks 0–5. Each rank costs skill points and unlocks that rank's perk,
so each skill is a short tree. A rank needs the previous rank; a few perks also need another
skill (cross-tree requirements, e.g. *Master of Disguise* needs Stealth 2).

| Skill | Governs | Rank perks (1 → 5) |
|---|---|---|
| **Firearms** | spread, recoil, reload | Steady Hands · Quick Reload · Headhunter (+50 % headshot) · Recoil Control · Deadeye |
| **Melee** | baton, takedowns | Clubber · Silent Takedown (from behind) · Fast Takedown · Heavy Hitter · One-Punch |
| **Stealth** | noise, visibility | Soft Steps · Low Profile (crouch speed) · Shadow (−visibility in dark) · Ghost (silent sprint) · Vanish |
| **Hacking** | terminals, cameras, turrets | Script Kiddie (tier-1) · Tier-2 · Loop Cameras · Turn Turrets · Tier-3 / Ghost Login |
| **Lockpicking** | doors, safes | Rake (tier-1) · Tier-2 · Fast Picks · Tier-3 · Safecracker |
| **Deception** | disguises, lies | Passing Glance · Fast Talk · Master of Disguise · Silver Tongue · Doppelgänger |
| **Persuasion** | charm, intimidate, prices | Friendly · Haggler (−15 % prices) · Intimidate · Negotiator · Kingmaker |

Every skill rank also adds **+1 to that skill's checks**; that's what dialog and disguise checks read.

### XP and levels

- **XP sources:** mission objectives (main 400–1000, side 150–300), passing a skill check
  (25–100), a non-lethal takedown (40, more than a kill's 25), exploration secrets (50),
  hacking or picking a lock (20 × tier).
- **Levels:** the next level needs `level × 500` XP. Each level gives 2 skill points, and the player
  starts with 4 points plus Deception 1 (the runner's trade).
- **Core stats:** Health 100 (+10 per level), Energy 100 (for augments, planned), Credits.

## 3. Inventory and equipment

- **Grid inventory** (Deus Ex style), 10 × 6 cells. Items take their footprint: a pistol 2×1,
  a shotgun 4×1, an SMG 3×2, a medkit 1×1, an outfit 2×2. Consumables and ammo stack. Right-click
  uses, equips or drops. Drag to move, or to put an item on the belt.
- **Equipment slots:** HEAD (hats, helmets, goggles), FACE (masks, respirators), BODY (outfits,
  the disguise base), ARMOR (vests, which add armour but can break a disguise if the faction
  doesn't wear them), BOOTS (silent soles).
- **Belt:** ten quick slots on keys 1–0 for weapons, gadgets and consumables. Picking up a weapon
  or gadget auto-assigns it. Pressing the active weapon's key holsters it. Holstering matters:
  a drawn weapon blows a disguise.
- **Credits** are a counter, not an item. Shops buy and sell through dialog (`trade` action).
- **Item categories:** weapon, ammo, consumable, gadget, clothing, armour, key/keycard, quest
  item, valuable (sell loot).

### Starting item set

| Weapons | Ammo | Consumables | Gadgets | Clothing (faction) | Keys / quest |
|---|---|---|---|---|---|
| Stun baton (non-lethal) | 10mm rounds | Medkit | Lockpick | Drain Rats jacket · respirator · goggles | Sewer service key |
| Silenced pistol | Shells | Stim (+25 HP, fast) | Multitool (hack) | Scrap Kings vest · welding goggles | Pump room key |
| Shotgun | Rockets | Noodle cup (+10) | EMP grenade | Sanitation overalls · cap (City Sanitation) | Yard gate keycard |
| SMG | | Synth-whisky (+5, blurs) | Frag grenade | MerSec armor · helmet (MerSec) | Nav core (junkyard target) |
| Rocket launcher (rare) | | | Noise maker | Street clothes (none) | Data shards, credit chips |

## 4. Dialog

- Dialog is **data-driven** (`game/data/dialog/*.json`, built and validated by
  `tools/dialog/build_dialogs.py`). An NPC references a tree by id; the tree is a graph of nodes.
- A **node** has the speaker's line, then either choices or `next`.
- A **choice** has text, optional **conditions** (`if`), an optional **check** and **effects** (`do`).
  - Conditions: flag set or unset, has item, credits ≥ N, skill ≥ N, disguised as faction X,
    quest state.
  - Checks are deterministic: `{"skill": "deception", "dc": 3}` goes to `pass` or `fail`. The
    requirement is always visible, greyed out when the player can't meet it. A failed lie on a
    hostile ends the conversation with them attacking.
  - Effects: set flag, give or take item, give or take credits, give XP, start, advance or complete
    a quest, open trade, turn hostile, leave.
- Every hub NPC has a tree: named characters get real content, and civilians get short
  randomised small talk plus a rumour pool.
- **Hostile NPCs are talkable when the player is disguised as their faction and passes the
  disguise check** (below). Guards then answer questions, pass on passwords and let the player
  through.

## 5. Disguise and perception

Disguise pieces carry a faction tag:

- **Disguise quality Q** is the sum of the matching pieces: BODY 2, HEAD 1, FACE 1 (0–4).
- **Cover = Deception + Q.** This is the number an observer compares with their **intelligence I**
  (1–5).
- **Distance:** an observer who looks at a disguised player from further than their scrutiny
  range (`2 + I × 2` m) accepts them. Inside that range they accept them only if Cover ≥ I;
  otherwise they turn suspicious and then hostile ("You ain't one of ours!").
- **Talking** always uses the scrutiny rule, and bosses add extra `[Deception N]` checks in their
  dialog.
- **Disguises are broken by:**
  - a drawn weapon;
  - armour the faction doesn't wear;
  - sprinting or crouch-creeping near guards;
  - being inside a restricted zone (bosses' offices, cages);
  - being seen attacking, or next to a body;
  - an alarm.
- **Unfoolable observers:** robot dogs (scent), cameras and turrets (sensors, fooled only by
  hacking) and anyone who has already fought the player.
- **Perception:**
  - Sight is a cone scaled by light level, with crouching and stealth ranks reducing visibility.
  - Hearing covers footsteps, gunfire and thrown noise-makers.
  - Suspicion builds on a meter shown as an eye icon over the NPC: unaware → suspicious →
    searching → combat → (lost you) → searching → unaware.

Intelligence tiers in this first slice:

| I | Who | Can be fooled with |
|---|---|---|
| 1 | Drain Rat grunts, junkies | any matching jacket (Deception 1 + BODY 2 = 3) |
| 2 | Scrap King grunts, Rat lieutenants | jacket + one more piece, or Deception 2 |
| 3 | Twitch (hostage guard), Scrap King foremen | near-full outfit |
| 4 | Mother Rat, MerSec officers | full outfit + Deception 2, plus her dialog check |
| 5 | Crusher (Scrap King boss), corp security chiefs (future) | full outfit + Deception 3 + dialog check |

## 6. Factions

| Faction | Where | Default stance | Notes |
|---|---|---|---|
| Sump residents | hub | friendly | all talkable, give rumours |
| **Drain Rats** | sewers (and one scout in the hub) | hostile in territory, neutral in hub | scavenger gang in respirators and patchwork hoods; hold sanitation workers hostage |
| **Scrap Kings** | junkyard | hostile in territory, neutral in hub | chop-shop gang, ex-military mechanics, cyber-arms, robot dogs |
| **MerSec** | hub gate, towers (future) | neutral, bribable | corrupt private police |
| City Sanitation | sewers (maintenance) | friendly | their overalls get you into maintenance areas |

## 7. The hub: Sump Market

The Sump is the bottom of Low Harbor, a market square wedged under the elevated maglev viaduct
and the foundations of the megatowers, whose lit windows fill the sky. It rains, puddles reflect
the neon, and steam rises from vents.

```
                N   (megatower foundations, towers in the skyline)
   +-----------------------------------------------------------+
   |  THE RUSTY ANCHOR bar       |  KESSLER'S PAWN  | DOC VO'S  |
   |  (Mags; Silk's booth in the |  (arms, gear)    | CLINIC    |
   |   back room; Tank at door)  |                  |           |
   |------+--------------   ------+-----    -------+---  ------|
   |      |          SUMP MARKET PLAZA (under viaduct)         |
   | ALLEY|   noodle stall (Nguyen)   viaduct pillars           |
   |(Rivet|   neon signs, puddles     stairs to upper walkway   |
   | Mouse|                                                    |
   | burn |   upper walkway (fire escapes, roof over the bar)  |
   |barrel|                                                    |
   |  |   +----------------+     +----------+     +--------------|
   | [storm drain] -> SEWER      | Petra's   |  [MerSec checkpoint]
   |  stairs down               | stall     |   Officer Dace
   +----------------------------+-----------+------ gate -> JUNKYARD
                                   S
```

- **Places:**
  - Plaza with the noodle stall.
  - Bar interior (bar counter, booths, Silk's back room).
  - Pawn shop and clinic interiors.
  - West alley with a burn barrel.
  - Upper walkway and fire escapes (vertical route, secret stash).
  - Storm drain stairs to the sewer.
  - MerSec gate to Scrapyard Road (the junkyard).
- **NPCs (all talkable):**
  - **Silk**, the fixer: gives both missions.
  - **Mags**, the bartender: rumours, sells drinks.
  - **Tank**, the bouncer: intimidation check.
  - **Kessler**, the pawnbroker: arms and gear shop, buys loot.
  - **Doc Vo**: heals, sells medkits and stims.
  - **Nguyen**, the noodle vendor: noodles, gossip, the sewer grate code.
  - **Rivet**, a scavenger: sells a Drain Rats jacket.
  - **Mouse**, a street kid: hints about vents, trades info for credits.
  - **Petra**, a sanitation worker: her brother is a hostage; she gives overalls and the service key.
  - **Officer Dace**: bribe, persuade or sneak past him to the junkyard.
  - **Skiv**, a Drain Rats scout: talkable.
  - **Jax**, a Scrap Kings recruiter: can be conned into giving a gang pass.
  - Ambient civilians with small talk.

## 8. Level: The Drains (sewer)

Drain Rats territory under the Sump. Brick collector tunnels, water channels, pump machinery,
and a shanty camp in an overflow cistern.

```
 HUB storm drain
      |
 [MAINTENANCE] lockers (sanitation overalls, service key door), terminal, crawl vent ----------+
      |                                                                                        |
 [COLLECTOR TUNNEL] walkways both sides, water channel (wade = noisy), bridge             (vent crawl)
      |                         \                                                              |
 [JUNCTION] checkpoint:          (flooded bypass: underwater grate, lockpick 1)                |
  2 Rats, talk/disguise/fight     \                                                            |
      |                            \                                                           |
 [RAT CAMP] overflow cistern: tents, fires, barrels, 5 Rats, Skiv's cousin (dialog)             |
      |  catwalk ring above camp (from junction ladder)                                        |
 [PUMP STATION] hostages in the cage, guard Twitch (I3) <----------------------------------------+
      |  upstairs: MOTHER RAT's nest (control room, I4), ransom safe, pump room key
```

**Mission: "Rat Trap" (hostage rescue).** The Drain Rats hold two sanitation workers in the pump
station and are extorting the city. Free them.

- **Violent:** fight through. If Twitch hears combat, he executes a hostage.
- **Stealth:** take the vent crawl to the pump station, knock Twitch out from behind, and open
  the cage with the pump room key (from Mother Rat's desk) or pick it (Lockpicking 2).
- **Social:** in a Rat disguise, talk past the checkpoint. Then either convince Twitch that
  "Mother says let them go" ([Deception 2], jacket + respirator), or convince Mother Rat that
  the city paid ([Deception 3] or [Persuasion 3]), or pay 500 credits.
- **Bonus:** Mother Rat's safe (Lockpicking 3 or code from her terminal, Hacking 2).
- **Result:** Petra's thanks, XP, credits. If a hostage dies, Petra is hostile and Silk pays less.

## 9. Level: Scrap King's Yard (junkyard)

A walled scrapyard at night: stacks of crushed cars, container rows, a crane, a car crusher,
searchlights, robot dogs, and the Scrap Kings' warehouse and office.

```
        (container stacks, climbable)          searchlight tower (hackable, needs power)
   +----------------------------------------------------------------------+
   | CRANE + crusher    CONTAINER MAZE    |  WAREHOUSE (chop shop)          |
   |   dog patrol ~~~                     |  cars on lifts, 4 Kings         |
   |                                      |  stairs -> OFFICE: CRUSHER (I5),|
   |  car stacks        generator shed    |  SAFE with the nav core         |
   | (fence gap, W) --> (power: off kills |  roof skylight <- catwalk from   |
   |                     lights + gate)   |  the container stack           |
   |------------------------------- yard gate (2 guards, keycard) ---------|
   +----------------------------------------------------------------------+
                           Scrapyard Road  <- HUB
```

**Mission: "Chop Job" (robbery).** Steal the prototype nav core from the Scrap Kings' office
safe. Bonus: Jax (hub) wants Crusher dead (assassination), and Petra's brother wants the Kings'
ledger.

- **Front gate:** show the gang pass (conned from Jax), bluff the guards in a Scrap Kings vest
  (I2), or bribe them.
- **Fence gap:** the west gap is a crouch route past the dog patrol. Dogs smell you through any
  disguise, so use the EMP, a noise maker or timing.
- **Power:** kill the generator to blind the searchlights and unlock the gate. It also alerts a
  foreman.
- **Up high:** climb the container stack to the catwalk and drop through the warehouse skylight
  into the office.
- **The safe:** Lockpicking 3, the combination from Crusher's terminal (Hacking 3), or talk
  Crusher into opening it for a "buyer" ([Deception 4] with full Kings outfit).

## 10. Technical design (what exists in code)

| System | Code |
|---|---|
| Persistent run state (character, inventory, flags, quests, faction stances) | `scripts/RPG/GameState.cs` |
| Skills, XP, levels, perks | `scripts/RPG/Character.cs` |
| Item database | `data/items.json`, `scripts/RPG/Items.cs` |
| Inventory grid, equipment, belt | `scripts/RPG/Inventory.cs` |
| Use key, pickups, containers, doors, exits | `scripts/RPG/Interactable.cs` and friends |
| Dialog runtime and UI | `scripts/RPG/Dialog*.cs`, trees in `data/dialog/` |
| Quests and journal | `scripts/RPG/Quests.cs`, `data/quests.json` |
| NPCs: humanoids, factions, disguise perception | `scripts/NPC/*.cs` |
| Humanoid models (segmented rigs, faction outfits) | `tools/blender/build_characters.py` |
| Levels | `tools/blender/build_hub.py`, `build_sewer.py`, `build_junkyard.py` |
