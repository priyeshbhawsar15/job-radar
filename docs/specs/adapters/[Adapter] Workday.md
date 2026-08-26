# [Adapter] Workday

- **Family ID:** `workday`
- **Target Boards:** Adobe, Walmart, Cisco, Solera, Motorola Solutions, eBay, EisnerAmper, JioStar, Thomson Reuters, TP, JLL, SOTI, Amgen.

---

## 1. Job Listing Acquisition Logic

Workday candidate discovery uses direct POST calls to Workday's Customer Experience Search (`CXS`) REST API.

- **HTTP Method:** `POST`
- **Endpoint Pattern:** `https://{tenant_domain}/wday/cxs/{tenant_name}/{site_name}/jobs`
- **Headers:**
  - `Accept: application/json`
  - `Content-Type: application/json`
- **Payload Structure:**
  ```json
  {
    "appliedFacets": {},
    "limit": 20,
    "offset": 0,
    "searchText": ""
  }
  ```
- **Pagination Strategy:**
  - Pagination increments `offset` by 20 (`offset = page_index * 20`) up to `max_pages` (default: 3 pages = 60 listings).
  - Stops when returned `jobPostings` list is empty or `total` count is reached.
- **Listing Data Extraction:**
  - `sourceJobId`: Extracted from `bulletFields[0]` or regex pattern in candidate URL (`R\d+` or `\d{6,}`).
  - `title`: `title` field.
  - `public_apply_url`: Appends `externalPath` to base board domain (e.g. `https://{tenant_domain}/en-US/{site_name}{externalPath}`). Preserves original query parameters.
  - `location`: Parsed from `locationsText` or path parameters (`/job/{city}/...`).

---

## 2. Job Details Extraction Logic

Workday details use a layered extraction pipeline to get clean job descriptions.

### Layer 1: CXS Detail REST API (Primary)
- **HTTP Method:** `GET`
- **Endpoint Pattern:** `https://{tenant_domain}/wday/cxs/{tenant_name}/{site_name}/jobPostingInfo/{job_id}`
- **Headers:** `Accept: application/json`
- **Extracted Fields:**
  - `jobDescription`: `jobPostingInfo.jobDescription` (HTML string).
  - `location`: `jobPostingInfo.location`.
  - `title`: `jobPostingInfo.title`.
  - `posted_date`: `jobPostingInfo.postedOn`.

### Layer 2: Playwright Chromium DOM Fallback (Secondary)
- If CXS detail API returns 404 or missing description, navigates Playwright Chromium to the public URL.
- **DOM Selector:** `[data-automation-id="jobPostingDescription"]`, `div.section-content`, or `main`.

### Layer 3: Text Cleaning & Sanitization
- Runs HTML text through `BeautifulSoup` sanitizer (`DetailExtractor`).
- Removes `<script>`, `<style>`, `<nav>`, `<footer>`, and raw CSS keyframe code.
- Caps cleaned description at 40,000 characters.
