# [Adapter] Phenom

- **Family ID:** `phenom`
- **Target Boards:** Philips, Ameriprise.

---

## 1. Job Listing Acquisition Logic

Phenom People platforms use public API endpoints or client-side rendered search pages (`/phb/`).

- **HTTP Method:** `GET` / `POST`
- **Endpoint Pattern:** `https://{tenant_domain}/widgets/search-jobs-result` or direct search page rendering.
- **Parameters:**
  - `keyword`: `Software` / `Technology`.
  - `location`: Target region (e.g. `India`).
- **Listing Data Extraction:**
  - `sourceJobId`: `refNum` or `reqId`.
  - `title`: `title`.
  - `public_apply_url`: Canonical URL path (e.g. `/in/en/job/{id}/{slug}` or `/search-jobs/{id}/{slug}/`).

---

## 2. Job Details Extraction Logic

### Layer 1: Phenom Details API / Hydration State
- Queries Phenom job details endpoint or parses `window.phApp.pageData.jobDetail`.
- **Extracted Fields:**
  - `description`: `description` / `jobDescription` (HTML text).
  - `location`: `city`, `state`, `country`.
  - `category`: `category` / `department`.

### Layer 2: Playwright DOM Fallback
- Rendered Playwright Chromium extraction via selector `.job-description`, `.ph-job-description`, or `[data-ph-id]`.

### Layer 3: Text Cleaning
- Strips navigation headers, cookie consent banners, and social share widgets.
