# [Adapter] Avature

- **Family ID:** `avature`
- **Target Boards:** Tesco.

---

## 1. Job Listing Acquisition Logic

Avature portals use client-rendered search forms and dynamic HTML portal rendering.

- **HTTP Method:** `GET` / `POST`
- **Endpoint Pattern:** `https://{tenant_domain}/careers/SearchJobs/`
- **Parameters:**
  - `jobSort`: `postedDate`
  - `jobSortDirection`: `ASC` / `DESC`
  - `listFilterMode`: `1`
- **Listing Data Extraction:**
  - `sourceJobId`: Extracted from URL path `/careers/JobDetail/{slug}/{job_id}`.
  - `title`: Job link link text or heading element.
  - `public_apply_url`: Canonical URL path `https://{tenant_domain}/careers/JobDetail/{slug}/{job_id}`.

---

## 2. Job Details Extraction Logic

### Layer 1: Playwright DOM & Meta Description Extraction
- Renders the detail page using Playwright Chromium.
- **Selectors:** `.job-detail-description`, `div.avature-job-details`, or `<meta name="description">`.

### Layer 2: Sanitization
- Cleans HTML markup and removes site navigation/header footers.
