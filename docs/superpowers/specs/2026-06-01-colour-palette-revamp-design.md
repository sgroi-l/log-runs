# Colour Palette Revamp — Design

**Date:** 2026-06-01
**Status:** Approved

## Problem

The dashboard reads as dull. The cause is structural, not the specific hues: the UI
is effectively monochromatic — almost every coloured element resolves to a single
`--accent` (Strava orange `#fc4c02`) sitting on neutral grey-black. Charts, the map
polyline, badges, links, and selected states are all the same colour.

## Goal

Apply a new five-colour palette as a **full multi-colour system**: one primary accent
plus the remaining colours distributed across charts, badges, and the map, on
purple-tinted dark neutrals — coherent, not a rainbow.

### Decisions (from brainstorming)

- **Ambition:** full multi-colour system (not a single-accent swap; no gradients).
- **Primary accent:** molten orange `#f24b04` (closest to the outgoing orange).
- **Neutrals:** tinted toward deep purple to harmonise with royal/lilac.
- **Out of scope:** `--radius` / shape, layout, typography. Colour only.

## Source palette

```
vivid royal   #471ca8
deep lilac    #884ab2
deep saffron  #ff930a
molten orange #f24b04
rosewood      #d1105a
```

## Token layer (`frontend/src/index.css` `:root`)

Two tiers: raw brand colours, then semantic roles mapping onto them.

**Purple-tinted neutrals (replacing grey-black):**

```
--bg:      #120b1f   (was #0f0f0f)
--surface: #1c1430   (was #1a1a1a)
--border:  #2e2348   (was #2a2a2a)
--text:    #ece9f2   (was #e8e8e8 — slightly cooler white)
--muted:   #9990ad   (was #888 — muted lilac-grey)
```

**Brand palette (new raw tokens):**

```
--royal:    #471ca8
--lilac:    #884ab2
--saffron:  #ff930a
--molten:   #f24b04
--rosewood: #d1105a
```

**Semantic roles:**

```
--accent:     var(--molten)
--accent-dim: rgba(242, 75, 4, 0.15)
--badge-bg:   rgba(209, 16, 90, 0.15)   /* rosewood-dim */
--badge-fg:   var(--rosewood)
--error:      #f87171                    /* kept distinct so errors read as "error" */
```

`--radius: 0px` unchanged.

Royal is intentionally *not* painted onto a specific element — it is the hue the
tinted neutrals lean toward (the deep base of the theme), so the five colours don't
all compete at once.

## Colour assignment

| Surface | Colour | Token |
|---|---|---|
| Buttons, links, selected segment/distance, PR reference line | molten | `--accent` |
| Overview — pace-over-time line | molten | `--accent` |
| Overview — weekly distance bars | lilac | `--lilac` |
| Segments — effort-time line | saffron | `--saffron` |
| Map — route polyline | saffron | `--saffron` |
| Map — PR marker | rosewood | `--rosewood` |
| Map — start marker | lilac | `--lilac` |
| Badges | rosewood | `--badge-bg` / `--badge-fg` |
| Chart grid lines | border | `--border` (was hardcoded `#2a2a2a`) |
| Chart axis labels | muted | `--muted` (was hardcoded `#888`) |
| Sync error text | error red | `--error` (was hardcoded `#f87171`) |

## Files touched

- `frontend/src/index.css` — token rewrite + `.badge` uses `--badge-bg`/`--badge-fg`.
- `frontend/src/pages/Overview.jsx` — `GRID_STROKE` const → `var(--border)`; axis
  `#888` → `var(--muted)`; weekly bars `fill` → `var(--lilac)`.
- `frontend/src/pages/SegmentsPage.jsx` — `GRID_STROKE` → `var(--border)`; axis `#888`
  → `var(--muted)`; effort line `stroke` → `var(--saffron)` (PR reference line stays
  `var(--accent)`).
- `frontend/src/components/RouteMap.jsx` — `accentColor` default `#fc4c02` →
  `var(--saffron)`; PR marker `#facc15` → `--rosewood`; start marker `#60a5fa` →
  `--lilac`.
- `frontend/src/components/SyncButton.jsx` — error `#f87171` → `var(--error)`.

## Mechanism note

Chart/map colours already follow the existing `var(--…)` pattern used throughout the
JSX (e.g. `stroke="var(--accent)"`). New assignments reuse that exact pattern — no new
theming mechanism, no JS colour constants beyond the existing `GRID_STROKE`.

## Verification

No automated tests in this project. Verify visually in the running app
(`npm run dev` in `frontend/`, plus the backend/db): Overview charts, Activities list
badges, Segments detail chart, and a route map all render with the new colours and
remain legible on the tinted background.
