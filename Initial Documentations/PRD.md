# Parallax — Product Requirements Document

**Document status:** Product baseline  
**Product:** Parallax  
**Primary wedge:** AI PR Triage & Context Builder  
**Platform:** Engineering Operations Agent  
**Audience:** Founders, Product, Engineering, Design, GTM, Security

---

## 1. Executive summary

Engineering teams have more code-production capacity than review and coordination capacity. AI coding tools can increase the volume of pull requests without increasing the number of humans available to understand, validate, and merge them.

Parallax addresses the bottleneck **after code is produced and before engineering work becomes trusted team progress**.

Parallax connects GitHub, Slack, Jira/Linear, Notion, and Google Calendar into one agentic workflow. The system watches for relevant events, constructs a cross-tool context pack, assesses risk and review effort, selects an appropriate reviewer, checks calendar availability, schedules protected review time, posts a structured Slack request, tracks review SLA, and escalates when work becomes review debt.

Parallax is explicitly different from an AI code reviewer:

- A code reviewer evaluates code.
- Parallax **gets the right human to the right code with the right context at the right time**, then tracks what happens.

The longer-term product is a mission-based engineering operations agent that can execute approved multi-step workflows across the customer's existing tools.

---

# 2. Problem

## 2.1 Core problem

Code production is becoming faster, while engineering coordination remains fragmented.

The review workflow contains several manual operations:

1. Find the PR.
2. Determine what product/issue it belongs to.
3. Locate the acceptance criteria.
4. Understand what changed and why.
5. Find related PRs or commits.
6. Identify risky areas.
7. Estimate review effort.
8. Determine who should review.
9. Find calendar availability.
10. Request review in Slack.
11. Track whether the review happened.
12. Escalate stale reviews.
13. Update the broader project system.

Each operation is individually simple. Together they create context-switching overhead and review latency.

## 2.2 Product insight

The bottleneck is not only correctness of code.

It is **coordination latency**.

Parallax therefore optimizes:

- time-to-context
- time-to-correct-reviewer
- time-to-scheduled-review
- review SLA adherence
- review backlog and debt
- cross-tool project consistency

---

# 3. Target users

## Primary persona — Engineering Lead

Needs a reliable view of review bottlenecks, team capacity, risky changes, and stalled work.

**Goals**
- Keep reviews moving.
- Avoid overloading the same reviewer.
- Surface risky work early.
- Reduce unreviewed AI-generated code.
- Understand team review debt.

## Primary persona — Senior Engineer / Reviewer

Needs enough context to review quickly and confidently.

**Goals**
- Avoid searching multiple systems.
- Know why the PR exists.
- See acceptance criteria.
- Understand risk and expected effort.
- Review during protected focus time.

## Secondary persona — Engineering Manager / CTO

Needs engineering throughput and operational visibility.

**Goals**
- Understand review latency.
- Identify organizational bottlenecks.
- Measure AI-assisted development impact.
- Reduce process overhead.

## Secondary persona — Project Manager

Needs cross-tool project progress without manually reconciling GitHub, Jira, Notion, and Slack.

---

# 4. Jobs to be done

### JTBD-01 — review triage

> When a new or changed PR arrives, help me understand its business context, risk, review effort, and correct reviewer without manually searching multiple systems.

### JTBD-02 — review scheduling

> When a PR needs review, find a practical focus window for the correct reviewer and create a structured review request.

### JTBD-03 — review debt management

> When reviews accumulate, tell me where the bottleneck is, why it is happening, and which action will relieve it.

### JTBD-04 — project reconciliation

> When engineering execution diverges from planned work, identify mismatches and propose synchronized updates.

### JTBD-05 — mission execution

> When I describe engineering coordination work in natural language, plan and execute the approved workflow across connected tools.

---

# 5. Product positioning

## Category

**AI Engineering Operations / Review Orchestration**

## One-line value proposition

> **Parallax turns pull requests into scheduled, context-rich human reviews — then orchestrates the work around them.**

