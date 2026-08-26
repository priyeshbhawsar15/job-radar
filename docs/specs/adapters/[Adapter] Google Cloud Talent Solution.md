# [Adapter] Google Cloud Talent Solution

- **Family ID:** `google_cloud_talent_solution`
- **Target Boards:** Vanguard.

---

## 1. Job Listing Acquisition Logic

Google Cloud Talent Solution (`m-cloud`) powers career search for companies like Vanguard.

- **HTTP Method:** `POST` / `GET`
- **Endpoint Pattern:** `https://jobsapi-google.m-cloud.io/api/job/search`
- **Listing Data Extraction:**
  - `sourceJobId`: `reqId` or `job.id`.
  - `title`: `job.title`.
  - `location`: `job.location`.
  - `public_apply_url`: `https://www.vanguardjobs.com/job/{job_id}/{slug}`.

---

## 2. Job Details Extraction Logic

### Layer 1: Google Cloud Talent API / JSON-LD
- Endpoint provides full `description` in HTML/plain text format.

### Layer 2: Playwright DOM Fallback
- Selectors: `div.job-description`, `.details-section`.
