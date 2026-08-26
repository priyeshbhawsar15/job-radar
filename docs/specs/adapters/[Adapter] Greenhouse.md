# [Adapter] Greenhouse

- **Family ID:** `greenhouse`
- **Target Boards:** Cognite, Razorpay, PhonePe.

---

## 1. Job Listing Acquisition Logic

Greenhouse boards utilize the Greenhouse Public Board API or direct JSON endpoints.

- **HTTP Method:** `GET`
- **Endpoint Pattern:** `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`
- **Listing Data Extraction:**
  - `sourceJobId`: `id` (numeric string).
  - `title`: `title`.
  - `location`: `location.name`.
  - `public_apply_url`: `absolute_url`.

---

## 2. Job Details Extraction Logic

### Layer 1: Greenhouse Public API Job Detail Endpoint
- **HTTP Method:** `GET`
- **Endpoint Pattern:** `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}`
- **Extracted Fields:**
  - `description`: `content` (HTML string).
  - `title`: `title`.
  - `location`: `location.name`.

### Layer 2: Sanitization & HTML Cleaning
- Cleaned via `BeautifulSoup` text sanitizer (`DetailExtractor`).
- Strips `<script>`, `<style>`, and tracking pixels.
