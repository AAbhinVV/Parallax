# Parallax — Product Design System & Dashboard UX

**Reference:** Supplied Parallax dashboard image.

The visual reference establishes a premium engineering-control-plane aesthetic: dark navigation, dark translucent chrome, luminous blue/violet interaction surfaces, high-information cards, compact status indicators, and a large mission command surface.

The implementation should use the composition as a design reference, not as a pixel-for-pixel clone.

---

# 1. Design direction

## Keywords

**Operational. Intelligent. Cinematic. Dense. Calm. Precise.**

The dashboard should feel like a control room for engineering work.

Avoid:

- generic white SaaS dashboards
- oversized marketing copy
- excessive gradients
- noisy glassmorphism
- decorative 3D UI with no information value
- chat-first layouts
- AI gimmicks

Use:

- dark layered surfaces
- subtle transparency
- crisp borders
- luminous focus states
- compact information hierarchy
- readable data density
- strong motion restraint

---

# 2. Layout model

Reference composition:

```text
┌──────────────┬───────────────────────────────────────────────────────────┐
│              │ Top command/search bar                         utilities │
│   Sidebar    ├───────────────────────────────────────────────────────────┤
│              │ Hero / contextual greeting / environment status          │
│   Primary    │                                                           │
│ navigation   │ KPI strip                                                 │
│              │                                                           │
│              │ Mission command surface                                   │
│              │                                                           │
│              │ Recent missions / tasks      Activity / integrations     │
│              │                                                           │
│              │ Projects / insights / quick actions                       │
│              │                                                           │
└──────────────┴───────────────────────────────────────────────────────────┘
```

Desktop target:

- left sidebar: 224–248px
- top command bar: 64px
- page content: responsive
- right rail: 300–360px when visible

Tablet:

- collapsible sidebar
- right rail becomes drawer

Mobile:

- bottom navigation or compact drawer
- cards stack
- mission composer remains primary

---

# 3. Information hierarchy

Highest priority:

1. Active mission state
2. Review bottlenecks
3. Pending approvals
4. Risky PRs
5. Actionable insights

Second level:

- projects
- recent missions
- recent activity
- integration state

Third level:

- historical analytics
- documentation
- administration

---

# 4. Color semantics

Use semantic tokens rather than hard-coded colors.

### Base

- `bg-0`: deep application background
- `bg-1`: navigation layer
- `bg-2`: card layer
- `bg-3`: elevated panel
- `border-subtle`
- `border-strong`

### Accent

- Primary: electric indigo/violet
- Focus: cyan/blue
- Positive: green
- Warning: amber
- Danger: red
- Neutral info: slate/blue-gray

Accent gradients should be rare and primarily reserved for:

- primary CTA
- hero glow
- active command surface

---

# 5. Typography

Recommended:

- **Inter** or a similarly neutral grotesk for UI
- **JetBrains Mono** for IDs, metrics, event IDs, code-like data

Hierarchy:

- Page title: 32–44px
- Section title: 16–20px
- Card title: 14–16px
- Body: 13–15px
- Metadata: 11–12px
- Mono: 11–13px

Do not oversize dashboard headings.

---

# 6. Sidebar

Items:

- Home
- Missions
- Projects
- Integrations
- Knowledge
- Team
- Analytics
- Settings

The reference uses a dark left rail with a luminous active state.

### Sidebar details

Top:

- Parallax mark
- Product label

Bottom:

- Workspace/user
- Team/org
- profile menu

Additional contextual card:

> Turn ideas into progress

This card can promote mission creation, but should remain subordinate to the navigation.

---

# 7. Command bar

The top command bar should support:

- global search
- Ask Parallax
- keyboard shortcut
- notification center
- New Mission
- workspace/user menu

The command bar is not the main UI.

It is a universal entry point into mission creation and discovery.

---

# 8. Hero / greeting

Use a contextual project/team surface.

Example:

> Good morning, Sarah.

Then:

> Here’s the latest from your projects. Your AI agent is on it.

Reference includes a mountain image.

Production guidance:

- keep background photography extremely low contrast
- use a dark overlay
- prefer abstract engineering imagery in production
- ensure text contrast is high
- do not rely on image content for meaning

The hero should optionally show:

- current review pressure
- active mission
- team health
- system status

---

# 9. KPI strip

Reference cards:

- Active tasks
- Completed
- Blocked
- Awaiting approval
- Project health

Parallax-specific replacement:

- PRs awaiting review
- Median review wait
- SLA at risk
- Pending approvals
- Review health

Each KPI needs:

- number
- label
- trend
- timeframe
- semantic state

Avoid fake live values in production.

---

# 10. Mission command surface

This is the most important UI element.

Visual treatment:

- elevated panel
- subtle luminous focus border
- strong input affordance
- compact action chips

Example:

> Tell Parallax what you need to do…

Suggested shortcuts:

- Triage PRs
- Find blockers
- Schedule reviews
- Update Jira
- Notify team
- Search docs
- More

Input footer:

- execution mode
- submit/action button

Execution modes:

- Review first
- Guided
- Auto

Display exactly what each mode permits.

---

# 11. Recent missions

Use dense list/table hybrid.

Each mission row:

- icon
- title
- summary
- status
- project
- progress
- last activity
- navigation chevron

Statuses:

