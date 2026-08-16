---
type: "design"
area: "project"
project: "Job Radar"
status: "complete"
tags:
  - "project"
  - "ui"
  - "design"
parent: "[[20 Projects/Job Radar/Project]]"
---

# Job Radar UI Design

## Scope

## Frontend-design-stack direction (2026-08-16)

**Audience and job:** a private operator needs to quickly decide whether a pipeline run, board configuration, board attempt, or normalized job requires action—without mistaking static mock data for a live control plane.

**Visual system:** “calm operations cockpit.” Use an ink/navy navigation foundation, warm-white/near-black surfaces per theme, teal for healthy/accepted progress, amber for attention/held/partial states, and restrained red for failed/rejected outcomes. Prefer a compact, legible type scale, a stable card/table rhythm, rounded-but-not-soft panels, and one quiet signature element: the radar-like outlined brand mark and status pulse—not decorative motion.

**Interaction invariants:** retain the collapsible desktop rail, contained mobile navigation overflow, persisted light/dark preference, explicit static/mock notices, keyboard-visible focus, and route-based back-navigation. Long public URLs, payload values, and identifiers must wrap rather than widen the document. No raw Playwright payload or unsafe browser capability is exposed.

**Screen hierarchy:** run history answers “what changed?”; pipeline detail answers “which boards contributed?”; board detail answers “is this configuration ready?”; board-run detail answers “what safely happened?”; jobs answers “which normalized discoveries are actionable?” Search and filters remain immediately visible on the jobs page; dates sort newest-first by default.

**Acceptance viewports:** inspect 1440×1000 desktop and 390×844 mobile. Validate navigation, sidebar/theme controls, job search/filter/sort, a run → board run flow, a board → configuration flow, an extracted job detail, empty/filter states, focus state, and `scrollWidth <= viewport width` on mobile.

### Expanded static navigation prototype (2026-08-15)

The Gaming PC static artifact now models the requested operator information architecture with client-side hash routes: pipeline-run history and detail, boards index, board detail, static configuration/edit view, reusable board-run audit detail, jobs index, and normalized Job Ops payload detail. It also includes a persisted light/dark preference, collapsible desktop sidebar, responsive mobile navigation, and `system-design.html` as a standalone visual architecture reference.

Board-run audit events intentionally expose only safe structured metadata: time, BoardRun capability/config revision, safe status/outcome, duration/counts, and bounded diagnostic code. The UI must not display raw Playwright request/response bodies, cookies, headers, tokens, internal endpoints, selectors, console text, or browser exception strings.

Artifacts: `/home/priyesh/Work/job-radar/ui-prototype/index.html` and `/home/priyesh/Work/job-radar/ui-prototype/system-design.html`. These remain static mock data with no backend, source, scheduler, Playwright, or Job Ops connection.

Completed static operator-dashboard prototype only. It has no backend, database, scheduler, source run, Job Ops request, Discord action, or persisted state. Every visible run, job, failure, and delivery outcome is local sample data.

## Operator workflow

1. Review the last seven days of retained pipeline runs from newest to oldest.
2. See each run's duration, board coverage, extracted count, Job Ops accepted/held counts, and safe-failure count.
3. Select a run to inspect its board outcomes, sanitized failures, extracted jobs, and per-job Job Ops delivery result/receipt or safe reason.
4. See the visible seven-day retention boundary and next purge indicator.
5. See a prominent manual `Run pipeline` control. In this prototype it opens only an explicit “not connected” explanation; it cannot start work.

## Information architecture

- **Summary:** retained runs, extracted jobs, Job Ops accepted, safe failures, and upcoming purge.
- **Run history:** local status filter, empty-state affordance, and completed/partial/failed run examples.
- **Selected run drawer:** board outcomes; sanitized failure code/stage/message; individual extracted jobs; `accepted`, `sent`, `held`, or `not-sent` Job Ops outcome.

## Visual contract

A calm operations interface: dark navy navigation, warm off-white working surface, restrained teal healthy state, amber hold/partial state, and red failure state. The persistent detail drawer is the primary inspection surface. Desktop uses a dense two-column run-list/detail composition; mobile stacks the panels without horizontal scrolling.

## Prototype artifact and verification

- Source: `/home/priyesh/Projects/job-radar/ui-prototype/index.html`
- Screenshots: `ui-prototype/artifacts/desktop.png` (1440 × 1337) and `mobile.png` (390 × 2755)
- Browser check: both 1440 × 1000 and 390 × 844 viewports had no horizontal overflow; the Run Pipeline action opened only the inert static-prototype explanation.

## Later backend-design inputs

The future system design must define the persisted run/job/handoff schema, seven-day deletion transaction and audit boundary, safe failure taxonomy, authorization/audit semantics for manual runs, Job Ops idempotency/reconciliation states, and APIs that replace the local mock data. None is approved or implemented by this static UI artifact.
