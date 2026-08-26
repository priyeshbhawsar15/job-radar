# [Adapter] Apple

- **Family ID:** `apple_jobs`
- **Target Boards:** Apple.

---

## 1. Job Listing Acquisition Logic

Apple Jobs renders search results using dynamic hydration data.

- **HTTP Method:** `GET`
- **Search URL:** `https://jobs.apple.com/en-in/search?search=Software&sort=newest&location=bangalore-metro-BANG`
- **Listing Data Extraction:**
  - Playwright Chromium loads search page and extracts job links matching `/en-in/details/{job_id}/{slug}`.
  - `sourceJobId`: Extracted numeric ID string.
  - `title`: Table row anchor text.
  - `public_apply_url`: `https://jobs.apple.com/en-in/details/{job_id}/{slug}`.

---

## 2. Job Details Extraction Logic

### Layer 1: Structured Window Router Hydration Data (Primary)
- Apple detail pages embed structured router data inside `window.__staticRouterHydrationData`.
- **JSON Path:** Parses `loaderData` for job summary, key qualifications, and description.

### Layer 2: Playwright DOM Fallback
- Selectors: `#jd-job-summary`, `#jd-key-qualifications`, `#jd-description`.
- Filters out non-job routes like `locationPicker`.
