## ADDED Requirements

### Requirement: Street signs are one family placed by rule from an ad catalogue
A city level's signs SHALL be built by one sign builder in the level plan, in seven kinds (name,
blade, lightbox, panel, billboard, banner or poster, holo), each showing an ad from
`tools/levels/ads.json`. The plan SHALL place street-level signs at one per 5 m of street frontage
on the market streets and one per 15 m elsewhere, each within 20 %, from a seeded stream of their
own. One placed ad in eight, within one sign in forty, SHALL name a real place, vendor or faction
of the level. No sign SHALL hang below 2.6 m over walkable ground unless it lies flat on its
surface, overlap another sign, a window, an awning, a fire escape, a lamp or a door frame, or
reach past the kerb over a road. The city plan generator (`check_signs`) SHALL refuse a plan that
breaks any of this, naming the sign.

#### Scenario: Lantern Row
- **WHEN** the hub is planned at seed 7
- **THEN** Lantern Row's 477 m of street frontage carries 76 to 115 street-level signs, and one
  roof in two facing a street carries a billboard, within 20 %

#### Scenario: A sign over a door lamp
- **WHEN** a lightbox is forced onto a spot that covers a door's lintel lamp
- **THEN** the plan is refused, naming the sign and the door

#### Scenario: One in eight
- **WHEN** the hub is planned
- **THEN** one placed ad in eight, within one sign in forty, carries a `place` naming a building or
  faction in the hub's layout
