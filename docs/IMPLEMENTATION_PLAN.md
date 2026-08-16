---
type: "plan"
area: "project"
project: "Job Radar"
status: "review-gated"
tags:
  - "project"
  - "plan"
  - "implementation"
parent: "[[20 Projects/Job Radar/Project]]"
---

# Job Radar — Implementation Plan

> **Instructions for Coding Agent:** This file is your main execution plan. Follow the phases in order. For detailed specs on schema, endpoints, UI visual rules, and ATS adapters, consult the reference documents indexed in **Section 0** below.

---

## 0. Reference Specifications & Document Index

Every phase in this plan directly implements a component of the approved system design and visual prototype. Refer to these files in the repository for detailed specifications:

| Document | Path in Repository | What it Specifies | Primary Use in Implementation |
|---|---|---|---|
| **System Design** | `SYSTEM_DESIGN.md` (or `docs/SYSTEM_DESIGN.md`) | Database schema, SQLAlchemy entities, API contracts (`/api/v1/*`), state machines, auth headers, error taxonomy, and retention rules. | **Phases 1, 3, 4, 5, 6, 7** |
| **System Architecture Diagram** | `docs/system-design.html` (or `ui-prototype/system-design.html`) | Interactive SVG component architecture map, tech stack definitions, and data flow bounds. | **Phases 1, 3, 4, 7** |
| **UI Mockup Prototype** | `ui-prototype/index.html` | Canonical HTML/CSS/JS cockpit mock, layout structures, visual state rhythms, and mock payload views. | **Phase 2** |
| **UI Visual Design** | `docs/UI_DESIGN.md` | Color palette (ink/navy, warm surfaces, teal/amber/red states), typography, component rhythm, and responsive viewports (1440px / 390px). | **Phase 2** |
| **Adapter Research** | `docs/ADAPTER_RESEARCH.md` | 38 company board classifications, shared ATS families (`lever`, `amazon`, `eightfold`, `avature`, `highradius`), API contracts, and extraction strategies. | **Phase 3** |
| **Product Requirements** | `docs/PRD.md` | High-level business rules, functional scope, safety gates, and homelab operational requirements. | **All Phases** |

---

## 1. Overview & Phasing Strategy

The implementation is broken into **7 modular, testable phases**. Each phase produces verified artifacts, unit/integration test coverage, and clear rollback boundaries before proceeding to the next.

| Phase | Scope | Primary Deliverable | Primary Stack | Verification Gate |
|---|---|---|---|---|
| **Phase 1** | Backend Core & Database | FastAPI app skeleton, SQLAlchemy 2.0 models, Alembic migrations | Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL | pytest schema & state-machine tests pass |
| **Phase 2** | React Operations Cockpit | Vite + React + Tailwind SPA, UI routes, SSE client, dark/light theme | React, Vite, Tailwind CSS, Lucide | Build passes, visual verification, static asset serving via FastAPI |
| **Phase 3** | Reviewed Adapter Registry | Typed adapter interface, 5 initial low-risk adapters, Playwright client | Python, Async HTTP, Playwright client | Adapter contract tests pass, Playwright client typed error handling |
| **Phase 4** | Execution & Scheduler Engine | APScheduler integration, worker lease fencing, auto-pause logic | APScheduler, PostgreSQL `FOR UPDATE SKIP LOCKED` | Execution state-machine & concurrency tests pass |
| **Phase 5** | Normalization & Retention Purger | Candidate deduplication ledger, canonicalization, 7-day retention purger | Python, SQL range purges | Candidate identity deduplication & purge boundary tests pass |
| **Phase 6** | Transactional Outbox & Job Ops | Handoff outbox queue, HTTP Basic Auth client (`handoff_enabled: false`) | Python async HTTP client | Outbox idempotency & receipt validation tests pass |
| **Phase 7** | Production Deployment | Docker Compose on The Shell, Caddy reverse-proxy wiring, verification | Docker, Caddy, The Shell homelab | 5-board initial tick verification, zero secret leaks, docs update |

---

## 2. Phase Detailed Breakdowns

