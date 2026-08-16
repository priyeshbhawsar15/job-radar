# Job Ops Intake API & Detail Enrichment Implementation Plan

## 1. Objective & Requirements
Upgrade Job Radar to fetch full job detail content (description, company_name, salary range/currency) from candidate apply links (public_apply_url), store enriched metadata in the database, update the operator UI views, and construct the rich Job Ops Intake API dispatch payload.

## 2. Architecture & Pipeline Sequence
Listing Acquisition -> Candidate Link Discovery -> Detail Extractor Service (Fetch & Parse Full HTML DOM) -> Normalize Description & Salary -> Update CandidateJob Entity -> Construct Rich Job Ops Payload -> Handoff Outbox

## 3. Rich Job Ops Intake API Payload Schema
{
  "idempotency_reference": "jr:cand-12345:policy-11",
  "title": "Software Engineer III",
  "company_name": "Walmart",
  "location": "Chennai, India",
  "apply_url": "https://walmart.wd504.myworkdayjobs.com/...",
  "description": "Full job description text in clean markdown format...",
  "salary": {
    "raw": "INR 2,000,000 - INR 3,000,000 per year",
    "min": 2000000,
    "max": 3000000,
    "currency": "INR"
  },
  "employment_type": "Full-time",
  "department": "Engineering",
  "posting_date": "2026-08-16",
  "source_board": "board-walmart"
}

## 4. Step-by-Step Implementation Sequence
1. DB Schema & Models (models/candidate.py & seed.py):
   - Add columns: description (TEXT), salary_raw (VARCHAR), salary_min (BIGINT), salary_max (BIGINT), salary_currency (VARCHAR).
2. Detail Extractor Service (services/detail_extractor.py):
   - Implement DetailExtractor service.
   - Use BrowserServiceClient to fetch raw HTML DOM for public_apply_url.
   - Parse job description text/markdown, salary range/currency patterns (INR, USD, salary, compensation), employment type, and department.
3. Execution Engine & Handoff Service (services/engine.py & services/handoff.py):
   - Integrate detail_extractor.enrich_candidate_job into execution_engine.execute_board_run.
   - Build rich JobOpsIntakePayload in HandoffService.build_payload.
4. UI Cockpit Updates (JobDetail.tsx, Jobs.tsx, JobItem type):
   - Render job description text/markdown in candidate details.
   - Display salary badge if available.
   - Update syntax-highlighted Job Ops JSON payload viewer in JobDetail.tsx.
5. Verification & Testing:
   - Run end-to-end extraction across job boards to verify that description, company_name, salary, and apply_url are properly extracted and presented.
