# Traverse's own look

Traverse keeps every family role, component and rule in the family's `DESIGN.md`, and every token *name*, so the
shared components work unchanged. It sets itself apart in the places the family's `DESIGN.md` §2 leaves to each app
(its name, mark, scene, motif and copy), and, since the redesign, in the *values* of its palette too: brighter, and
leaning toward yellow and orange.

**The idea:** *a traverse* is the stretch of trail that cuts across a slope instead of straight up it: the steady
way to make progress on a mountain. Trailmix is out on the walk, The Lodge is where your people are, and Traverse is
the route you're working through, cairn by cairn. The cairn is the motif of the mark and the scene; the background is
the map the route is drawn on.

## Palette

`identity/tokens.css` holds it, for Day and Dusk. Day is golden hour (buttery cream, burnt-orange actions); Dusk is
the same light after sunset (warm charcoal-brown, accents lifted, text on them dark). Dusk is not an inverted Day.

| Role (token) | Day | Dusk | Notes |
| --- | --- | --- | --- |
| Primary, the brand (`forest`) | `#B94F08` | `#F5963A` | Burnt orange. The token keeps the family's name; the hue is Traverse's. White on it is 5.0:1 |
| Errors, destructive (`trail`) | `#C8321F` | `#F0674E` | A clear vermilion, so an error never reads as the brand |
| Needs you (`sun`) | `#F6B81E` | `#F7C645` | Sunflower |
| Muster (`--mustard`) | `#DDAA17` | `#E6B52C` | Muster's own. See below |
| In progress, You (`sky`) / Them (`berry`) | `#3F82A6` / `#A8486A` | `#6FB1D4` / `#D88AA6` | Kept cool and rosy so statuses stay distinct from the warm brand |
| Surfaces | `#FDF6E3`, `#FFFCF5` | `#17110B`, `#241B12` | Cream and warm brown, never gray, never green-black |

**Muster is mustard.** Wrapping a view in `accent-mustard` (defined in `tokens.css`) re-points `--forest` and its
siblings at the mustard, so the primary button, checks, focus ring, selection and wells inside it turn mustard with no
component changes, and text on mustard goes dark (`#2A2108`) in both themes. Muster's page and its Settings section
use it; its sidebar icon is mustard everywhere.

## Artwork and atmosphere

| | The Lodge | Traverse |
| --- | --- | --- |
| Mark | A low sun and a cream A-frame, on a forest tile | A cairn of five balanced cream stones and a pale sun on a sunrise tile (`#FFD05A → #F0702A`), over a soft darker hill. No trail, no contour lines: just the stack. Each stone has a shaded underside so the stack reads at 16px |
| Hero art (`Scene`) | The lodge by the lake, keeping the clock | A trail traversing a mountainside toward a saddle in the far ridge, with a cairn at each turn, the nearest one large. Day is golden hour and Dusk is sunset. With `parallax`, the layers drift a few pixels with the pointer (never with reduced motion) |
| `Ambient` | Growth rings in warm cedar | A faint, abstract map (Trailmix has contours, The Lodge has rings): two main roads and two lanes crossing, towns as small clusters of blocks where they meet, a river with a bridge, a lake, spot heights, a camp and a viewpoint, and a dashed trail switchbacking up the slope. All in `--grain`, fading out from a golden sun glow top right. The release page (`docs/index.html`) draws the same map |
| Empty-state badge | Growth rings around the heart of a log | An icon in a brand-colored well, ringed by a short dashed route with three waypoints |
| Menu bar | The A-frame and sun as line art | The sun and the cairn, filled |
| Live action (orange) | Not used | Not used: `btn-record` stays Trailmix's |
| Brand copy | "Come on in" | "Pick up the trail" |

The cairn's shape (`STONES` in `art.tsx`) is shared by the scene's cairns. The map (`MAP` in `art.tsx`) is copied into the release page as plain SVG; change both together.

## Section icons

Lucide: `Mountain` (projects), `Flag` (milestones), `ListChecks` (my tasks), `Kanban` (board), `Users` (team),
`Inbox` (inbox), `Send` (sent to Plane), `Sunrise` (Muster; inside it `Sun` today, `Signpost` the plan, `History` what
moved, `Compass` ahead, `Moon` the wrap-up).

## Files

`tokens.css` (the palette, and `accent-mustard`), `art.tsx` (`Logo`, `Scene`, `Ambient`, `Badge`), `copy.ts`, `public/favicon.svg`,
`mac/Mark.swift` (the menu bar icon), `mac/AppIcon.icns`, made from the favicon by `mac/make-icon.swift`.
