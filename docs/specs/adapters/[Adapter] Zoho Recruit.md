# [Adapter] Zoho Recruit

- **Family ID:** `zoho`
- **Target Boards:** Wynploy, Zoho.

---

## 1. Job Listing Acquisition Logic

Zoho Recruit embeds positions via iframe or API endpoints.

- **HTTP Method:** `GET`
- **Endpoint Pattern:** `https://{tenant_domain}.zohorecruit.in/jobs/Careers` or Zoho Recruit embeds.
- **Listing Data Extraction:**
  - `sourceJobId`: `rec_job_id` or job opening ID.
  - `title`: `Job_Title`.
  - `public_apply_url`: Direct job opening detail page link.

---

## 2. Job Details Extraction Logic

### Layer 1: Playwright Client-Side DOM Hydration
- Zoho Recruit uses dynamic client-side rendering (`div.cw-jobdescription`).
- Static HTTP requests return only an unhydrated shell; requires Playwright Chromium with explicit waiting for `.cw-jobdescription` selector.

### Layer 2: Sanitization
- Removes script blocks and cleans embedded HTML formatting.
