## ADDED Requirements

### Requirement: Towers surround the hub
A hub level's layout SHALL list the towers around it, and seen from the hub's centre at eye
height, every 30-degree sector of the horizon SHALL hold at least one tower whose top rises at
least 25 degrees above the horizon. Every tower SHALL stand at least 25 m outside the hub's
playable rectangle, no two towers SHALL overlap, and the skyline SHALL stay within 30,000
triangles. The city plan generator SHALL refuse a skyline that breaks this.

#### Scenario: An empty quarter of sky
- **WHEN** the layout's skyline leaves a 30-degree sector with no tower rising 25 degrees
- **THEN** the plan exits naming the sector's bearings, and nothing is built

#### Scenario: A tower inside the hub
- **WHEN** a skyline tower's footprint comes within 25 m of the hub's rectangle
- **THEN** the plan exits naming the tower

### Requirement: The skyline reads as dark towers with lit windows
Skyline towers SHALL render unshaded with procedural lit windows and their own distance haze
toward a colour darker than the sky's horizon, SHALL ignore the scene fog, cast no shadows and
have no collision, and SHALL be drawn out to 1,500 m.

#### Scenario: Looking north from the market
- **WHEN** the runner looks north from the Sump Market
- **THEN** the Halcyon Spire rises above the foundation wall with lit windows and its halo, and
  the sky above the roofline is no longer empty

### Requirement: The map shows the skyline
The design map's legend SHALL carry a locator inset drawn from the same skyline list as the
level, showing the hub inside its towers and naming the named ones.

#### Scenario: Rendering the design map
- **WHEN** `render_map.py` renders the hub
- **THEN** the legend's inset shows every skyline tower's footprint and the named towers'
  labels
