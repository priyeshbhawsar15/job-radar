# [Adapter] Google Careers

- **Family ID:** `google_careers`
- **Target Boards:** Google.

---

## 1. Job Listing Acquisition Logic

Google Careers uses Playwright Chromium DOM extraction over Google's public search URL.

- **HTTP Method:** `GET`
- **Search URL:** `https://www.google.com/about/careers/applications/jobs/results?location=India&q=%22Software%20Engineer%22&sort_by=date`
- **Listing Data Extraction:**
  - Playwright renders listing elements `li.aria-posinset` or `a[href*="/jobs/results/"]`.
  - `sourceJobId`: Extracted numeric ID from URL pattern `/jobs/results/{job_id}-{slug}`.
  - `title`: Job card heading element text.
  - `public_apply_url`: `https://www.google.com/about/careers/applications/jobs/results/{job_id}`.

---

## 2. Job Details Extraction Logic

### Layer 1: Playwright DOM & Meta Description Extraction
- Navigates Playwright Chromium to the job URL.
- **Selectors:** `div[role="main"]`, `section.job-description`, or `<meta name="description">`.

### Layer 2: Job Ops Inference Fallback
- If Playwright detail extraction returns unhydrated shell, text is sanitized and dispatched to Job Ops `/api/manual-jobs/infer` for AI summary extraction.
