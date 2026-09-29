# Tasks

## 1. Core

- [x] 1.1 `LockRules.Best(lock, ctx)` returning way, hold time, cost, XP, noise and the prompt text.
- [ ] 1.2 `Device` states (camera, turret, panel, kennel, generator, sluice) and their hack options.
- [x] 1.3 `Terminal` model: login, pages, actions using dialog effects.
- [x] 1.4 `Container` model: fixed contents, owner, stolen marking.
- [ ] 1.5 `LevelPersistence`: sets by stable id, applied on load.

## 2. Tests

- [x] 2.1 Way order: key, code, pick, hack; missing requirements in the prompt.
- [x] 2.2 Tools consumed only on completion; not at rank 5.
- [x] 2.3 Hold times with Fast Picks, Operator, safes and Safecracker.
- [x] 2.4 Persistence round trip through a save.

## 3. Godot (after the core)

- [ ] 3.1 `Interactor` with progress ring, cancel on release, damage or detection.
- [ ] 3.2 Kit scenes: door, loot container, terminal, security camera, turret, level exit, world item.
- [ ] 3.3 Terminal screen scene (after mockup approval).
- [ ] 3.5 Lockpicking and hacking minigames (after mockups E1 and E2 are approved); held-timer stand-in until then.
- [ ] 3.4 Capture: a lock opened four ways in a test room; a camera looped; a turret turned.
