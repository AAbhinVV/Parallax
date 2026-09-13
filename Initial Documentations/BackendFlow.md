### Flow of the Backend

GitHub event / user mission / manual action
        ↓
1. Observe
   Receive webhook or request; validate signature, authenticate, normalize event.
        ↓
2. Deduplicate + persist
   Prevent replayed webhooks from creating duplicate work.
   Store event, tenant, repository, PR, correlation ID.
        ↓
3. Contextualize
   Fetch PR metadata, commits, diff summary, changed files, CI status,
   CODEOWNERS/history, linked Jira issue, and related Notion knowledge.
        ↓
4. Build Context Pack
   Assemble evidence-backed PR context:
   why it exists, what changed, risks, tests, related work, and citations.
        ↓
5. Reason
   Generate structured risk level, review-effort estimate, reviewer candidates,
   confidence, and explanation. AI may synthesize; deterministic logic validates.
        ↓
6. Propose typed actions
   Example: recommend a reviewer and draft a Slack review request.
   No external system is changed yet.
        ↓
7. Critique + policy check
   Ensure targets/evidence are valid, scope is allowed, confidence is adequate,
   and determine whether approval is required.
        ↓
8. Approval state
   Approval can be approved, edited, rejected, or cancelled.
   An edit returns the proposal for revalidation and policy evaluation.
        ↓
9. Execute approved actions
   Use idempotency keys, then perform permitted actions:
   post/update a Slack request, create/update Jira links or issues,
   and write approved Notion documentation.
        ↓
10. Verify
   Read each external system back to confirm the intended state actually exists.
   API success alone is not treated as verification.
        ↓
11. Record + monitor
   Persist execution result, external IDs, evidence, audit events,
   errors/retries, review SLA state, and analytics aggregates.

### For the current four-integration scope, the normal PR path is:

GitHub PR webhook
→ GitHub PR/context retrieval
→ Jira issue resolution
→ Notion decision/document retrieval
→ Context Pack + risk/effort + reviewer recommendation
→ approval request
→ Slack review request
→ verification
→ audit record + SLA tracking


### Backend's Flow in simple explainantion.

GitHub event, user request, or manual button click
↓
1. Receive the request
   The backend receives the event and checks that it is genuine.
↓
2. Avoid duplicates
   If the same event comes again, do not create the same task twice.
   Save basic details such as the PR, repository, and team.
↓
3. Collect information
   Get PR details, commits, changed files, test results, code owners,
   linked Jira ticket, and useful Notion documents.
↓
4. Create a Context Pack
   Make one clear summary explaining why the PR exists, what changed,
   possible risks, test status, and related work.
↓
5. Analyze the PR
   Estimate risk and review time, suggest suitable reviewers,
   and explain why they were selected.
↓
6. Prepare suggested actions
   For example: suggest a reviewer and prepare a Slack review message.
   Nothing is changed in GitHub, Slack, Jira, or Notion yet.
↓
7. Check rules and permissions
   Confirm the suggested action is safe, valid, supported by evidence,
   and whether user approval is needed.
↓
8. Wait for user decision
   The user can approve, edit, reject, or cancel the suggestion.
   Edited actions are checked again before continuing.
↓
9. Perform approved actions
   Send the Slack message, update or create Jira work, and update
   approved Notion documentation. Prevent accidental duplicate actions.
↓
10. Confirm the result
   Read Slack, Jira, or Notion again to make sure the update happened.
↓
11. Save history and track progress
   Store what happened, who approved it, evidence, errors, retries,
   review SLA status, and reporting data.