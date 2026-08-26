# [Adapter] Ashby

- **Family ID:** `ashbyhq`
- **Target Boards:** Weave, Aspora, Plane.

---

## 1. Job Listing Acquisition Logic

Ashby boards query the Ashby Public API endpoint.

- **HTTP Method:** `POST` / `GET`
- **Endpoint Pattern:** `https://api.ashbyhq.com/posting-api/job-board/{organization_slug}?includeDetails=true`
- **Listing Data Extraction:**
  - `sourceJobId`: `id`.
  - `title`: `title`.
  - `location`: `locationName`.
  - `department`: `departmentName`.
  - `public_apply_url`: `jobUrl`.

---

## 2. Job Details Extraction Logic

### Layer 1: Inline API Description
- When `includeDetails=true` is requested, Ashby API provides complete job details inline:
  - `description`: `descriptionHtml` / `descriptionPlain`.
  - `employmentType`: `employmentType`.
- Sanitized using `DetailExtractor` HTML cleaner.
