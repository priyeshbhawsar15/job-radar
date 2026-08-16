---
type: "prd"
area: "project"
status: "draft"
project: "Job Radar"
tags:
  - "project"
  - "prd"
  - "job-search"
parent: "[[20 Projects/Job Radar/Project]]"
---

# Job Radar — Product Requirements Document

## Status and decision gates

This is a draft product definition, created at Priyesh's request on 2026-08-14. It authorizes research and design only. Implementation, production deployment, source enablement, scheduled collection, Job Ops handoff, and notifications require explicit approval through the sequence in [[20 Projects/Job Radar/Tasks|Tasks]].

## Product statement

Job Radar is a self-hosted service that monitors user-approved public career-board listing URLs on a configurable schedule, finds newly listed jobs, obtains structured public job details, deduplicates the result, and submits only eligible new jobs to the existing Job Ops service for downstream processing.

## Problem

Priyesh tracks many company career boards with different ATS platforms and filtering behavior. Checking each site manually is repetitive; pages are often JavaScript-driven and may expose listing data only after rendering. The system must discover new jobs reliably while remaining conservative, traceable, and safe.

## Goals

1. Maintain a curated inventory of approved career boards and their board/ATS family.
2. Reuse adapter logic across equivalent board families and keep unsupported sites explicitly classified as `custom`.
3. Discover candidate job links from current public listing pages using official public APIs where available or the dedicated Playwright service for dynamic boards.
4. Visit approved public job-detail URLs, normalize the data needed by Job Ops, and deduplicate repeat observations.
5. Hand off only eligible, previously unseen jobs to Job Ops through an idempotent integration.
6. Give Priyesh a reviewable UI for boards, configuration, test results, runs, and safe diagnostics.
7. Operate on The Shell with bounded resources, observability, rollback, and durable configuration/history.

## Non-goals

- Login, authenticated/private job portals, CAPTCHA solving, proxy rotation, stealth/fingerprint evasion, or bypassing access controls.
- Generic web crawling or accepting arbitrary browser scripts/actions from the UI.
- Replacing Job Ops' job analysis, ranking, application workflow, or storage responsibilities.
- Guaranteeing that every listed board is technically or contractually collectible.
- Enabling a board, scheduling collection, importing to Job Ops, or sending notifications without explicit approval.

## Source inventory and adapter principle

The canonical initial inventory is [[10 Personal/Career/Job Boards|Job Boards]]. Priyesh has recorded a first-pass family value in its `jobboard` column, including `oracle`, `workday`, `greenhouse`, `lever`, `ashbyhq`, `careerpage`, `zoho`, and `custom`.

An adapter is a reviewed translator for one board family. It defines the allowed readiness signal, approved public data source (official API, rendered DOM, or specific public browser response), extraction/mapping rules, pagination behavior, and job-link acceptance policy. Board configuration supplies that adapter's reviewed parameters; it does not execute arbitrary user-provided code.

## Primary workflow

```text
Approved board configuration
  → choose verified adapter
  → obtain listing data (official public API or Playwright)
  → extract and strictly validate candidate job URLs
  → canonicalize and deduplicate
  → acquire approved public job-detail data
  → normalize into Job Ops handoff shape
  → idempotent Job Ops submission
  → safe run/audit history and operator-visible outcome
```

## Functional requirements

### Board management

- Store a board name, public listing URL, adapter family, reviewed configuration, enabled/disabled state, schedule/override, and revision/audit reason.
- Support the board families verified by research and deliberately preserve `custom` for sites without a reusable adapter.
- Provide a non-mutating board test that uses stored configuration and yields an ephemeral sample only.

### Acquisition and extraction

- Prefer documented official public ATS endpoints when they are available and permitted.
- For dynamic boards, use the private Playwright service with Chromium, one isolated browser context per board run, explicit readiness signals, strict time/size limits, and serialized initial concurrency.
- Permit only exact reviewed public listing/resource origins and paths. Keep browser-resource policy separate from the narrower accepted job-detail URL policy.
- Accept a candidate only after URL canonicalization, host/path policy checks, and deduplication.
- Extract only the fields required for the agreed Job Ops handoff; retain safe provenance/counts rather than raw upstream payloads.

### Scheduling and handoff

- Support configurable schedules, time zones, per-board overrides, retries/backoff, and an operator-controlled enable/disable state.
- Prevent overlapping board runs and duplicate Job Ops submissions.
- Require a reviewed, authenticated integration contract with Job Ops; secrets remain local, Git-ignored, and never appear in UI, source control, logs, or diagnostics.

### UI

- The initial UI milestone is static HTML only, with no functional actions.
- The eventual UI must allow review of board configuration, adapter choice, state, safe test results, run summaries, failures, and audit history.
- It must not expose credentials, cookies, raw upstream payloads, internal service URLs, private headers, or browser-control primitives.

## Safety, compliance, and privacy requirements

- Use only public, user-approved sources after terms/robots/rate-limit review as applicable.
- No authentication, custom session persistence, CAPTCHA bypass, stealth behavior, or access-control evasion.
- Restrict SSRF-sensitive navigation, redirects, DNS resolution, and browser subresources to reviewed public policies.
- Bound browser CPU, memory, PIDs, concurrency, time, output size, retries, and retained artifacts.
- Store durable configuration/audit evidence and safe operational summaries; avoid raw HTML, JSON bodies, tokens, cookies, passwords, and private/internal URLs in logs or persistent diagnostics.

## Deployment constraint

Production runs on The Shell (`192.168.2.201`); the Gaming PC is development-only. The planned `job-radar-browser` Playwright service is private, has no host port/Caddy route, and initially runs at 768 MiB RAM, 0.75 CPU, 128 PIDs, and one serialized board acquisition pending a capacity spike. See [[30 Homelab/Services/AI and Work/Job Radar|Homelab service note]].

## Delivery and acceptance gates

1. Finalize board/adapter classification.
2. Produce adapter extraction logic without implementation and obtain review.
3. Produce static UI design and obtain review.
4. Produce backend/system design, then incorporate Priyesh's feedback and obtain approval.
5. Produce an approved end-to-end implementation plan.
6. Implement only the approved plan.
7. Verify with unit, integration, browser, resource, deployment, and end-to-end tests; collect feedback and deliver approved improvements.

## Success criteria

- Every enabled board has a reviewed adapter/configuration, public-source policy, extraction logic, limits, and test evidence.
- A scheduled run can distinguish verified-empty, successful discovery, policy rejection, acquisition failure, and handoff failure.
- Repeated observations do not create duplicate Job Ops submissions.
- Browser workload remains inside verified Shell resource limits and does not expose a public browser-control endpoint.
- Priyesh can review outcomes and audit evidence without accessing secrets or raw upstream data.