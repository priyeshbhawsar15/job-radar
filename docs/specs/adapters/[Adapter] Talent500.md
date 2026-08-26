# [Adapter] Talent500

- **Family ID:** `talent500`
- **Target Boards:** TMUS Global Solutions, Best Buy, Evernorth, Marriott Tech Accelerator, McDonalds in India.

---

## 1. Job Listing Acquisition Logic

Talent500 platforms use a public JSON search API endpoint on `prod-warmachine.talent500.co`.

- **HTTP Method:** `GET`
- **Endpoint Pattern:** `https://prod-warmachine.talent500.co/api/v3/jobs/search/`
- **Parameters:**
  - `company`: Target company name (e.g. `TMUS Global Solutions`, `Best Buy`, `Evernorth`, `Marriott Tech Accelerator`, `McDonalds in India`).
  - `sort_by_created_date`: `1` (newest first).
  - `offset`: Offset integer for pagination (e.g. `0`, `20`, `40`).
  - `limit`: Page limit integer (default `20`).
  - `is_leadership_job`: `false`.
- **Response Structure:**
  - `total`: Total available jobs count across all pages.
  - `data`: Array of job objects containing stable `id` (UUID), `job_code`, `slug`, `title`, `company` object (`name`, `slug`), `location` (city), `country` object (`name`), `employment_type`, and `job_category` / `role_category`.
- **Listing Data Extraction:**
  - `id`: Talent500 UUID (e.g. `5c076879-8949-4fa2-a3dd-a6f3a9ba15bc`).
  - `title`: `title` or `title_alias_1`.
  - `company`: `company.name` (e.g. `TMUS Global Solutions`).
  - `location`: Combination of city and country name (`"Hyderabad, India"`).
  - `canonical_url`: `https://talent500.com/jobs/{company.slug}/{job.slug}/`.

---

## 2. Job Details Extraction Logic

### Layer 1: Talent500 Public Detail API
- **Endpoint:** `GET https://prod-warmachine.talent500.co/api/jobs/{slug}/`
- **Extracted Fields:**
  - `description`: HTML job description containing responsibilities, qualifications, and skills.
  - `title`: `title` or `title_alias_1`.
  - `location`: City and country object (`"Hyderabad, India"`).
  - `employment_type`: `employment_type` (e.g. `Full-time`).
  - `department`: `category` / `role_category` / `job_function`.

### Layer 2: Text Cleaning & Validation
- Converts HTML description to clean plain text via HTML unescaping, script/style tag stripping, and structure preservation.
- Verifies description semantic quality (valid length and indicator keywords).
