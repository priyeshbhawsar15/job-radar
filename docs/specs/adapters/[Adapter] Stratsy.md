# [Adapter] Stratsy

- **Family ID:** `stratsy`
- **Target Boards:** RBCTech.

---

## 1. Job Listing Acquisition Logic

Stratsy / AlignCRM platforms expose public REST opportunities APIs.

- **HTTP Method:** `GET`
- **Endpoint Pattern:** `https://{tenant_subdomain}.stratsy.us/api/public/opportunities`
- **Listing Data Extraction:**
  - `sourceJobId`: `id` or `opportunity_id`.
  - `title`: `title` / `name`.
  - `location`: `location`.
  - `public_apply_url`: Constructed job detail link.

---

## 2. Job Details Extraction Logic

### Layer 1: Public Opportunities API
- Response JSON contains complete job posting attributes:
  - `description`: `description` (HTML / plain text).
  - `requirements`: `requirements`.
- Sanitized using standard `DetailExtractor` HTML text cleaner.
