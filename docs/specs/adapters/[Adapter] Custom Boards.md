# [Adapter] Custom Boards

- **Family ID:** `custom`
- **Target Boards:** Abnormal AI, Celonis, HighRadius, Novartis, Mattel, Coupa.

---

## Overview

The `custom` adapter classification handles specialized first-party career portals where no multi-tenant vendor API (like Workday or Eightfold) is shared across multiple companies.

---

## Specific Custom Adapter Logic

### 1. Abnormal AI
- **Listing:** Playwright Chromium renders `/careers/open-roles?location=Hybrid+-+Bangalore%2C+India&category=Engineering`. Extracts candidate links with `gh_jid={id}` parameter.
- **Detail:** Greenhouse Public API integration (`/v1/boards/abnormalsecurity/jobs/{id}`) or Playwright DOM. HTML text sanitizer removes script/CSS noise.

### 2. Celonis
- **Listing:** Browser queries `dxp-api.celonis.com/v1/jobs` or renders `/join-us/open-positions`.
- **Detail:** JSON payload / Playwright DOM extraction (`.job-detail`).

### 3. HighRadius
- **Listing:** Playwright renders `/about/career/` and extracts `/about/careers-list/?gh_jid={id}` job links. Dedicated title element selector prevents link/card text pollution.
- **Detail:** Greenhouse API / DOM fallback.

### 4. Novartis
- **Listing:** Renders `/career-search` with `search_api_fulltext=software` and `country[0]=LOC_IN`.
- **Detail:** Playwright DOM extraction for `/career-search/job/details/{slug}` pages.

### 5. Mattel
- **Listing:** Renders `/search-jobs/software/Hyderabad...`.
- **Detail:** Renders detail link `/en/job/{city}/{slug}/{id}`.

### 6. Coupa
- **Listing:** Lever-based direct account query `https://api.lever.co/v0/postings/coupa?mode=json`.
- **Detail:** Lever JSON description payload with local location substring matching for India roles.