### Phase 1: Backend Core & Database Models
* **Reference Specs:** `SYSTEM_DESIGN.md` Section 3 (Components), Section 5 (API Surface), Section 6 (Data Model & Entities).
* **Objective:** Establish the Python FastAPI application structure, PostgreSQL database connection pooling, SQLAlchemy 2.0 async models, and Alembic migrations.
* **Tasks:**
  1. Initialize Python project structure under `/home/priyesh/Work/job-radar` with `pyproject.toml` or `requirements.txt`.
  2. Implement database models:
     - `boards`, `board_revisions`
     - `run_requests`, `execution_attempts`
     - `pipeline_runs`, `board_runs`
     - `candidate_jobs`, `run_candidates`
     - `handoff_outbox`, `handoff_attempts`
     - `audit_events`
  3. Configure Alembic migration scripts and forward-only migration gates.
  4. Write core CRUD repositories and database health check endpoints (`GET /health`, `GET /ready`).
* **Verification:** `pytest` database suite verifying schema creation, constraints, FK cascade rules, and readiness checks against local PostgreSQL instance.

---

### Phase 2: Modern React Operations Cockpit (UI)
* **Reference Specs:** `ui-prototype/index.html` (Full HTML/JS mock), `docs/UI_DESIGN.md` (Design System), `SYSTEM_DESIGN.md` Section 5 (API Routes & SSE).
* **Objective:** Replace the static HTML prototype with a production Vite + React SPA served directly by FastAPI's static mount.
* **Tasks:**
  1. Initialize Vite + React + Tailwind CSS project in `/ui` directory.
  2. Build reusable UI components (cards, tables, status badges, modal drawers, theme toggle).
  3. Implement client-side routing matching UI Design:
     - Dashboard overview (`/`)
     - Pipeline Runs list & detail (`/runs`, `/runs/:id`)
     - Boards index & detail (`/boards`, `/boards/:id`)
     - Board Configuration edit view (`/boards/:id/config`)
     - Extracted Jobs Explorer & modal detail (`/jobs`, `/jobs/:id`)
  4. Connect real-time Server-Sent Events (SSE) hook (`GET /api/v1/stream`) for live run updates.
  5. Configure Vite build output to `/dist` and mount in FastAPI app (`app.mount("/", StaticFiles(directory="dist", html=True))`).
* **Verification:** `npm run build`, visual verification in Chrome/Firefox, responsive 1440px desktop & 390px mobile viewport check with zero horizontal scroll.

---

### Phase 3: Reviewed Adapter Registry & Private Playwright Boundary
* **Reference Specs:** `docs/ADAPTER_RESEARCH.md` (38 board strategies & API schemas), `SYSTEM_DESIGN.md` Section 3 (Adapter Registry & Browser Client), Section 8 (Security).
* **Objective:** Build the typed board acquisition framework and the initial 5 low-risk board adapters.
* **Tasks:**
  1. Implement typed `BoardAdapter` abstract base class and extraction models (`ListingResult`, `CandidateRecord`).
  2. Implement private Playwright HTTP/WebSocket client communicating with `job-radar-browser` container on The Shell (`127.0.0.1:3013`).
  3. Implement initial 5 low-risk adapters:
     - `lever`: Coupa (`https://api.lever.co/v0/postings/coupa?mode=json`)
     - `amazon_jobs`: Amazon (`/en/search.json`)
     - `eightfold`: Qualcomm (`/api/pcsx/search`)
     - `avature`: Tesco (`SearchJobs`/`JobDetail`)
     - `highradius`: DOM-first route (`/about/careers-list/?gh_jid=`)
  4. Enforce strict outcome taxonomy (`success`, `empty_verified`, `partial`, `challenge`, `timeout`, `parser_contract`, `provider_failure`).
* **Verification:** Mock response fixture tests for all 5 adapters; typed error handling tests ensuring raw HTML, cookies, or tokens are never exposed.

---

### Phase 4: In-Process APScheduler & Stateful Execution Engine
* **Reference Specs:** `SYSTEM_DESIGN.md` Section 4 (Sequence), Section 6 (Entities), Section 7 (State Machines & Transition Tables).
* **Objective:** Build the worker engine that runs scheduled and manual board acquisition runs safely without overlap.
* **Tasks:**
  1. Integrate APScheduler in-process with FastAPI lifecycle.
  2. Implement database row locking (`FOR UPDATE SKIP LOCKED`) for worker execution claims and fencing generations.
  3. Implement state machine transitions:
     - Board state: `draft` → `reviewed` → `enabled` → `paused` → `retired`
     - Execution lifecycle: `requested` → `admitted` → `running` → `completed` / `partial` / `failed` / `cancelled` / `expired`
  4. Implement auto-pause logic: pause board automatically after **3 consecutive `parser_contract` failures**.