## Extended positioning

Parallax is the control plane between engineering execution and organizational coordination.

---

# 6. Product principles

### 6.1 Context before action

Parallax must understand the work before proposing a tool mutation.

### 6.2 Evidence-backed intelligence

Every important recommendation must have inspectable evidence.

### 6.3 Human accountability

Consequential changes require approval unless a team policy explicitly authorizes the action.

### 6.4 Least privilege

Each integration receives only the scopes required for the enabled workflows.

### 6.5 Explainable routing

A reviewer should be able to see why Parallax selected them.

### 6.6 No fake certainty

Confidence is explicit. Unknown information is shown as unknown.

### 6.7 Verify after execution

Successful API responses are not enough. Parallax records post-action verification.

---

# 7. Product scope

## In scope — MVP

### Integrations

- GitHub
- Slack
- Jira or Linear
- Notion
- Google Calendar

### PR intelligence

- PR discovery
- Draft/open/ready-for-review state tracking
- PR metadata extraction
- Issue/ticket linking
- Commit and branch context
- Related PR detection
- Risk classification
- Review effort estimate
- Context Pack generation
- AI-generated PR signal
- Reviewer recommendation

### Review orchestration

- Reviewer availability lookup
- Skill/ownership matching
- Calendar conflict analysis
- Review block proposal
- Slack review request
- Review SLA tracking
- Escalation rules
- Review Debt Dashboard

### Safety

- Approval gates
- Action preview
- Policy engine
- Audit trail
- Idempotency
- Verification

## Phase 2

- Full mission engine
- Cross-tool project reconciliation
- Jira/Linear synchronization
- Notion project memory
- Project reports
- Team-level routing
- Mission templates

## Phase 3

- Predictive review bottlenecks
- Organization-wide capacity intelligence
- Learning from review outcomes
- Advanced analytics
- Enterprise policy packs
- Multi-repository dependency intelligence

## Out of scope for initial release

- Automatic PR merge without explicit policy.
- Automatic destructive repository actions.
- Autonomous code modification.
- Replacing expert code review.
- Replacing Jira/Linear, GitHub, Slack, or Notion.

---

# 8. Core user flows

## 8.1 PR-to-review flow

1. GitHub event arrives.
2. Parallax deduplicates the event.
3. PR context is collected.
4. Linked issue/ticket is resolved.
5. Related work is discovered.
6. Risk and review-effort analysis runs.
7. Best reviewer candidates are ranked.
8. Calendar availability is checked.
9. Context Pack is generated.
10. Parallax creates a proposal.
11. Policy determines whether approval is required.
12. User approves/edits/rejects.
13. Calendar block is created when authorized.
14. Slack request is posted.
15. Review state is tracked.
16. SLA timer starts.
17. On completion, outcome is recorded.

## 8.2 Mission flow

Example mission:

> Review the Payments project, find unfinished work from GitHub, sync relevant tasks to Jira, document the updates in Notion, and notify the Payments team in Slack.

Execution:

1. Parse mission.
2. Resolve project and connected systems.
3. Build execution plan.
4. Gather evidence.
5. Detect candidate changes.
6. Generate proposed actions.
7. Run policy checks.
8. Request approval for external mutations.
9. Execute approved actions.
10. Verify each result.
11. Persist evidence and mappings.
12. Produce mission report.
13. Notify relevant team if approved.

---

# 9. Context Pack specification

Each Context Pack should contain:

### Header
- PR title
- Repository
- Author
- Current state
- Estimated review time
- Risk level
- AI-generated signal
- Recommended reviewer(s)

### Why this PR exists
- Linked issue/ticket
- Acceptance criteria
- Product/project context
- Relevant decisions

### What changed
- Files/modules affected
- Functional summary
- Architectural impact
- Data model impact
- Dependencies

### Risk analysis
- Auth/security
- Payments
- Data migrations
- API contracts
- Concurrency
- Configuration
- Infrastructure
- Rollback complexity

