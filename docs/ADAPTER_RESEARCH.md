---
type: "research"
area: "project"
status: "active"
project: "Job Radar"
tags:
  - "job-search"
  - "research"
  - "playwright"
parent: "[[20 Projects/Job Radar/Project]]"
---

# Job Radar — Board Classification and Adapter Research

> **Status:** design-only research. It defines reviewed acquisition contracts; it is not implementation approval. No scheduler, source enablement, job persistence, Job Ops handoff, notification, or saved board mutation is authorized by this note.

## Scope and method

- Scope is the 38 company rows under `## Company` in [[10 Personal/Career/Job Boards|Job Boards]]. `## aggregators` and `## limited application submission` are explicitly outside this phase.
- Each diagnostic used the Shell-hosted Playwright service with a fresh context, one listing navigation, `domcontentloaded`, a bounded attempt at `networkidle`, and an additional short render wait. It recorded only page title, counts, public response host/path/content type, and public link patterns—not response bodies, credentials, or job persistence.
- `networkidle` is only a settling hint. Every production adapter needs a board-specific readiness condition: an exact public listing-response predicate/shape, visible result locator, or both. [Playwright Page API](https://playwright.dev/docs/api/class-page)
- The **listing acquisition allowlist** and **accepted job-detail URL allowlist** are separate. Browser resource origins must be reviewed per adapter; a narrow job-detail path must never be repurposed as a blanket subresource rule.
- A blocked challenge/403/crash is a valid research outcome, not a reason to add stealth, credentials, proxying, CAPTCHA bypass, or a guessed direct API request.

## Common runtime contract

1. Create an isolated context; navigate only the stored, approved listing URL.
2. Wait for the adapter’s reviewed response/locator with a 30-second hard cap; close the context in `finally`.
3. Keep only bounded, normalized candidate fields in memory: stable external ID where exposed, title, location, posting date if available, and the candidate detail URL. Do not persist raw upstream HTML/JSON.
4. Validate every candidate: HTTPS, public DNS, exact board-approved host, reviewed detail-route pattern, no credential/non-default-port URL, strip fragment/tracking query parameters when safe, then deduplicate canonical URLs/IDs.
5. For pagination, use only a declared first-party pagination rule and a small configured cap; stop on repeated IDs, no next control, or timeout. Do not invent clicks, scroll indefinitely, or follow arbitrary links.
6. Fetch a detail page only after a candidate passes policy. Revalidate canonical URL after the response; report safe counts/outcomes only.

## Classification changes from the `custom` review

| Board | Previous | Verified classification | Evidence / decision |
|---|---|---|---|
| Google | custom | `google_careers` | Rendered exact job links under `/about/careers/applications/jobs/results/{numeric-id}-{slug}`. |
| Qualcomm, Microsoft, HP | custom | `eightfold` | Public browser responses included each tenant’s `/api/pcsx/search`; HP exposed `/careers/job/{id}` links. |
| Amazon | custom | `amazon_jobs` | Browser observed `www.amazon.jobs/en/search.json` and rendered first-party search links. |
| Tesco | custom | `avature` | Rendered portal loaded Avature CDN assets and uses `/careers/SearchJobs` → `/careers/JobDetail/.../{id}` routes. |
| RBCTech | custom | `stratsy` | Browser observed `aligncrm.stratsy.us/api/public/opportunities`. |
| Ameriprise, Philips | custom | `phenom` | Philips loaded `content-ir.phenompeople.com` configuration; Ameriprise uses the Phenom-hosted (`/phb/`) page family and rendered first-party job routes. |
| Vanguard | custom | `google_cloud_talent_solution` | Browser observed `jobsapi-google.m-cloud.io/api/job/search` and rendered `/job/{id}/...` routes. |
| Apple | custom | `apple_jobs` | Rendered first-party Apple Jobs result page; use a first-party DOM/detail-route adapter. |
| Meta | blank | `meta_careers` | Rendered `www.metacareers.com/profile/job_details/{id}` links. |

The remaining `custom` labels are deliberate: a board-specific, first-party contract was verified, but no reusable provider family was established. They remain research targets, not failures.

| Board(s) | State after inspection | Required next evidence before reclassification |
|---|---|---|
| Abnormal AI | First-party page rendered `/careers/jobs/{id}?gh_jid={id}` links under the approved India/Engineering listing. | Retain as custom until a second company demonstrates the same stable data contract. |
| Celonis | First-party page rendered filtered job-detail links and observed `dxp-api.celonis.com/v1/jobs`. | Retain as custom/tenant-specific until stable response shape and pagination are reviewed. |
| HighRadius | `/about/career/` rendered first-party `/about/careers-list/?gh_jid={id}` job links. | Retain as custom pending a shared vendor/data contract. |
| Novartis | First-party page rendered `/career-search/job/details/{slug}` links. | Retain custom pending a stable list/pagination contract. |
| Mattel | First-party page rendered `/en/job/{city}/{slug}/{id}` links. | Retain custom pending a shared vendor/data contract. |
| Gururo / CareerPage | Chromium page crashed twice during ordinary navigation; later content-only rendering did not expose job links. | Treat as `provider_failure`; investigate only with a bounded isolated retry after the browser capacity gate. |

## Shared adapter contracts

### `oracle` — Oracle HCM Candidate Experience

**Boards:** Oracle, AMEX, JPMC.

- **Observed:** Oracle’s normal listing navigation rendered `/en/sites/jobsearch/job/{id}/` detail links and public Candidate Experience responses, including `.../hcmRestApi/resources/latest/recruitingCEJobRequisitions`.
- **Acquisition:** wait for the configured tenant/site Candidate Experience requisition response *during the ordinary listing navigation*, or a reviewed visible job-card locator. The adapter must accept only the reviewed wrapper/record shape and flatten it safely before normal candidate validation. Direct detail extraction utilizes the public `recruitingCEJobRequisitionDetails` endpoint (`finder=ById;Id="{public_id}"`) configured via `oracle_detail` provider config (`api_origin`, `allowed_origins`, `site_number`).
- **Detail rule:** configured public host, exact site prefix, `/job/{numeric-id}` route only.
- **Pagination:** configured page/offset behavior inferred from the observed response; bounded and stopped on repeated requisition IDs.
- **Failure:** response missing = `not_observed`; mismatched schema = `parser_contract`; challenge/403 = `blocked_resource`/`challenge`. Never call an unconfigured or un-allowed origin.

### `workday` — Workday Candidate Experience Search

**Boards:** Walmart, Solera, JioStar, Cisco, Thomson Reuters, TP, EisnerAmper, Adobe, Motorola Solutions, eBay.

- **Observed:** a normal Walmart navigation requested a tenant/site `.../wday/cxs/{tenant}/{site}/jobs` response and rendered `/en-US/{site}/job/{location}/{slug}_{requisition}` detail links.
- **Acquisition:** wait for the exact configured `wday/cxs` jobs response and validate its expected collection shape, with rendered DOM job links as a cross-check/fallback. The request must result from page navigation, not a separate constructed API call.
- **Detail rule:** configured tenant host and locale/site prefix; exact `/job/` path with a final non-empty requisition key. Preserve only canonical first-party detail links.
- **Pagination:** only the board’s reviewed pagination request/control; cap pages and stop on repeated requisition IDs.
- **Failure:** an empty filtered set after a verified response is `empty_verified`, not an error.

### `greenhouse` — Greenhouse Job Board

**Boards:** Cognite.

- **Observed:** the rendered board exposed `/cognite/jobs/{numeric-id}` links.
- **Preferred source:** Greenhouse documents a public Job Board API for public boards; use it only after a board token and API origin are explicitly reviewed/configured. [Greenhouse Job Board API](https://developers.greenhouse.io/job-board.html)
- **Fallback:** normal browser navigation plus exact rendered job links, if public API use is not configured.
- **Detail rule:** configured `job-boards*.greenhouse.io/{board}/jobs/{numeric-id}` route.
- **Pagination:** API paging only when the documented/configured endpoint is enabled; DOM pagination otherwise.

### `lever` — Lever Postings

**Boards:** Resilinc, Coupa.

- **Observed:** rendered `jobs.lever.co/resilinc/{uuid}` links. Coupa's official public Lever postings endpoint returned records with country code `IN` and canonical `jobs.lever.co/coupa/{uuid}` URLs.
- **Preferred source:** Lever’s public postings API, only with the exact reviewed site slug and official endpoint configuration. For Coupa, filter `country == "IN"`. [Lever developer documentation](https://hire.lever.co/developer/documentation) · [Postings API reference](https://github.com/lever/postings-api)
- **Fallback:** normal rendered DOM links.
- **Detail rule:** `jobs.lever.co/{site}/{uuid}` only; never candidate/application routes.

### `ashbyhq` — Ashby public jobs page

**Boards:** Weave, Aspora, Plane.

- **Observed:** a normal Weave navigation requested `jobs.ashbyhq.com/api/non-user-graphql` and rendered `{board}/{uuid}` job links.
- **Acquisition:** use an exact, board-owned browser-observed GraphQL response predicate/validated shape, or the rendered detail links. Do not turn this into a generic caller-supplied GraphQL client.
- **Detail rule:** `jobs.ashbyhq.com/{board}/{uuid}`; explicitly exclude `/form/` talent-community routes.
- **Pagination:** only observed, configuration-declared page/cursor behavior; cap it.

### `careerpage` — CareerPage

**Boards:** Gururo.

- **State:** no contract yet. Two normal Playwright navigations crashed Chromium before `domcontentloaded`.
- **Planned logic after a successful bounded inspection:** rendered first-party job links or one validated public listing response only. No direct endpoint inference from third-party examples.

### `zoho` — Zoho Recruit Careers Site

**Boards:** Wynploy.

- **Observed:** rendered `/jobs/Careers/{numeric-id}/{slug}` links and a public `/jobs/Careers/rss` link.
- **Acquisition:** DOM-first; optionally use the exact public RSS representation only after its schema/terms are reviewed and configured. Zoho’s authenticated Recruit API is not a replacement for public board discovery. [Zoho Recruit API](https://www.zoho.com/recruit/developer-guide/apiv2/)
- **Detail rule:** configured public tenant host and `/jobs/Careers/{numeric-id}/{slug}` route.

### `eightfold` — PCSX browser-response adapter

**Boards:** Qualcomm, Microsoft, HP.

- **Observed:** all three exposed tenant-owned `/api/pcsx/search` during normal navigation; HP rendered `/careers/job/{id}` links.
- **Acquisition:** capture exactly one configured same-origin `/api/pcsx/search` response in memory after the approved listing navigation and validate the reviewed record schema. DOM job links provide the safe fallback.
- **Detail rule:** configured `/careers/job/{id}` path only.
- **Pagination:** response cursor/page only if documented by observed shape and explicitly configured; otherwise use a reviewed visible next control.

### `phenom` — Phenom-hosted careers

**Boards:** Ameriprise, Philips.

- **Observed:** Philips loaded `content-ir.phenompeople.com` configuration; Ameriprise rendered first-party `/search-jobs/{requisition}_{id}/{slug}/` routes. Philips static HTML embedding exposes complete `application/ld+json` `JobPosting` structured payloads directly during initial GET fetch, bypassing dynamic browser rendering.
- **Acquisition:** DOM-first and static JSON-LD parser. Treat Phenom configuration as readiness metadata, not permission to call an inferred vendor endpoint. Capture a public response or static HTML JSON-LD node only when exact origin/path and record schema have been observed for that board.
- **Detail rule:** board-specific configured first-party detail pattern, never generic `/search-jobs/` listings, profile, or saved-job paths.

### `avature` — Avature portal

**Boards:** Tesco.

- **Observed:** Avature portal assets and `/careers/SearchJobs` → `/careers/JobDetail/{slug}/{numeric-id}` routes.
- **Acquisition:** wait for reviewed visible result cards; capture a list response only after its exact public portal path/shape is observed. Use DOM detail links initially.
- **Pagination:** configured portal next/page behavior only.

### `amazon_jobs`

**Boards:** Amazon.

- **Observed:** normal search navigation requested `www.amazon.jobs/en/search.json` and rendered first-party result links.
- **Acquisition:** one exact browser-observed search JSON response or DOM job-card links; do not use auth/token/cognito responses.
- **Detail rule:** configured `www.amazon.jobs/en/jobs/{numeric-id}/...` route.
- **Pagination:** reviewed `offset`/page behavior from the listing page, bounded by configured limit.

### `google_careers`, `apple_jobs`, `meta_careers`

- **Google and Meta:** automated acquisition remains excluded because the reviewed public-source/robots policy does not authorize it. Treat them as manual-only unless an approved, compliant public source is established.
- **Apple:** DOM-first on `jobs.apple.com`; admit only reviewed first-party job-detail route(s) after confirming them per locale.

### `google_cloud_talent_solution`

**Boards:** Vanguard.

- **Observed:** normal navigation requested `jobsapi-google.m-cloud.io/api/job/search` and rendered `www.vanguardjobs.com/job/{numeric-id}/{slug}` links.
- **Acquisition:** capture the exact reviewed public search response only during first-party listing navigation, validate schema, and prefer rendered canonical detail URLs. No constructed m-cloud API calls.

### `stratsy`

**Boards:** RBCTech.

- **Observed:** normal navigation requested `aligncrm.stratsy.us/api/public/opportunities`.
- **Acquisition:** one exact configured public opportunities response with a validated shape, or rendered first-party details if present. Keep tenant/API host allowlisted separately from accepted detail URL host.

## Custom-board contract template

For Abnormal AI, Celonis, HighRadius, Novartis, Mattel, and future custom sources, an individual adapter declaration must contain:

```text
listing_url                 exact stored public URL
readiness                   visible locator and/or exact response predicate
resource_origins            reviewed public rendering/API origins and paths
listing_representation      DOM links | one observed JSON response | both
detail_url_allowlist        exact public host + detail route regex
pagination                  declared UI control/cursor, maximum pages
normalization               stable ID and canonical URL policy
limits                      30 s run, 5 MiB response cap, serial execution
outcomes                    success | empty_verified | challenge | blocked_resource |
                            timeout | parser_contract | provider_failure
```

No configuration may contain arbitrary JavaScript, selectors supplied by a caller, headers/cookies, proxy controls, credentials, or direct arbitrary URLs.

## Next research actions

1. Review this taxonomy and decide whether `amazon_jobs`, `apple_jobs`, `google_cloud_talent_solution`, and `stratsy` should remain distinct provider adapters or be grouped under a deliberately limited `first_party_rendered` base class with provider-specific URL contracts.
2. Review the stable response shape/pagination for Celonis, and retry CareerPage only after the browser capacity gate; record `provider_failure` if repeatable.
3. After review, convert these design contracts into a backend/system design. Do not implement yet.
