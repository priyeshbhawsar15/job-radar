---
type: "implementation-plan"
area: "project"
project: "Job Radar"
status: "approved-in-progress"
tags:
  - "project"
  - "implementation-plan"
  - "location-policy"
parent: "[[20 Projects/Job Radar/Project]]"
---

# Job Radar — Location Admission Remediation Implementation Plan

> **Approval:** Priyesh approved implementation on 2026-08-28. Implementation is confined to the isolated Gaming PC worktree. No production deployment, merge, push, persistent-database mutation, scheduler enablement, or Job Ops request is authorized.

## 0. Reference specifications and document index

| Reference | Authoritative behavior | Used by |
|---|---|---|
| `src/job_radar/services/location.py` | Current `INDIA` / `NON_INDIA` / `UNKNOWN` / `CONFLICT` decisions and eligibility | Phases 1–5 |
| `src/job_radar/adapters/base.py` | Extracted candidate contract | Phases 2–4 |
| `src/job_radar/adapters/families.py` | Greenhouse/Ashby raw payload parsing | Phases 2 and 4 |
| `src/job_radar/services/engine.py` | Provider-native acquisition, including endpoint translation | Phase 4 |
| `src/job_radar/services/normalization.py` | Candidate classification, persistence, enrichment, and enqueue | Phases 2, 5, and 6 |
| `src/job_radar/services/handoff.py` | Enqueue and dispatch boundaries | Phase 5 |
| `src/job_radar/api/v1/jobs.py` | Manual Job Ops admission path | Phase 5 |
| `src/job_radar/db/models/candidate.py` and migrations | Durable candidate location evidence | Phases 2 and 5 |
| `src/job_radar/db/seed.py` | Reviewed GoDaddy and provider configuration | Phase 4 |
| `tests/test_location_gate.py` and `tests/test_location_decision_system.py` | Existing location-policy contract | Phases 1, 3, and 7 |
| `[[System Design]]` | Scheduler, normalization, persistence, and handoff architecture | All phases |
| `[[History]]` | Append-only implementation and verification record | Completion gate |

### Confirmed evidence baseline

- Explicit foreign locations were misclassified as `UNKNOWN`, which is eligible under the approved policy.
- The hand-maintained foreign vocabulary omits UAE, Turkey, Serbia, Ontario, Bulgaria, Colombia, Estonia, Saudi Arabia, Austria, Denmark, South Korea, California, Washington, Charlotte, Bermuda, and related subdivisions/cities.
- Greenhouse provides usable location evidence in `location.name`, `offices[]`, and metadata such as `Country`, but the adapter persists only `location.name`.
- Ashby provides `address.postalAddress.addressCountry/addressRegion` and `secondaryLocations`, but the custom acquisition path discards those fields.
- GoDaddy’s reviewed URL has `country_codes[]=IN`, but endpoint translation fetches the unfiltered global Greenhouse API.
- The local evidence set contains 188 affected `UNKNOWN` eligible records: 171 queued and 17 eligible but not outboxed. No Job Ops attempts or accepted rows exist in this local database.

## 1. Safety freeze and failing regression matrix

**Reference specs:** Section 0; `tests/test_location_gate.py`; `tests/test_location_decision_system.py`.

1. Confirm the exact worktree, branch, clean baseline, scheduler-disabled state, and handoff-disabled state.
2. Do not run the persistent pipeline or modify `/home/priyesh/.local/share/job-radar-local/job-radar.db`.
3. Add failing unit tests for all reported explicit foreign values:
   - UAE and aliases; Turkey; Serbia; Bulgaria; Colombia; Estonia; Saudi Arabia; Austria; Denmark; South Korea / Republic of Korea; Bermuda.
   - Ontario and Canadian provinces.
   - California, Washington, Delaware, North Carolina, Washington DC, and context-aware state abbreviations such as `NC`.
   - Bellevue, Mountain View, Charlotte, Wilmington, Belgrade, and Seoul only when provider/subdivision evidence safely disambiguates them.