### Evidence
- PR
- Issue/ticket
- Relevant commits
- Related PRs
- Recent changes
- Test results
- Coverage delta when available
- Documentation

### Review plan
- Estimated effort
- Recommended reviewer
- Why reviewer matched
- Available time window
- Suggested focus areas

### Actions
- Start review
- Open PR
- Open ticket
- Open calendar event
- Request another reviewer
- Reject proposal

---

# 10. Risk model

Risk should not be a single opaque LLM score.

Use a structured model:

`Risk = weighted_signals + model_assessment + historical_signal`

Signal examples:

| Signal | Example |
|---|---|
| Security | auth middleware, permissions |
| Payments | payment/checkout modules |
| Data | migration/schema/index |
| Blast radius | number of services/modules |
| API | public contract changes |
| Infrastructure | CI/CD/IaC changes |
| Test delta | coverage reduction |
| Change size | very large diff |
| Ownership | unusual code owner |
| Freshness | stale PR |
| Related failures | recent failing checks |

Risk levels:

- **Low**
- **Medium**
- **High**
- **Critical**

Critical actions require stronger policy/approval.

---

# 11. Reviewer routing model

Reviewer ranking combines:

`ReviewerScore = ownership + skill_match + historical_context + availability + load + recency`

### Ownership

Derived from repository ownership, CODEOWNERS, git history, and component ownership.

### Skill match

Examples:

- DB schema → backend/data reviewer
- auth → security/backend reviewer
- payments → payments specialist
- frontend accessibility → frontend/accessibility reviewer

### Availability

Prefer calendar windows with no conflicting high-priority meetings.

### Load

Avoid repeatedly selecting a reviewer who already carries excessive review debt.

### Fairness

Do not optimize only for “best reviewer.” The system must also avoid pathological concentration.

---

# 12. Review Debt Dashboard

Primary metrics:

- Open PR count
- Review queue size
- Median review wait
- P75 review wait
- P95 review wait
- AI PR review wait
- Human PR review wait
- Reviews due in SLA
- Reviews overdue
- Average review effort
- Reviewer utilization
- Bottleneck reviewers
- Bottleneck repositories
- Risk distribution
- Review debt trend
- Predicted next bottleneck

### Dashboard actions

- Re-route a review
- Add reviewer
- Schedule focus block
- Escalate
- Inspect evidence
- Open team-level analytics

---

# 13. Mission dashboard requirements

The dashboard should expose:

- Recent Missions
- My Tasks
- All Projects
- Agent Insights
- Connected Apps
- Recent Activity
- Review Debt
- Quick Actions
- Mission status
- Approval queue

Statuses:

`Draft → Planning → Waiting for Approval → Running → Partially Complete → Completed → Failed`

---

# 14. Functional requirements

## FR-01 — integrations

System shall securely connect supported external services through OAuth/app authentication.

## FR-02 — event ingestion

System shall receive webhook/event notifications and periodically reconcile state.

## FR-03 — context retrieval

System shall retrieve relevant cross-tool records for a PR or mission.

## FR-04 — context pack

System shall produce a structured review context pack with citations/evidence.

## FR-05 — triage

System shall classify risk and estimate effort.

## FR-06 — routing

System shall produce a ranked reviewer list with reasons.

## FR-07 — scheduling

System shall evaluate calendar availability and propose review windows.

## FR-08 — Slack request

System shall produce an actionable review request containing risk, effort, context, and review action.

## FR-09 — SLA

System shall track review aging and evaluate configurable escalation policies.

## FR-10 — approval

System shall support approve/edit/reject flows.

## FR-11 — execution

System shall execute only authorized actions.

## FR-12 — verification

System shall verify external state after execution whenever the API supports observation.

## FR-13 — audit

System shall persist actor, action, reason, evidence, timestamps, and external IDs.

## FR-14 — mission planning

System shall translate natural-language missions into a structured action graph.

## FR-15 — project reconciliation

