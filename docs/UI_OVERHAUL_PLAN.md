---
type: "plan"
area: "project"
project: "Job Radar"
status: "active"
tags:
  - "project"
  - "plan"
  - "ui"
parent: "[[20 Projects/Job Radar/Project]]"
---

# Job Radar — UI Overhaul & Feature Completeness Implementation Plan

> **Goal:** Upgrade the React application in `ui/src/` to 100% feature completeness with the original UI prototype (`ui-prototype/index.html`), restoring all 8 views, detail routes, filters, safe Playwright audit logs, formatted JSON payload viewers, and mobile navigation overlays.

---

## 1. Information Architecture & Routing Specification

The application MUST implement full routing for all 8 views defined in the original UI design prototype:

| Route Path | Component / Page | Purpose & Key Features |
|---|---|---|
| `/runs` | `Runs.tsx` | Pipeline Run History list with top summary metrics bar (Retained runs, Extracted count, Accepted count, Held count, Next purge indicator) & clickable run cards. |
| `/runs/:id` | `RunDetail.tsx` | **Dedicated Pipeline Run Detail View.** Displays run ID, timestamp, duration, board contribution grid (cards with state badges), and extracted jobs list for that run. |
| `/boards` | `Boards.tsx` | Board Inventory Card Grid. Cards showing adapter, name, URL, observed runs, completion %, missing mandatory fields tag, or next due time. |
| `/boards/:id` | `BoardDetail.tsx` | **Dedicated Board Detail View.** Displays board KV config, Missing Mandatory Fields alert box, Run stats summary metrics, and Recent board runs list with links to audit logs. |
| `/boards/:id/config` | `BoardConfig.tsx` | Board Configuration Edit View with breadcrumbs, form fields, Review Gate warning box, and **Required Configuration Status Checklist (6 typed field badges)**. |
| `/board-runs/:id` | `BoardRunLog.tsx` | **Dedicated Safe Audit Log Page.** Reusable audit detail view displaying safe Playwright execution timeline: `BoardRunRequest issued`, `Playwright request admitted`, `Playwright result received`, `Run finalized`. |
| `/jobs` | `Jobs.tsx` | Extracted Jobs Explorer with Search input, **Date Sort Dropdown (`newest`/`oldest`)**, Board filter, **Job Ops Status Filter (`all`/`accepted`/`held`)**, and clickable job cards. |
| `/jobs/:id` | `JobDetail.tsx` | **Dedicated Job Candidate Detail View.** Displays candidate status badge, full normalized fields list, and **Syntax-Highlighted Formatted JSON `Job Ops Payload` Viewer (`pre` block)**. |

---

## 2. Step-by-Step Task Breakdown

### Task 1: Client-Side Routing & Navigation Setup
- Update `ui/src/App.tsx` and `ui/src/main.tsx` to handle client-side hash routing (`#/runs`, `#/runs/:id`, `#/boards`, `#/boards/:id`, `#/boards/:id/config`, `#/board-runs/:id`, `#/jobs`, `#/jobs/:id`).
- Add dynamic breadcrumbs to `Header.tsx` (`Runs / RUN-1042`, `Boards / Stripe / Configuration`, `Jobs / Senior Software Engineer`).

### Task 2: Implement Job Detail View (`ui/src/pages/JobDetail.tsx`)
- Display job header: Title, Company, Location, Candidate Status badge.
- Render Key-Value pairs: Apply URL link (opens in new tab), Posting Date, Employment Type, Department, Board ID, Source Stable ID, Revision ID, Discovered At, Normalization state, Eligibility state.
- Render formatted JSON `Job Ops Payload` in a styled `<pre class="code payload">` block with copy button.

### Task 3: Implement Board Detail View (`ui/src/pages/BoardDetail.tsx`)
- Display board header with adapter tag and current status badge.
- Render Board Configuration KV card: Public listing link, Adapter family, Current revision ID, Next admission time.
- Render Mandatory Configuration incomplete alert box when `missing` fields exist.
- Render Run Stats metrics grid (Retained runs, Completion %, Adapter, State).
- Render Recent Board Runs list with direct links to `/board-runs/:id`.

### Task 4: Implement Board-Run Safe Audit Timeline (`ui/src/pages/BoardRunLog.tsx`)
- Display board run summary card (Board name, outcome, revision, pipeline run ID, safe outcome class).
- Render Safe Audit Boundary banner (confirming no raw HTML, cookies, tokens, or browser exceptions are exposed).
- Render chronological Execution Timeline with 4 safe event cards:
  1. `BoardRunRequest issued` (capability ID, board ID, revision, time/page/byte limits).
  2. `Playwright request admitted` (safe response state, diagnostic code).
  3. `Playwright result received` (outcome, duration ms, candidate count, safe diagnostic code).
  4. `Run finalized` (candidate policy & eligibility decision).

### Task 5: Implement Pipeline Run Detail View (`ui/src/pages/RunDetail.tsx`)
- Display run summary: Run ID, trigger origin, duration, status badge.
- Render Run Metrics bar (Board outcomes completed/total, Extracted count, Job Ops accepted count, Held count).
- Render Board Runs grid with cards per board.
- Render Extracted Jobs stack for this specific run.

### Task 6: Refine Jobs Explorer Filters (`ui/src/pages/Jobs.tsx`)
- Add **Date Sort Dropdown** (`Newest first` / `Oldest first`).
- Add **Job Ops Status Filter** (`All outcomes`, `Accepted`, `Held`).
- Make job cards clickable to navigate to `/jobs/:id`.

### Task 7: Refine Board Config Page (`ui/src/pages/BoardConfig.tsx`)
- Add **Required Configuration Status Matrix** (6 field status badges: adapter family, public listing link, detail route allowlist, pagination cap, readiness descriptor, resource policy).
- Add Review Gate warning banner and breadcrumb navigation.

### Task 8: Shell Polish & UI Aesthetics
- Add **Radar-like outlined brand mark with quiet status pulse** in `Sidebar.tsx`.
- Implement collapsible rail state toggle persisted in `localStorage`.
- Implement mobile drawer navigation overlay.

### Task 9: Asset Build & Playwright Automated Verification
- Run `npm run build` in `ui/` to output bundle to `src/job_radar/static/`.
- Launch app server on `http://localhost:3000`.
- Execute automated browser testing (using Playwright / Playwright MCP) to click through all 8 pages, verify filter behavior, inspect JSON payload viewers, trigger a run, and capture desktop & mobile screenshots.

---

## 3. Playwright Acceptance Criteria

1. **Route Test:** Navigating to `#/runs`, `#/runs/1`, `#/boards`, `#/boards/board-coupa-01`, `#/boards/board-coupa-01/config`, `#/board-runs/br-1`, `#/jobs`, and `#/jobs/job-1` renders the correct view without blank screens or console errors.
2. **Job Detail Test:** Clicking a job on `#/jobs` opens `#/jobs/:id`, displays all normalized KV fields, and renders formatted JSON in `<pre class="code payload">`.
3. **Board Detail Test:** Clicking a board on `#/boards` opens `#/boards/:id`, displaying board config, missing fields alert, and recent runs.
4. **Safe Audit Log Test:** Clicking a board run opens `#/board-runs/:id`, rendering the safe 4-stage Playwright timeline.
5. **Filter Test:** Sorting by date (oldest first / newest first) and filtering by Job Ops status (`accepted` / `held`) updates the jobs list dynamically.
