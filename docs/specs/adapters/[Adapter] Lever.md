# [Adapter] Lever

- **Family ID:** `lever`
- **Target Boards:** Resilinc, Paytm.

---

## 1. Job Listing Acquisition Logic

Lever platforms utilize Lever's Public Postings API.

- **HTTP Method:** `GET`
- **Endpoint Pattern:** `https://api.lever.co/v0/postings/{account_slug}?mode=json`
- **Location Filtering:**
  - Fetches all postings for the tenant account, then locally filters jobs matching target locations (e.g. `India`, `Pune`, `Hyderabad`).
- **Listing Data Extraction:**
  - `sourceJobId`: `id` (GUID string).
  - `title`: `text`.
  - `location`: `categories.location`.
  - `public_apply_url`: `hostedUrl` or `applyUrl`.

---

## 2. Job Details Extraction Logic

### Layer 1: Lever Public API Response
- Lever's postings endpoint includes full description fields inline:
  - `description`: `content.descriptionHtml` or `description`.
  - `lists`: Array of responsibility/qualification list items.
- Concatenates description text and list items.

### Layer 2: Sanitization & HTML Cleaning
- Strips custom styles and converts HTML lists to clean markdown text.