System shall compare engineering execution with project-management records.

---

# 15. Non-functional requirements

| Category | Requirement |
|---|---|
| Availability | 99.9% target for production control plane |
| Event durability | No silently dropped actionable events |
| Security | Encryption in transit/at rest |
| Secrets | Never persist raw access tokens in application tables |
| Auditability | Immutable action/event history |
| Latency | Initial triage target < 60 seconds after ingestion for normal PRs |
| Idempotency | Replayed events must not duplicate actions |
| Multi-tenancy | Hard isolation between tenants |
| Reliability | External failures handled with retries/backoff |
| UX | Core PR triage usable without training |
| Accessibility | WCAG 2.2 AA target |
| Observability | Logs, metrics, traces, audit events |
| Disaster recovery | Documented RPO/RTO by tier |

---

# 16. Success metrics

## North-star metric

**Median time from PR readiness to qualified human review start**

Supporting metrics:

- % of PRs receiving a context pack
- % of PRs routed successfully
- % of review requests scheduled
- Median time to reviewer assignment
- Median time to review start
- SLA attainment
- Review queue size
- Reviewer load imbalance
- User approval rate
- Proposal edit rate
- Action failure rate
- Duplicate action rate
- Mission completion rate

## Product outcome hypothesis

Parallax should materially reduce review wait and administrative coordination without increasing review errors or reviewer overload.

---

# 17. Trust and safety requirements

Every externally consequential mutation must have:

- Action identity
- Target identity
- Evidence
- Reason
- Confidence
- Policy decision
- Authorization record
- Execution result
- Verification result

High-impact actions should default to manual approval.

---

# 18. Permissions model

Roles:

### Owner
All organization settings.

### Admin
Integrations, policies, team configuration.

### Manager
Missions, approvals, analytics.

### Reviewer
Assigned review tasks and review context.

### Viewer
Read-only project and analytics access.

Permissions should also be resource-scoped where possible.

---

# 19. MVP acceptance criteria

MVP is complete when:

1. A GitHub PR webhook is received.
2. The system builds a cross-tool Context Pack.
3. Risk and review effort are shown with supporting evidence.
4. At least three reviewer candidates can be ranked.
5. Calendar availability can be evaluated.
6. A Slack review request can be generated.
7. The request contains a review action and Context Pack link.
8. Review SLA begins automatically.
9. A user can approve or reject the orchestration.
10. Approved calendar/Slack actions execute idempotently.
11. Actions can be audited.
12. Review Debt Dashboard shows live or reconciled data.
13. External API failures produce visible recoverable errors.
14. The system never performs prohibited actions silently.

---

# 20. Roadmap

### Release 0 — platform foundation

- Auth
- Tenant model
- GitHub integration
- Slack integration
- Calendar integration
- Event bus
- Audit framework
- Design system

### Release 1 — PR Intelligence

- PR ingest
- Context Pack
- Risk engine
- Reviewer routing
- Slack request
- Basic SLA

### Release 2 — Review Orchestration

- Calendar scheduling
- Approval center
- Review Debt Dashboard
- Escalations
- Analytics

### Release 3 — Missions

- Mission parser/planner
- Jira/Linear
- Notion
- Cross-tool reconciliation
- Mission reporting

### Release 4 — Intelligent operations

- Predictive bottlenecking
- Capacity forecasting
- Team learning
- Enterprise controls

---

# 21. Open product decisions

- Jira vs Linear priority for first generalized mission connector.
- Exact AI-generated PR detection strategy and user controls.
- Default SLA thresholds by team.
- How historical reviewer performance affects ranking.
- Whether calendar blocks are hard events or tentative holds.
- Organization-level model/provider selection.
- Data retention periods.

---

# 22. Final product definition

Parallax should feel like an **engineering operations control plane**, not a chatbot.

The AI is the reasoning layer.

The dashboard is the operational surface.

The connected tools remain the systems of record.

The approval/audit layer makes the agent accountable.
