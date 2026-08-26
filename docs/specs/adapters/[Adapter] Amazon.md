# [Adapter] Amazon

- **Family ID:** `amazon_jobs`
- **Target Boards:** Amazon.

---

## 1. Job Listing Acquisition Logic

Amazon Careers queries the official `amazon.jobs` public JSON search API.

- **HTTP Method:** `GET`
- **Endpoint Pattern:** `https://www.amazon.jobs/en/search.json`
- **Query Parameters:**
  - `query_options`: `sort=recent`
  - `category[]`: `software-development`
  - `loc_query`: `India`
  - `result_limit`: `10` or `30`
  - `offset`: `0`
- **Listing Data Extraction:**
  - `sourceJobId`: `id_icims` or `job_path`.
  - `title`: `title`.
  - `location`: `location`.
  - `public_apply_url`: `https://www.amazon.jobs{job_path}`.

---

## 2. Job Details Extraction Logic

### Layer 1: Amazon Search API / Detail API
- `amazon.jobs` JSON payload includes `description` and `basic_qualifications` inline.
- Concatenates `description`, `basic_qualifications`, and `preferred_qualifications`.

### Layer 2: Sanitization
- Strips residual HTML formatting and normalizes Amazon-specific disclaimer blocks.
