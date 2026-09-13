# Parallax — Light Mode Design System (Stitch Build Spec)

**Status:** Supersedes the dark "control room" direction in the original `DESIGN.md` for all new UI work.
**Reference implementation:** `http://localhost:3000/dashboard` (existing skeleton — evolve, don't rebuild)
**Purpose:** This is the source-of-truth spec to feed into Stitch, page by page, while iterating on the existing frontend skeleton described in `PARALLAX_FRONTEND_HACKATHON_BLUEPRINT.md`, `PRD.md`, `AGENT_FLOW.md`, and `TECH_STACK.md`.

The information architecture, component taxonomy, and agent-lifecycle visualization requirements from the original `DESIGN.md` **stay the same**. What changes is the surface: light, calm, cool-toned, rounded, and deliberately unflashy.

---

# 1. Design mandate

## 1.1 What we're moving away from

The current build (see screenshot at `/dashboard`) reads as **AI-slop**: a dark hero with a stock mountain photo, a violet-to-pink gradient search bar, saturated emoji, glowing card borders, and rounded pill badges in five different candy colors. It looks like a generic "AI startup" template, not a serious engineering control plane.

Retire:

- dark navy backgrounds as the default surface
- photographic hero imagery (mountains, skylines, abstract cosmic art)
- purple→pink or blue→pink gradients on buttons, cards, or text
- saturated/neon accent colors (hot pink, bright orange, lime)
- emoji in UI copy (👋, ✨, 🚀)
- glassmorphism / heavy blur / glow rings
- sparkle icons as a stand-in for "AI"
- drop shadows with color tint (violet shadows, glow-on-hover)
- more than one accent color competing for attention per screen

## 1.2 What we're building instead

**Light. Calm. Serene. Cool-toned. Rounded. Quietly confident.**

Think: a well-funded fintech ops console or a modern observability tool (Linear, Vercel dashboard, Ramp, Ashby, Ondo-style clarity) — not a hackathon AI demo. The product manages risk and approvals for engineering teams; the UI should feel like it can be trusted with production decisions.

Five words to design against on every screen:

```text
Quiet     — nothing pulses, glows, or shouts unless something needs a human
Precise   — alignment, spacing, and type are exact, not decorative
Cool      — blues/slates/greens, never warm or saturated
Rounded   — soft geometry throughout, no sharp rectangles
Legible   — data density without visual noise
```

---

# 2. Color system

Light mode only. Cool, low-saturation, desaturated-first palette. One accent hue used sparingly.

## 2.1 Surfaces

| Token | Value | Use |
|---|---|---|
| `surface-canvas` | `#F6F8FA` | app background |
| `surface-raised` | `#FFFFFF` | cards, panels, composer |
| `surface-sunken` | `#EEF1F5` | table stripes, input wells, code/mono blocks |
| `surface-overlay` | `#FFFFFF` (with `shadow-overlay`) | modals, drawers, popovers |
| `sidebar-bg` | `#FBFCFD` | left navigation (very light, one step off canvas) |
| `border-subtle` | `#E4E8ED` | default hairline border |
| `border-strong` | `#D2D8E0` | dividers that need more separation |

No pure black, no pure white text on saturated color. No card ever floats on a gradient.

## 2.2 Text

| Token | Value | Use |
|---|---|---|
| `text-primary` | `#111827` | headings, primary content |
| `text-secondary` | `#5B6472` | supporting text, descriptions |
| `text-tertiary` | `#8A93A1` | metadata, timestamps, placeholder |
| `text-on-accent` | `#FFFFFF` | text on filled accent buttons |

## 2.3 Accent (single primary hue)

Use one restrained cool accent — **indigo-slate**, not violet-magenta:

| Token | Value | Use |
|---|---|---|
| `accent-600` | `#3652C9` | primary buttons, active nav item, links |
| `accent-500` | `#4A63D6` | hover state |
| `accent-100` | `#E7ECFB` | selected row / active tab background |
| `accent-050` | `#F2F5FD` | subtle highlight fill |

This is the **only** saturated color allowed to dominate a component. Everything else is semantic (below) or neutral.

## 2.4 Semantic status colors

Desaturated, never neon. Used only for meaning, never decoration.

| State | Text/Icon | Background fill |
|---|---|---|
| Positive / Completed / Connected | `#1A7F5A` | `#E7F5EE` |
| Warning / At risk / Awaiting | `#9A6B12` | `#FBF1DD` |
| Danger / Blocked / High risk | `#B4463A` | `#FBE9E7` |
| Info / Running / In progress | `#2F6FBF` | `#E9F1FB` |
| Neutral / Skipped / Draft | `#6B7280` | `#EEF0F3` |

Rule: **color is always paired with an icon or label.** Never rely on a colored dot alone to convey status (accessibility requirement carried over from the original spec).

## 2.5 What NOT to do with color

- No gradients on buttons, cards, avatars, or text.
- No colored shadows/glows (`box-shadow: 0 0 40px rgba(purple...)` is banned).
- No more than 2 semantic colors visible in a single card.
- Risk levels use text + icon + the muted palette above — not traffic-light red/yellow/green at full saturation.

---

# 3. Shape, radius & elevation

## 3.1 Radius scale

Rounded, consistently, everywhere. No sharp 0px corners anywhere in the product except 1px hairlines.

| Token | Value | Use |
|---|---|---|
| `radius-sm` | 8px | chips, small buttons, input fields |
| `radius-md` | 12px | cards, list rows, dropdowns |
| `radius-lg` | 16px | panels, the mission composer, modals |
| `radius-xl` | 24px | hero/greeting surface, full-bleed containers |
| `radius-full` | 999px | avatars, status pills, icon buttons |

Never mix a sharp corner with a rounded one on the same shape. Nested cards should have a radius 2–4px smaller than their parent so corners feel concentric, not clipped.

## 3.2 Elevation

Elevation is used for *hierarchy*, not decoration — flat, cool-toned, very soft.

| Token | Spec | Use |
|---|---|---|
| `shadow-none` | none, border only | default cards on canvas |
| `shadow-sm` | `0 1px 2px rgba(16, 24, 40, 0.04)` | hover state on rows/cards |
| `shadow-md` | `0 4px 12px rgba(16, 24, 40, 0.06)` | dropdowns, popovers |
| `shadow-overlay` | `0 12px 32px rgba(16, 24, 40, 0.10)` | modals, drawers |

No shadow should ever use anything but neutral slate at low opacity. If a card needs to stand out, use a slightly stronger border (`border-strong`) or `surface-raised` on `surface-canvas`, not a heavier shadow.

## 3.3 Borders over shadows

Prefer a 1px `border-subtle` to define a card's edge before reaching for shadow. This is what keeps the UI feeling calm and flat rather than "floaty."

---

# 4. Typography

| Token | Family | Use |
|---|---|---|
| `font-ui` | Inter (or system default: -apple-system, Segoe UI) | all UI text |
| `font-mono` | JetBrains Mono | PR numbers, ticket IDs, commit SHAs, timestamps in tables, event IDs |

## 4.1 Scale

| Role | Size / Weight | Color |
|---|---|---|
| Page title | 22px / 600 | `text-primary` |
| Section title | 15px / 600 | `text-primary` |
| Card title | 14px / 600 | `text-primary` |
| Body | 13.5px / 400 | `text-secondary` |
| Metadata / caption | 12px / 500 | `text-tertiary` |
| Mono data | 12.5px / 500, `font-mono` | `text-secondary` |

Deliberately smaller than the original spec's 32–44px page titles. This is an operator's tool used all day — it should read like dense, calm software, not a marketing landing page. No heading on any dashboard screen should exceed 24px.

---

# 5. Iconography & imagery

- Use a single consistent icon set (Lucide or Phosphor, regular/outline weight, 1.5px stroke). Never mix icon families.
- Icons are always neutral-slate by default; they take on a semantic color only when representing that state (success, warning, danger, info).
- **No photographic imagery anywhere in the product** — no hero photos, no mountains, no stock people. If a hero/greeting area needs visual interest, use a subtle geometric line pattern or soft gradient mesh in near-white/cool-gray tones only (max 4% color saturation), or nothing at all.
- No decorative 3D renders, no isometric illustrations, no sparkle/magic-wand icons to represent "AI." Represent agent activity with a simple pulsing dot or progress indicator instead — motion communicates "working," not iconography.
- Avatars: initials on a flat neutral-tinted circle (`accent-100` background, `accent-600` text), not gradient orbs.

---

# 6. Motion

Motion should feel like calm confirmation, never like a marketing flourish. The product is making decisions about production systems — nothing should feel gamified.

## 6.1 Timing

| Interaction | Duration | Easing |
|---|---|---|
| Hover state (row/card/button) | 100–150ms | ease-out |
| Panel/drawer open | 180–220ms | ease-in-out |
| Tab switch / content swap | 150ms | ease-out |
| Status change (badge, progress bar fill) | 250–300ms | ease-in-out |
| Toast in/out | 200ms | ease-out |

## 6.2 Rules

- No looping animation, ever (no pulsing glows, no shimmer-forever skeletons after data loads, no breathing borders).
- Skeleton loaders may shimmer *only* while genuinely loading, then must stop immediately when content arrives.
- Live agent progress (OBSERVE → CONTEXTUALIZE → REASON → ...) animates step-by-step as each stage completes — a checkmark fade-in and a thin connecting line filling left-to-right. No bouncing, no confetti, no celebratory animation on mission completion beyond a single checkmark fade.
- Respect `prefers-reduced-motion`: disable all non-essential transitions, keep only instant state changes.
- Approvals and destructive actions get **zero** playful motion — state changes there should feel deliberate and slightly slower (200–250ms) rather than snappy, to reinforce "this matters."

---

# 7. Layout (unchanged structure, new surface)

Structure from the original spec and current skeleton stays:

```text
┌──────────────┬───────────────────────────────────────────────────────────┐
│              │ Top command/search bar                         utilities │
│   Sidebar    ├───────────────────────────────────────────────────────────┤
│  (light,     │ Hero / contextual greeting / status strip (no photo)     │
│  224–248px)  │ KPI strip                                                 │
│              │ Mission command surface                                   │
│              │ Recent missions / tasks      Activity / integrations     │
│              │ Projects / insights / quick actions                       │
└──────────────┴───────────────────────────────────────────────────────────┘
```

- Sidebar: `sidebar-bg`, 1px `border-subtle` on the right edge only. Active nav item = `accent-100` fill, `radius-md`, `accent-600` text/icon — not a glowing pill, not a colored bar indicator.
- Top command bar: `surface-raised` on `surface-canvas`, 64px, bottom hairline border. Search input is `surface-sunken` with `radius-md`, not a gradient-bordered pill.
- Content max-width on desktop: constrain to ~1440px centered, generous side padding (32–40px), so it doesn't feel like it's stretching to fill ultrawide monitors.

---

# 8. Component direction (mapped to existing taxonomy)

Same components as the original taxonomy (`AppShell`, `Sidebar`, `TopCommandBar`, `MissionComposer`, `KpiCard`, `MissionList`, `MissionRow`, `ProjectCard`, `InsightCard`, `QuickActions`, `IntegrationCard`, `ActivityTimeline`, `ReviewDebtChart`, `ReviewQueue`, `ContextPack`, `RiskBadge`, `ReviewerMatch`, `ApprovalPanel`, `ExecutionTimeline`, `EvidenceDrawer`). Restyle per below.

## Hero / greeting

Replace the photo-hero entirely. Use a plain `surface-raised` band or nothing at all — just the page title ("Good morning, Sarah") in `text-primary` at 22px, a one-line status subtitle in `text-secondary`, no gradient overlay, no emoji wave. If ambient visual interest is wanted, a faint 4%-opacity dot-grid or line pattern in cool gray only.

## KPI strip

Flat `surface-raised` cards, `radius-md`, `border-subtle`. Icon in a small `radius-sm` neutral or semantic-tinted square (not a circle-in-gradient). Number in `font-ui` 600 weight, 20px. Trend arrows use semantic color only, small, no bold colored badges.

## Mission composer

This remains the single most important surface — keep it prominent, but calm:

- `surface-raised`, `radius-lg`, `border-subtle` at rest.
- On focus: border becomes `accent-600` at 1.5px — no glow, no gradient ring, no drop shadow bloom.
- Placeholder copy stays plain and specific (already good: *"Tell Parallax what you need to do…"*) — drop the sparkle icon; use a simple command/terminal-style icon or none.
- Suggested-shortcut chips: `surface-sunken`, `radius-full`, `text-secondary`, hover → `accent-050` fill.
- Execution mode selector (Review first / Guided / Auto): segmented control, not a dropdown pretending to be casual — should visually communicate "this changes how much autonomy the agent has."

## Recent Missions / Review Queue

Dense table-like rows, `radius-md` container, row hover = `surface-sunken`, no card-per-row shadow. Status uses the semantic tokens from §2.4 as a small label with icon, not a saturated pill.

## Context Pack, Risk Badge, Reviewer Match, Approval Panel

These are the highest-trust surfaces in the product — keep the structure specified in `AGENT_FLOW.md` §10 and `PARALLAX_AGENT_CORE_INTEGRATION.md` (Why / What changed / Risk / Evidence / Reviewer / Actions), but:

- Risk badge: text label ("High risk") + icon in the semantic tint, never a bare colored dot or a loud red pill.
- Approval panel: render the proposed action list as a plain checklist with system icons (GitHub/Jira/Slack/Calendar marks, all monochrome/neutral unless brand-required), not as glowing "AI decision" cards. Approve = filled `accent-600` button, `radius-sm`; Reject = outline neutral button; Edit = text/ghost button. No color implies risk on the buttons themselves.
- Evidence should look like data (mono font, muted background), not like a chat bubble.

## Execution Timeline / Agent stages

Horizontal or vertical stepper: filled circle + check for completed, outlined circle for pending, a slim `accent-600` ring (no glow) for the currently running stage with a subtle rotating arc — this is the one place a *very* restrained continuous animation is acceptable, since it's communicating real ongoing work.

## Connected Apps / Integrations

Row-based, monochrome provider marks, health as a small labeled dot + text (Connected / Degraded / Re-auth required / Disconnected) using semantic colors — never green-glow "online" indicators.

## Activity Timeline

Vertical line + node per event, `text-tertiary` timestamps in mono, no icon soup — one icon per row max.

---

# 9. Corporate tone in copy

- No exclamation points in system copy. No emoji.
- Prefer plain, declarative statements over hype: "Your AI agent is on it" → "Here's what changed since your last visit."
- Insights should read like an analyst's note, not a chatbot: "PR #482 has been waiting 6 hours and is trending toward its SLA" rather than "Uh oh! This PR might miss its deadline!"
- Numbers and states should always be scannable at a glance without needing to read a sentence — copy supports the data, it doesn't replace it.

---

# 10. Accessibility (carried forward, unchanged)

- WCAG 2.2 AA contrast minimum — verify accent-on-white and semantic colors against `surface-raised`.
- Every status must have a text label, not color alone.
- Visible focus rings using `accent-600` at 2px offset outline — never suppressed.
- `prefers-reduced-motion` disables all transitions beyond instant state swaps.
- All icon-only buttons get `aria-label`s; live mission-state changes get `aria-live="polite"` announcements.

---

# 11. How to use this with Stitch

Work page by page against the existing skeleton at `localhost:3000`, one Stitch prompt per screen. Suggested order, each referencing this file plus the named source doc for content/structure:

1. **App shell + sidebar + top command bar** — layout unchanged, restyle per §7.
2. **Home / Dashboard** (KPI strip, mission composer, recent missions, agent insights, quick actions, connected apps, activity) — per §8, using `DESIGN.md` §9–16 (original) for content and this file for surface.
3. **Mission detail** (execution timeline, approval panel) — per §8 + `AGENT_FLOW.md` §10–11.
4. **PR / Context Pack view** — per §8 + `AGENT_FLOW.md` §5 and `PARALLAX_AGENT_CORE_INTEGRATION.md` §4.
5. **Review Debt dashboard** — per original `DESIGN.md` §17 layout, restyled per this file.
6. **Projects, Integrations, Team, Analytics, Settings** — apply the same tokens/components; these are lower-priority per the information hierarchy in §3.

For each Stitch prompt, explicitly state: *light mode, cool-toned neutral palette with a single indigo accent, fully rounded corners (8–24px radius scale), no gradients, no photographic imagery, flat cards with hairline borders, restrained shadows, calm micro-motion only* — and paste the relevant token table from §2–§4 so Stitch doesn't default back to a dark or gradient-heavy AI-template look.
