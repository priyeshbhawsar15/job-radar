# [Adapter] Oracle HCM

- **Family ID:** `oracle`
- **Target Boards:** Oracle, JPMC, Amex.

---

## 1. Job Listing Acquisition Logic

Oracle HCM Candidate Experience (`CX`) uses Oracle Recruiting REST Services or Fusion Direct Listing.

- **HTTP Method:** `GET` / `POST`
- **REST Endpoint Pattern:** `https://{tenant_domain}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails`
- **Parameters:**
  - `finder`: `ReqBidsWithKeyword;siteNumber={site_id},keyword={query},locationId={loc_id}`
- **Fusion Direct Listing Transport:**
  - For configured sites (e.g. `CX_1001` for JPMC, `CX_1` for Amex), queries candidate experience API directly.
- **Listing Data Extraction:**
  - `sourceJobId`: `Id` or `JobRequisitionId`.
  - `title`: `Title`.
  - `public_apply_url`: Constructed canonical URL `https://{tenant_domain}/hcmUI/CandidateExperience/en/sites/{site_id}/job/{Id}/`.

---

## 2. Job Details Extraction Logic

### Layer 1: Oracle HCM Recruiting REST API (Primary)
- **HTTP Method:** `GET`
- **Endpoint:** `https://{tenant_domain}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?expand=all&onlyData=true&finder=ById;Id="{PUBLIC_JOB_ID}"`
- **Extracted Fields:**
  - `description`: Concatenation of `ExternalDescriptionStr`, `ExternalResponsibilitiesStr`, and `ExternalQualificationsStr`.
  - `title`: `Title`.
  - `location`: `PrimaryLocation`.

### Layer 2: Playwright Chromium DOM Fallback
- If REST API finder fails, renders page and extracts from `[id*="job-description"]` or `.job-details`.

### Layer 3: Text Cleaning & Sanitization
- Cleans HTML markup, strips raw inline CSS keyframes (`@keyframes ...`), and normalizes spacing.