4. Preserve expected eligible behavior for truly unresolved values such as empty, `Remote`, `Multiple locations`, and `2 Locations`.
5. Preserve `CONFLICT` eligibility for genuine multi-location jobs that explicitly offer India and foreign alternatives.
6. Add a regression proving that trusted India source scope plus explicit foreign-only job evidence is `NON_INDIA`, not eligible `CONFLICT`.
7. Add collision tests so ordinary `in` is not India and ambiguous short codes (`IN`, `CA`, `DE`) are interpreted only with structural context.

**Gate:** Tests must reproduce the current leak before production code changes.

## 2. Typed provider-location evidence contract

**Reference specs:** `src/job_radar/adapters/base.py`; `src/job_radar/services/normalization.py`; candidate model/migrations.

1. Define a bounded typed evidence structure containing only safe geography facts, not raw provider payloads:
   - provider family;
   - country names/codes and evidence paths;
   - regions/subdivisions and evidence paths;
   - office/secondary display locations needed for classification;
   - reviewed source-scope evidence.
2. Preserve `ExtractedCandidate.location` exactly as the provider’s primary display location.
3. Carry typed evidence independently through extraction and normalization.
4. Persist a bounded structured evidence representation or an equivalent durable typed representation so dispatch-time revalidation does not depend on the original provider response.
5. Keep the existing human-readable `location_evidence` summary, confidence, decision, eligibility, and exclusion reason synchronized.
6. If a schema change is necessary, add a forward-only migration compatible with SQLite tests and PostgreSQL production. Do not apply it to production or the persistent local database during implementation.
7. Do not store raw HTML, full provider JSON, descriptions, credentials, or unbounded metadata in location evidence.

**Gate:** Round-trip tests prove typed evidence survives extraction → normalization → persistence → readback.

## 3. Deterministic geography classifier

**Reference specs:** `src/job_radar/services/location.py`; approved decision policy in Section 1.

1. Replace sparse foreign-country/city deny-list behavior with deterministic country aliases and subdivisions:
   - ISO-3166 country names/codes and reviewed aliases;
   - explicit India aliases and states/cities;
   - US state names and context-aware abbreviations;
   - Canadian province names and context-aware abbreviations;
   - reviewed territory and country aliases required by the regression matrix.
2. Prefer structured provider country evidence over display-string inference.
3. Use exact token/boundary parsing rather than unsafe substring matching.
4. Implement precedence:
   1. explicit India-only job evidence → `INDIA`;
   2. genuine India plus foreign alternatives → `CONFLICT`, eligible;
   3. explicit foreign-only provider/job evidence → `NON_INDIA`, ineligible;
   4. truly unresolved geography → `UNKNOWN`, eligible under current policy.
5. A nominal India source scope must not override explicit foreign-only evidence.
6. Keep raw location unchanged and generate auditable evidence describing which structured/text signals drove the decision.
7. Do not add network geocoding or runtime dependency on an external geography service.

**Gate:** Every reported foreign example becomes `NON_INDIA`; existing Indian and genuinely ambiguous fixtures retain their approved behavior.

## 4. Greenhouse, Ashby, and GoDaddy acquisition fixes

**Reference specs:** `src/job_radar/adapters/families.py`; `src/job_radar/services/engine.py`; `src/job_radar/db/seed.py`.

### Greenhouse

1. Extract and normalize evidence from:
   - `location.name`;
   - `offices[].name` and `offices[].location`;
   - explicit country metadata fields, case-insensitively.
2. Do not treat arbitrary metadata prose as geography.
3. Preserve the exact provider job ID and canonical URL behavior.

### Ashby

1. Extract `address.postalAddress.addressCountry/addressRegion`.
2. Extract bounded `secondaryLocations` geography.
3. Preserve the primary display location and existing IDs/URLs/descriptions.

### GoDaddy

1. Detect the reviewed `country_codes[]=IN` source filter when translating to Greenhouse’s global API.
2. Enforce the filter locally using independently verified structured `Country=India` evidence; do not rely on display-string substring matching.
3. If provider country evidence is missing, preserve the candidate for central classification rather than fabricating India.
4. Record the source-filter and provider-country evidence used for admission.

