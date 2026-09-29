## ADDED Requirements

### Requirement: The gun sways gently while walking
While the runner walks or sprints, the view weapon SHALL sway on smooth sines at a person's
pace: footsteps SHALL come no more often than `max_cadence_walk_hz` (2.0 a second) walking and
`max_cadence_sprint_hz` (2.6) sprinting, whatever the ground speed; the gun SHALL rise and fall
once a footstep and swing side to side once a stride; and neither the gun nor the view SHALL
turn sharply at a footstep. The view's own bob SHALL be at most 1 cm peak to peak. The view,
the gun and the footstep sounds SHALL follow one gait, whose numbers come from
`game/data/view_motion.json`.

#### Scenario: Walking down Lantern Row
- **WHEN** the runner walks at 7.5 m/s with the Kestrel drawn
- **THEN** the view test counts at most 2.0 footsteps a second, the gun's height moves at no
  more than 2.1 Hz, and the view's peak vertical acceleration stays under 1 m/s²

#### Scenario: Sprinting
- **WHEN** the runner sprints at 10.5 m/s
- **THEN** at most 2.6 footsteps a second, and the view's peak vertical acceleration stays under
  1.5 m/s²

#### Scenario: No corner at a footstep
- **WHEN** the view test compares the view's vertical speed between consecutive frames at 60 fps
- **THEN** it never changes by more than 0.05 m/s