- Running
- Completed
- Waiting
- Blocked
- Needs approval

Hover:

- highlight row
- reveal quick actions

Click:

- mission detail drawer/page

---

# 12. Projects

Compact project list:

- project icon
- name
- health/progress
- active review count
- blockers

Clicking opens project control plane.

---

# 13. Agent Insights

This should be evidence-based.

Examples:

> 2 potential review bottlenecks detected.

> PR #482 is awaiting review and is likely to breach the team SLA.

> 3 PRs are linked to Jira issues still marked In Progress.

Each insight must expose:

- source
- confidence
- reasoning
- recommended action

---

# 14. Quick Actions

Quick actions should be operational, not generic.

Examples:

- Summarize a project
- Triage review backlog
- Find reviewers
- Schedule review blocks
- Update Jira from GitHub
- Notify Slack
- Generate report

---

# 15. Connected Apps

Display connector health.

Each row:

- integration icon
- provider
- connected state
- workspace/account
- last sync
- configuration action

Health states:

- Connected
- Degraded
- Re-auth required
- Disconnected

Never expose access tokens.

---

# 16. Recent Activity

Activity should use a timeline.

Every entry:

- provider
- event
- target
- result
- timestamp

Examples:

- merged PR
- review request posted
- Jira ticket updated
- Notion document updated
- blocker detected

---

# 17. Review Debt Dashboard design

Recommended layout:

```text
┌─────────────────────────────────────────────────────────────────┐
│ Review Debt                         7-day trend                 │
├────────────┬────────────┬────────────┬────────────┬─────────────┤
│ Queue      │ Median     │ SLA Risk   │ AI PRs     │ Bottleneck  │
│ 23         │ 3h 12m     │ 6          │ 41%        │ Backend     │
├──────────────────────────┬──────────────────────────────────────┤
│ Review wait trend        │ Reviewer load                        │
│ [chart]                  │ [chart]                              │
├──────────────────────────┴──────────────────────────────────────┤
│ PR queue                                                          │
│ Risk │ PR │ Reviewer │ Wait │ Effort │ Status │ Action           │
└──────────────────────────────────────────────────────────────────┘
```

Use charts only where trends matter.

---

# 18. PR Context Pack design

Layout:

```text
┌─────────────────────────────────────────────────────────┐
│ PR #482   Payment retry handling             HIGH RISK   │
│ 35 min estimated review                                 │
├─────────────────────────────────────────────────────────┤
│ Why                                                     │
│ Linked issue • acceptance criteria • product context    │
├─────────────────────────────────────────────────────────┤
│ What changed                                            │
│ modules • files • architectural impact                  │
├──────────────────────┬──────────────────────────────────┤
│ Risk                 │ Tests                            │
│ auth                 │ coverage                         │
│ payment              │ checks                           │
│ migration            │ failures                         │
├──────────────────────┴──────────────────────────────────┤
│ Recommended reviewer                                    │
│ Alex Chen — payment/backend ownership                   │
│ Available 3:00–3:45 PM                                 │
├─────────────────────────────────────────────────────────┤
│ [Start Review] [Schedule] [Change Reviewer] [Dismiss]  │
└─────────────────────────────────────────────────────────┘
```

---

# 19. Approval UX

Approval must show consequences before confirmation.

Example:

```text
APPROVAL REQUIRED

Parallax proposes:

1. Create Jira PAY-482
2. Add GitHub PR link
3. Schedule review with Alex at 3:00 PM
4. Post request in #payments

Why:
High-confidence match to PR #482.

Affected systems:
GitHub • Jira • Google Calendar • Slack

[Approve all] [Edit] [Reject]
```

Use grouped approvals for related low-risk mutations.

---

# 20. Interaction rules

### Motion

Use short transitions.

Good:

- 120–220ms
- subtle opacity/translate
- progress movement

Avoid:

- constant pulsing
- large card movement
- decorative parallax
- animation in every component

### Loading

Use skeletons for initial page data.

For agent work:

- display stages
- show elapsed time
- show current operation
- allow details

Example:

`Reading PR → Resolving ticket → Assessing risk → Finding reviewer`

---

# 21. Responsive behavior

### Desktop

Full dashboard composition.

### Tablet

- right rail collapses
- cards become 2-column
- command surface remains full width

### Mobile

- single-column
- command input sticky where appropriate
- mission progress full-screen
- approval actions fixed at bottom

---

# 22. Accessibility

Requirements:

- WCAG 2.2 AA target
- keyboard navigation
- visible focus state
- correct semantic headings
- aria labels for icon buttons
- screen-reader status announcements for mission state
- no color-only meaning
- reduced-motion support

---

# 23. Component taxonomy

```text
AppShell
Sidebar
TopCommandBar
MissionComposer
KpiCard
MissionList
MissionRow
ProjectCard
InsightCard
QuickActions
IntegrationCard
ActivityTimeline
ReviewDebtChart
ReviewQueue
ContextPack
RiskBadge
ReviewerMatch
ApprovalPanel
ExecutionTimeline
EvidenceDrawer
```

---

# 24. Visual quality bar

The dashboard should feel:

- expensive
- controlled
- information-dense
- modern
- technical
- trustworthy

The reference image's strongest idea is not its color palette.

It is the **composition: one dominant command surface surrounded by operational context**.

That composition should become Parallax's defining UX.
