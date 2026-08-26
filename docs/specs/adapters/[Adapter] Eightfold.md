# [Adapter] Eightfold

- **Family ID:** `eightfold`
- **Target Boards:** Microsoft, Qualcomm, HP.

---

## 1. Job Listing Acquisition Logic

Eightfold boards utilize the Eightfold PCSX public search API endpoint.

- **HTTP Method:** `GET`
- **Endpoint Pattern:** `https://{tenant_domain}/api/pcsx/search`
- **Query Parameters:**
  - `query`: `software` or configured search keyword.
  - `start`: `0` (offset).
  - `num`: `10` or `20`.
  - `location`: `india` / target country.
  - `sort_by`: `timestamp`.
- **Pagination Strategy:**
  - Increments `start` by batch size (`start += num`).
- **Listing Data Extraction:**
  - `sourceJobId`: `positions[].id` or `positions[].display_job_id`.
  - `title`: `positions[].name`.
  - `location`: `positions[].location`.
  - `public_apply_url`: Constructed as `https://{tenant_domain}/careers/job/{position_id}` or `position_url`.

---

## 2. Job Details Extraction Logic

### Layer 1: Embedded JSON-LD / schema.org Parsing
- Eightfold detail pages embed standard `schema.org/JobPosting` structured JSON-LD within `<script type="application/ld+json">`.
- Extracted Fields:
  - `description`: `JobPosting.description` (HTML or markdown).
  - `title`: `JobPosting.title`.
  - `jobLocation`: `JobPosting.jobLocation.address.addressLocality` / `addressCountry`.
  - `employmentType`: `JobPosting.employmentType`.

### Layer 2: Playwright Chromium Client-Side Rendering
- For SPA detail views (e.g. Microsoft/Qualcomm), Playwright renders the page and waits for selector `div.job-description` or `.position-details`.

### Layer 3: Text Cleaning & Sanitization
- Strips custom keyframes, vendor tracking pixels, and CSS styles.
