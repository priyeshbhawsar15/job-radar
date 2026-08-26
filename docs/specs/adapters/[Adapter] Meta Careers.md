# [Adapter] Meta Careers

- **Family ID:** `meta_careers`
- **Target Boards:** Meta.

---

## 1. Job Listing Acquisition Logic

Meta Careers renders candidate search results dynamically via Playwright Chromium.

- **HTTP Method:** `GET`
- **Search URL:** `https://www.metacareers.com/jobsearch/?sort_by_new=true&offices[0]=Bangalore%2C%20India&offices[1]=Hyderabad%2C%20India`
- **Listing Data Extraction:**
  - Playwright extracts links matching `/profile/job_details/{job_id}`.
  - `sourceJobId`: Extracted requisition ID from URL path.
  - `title`: Requisition title element or `Meta Job Requisition {job_id}` placeholder.
  - `public_apply_url`: `https://www.metacareers.com/profile/job_details/{job_id}`.

---

## 2. Job Details Extraction Logic

### Layer 1: Playwright DOM Parsing
- Navigates Playwright Chromium to the Meta requisition detail link.
- **Selectors:** `div._97w3`, `div._8sel`, or `main`.
- Replaces temporary `Meta Job Requisition {job_id}` placeholder with validated source title once loaded.

### Layer 2: Sanitization
- Removes Facebook/Meta cookie banners, footer links, and legal disclaimers.