* **Verification:** Unit tests for concurrent run requests, fencing lease expiration, crash reaping, and auto-pause triggering.

---

### Phase 5: Normalization, Deduplication & Retention Purger
* **Reference Specs:** `SYSTEM_DESIGN.md` Section 3 (Policy & Normalization), Section 6 (Candidate Jobs & 7-Day Purge Rules).
* **Objective:** Deduplicate candidate jobs safely across repeat scans and automatically purge expired 7-day run telemetry.
* **Tasks:**
  1. Implement canonical URL normalizer (HTTPS enforcement, lowercasing, query parameter stripping).
  2. Implement candidate identity hashing (`SHA-256(canonical_url + board_id)`) to prevent duplicate job insertion.
  3. Build 7-day retention background purger task:
     - Delete `execution_attempts`, `pipeline_runs`, and `board_runs` records older than 7 days based on `terminal_at`.
     - Preserve durable `candidate_jobs`, `handoff_outbox`, and `audit_events`.
* **Verification:** Test duplicate job ingestion attempts (upsert idempotency check) and retention purge SQL logic.

---

### Phase 6: Transactional Outbox & Job Ops Client
* **Reference Specs:** `SYSTEM_DESIGN.md` Section 4 (Outbox Flow), Section 6 (Handoff Entities), Section 7 (Handoff Lifecycle).
* **Objective:** Queue discovered jobs in a transactional outbox and support HTTP Basic Auth handoff.
* **Tasks:**
  1. Implement `handoff_outbox` transactional queue writer inside the candidate discovery pipeline.
  2. Build async HTTP Job Ops client with HTTP Basic Auth support (`JOBOPS_USERNAME`, `JOBOPS_PASSWORD`).
  3. Keep outbox handoff disabled by default (`handoff_enabled: false`) until explicitly enabled via config.
  4. Implement outbox lifecycle (`queued` → `dispatching` → `accepted` / `held` / `rejected` / `uncertain`).
* **Verification:** Outbox queueing tests, receipt verification tests, and mock HTTP Basic Auth dispatch tests.

---

### Phase 7: Production Deployment & Verification on The Shell
* **Reference Specs:** `SYSTEM_DESIGN.md` Section 10 (Deployment & Environments), `docs/PRD.md`.
* **Objective:** Containerize Job Radar, deploy on The Shell homelab host, wire reverse proxy, and run the initial production tick.
* **Tasks:**
  1. Write production `Dockerfile` (multi-stage build with Python 3.12 + Node static build).
  2. Configure `docker-compose.yml` on The Shell linking PostgreSQL and `job-radar-browser`.
  3. Configure environment file (`.env`) with secrets and database credentials.
  4. Configure Caddy reverse proxy on The Shell with `X-Remote-User` and `X-Remote-Role` auth headers.
  5. Deploy and execute the initial 5-board acquisition tick in production.
  6. Update homelab documentation (`/home/hermes/homelab_overview.md` and Obsidian `30 Homelab/Services/AI and Work/Job Radar`).
* **Verification:** Production container health check, Caddy endpoint accessibility, 5-board initial run tick review, and zero secret leaks.

---

## 3. Risk & Mitigation Matrix

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| **Upstream Board DOM/API Change** | Medium | Auto-pause after 3 `parser_contract` failures; safe error codes prevent pipeline crash. |
| **Playwright Browser Crash** | High | `job-radar-browser` runs in isolated container with `unless-stopped` restart; worker catches client timeout. |
| **Database Lock Contention** | Medium | Row-level `SKIP LOCKED` lease claims and bounded SQLAlchemy connection pool. |
| **Double Posting to Job Ops** | High | Transactional outbox with stable candidate identity keys and `uncertain` reconciliation state. |

---

## 4. Rollback & Safety Gates

1. **Code Rollback:** Git feature branch workflow on `fresh-job-radar`; clean commits per phase.
2. **Database Rollback:** Alembic down-migrations tested for every migration script.
3. **Deployment Safety:** Production deployment remains disabled until explicit authorization after Phase 6 testing.

---

## Explicit Non-Actions

This document does **not** authorize code execution, database creation, source enablement, live board scraping, Job Ops API calls, or production deployment. Implementation begins only after Priyesh explicitly authorizes Phase 1.
