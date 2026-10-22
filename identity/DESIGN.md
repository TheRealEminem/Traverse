# Traverse's own look

Traverse keeps every family role, component and rule in the family's `DESIGN.md`, and The Lodge's palette exactly
(the project app's blueprint, `_reference/Lodge Family Design Guide/03-project-app-blueprint.md` §5), so it reads as
a sibling of The Lodge and could share a window with it later. It sets itself apart only in the places the family's
`DESIGN.md` §2 leaves to each app: its name, mark, scene, motif and copy.

**The idea:** *a traverse* is the stretch of trail that cuts across a slope instead of straight up it: the steady
way to make progress on a mountain. Trailmix is out on the walk, The Lodge is where your people are, and Traverse is
the route you're working through, cairn by cairn.

## Palette

The Lodge's, unchanged: `identity/tokens.css` holds the same values (warm linen and spruce by day, a spruce-blue
night at Dusk). See the Lodge guide for the values and their contrast.

## Artwork and atmosphere

| | The Lodge | Traverse |
| --- | --- | --- |
| Mark | A low sun and a cream A-frame, on a forest tile | A low sun and a cream trail crossing a slope to a small cairn, on the family's **sky** tile (`#4F86A8 → #285B7A`). The stones are filled, not stroked, so they stay legible at 16px |
| Hero art (`Scene`) | The lodge by the lake, keeping the clock | A trail traversing a mountainside toward a saddle in the far ridge, with a cairn at each turn, the nearest one large. Day shows day and Dusk shows sunset, as Trailmix does. With `parallax`, the layers drift a few pixels with the pointer (never with reduced motion) |
| `Ambient` linework | Growth rings in warm cedar | A route drawn on a map: a faint dashed line wandering top right between waypoint dots, and a shorter one low on the left, in `--grain` |
| `Ambient` glows | A sun glow top right and a hearth glow low on the left | The sun glow top right only |
| Empty-state badge | Growth rings around the heart of a log | An icon in a forest well, ringed by a short dashed route with three waypoints |
| Menu bar | The A-frame and sun as line art | The sun, the trail and the cairn: the trail stroked at 1.9pt, the stones filled |
| Live action (orange) | Not used | Not used: `btn-record` stays Trailmix's |
| Brand copy | "Come on in" | "Pick up the trail" |

The scene is a first version (chunk 1 of `PLAN.md`): the composition is settled, and it can gain the clock The
Lodge's scene keeps later.

## Section icons

Lucide: `Mountain` (projects), `Flag` (milestones), `ListChecks` (my tasks), `Kanban` (board), `Users` (team),
`Inbox` (inbox), `Send` (sent to Plane), `Sunrise` (Muster; inside it `Sun` today, `Signpost` the plan, `History` what
moved, `Compass` ahead, `Moon` the wrap-up, `Sparkles` the AI's summary and suggested plan), `CalendarDays`
(Settings → Calendar, and a calendar read by its address; `Laptop` this Mac's Calendar).

## Files

`tokens.css` (the palette), `art.tsx` (`Logo`, `Scene`, `Ambient`, `Badge`), `copy.ts`, `public/favicon.svg`,
`mac/Mark.swift` (the menu bar icon), `mac/AppIcon.icns`, made from the favicon by `mac/make-icon.swift`.