**Gate:** Live read-only canaries prove provider fields for representative GitLab/GoDaddy/Twilio/Okta/Coinbase and Camunda/Redis jobs, then unchanged canaries pass after implementation.

## 5. Handoff defense and stale-outbox reconciliation

**Reference specs:** `src/job_radar/services/handoff.py`; `src/job_radar/api/v1/jobs.py`; `src/job_radar/services/normalization.py`.

1. Centralize candidate eligibility revalidation so automatic enqueue, manual push, and dispatch use the same logic.
2. Revalidate immediately before external dispatch using persisted raw location plus durable typed provider evidence.
3. Refuse dispatch for `NON_INDIA` even if a stale outbox row exists.
4. Implement an explicit dry-run-first reconciliation command/service that reports:
   - candidate ID, board, URL, raw location;
   - old/new decision and evidence;
   - old eligibility and outbox state;
   - proposed quarantine action.
5. Test an apply mode only against an isolated database. The apply action must quarantine/cancel queued foreign rows without deleting candidates or audit evidence.
6. Do not mutate accepted/imported rows automatically; report them separately for approval-gated external remediation.
7. Do not contact Job Ops in tests or local regression. Use a fail-on-call fake client to prove zero outbound attempts.

**Gate:** A stale queued foreign candidate cannot reach the HTTP client, and isolated reconciliation preserves candidate evidence while neutralizing its queue record.

## 6. Integrated isolated regression

**Reference specs:** all prior phases; affected provider fixtures and live canaries.

1. Use a fresh disposable SQLite database, never the persistent local database.
2. Exercise the real caller-to-database path for:
   - GitLab, GoDaddy, Twilio, Postman, Databricks, Okta, Coinbase;
   - Camunda and Redis.
3. Read back candidate decision, typed evidence, confidence, eligibility, exclusion reason, outbox presence/state, and dispatch-attempt count.
4. Prove all explicit foreign-only examples are persisted for audit but excluded from active handoff.
5. Prove Indian jobs remain eligible and genuine India+foreign alternatives follow approved `CONFLICT` behavior.
6. Run all boards sharing Greenhouse and Ashby adapters as regression controls where practical.
7. Keep scheduler and handoff disabled and assert zero Job Ops attempts.

**Gate:** No affected explicit foreign row is eligible or actively queued; no previously working India case regresses.

## 7. Quality, review, and completion gates

**Reference specs:** entire plan.

1. Run focused location, adapter, normalization, API, and handoff tests.
2. Run the complete Python test suite with `PYTHONPATH` pinned to this exact worktree.
3. Run `git diff --check` and inspect all untracked/generated artifacts.
4. Perform one independent read-only diff review focused on:
   - geography collisions;
   - source-scope precedence;
   - GoDaddy filter preservation;
   - stale outbox bypass;
   - migration safety;
   - raw location and URL truth.
5. Run at most one targeted remediation pass, then rerun focused and full tests.
6. Do not commit, merge, push, deploy, restart production, enable the scheduler/handoff, reset databases, or make a real Job Ops request without a later explicit approval.
7. Update synchronized Markdown/HTML architecture and append-only history only after the implementation is independently verified.

## Acceptance criteria

- Every user-reported explicit foreign-only location is `NON_INDIA` and ineligible.
- Truly ambiguous `UNKNOWN` locations retain the approved eligible policy.
- Genuine India+foreign multi-location jobs retain auditable `CONFLICT` behavior.
- Greenhouse and Ashby structured geography reaches classification and persistence.
- GoDaddy’s reviewed India filter is not lost during endpoint translation.
- Enqueue, manual push, and dispatch share the same current eligibility decision.
- Existing stale queued foreign rows can be identified and safely quarantined through dry-run-first reconciliation.
- Isolated end-to-end evidence shows zero Job Ops calls.
- Full test suite passes from the exact worktree.
- No unauthorized persistent or production side effect occurs.

## Rollback

- Implementation remains uncommitted in the isolated feature worktree until reviewed.
- Source changes can be discarded without affecting canonical `main`.
- Any migration remains unapplied outside disposable test databases.
- Reconciliation apply mode is not run against persistent data without separate approval.
- No Job Ops remediation is attempted automatically.
