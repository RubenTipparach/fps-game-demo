# Font provenance

These fonts are borrowed, unchanged, from the Google Fonts repository (CLAUDE.md 5.6: borrowed
code keeps its provenance).

- Source: https://github.com/google/fonts
- Branch: `main`
- Fetched: 2026-09-27
- Licence: SIL Open Font License 1.1. Each family's `OFL.txt` sits beside its fonts, as upstream.

| File here | Upstream path | SHA-256 |
|---|---|---|
| `barlow/Barlow-Regular.ttf` | `ofl/barlow/Barlow-Regular.ttf` | `95aa02c7c43096e0dd44d787ba6216864a67157e402adab59b35572e0c1577ea` |
| `barlowcondensed/BarlowCondensed-SemiBold.ttf` | `ofl/barlowcondensed/BarlowCondensed-SemiBold.ttf` | `7b619d14bc2327509a9ef32b0890f709626f7ecc9ff61191c2a4314c5499d2d9` |
| `chakrapetch/ChakraPetch-Bold.ttf` | `ofl/chakrapetch/ChakraPetch-Bold.ttf` | `65fbf76d95651697275e19db4d717c0e95a789ddd3476478b05292104db278a0` |
| `ibmplexmono/IBMPlexMono-Medium.ttf` | `ofl/ibmplexmono/IBMPlexMono-Medium.ttf` | `a9b4c49bb299e05b5f6c481e7fb5e78943d2793249a0c8874ab574a2d1ea6755` |
| `ibmplexmono/IBMPlexMono-SemiBold.ttf` | `ofl/ibmplexmono/IBMPlexMono-SemiBold.ttf` | `d3c38e55c78f5b0f28009fddba4834ec503278936a5986032424c9bd2d23aa46` |

The roles they play (the design page's type, `docs/design/src/head.html`):

| Family | Role | Theme type |
|---|---|---|
| Chakra Petch Bold | Display: names, titles | `DisplayLabel` |
| Barlow Condensed SemiBold | Labels: tabs, captions, caps | `CapsLabel`, `Button` |
| Barlow Regular | Body text | the theme's default font |
| IBM Plex Mono Medium and SemiBold | Numbers, counts, requirements | `MonoLabel` |
