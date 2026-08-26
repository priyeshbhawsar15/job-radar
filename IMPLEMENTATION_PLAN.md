# New Boards and India Eligibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the 65 canonical `New Boards` sources through evidence-gated provider contracts, while enforcing a durable India eligibility decision before any Job Ops handoff for every Job Radar candidate.

**Architecture:** Preserve the source URL verbatim in each `BoardRevision`, but treat its listed provider label only as a routing hypothesis until a tenant-specific live canary confirms the real contract. Route every extracted candidate through one shared location classifier after normalization and again after detail enrichment; persist the decision on the candidate, stop excluded candidates before queueing, and defensively recheck before dispatch. New boards remain `draft`/`reviewed` until their individual canary, fixtures, and local gates pass.

**Tech Stack:** Python, Pydantic, SQLAlchemy async ORM, Alembic, FastAPI, httpx, Playwright/browser acquisition, pytest, in-memory SQLite test fixtures.

**Spec:** `docs/specs/NEW_BOARDS_REQUIREMENTS.md`; canonical inventory: `docs/specs/job-boards-source.md` → `## New Boards`; provider references: `docs/specs/adapters/*.md`.

## Global Constraints

- Work only in `/home/priyesh/Work/job-radar/.claude/worktrees/new-boards-india-filter` on `feature/new-boards-india-filter`.
- Do not use the source table’s family column as proof of a real provider contract. A board may be enabled only after its own live canary validates listing, detail, identifiers, location, filters, pagination, and allowed origin.
- Preserve each inventory URL exactly, including query keys, duplicate keys, encoding, sorting, location, department, employment type, pagination, and technology/engineering intent. Store it as the immutable source target in `BoardRevision.config_json`; derive provider requests only from canary-confirmed mappings.
- The India policy applies to all current and new boards. It is a handoff eligibility rule, not merely an upstream search filter.
- Never manufacture `location="India"` from a blank/unknown source location. Blank and unknown locations are eligible, but remain blank/null in persistence and payloads.
- Clearly non-Indian locations and ambiguous non-empty locations are excluded from Job Ops queueing and dispatch. Persist a queryable decision and durable reason.
- No hardcoded production dummy jobs. Deterministic records belong only in test fixtures.
- All implementation verification is local and isolated. Force Job Ops handoff disabled in runtime/config/database tests and mechanically prove zero `httpx.AsyncClient.post` calls.
- Run Python tests only with:
  ```bash
  PYTHONPATH="$PWD/src" /home/priyesh/Work/job-radar/.venv/bin/pytest -q
  ```
- Do not run a live canary, pipeline, Job Ops operation, deployment, merge, push, or change canonical `main` under this plan without separate approval. Live canaries are an explicit later approval gate, not a test substitute.

---

## 0. Evidence Policy and Document Index

### 0.1 Evidence hierarchy

1. `docs/specs/job-boards-source.md` is authoritative for the 65 board names and source URLs.
2. `docs/specs/adapters/*.md` describes reusable family contracts, not tenant validation.
3. Current application behavior and tests override an unverified source-table label.
4. A **standalone live canary** is required before implementing/enabling an individual board. It must capture only non-secret contract evidence: final host, method, listing/detail schema paths, source ID, title, raw location, canonical public URL, filter propagation, page continuation/termination, and description extraction. Do not save cookies, authorization material, or raw personal data in fixtures.
5. Record the canary evidence and exact config revision in the board’s review/audit trail. A failed or inconclusive canary produces `parser_contract`/`provider_failure`, leaves the board disabled, and creates no generic fallback integration.

### 0.2 Documents to read during execution

| Purpose | Files |
| --- | --- |
| Requirements and source URLs | `docs/specs/NEW_BOARDS_REQUIREMENTS.md`, `docs/specs/job-boards-source.md` |
| Existing provider contracts | `docs/specs/adapters/Index.md`, `[Adapter] Workday.md`, `[Adapter] Greenhouse.md`, `[Adapter] Lever.md`, `[Adapter] Ashby.md`, `[Adapter] Eightfold.md`, `[Adapter] Phenom.md`, `[Adapter] Stratsy.md`, `[Adapter] Zoho Recruit.md`, `[Adapter] Custom Boards.md`, and all other adapter documents |
| Adapter boundary | `src/job_radar/adapters/base.py`, `src/job_radar/adapters/families.py`, `src/job_radar/adapters/registry.py` |
| Acquisition and normalization | `src/job_radar/services/engine.py`, `src/job_radar/services/normalization.py` |
| Handoff boundary | `src/job_radar/services/handoff.py`, `src/job_radar/api/v1/jobs.py` |
| Persistence/API | `src/job_radar/db/models/candidate.py`, `src/job_radar/db/models/handoff.py`, `src/job_radar/db/models/run.py`, `src/job_radar/db/models/audit.py`, `src/job_radar/api/v1/runs.py` |
| Seed and test conventions | `src/job_radar/db/seed.py`, `tests/conftest.py`, `tests/test_adapters.py`, `tests/test_engine.py`, `tests/test_normalization.py`, `tests/test_handoff.py`, `tests/test_models.py`, `tests/test_api_runs_outcomes.py`, `tests/test_api_settings.py` |

### 0.3 Known corrections that must not be regressed

- The duplicate Elastic URL in the Twilio row is not a Twilio source. Twilio is blocked until the owner supplies and a canary verifies a correct Twilio URL and contract.
- GoDaddy’s `careers.godaddy` URL is not evidence of a Greenhouse token/API contract.
- Zoho’s main careers site is not evidence of the existing `.zohorecruit.in` adapter contract.
- VMware’s SmartRecruiters source cannot use a non-existent SmartRecruiters adapter.
- The five Talent500 URLs are not the existing `aligncrm.stratsy.us` Stratsy contract. They require a Talent500 family canary and likely a new adapter.
- `ashbyhq` in the source should normalize to the existing family key `ashby` only after canary validation.
- Existing `custom`, `phenom`, and `eightfold` labels are hypotheses until the specific board demonstrates the documented API/hydration contract.
- Do not let `AdapterRegistry` create `GenericAdapter` for an unknown/unverified family. It must return a typed unsupported-contract outcome that holds the board run and leaves the board unenabled.

---

## 1. Canonical 65-Board Inventory and Canary Worklist

**Legend:** `Verified-family candidate` means the family has a documented general contract, not that this tenant is approved. `Canary-only` means build no enabled integration until a board-specific evidence capture is approved. `Detail` is API/hydration/DOM only after the same canary establishes it. `Raw location` always means pass source text unchanged to the shared eligibility classifier.

| # | Board | Exact source target to persist | Proposed family / listing acquisition | Detail acquisition; filter, pagination, location strategy | Canary/fixture/blocker |
| --: | --- | --- | --- | --- | --- |
| 1 | JLL | `https://jll.wd1.myworkdayjobs.com/en-US/jllcareers?locationCountry=c4f78be1a8f14da0ab49ce1162348a5e&timeType=72e81fa31e6f01cf9aa5a4251a4e4e00&jobFamilyGroup=c608fc06410f01484a9fec7aba539450&jobFamilyGroup=f134f8e1c0811001fe9e2695d0c80000` | Verified-family candidate: Workday CXS POST with tenant/site and all source facets. | CXS `jobPostingInfo`, browser fallback; offset 20 until empty/total; raw `locationsText`. | Canary tenant/site/facet translation; fixture pages + detail. |
| 2 | Razorpay | `https://job-boards.greenhouse.io/razorpaysoftwareprivatelimited?departments%5B%5D=4024806005` | Verified-family candidate: Greenhouse board token `razorpaysoftwareprivatelimited`. | Greenhouse detail API; fetch all API jobs then retain exact department filter locally; raw API location. | Canary token and department ID; fixture filtered/unfiltered jobs. |
| 3 | SOTI | `https://soti.wd3.myworkdayjobs.com/en-US/Careers?locations=f35dd6d3a7da01adef33e8916446200f&locations=27190dd10fff1074b213f2d1500595ed&EEB_-_Job_Categories_for_External_Site_Extended=267bdbcbbd671001697698c0843a0001` | Verified-family candidate: Workday CXS. | CXS detail; preserve both location values and category facet; offset 20; raw location. | Canary all repeated facets; fixture multi-page. |
| 4 | Amgen | `https://amgen.wd1.myworkdayjobs.com/en-US/Careers?locations=be0893cb78ed012e9c728ee58144ec3b&jobFamilyGroup=3b16b67900e510859633b621ace7c537` | Verified-family candidate: Workday CXS. | CXS detail; preserve location and family facets; offset 20; raw location. | Canary tenant/site and facets; fixture listing/detail. |
| 5 | Paytm | `https://jobs.lever.co/paytm?department=Technology&commitment=Full-time%20Employment` | Verified-family candidate: Lever account `paytm`. | Inline Lever description; fetch all then apply Technology and full-time locally; raw location, including blank. | Canary account/schema; fixture blank, India, foreign location. |
| 6 | Atlassian | `https://www.atlassian.com/company/careers/all-jobs?team=Engineering&location=India&search=` | Canary-only dedicated/custom discovery. | Determine first-party API/hydration/DOM and detail route; retain team/location/search semantics and observed pagination. | No family assignment exists; block until contract canary + fixtures. |
| 7 | Uber | `https://jobs.uber.com/en/jobs/?search=software&countries=India` | Canary-only custom first-party contract. | Canary listing/query transport and detail extraction; preserve software and India filters/paging; raw location. | Dedicated fixture from approved evidence. |
| 8 | Gitlab | `https://job-boards.greenhouse.io/gitlab` | Verified-family candidate: Greenhouse token `gitlab`. | API detail; all results then no added filters; raw location. | Canary token/API host; listing/detail fixture. |
| 9 | Hobspot | `https://job-boards.greenhouse.io/hubspot` | Verified-family candidate: Greenhouse token `hubspot`; retain canonical inventory spelling as board name. | API detail; raw location. | Canary token and board-name-to-token mapping; fixture. |
| 10 | Godaddy | `https://careers.godaddy/jobs/search?page=1&query=&department_uids[]=6ed98616cdc63adf0b08529f08290235&country_codes[]=IN` | Canary-only first-party/custom; do not assume Greenhouse. | Discover transport/detail; preserve page=1, department UID, IN country, empty query and continuation mechanism. | Existing Greenhouse label disproven by URL alone; block until canary. |
| 11 | Phonepay | `https://job-boards.greenhouse.io/phonepe?gh_src=961e65dc3us` | Verified-family candidate: Greenhouse token `phonepe`. | API detail; preserve `gh_src` as source provenance, not necessarily API filter; raw location. | Canary token and tracking-query handling; fixture. |
| 12 | Buffer | `https://jobs.ashbyhq.com/buffer` | Verified-family candidate: Ashby (`ashby`, not `ashbyhq`) slug `buffer`. | Inline `includeDetails=true`; raw location. | Canary slug/schema; fixture listing with inline detail. |
| 13 | Sourcegraph | `https://boards-api.greenhouse.io/v1/boards/sourcegraph91/jobs?content=true` | Verified-family candidate: Greenhouse token `sourcegraph91`. | API content/detail; preserve `content=true`; raw location. | Canary direct API response; fixture. |
| 14 | Zapier | `https://jobs.ashbyhq.com/zapier` | Verified-family candidate: Ashby slug `zapier`. | Inline details; raw location. | Canary/fixture. |
| 15 | Automattic | `https://automattic.com/work-with-us/jobs/` | Canary-only custom first-party. | Discover API/hydration/DOM and detail; preserve path; raw location. | Dedicated canary and fixture. |
| 16 | Doist | `https://doist.com/careers#open-roles` | Canary-only custom first-party. | Discover listing/detail; preserve open-roles anchor intent; raw location. | Dedicated canary and fixture. |
| 17 | Deel | `https://www.deel.com/careers/?department=engineering` | Canary-only custom first-party. | Discover transport/detail; preserve engineering department; raw location. | Dedicated canary and fixture. |
| 18 | Remote.com | `https://job-boards.greenhouse.io/remote` | Verified-family candidate: Greenhouse token `remote`. | API detail; raw location. | Canary/fixture. |
| 19 | Elastic | `https://jobs.elastic.co/jobs/country/india?size=n_20_n` | Canary-only custom first-party. | Discover API/hydration/detail; preserve India and size=20 intent, prove continuation; raw location. | Dedicated canary and fixture. |
| 20 | Twilio | `https://jobs.elastic.co/jobs/country/india?size=n_20_n` | **Blocked: no acquisition.** | Do not treat Elastic’s URL/results as Twilio; no detail work. | Correct Twilio target and full contract evidence required before implementation. |
| 21 | Supabase | `https://jobs.ashbyhq.com/supabase` | Verified-family candidate: Ashby slug `supabase`. | Inline details; raw location. | Canary/fixture. |
| 22 | Bitwarden | `https://job-boards.greenhouse.io/bitwarden` | Verified-family candidate: Greenhouse token `bitwarden`. | API detail; raw location. | Canary/fixture. |
| 23 | Camunda | `https://jobs.ashbyhq.com/camunda` | Verified-family candidate: Ashby slug `camunda`. | Inline details; raw location. | Canary/fixture. |
| 24 | MailerLite | `https://www.mailerlite.com/jobs` | Canary-only custom first-party. | Discover listing/detail and paging; raw location. | Dedicated canary and fixture. |
| 25 | Zoho | `https://www.zoho.com/careers/` | Canary-only custom/possibly Zoho Recruit only if proven. | Discover actual careers contract and detail; raw location. | Existing Zoho Recruit adapter has different `.zohorecruit.in` contract; block until canary. |
| 26 | Postman | `https://job-boards.greenhouse.io/postman` | Verified-family candidate: Greenhouse token `postman`. | API detail; raw location. | Canary/fixture. |
| 27 | BrowserStack | `https://browserstack.wd3.myworkdayjobs.com/External?jobFamilyGroup=0cb9174e33c9100190f156427de80000` | Verified-family candidate: Workday CXS. | CXS detail; preserve family facet; offset 20; raw location. | Canary tenant/site/facet; fixture. |
| 28 | Atlan | `https://jobs.ashbyhq.com/atlan` | Verified-family candidate: Ashby slug `atlan`. | Inline details; raw location. | Canary/fixture. |
| 29 | Redis | `https://jobs.ashbyhq.com/redis` | Verified-family candidate: Ashby slug `redis`. | Inline details; raw location. | Canary/fixture. |
| 30 | Springworks | `https://jobs.goodfit.so/careers/springworks` | Canary-only custom/Goodfit discovery. | Determine whether a reusable Goodfit contract exists; preserve path/pagination; raw location. | Dedicated canary; create a family only after a second compatible tenant or keep custom. |
| 31 | Juspay | `https://juspay.io/careers` | Canary-only custom first-party. | Discover listing/detail; raw location. | Dedicated canary and fixture. |
| 32 | Groww | `https://job-boards.eu.greenhouse.io/groww` | Verified-family candidate: Greenhouse token `groww`, EU board host. | API detail; preserve board host/origin policy; raw location. | Canary `boards-api` host/token; fixture. |
| 33 | CRED | `https://jobs.lever.co/cred` | Verified-family candidate: Lever account `cred`. | Inline details; fetch all; raw location including blank. | Canary/fixture. |
| 34 | Snowflake | `https://careers.snowflake.com/us/en/search-results` | Canary-only Phenom hypothesis. | Prove Phenom widget/hydration API, detail route, filters/paging; raw location. | No generic Phenom DOM fallback; block until canary. |
| 35 | Databricks | `https://job-boards.greenhouse.io/databricks` | Verified-family candidate: Greenhouse token `databricks`. | API detail; raw location. | Canary/fixture. |
| 36 | IBM | `https://careers.ibm.com/en_IN/careers/search` | Canary-only custom first-party. | Discover search API/hydration/detail and pagination; preserve en_IN; raw location. | Dedicated canary and fixture. |
| 37 | Okta | `https://job-boards.greenhouse.io/okta` | Verified-family candidate: Greenhouse token `okta`. | API detail; raw location. | Canary/fixture. |
| 38 | CrowdStrike | `https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers?locationCountry=c4f78be1a8f14da0ab49ce1162348a5e&Job_Family=1408861ee6e201641be2c2f6b000c00&Job_Family=cb19f044639b1001f6a02595bc920000` | Verified-family candidate: Workday CXS. | CXS detail; retain India and both job-family facets; offset 20; raw location. | Canary/fixture. |
| 39 | Stripe | `https://stripe.com/careers/search?teams=Products&locations=Asia+Pacific--India&employment_types=Full+time` | Canary-only custom first-party. | Discover API/hydration/detail; preserve team, India region, full-time; raw location. | Dedicated canary and fixture. |
| 40 | Coinbase | `https://job-boards.greenhouse.io/coinbase` | Verified-family candidate: Greenhouse token `coinbase`. | API detail; raw location. | Canary/fixture. |
| 41 | Salesforce | `https://salesforce.wd12.myworkdayjobs.com/External_Career_Site` | Verified-family candidate: Workday CXS. | CXS detail; no added filter; offset 20; raw location. | Canary tenant/site; fixture. |
| 42 | SAP | `https://jobs.sap.com/search/?createNewAlert=false&q=&locationsearch=&optionsFacetsDD_department=Software-Design+and+Development&optionsFacetsDD_customfield3=&optionsFacetsDD_country=IN` | Canary-only Phenom hypothesis. | Prove actual search/detail contract; preserve department, country IN, blank search fields; raw location. | Block generic Phenom fallback until canary. |
| 43 | Workday | `https://workday.wd5.myworkdayjobs.com/Workday/?source=Careers_Website&Location_Country=c4f78be1a8f14da0ab49ce1162348a5e&jobFamilyGroup=8c5ce7a1cffb43e0a819c249a49fcb00` | Verified-family candidate: Workday CXS. | CXS detail; preserve source, country and family facets; offset 20; raw location. | Canary/fixture. |
| 44 | Intuit | `https://jobs.intuit.com/search-jobs?acm=9211424&alrpm=ALL&ascf=[{%22key%22:%22ALL%22,%22value%22:%22%22}]` | Canary-only custom first-party. | Discover transport/detail; preserve all encoded parameters; raw location. | Dedicated canary and fixture. |
| 45 | Nutanix | `https://careers.nutanix.com/en/jobs/?search=&country=India&team=Engineering&type=Full-Time&pagesize=20#results` | Canary-only Phenom hypothesis. | Prove actual contract; preserve India, engineering, full-time, page size and paging; raw location. | Canary/fixture. |
| 46 | VMware | `https://careers.smartrecruiters.com/Vmware2` | Canary-only new `smartrecruiters` family. | After canary, implement public SmartRecruiters listing/detail API with source IDs, pagination and raw location. | No existing family adapter: dedicated adapter + fixtures required. |
| 47 | NVIDIA | `https://jobs.nvidia.com/careers?start=0&location=Hyderabad%2C++Telangana%2C++India&pid=893395509555&sort_by=distance&filter_distance=160&filter_include_remote=1&filter_include_relocation=0&filter_job_category=engineering` | Canary-only Eightfold hypothesis. | Prove PCSX endpoint/detail; preserve all start/location/pid/sort/distance/remote/relocation/category semantics; raw location. | Canary and multi-page fixture. |
| 48 | Intel | `https://intel.wd1.myworkdayjobs.com/External?locations=1e4a4eb3adf101f44070f976bf8184cf&jobFamilyGroup=ace7a3d23b7e01a0544279031a0ec85c` | Verified-family candidate: Workday CXS. | CXS detail; preserve location/family facet; offset 20; raw location. | Canary/fixture. |
| 49 | Airbnb | `https://job-boards.greenhouse.io/airbnb` | Verified-family candidate: Greenhouse token `airbnb`. | API detail; raw location. | Canary/fixture. |
| 50 | Meesho | `https://www.meesho.io/jobs?&t=Business%20Analytics,Backend,QA,Infrastructure,CTO%20Office,Data%20Engineering,Data%20Science,Demand,Frontend,Supply,Security` | Canary-only custom first-party. | Discover transport/detail; preserve every comma-separated team filter; raw location. | Dedicated canary and fixture. |
| 51 | Target | `https://corporate.target.com/careers/job-search?currentPage=1&jobAreas=Target%20Tech&schedule=Full-time&country=India` | Canary-only Phenom hypothesis. | Prove actual contract; preserve current page, Target Tech, full-time and India filters; raw location. | Canary and page-continuation fixture. |
| 52 | Goldman Sachs | `https://higher.gs.com/results?JOB_FUNCTION=Software%20Engineering&page=1&sort=POSTED_DATE` | Canary-only custom first-party. | Discover listing/detail; preserve software engineering, page and date sort; raw location. | Dedicated canary and fixture. |
| 53 | Morgan Stanley | `https://morganstanley.eightfold.ai/careers?source=mscom&start=0&location=India&pid=549798643496&sort_by=distance&filter_include_remote=1&filter_include_relocation=0&filter_businessarea=technology&filter_employmenttype=full+time` | Canary-only Eightfold hypothesis. | Prove PCSX/detail; preserve all source/start/location/pid/sort/remote/relocation/business-area/full-time filters; raw location. | Canary and multi-page fixture. |
| 54 | HSBC | `https://portal.careers.hsbc.com/careers?query=software&location=India&pid=563774612163818&domain=hsbc.com&sort_by=relevance&triggerGoButton=false` | Canary-only Eightfold hypothesis. | Prove PCSX/detail; preserve query/location/pid/domain/sort/trigger semantics; raw location. | Canary and fixture. |
| 55 | BlackRock | `https://careers.blackrock.com/search-jobs/software/India/45831/1/2/1269750/22/79/0/2` | Canary-only Phenom hypothesis. | Prove actual route/API/detail; preserve encoded path filters and paging; raw location. | Canary/fixture. |
| 56 | UiPath | `https://www.uipath.com/careers/jobs` | Canary-only custom first-party. | Discover listing/detail/paging; raw location. | Dedicated canary and fixture. |
| 57 | Druva | `https://job-boards.greenhouse.io/druva` | Verified-family candidate: Greenhouse token `druva`. | API detail; raw location. | Canary/fixture. |
| 58 | Swiggy | `https://careers.swiggy.com/#/careers?career_page_category=Technology` | Canary-only custom first-party/hydrated SPA. | Discover route/API/detail; preserve Technology category; raw location. | Dedicated browser/API canary and fixture. |
| 59 | Publicis Sapient | `https://careers.publicissapient.com/job-search?q=&location_q=India&skipLocation=true&country=India&sortOrder=desc&teams=Technology+and+Engineering` | Canary-only Phenom hypothesis. | Prove contract/detail; preserve India, descending sort, technology/engineering and all blank/boolean parameters; raw location. | Canary/fixture. |
| 60 | EPAM Systems | `https://careers.epam.com/en/jobs/india?city=4060741400035606933&sort_by=relevance&specialization=developer&utm_content=job-search&utm_term=start-your-search-here` | Canary-only custom first-party. | Discover API/detail; preserve India path, city, relevance, developer and source terms; raw location. | Dedicated canary and fixture. |
| 61 | TMUS | `https://talent500.com/joblist/?company=TMUS+Global+Solutions&sort_by_created_date=1&offset=0&limit=20` | Canary-only new `talent500` family, not Stratsy. | Discover shared Talent500 list/detail schema; preserve company, date sort, offset, limit; raw location. | Family canary + company fixture; cannot use Stratsy. |
| 62 | Best Buy | `https://talent500.com/joblist/?company=Best+Buy&sort_by_created_date=1&offset=0&limit=20` | Canary-only `talent500`. | Same proven Talent500 contract; preserve company/sort/offset/limit; raw location. | Per-company canary + fixture even after family exists. |
| 63 | Evernorth | `https://talent500.com/joblist/?company=Evernorth&sort_by_created_date=1&offset=0&limit=20` | Canary-only `talent500`. | Same proven Talent500 contract; preserve company/sort/offset/limit; raw location. | Per-company canary + fixture. |
| 64 | Marriott Tech | `https://talent500.com/joblist/?company=Marriott+Tech+Accelerator&sort_by_created_date=1&offset=0&limit=20` | Canary-only `talent500`. | Same proven Talent500 contract; preserve company/sort/offset/limit; raw location. | Per-company canary + fixture. |
| 65 | McD | `https://talent500.com/joblist/?company=McDonalds+in+India&sort_by_created_date=1&offset=0&limit=20` | Canary-only `talent500`. | Same proven Talent500 contract; preserve company/sort/offset/limit; raw location. | Per-company canary + fixture. |

**Inventory completion rule:** Treat the preceding table as the sole implementation inventory. Before review, compare its 65 numbered rows against source lines 57–121, assert contiguous identifiers 1–65, and assert every canonical source name occurs once in the inventory’s Board column. Do not rename misspellings from the canonical source (for example, retain `Hobspot`, `Phonepay`, and `Godaddy`) without a separately approved data-name correction.

---

## 2. Target Design

### 2.1 Contract-gated adapter architecture

1. Add a typed `ProviderContractUnsupported` acquisition outcome/error containing `family`, `board_id`, and a non-secret `reason_code`.
2. Replace unknown-family generic parsing in `AdapterRegistry` with that explicit outcome. Retain existing generic behavior only for current, explicitly configured and reviewed boards if one exists; do not route any new inventory board through it.
3. Extend revision config with typed provider data, for example:
   ```json
   {
     "target_url": "<exact inventory URL>",
     "source_filters": {"preserved": true},
     "provider_contract": {
       "family": "workday",
       "status": "canary_verified",
       "allowed_origins": ["https://tenant.example"],
       "listing": {"method": "POST", "url": "...", "payload_template": {"appliedFacets": {}, "limit": 20, "offset": "{{offset}}"}},
       "detail": {"method": "GET", "url_template": ".../{source_job_id}"},
       "pagination": {"kind": "offset", "page_size": 20, "max_pages": 3}
     }
   }
   ```
   Do not invent this configuration from a table label; populate it only from recorded canary evidence.
4. Reuse documented Workday, Greenhouse, Lever, and Ashby code only after a tenant canary. Implement SmartRecruiters and Talent500 as dedicated families only after canary evidence establishes a stable public contract. Keep one-off first-party sites in focused custom adapters, not a giant switch or broad HTML fallback.
5. Every adapter must preserve `ExtractedCandidate.location` as the raw source value (`None`/`""` included) and must not set default India, full-time, engineering, title, or company values that were not supplied by the contract.

### 2.2 Shared India eligibility policy

Create `src/job_radar/services/india_eligibility.py` with a pure function and stable decision model:

```python
class IndiaEligibilityDecision(BaseModel):
    status: Literal["eligible", "excluded"]
    classification: Literal[
        "india", "india_city_or_state", "india_remote", "multi_location_india",
        "missing_or_blank", "unknown", "non_india", "ambiguous_non_empty",
    ]
    normalized_location: str | None
    reason_code: str | None


def classify_india_eligibility(raw_location: str | None) -> IndiaEligibilityDecision:
    ...
```

Policy, in this order:

- `None`, whitespace, known empty placeholders, and genuinely unavailable location become `eligible` with `missing_or_blank`/`unknown`; retain `None` or trimmed raw value rather than changing it to India.
- India, Indian city, state, union territory, India postal formats, and explicit India-remote become `eligible` with a precise classification.
- A delimiter-separated multi-location value is eligible if any independently parsed location is India-qualified; retain the entire raw location.
- Clearly foreign country/city/remote-only values become `excluded/non_india` with a stable reason such as `location_clearly_outside_india`.
- Non-empty text that cannot be confidently classified either way becomes `excluded/ambiguous_non_empty` with `location_ambiguous_non_empty`. Do not silently pass it as India.
- Classification must be deterministic and unit-testable; locale dictionaries/normalization are explicit constants, not external geocoding during pipeline execution.

Persist the latest policy result on `CandidateJob` with fields such as `india_eligibility_status`, `india_eligibility_classification`, `india_eligibility_reason_code`, `normalized_location`, and `india_eligibility_decided_at`. This is the durable, queryable source of truth. Add an `AuditEvent` only for operator override/reclassification and include an explicit reason. Do **not** create outbox rows for excluded candidates: absence of an outbox plus candidate fields prevents confusing a durable exclusion with a dispatch work item. This deliberately uses `HandoffOutbox.state="not_eligible"` only for already-created legacy/manual records being defensively stopped; add `exclusion_reason_code` to that model to explain the held record.

Apply the same policy in four places:

1. after candidate normalization/persistence;
2. immediately after a usable detail location replaces/clarifies source location;
3. inside `enqueue_candidate_handoff`, which returns a non-queued result for excluded candidates;
4. inside outbox dispatch immediately before `JobOpsClient.push_candidate`, so old/manual rows cannot bypass a later policy decision.

The manual `POST /jobs/{candidate_id}/push-jobops` route must surface a conflict/structured non-eligible response instead of queueing an excluded candidate. Job Ops payload generation must serialize `candidate.location` as stored (nullable) and never substitute India.

---

## 3. Expected Repository Changes

| Change | Files | Responsibility |
| --- | --- | --- |
| Eligibility model and migration | Create `src/job_radar/services/india_eligibility.py`; create `alembic/versions/<timestamp>_add_india_eligibility.py`; modify `src/job_radar/db/models/candidate.py`, `src/job_radar/db/models/handoff.py` | Pure policy, durable candidate/outbox reason fields, indexes, forward/backward migration. Migration starts from `20260821_enrich_state` unless migration history changes first. |
| Normalization and handoff boundary | Modify `src/job_radar/services/normalization.py`, `src/job_radar/services/handoff.py`, `src/job_radar/api/v1/jobs.py`, `src/job_radar/api/v1/runs.py` | Evaluate/re-evaluate policy, prevent queueing/dispatch, expose eligibility and reason safely. |
| Adapter contract gate | Modify `src/job_radar/adapters/base.py`, `src/job_radar/adapters/registry.py`, `src/job_radar/adapters/families.py`, `src/job_radar/services/engine.py` | Remove unsafe new-family fallback/defaults; preserve raw location and return typed contract failures. |
| New provider cohorts | Create focused modules under `src/job_radar/adapters/` only after canaries: `smartrecruiters.py`, `talent500.py`, and one module per truly independent custom contract; modify registry/engine and `src/job_radar/db/seed.py` | Implement only approved, canary-backed adapters and seed revisions in small cohorts. |
| Seeds/config | Modify `src/job_radar/db/seed.py` and, only if required by an existing typed config layer, `src/job_radar/config.py` | Add every board as disabled/review-gated source config with exact source target; never change default database/handoff behavior. |
| Fixtures and tests | Create `tests/fixtures/providers/<family>/...`; create `tests/test_india_eligibility.py`; modify `tests/conftest.py`, `tests/test_adapters.py`, `tests/test_engine.py`, `tests/test_normalization.py`, `tests/test_handoff.py`, `tests/test_models.py`, `tests/test_api_runs_outcomes.py`, `tests/test_api_settings.py` | Deterministic provider/eligibility/safety/DB/API coverage. |
| Operational presentation | Modify `src/job_radar/services/discord_notifier.py` only if it already renders per-run counts | Report eligible/excluded counts and reasons locally without counting exclusions as accepted Job Ops sends. |
| Execution record | Modify this `IMPLEMENTATION_PLAN.md` only if approved changes alter the plan | Record canary evidence references, cohort completion, and final receipt. |

Do not modify generated databases, runtime `.env` files, production deployment files, or canonical-main files while executing local cohorts.

---

## 4. Phased Implementation Tasks

### Task 1: Establish the regression harness and policy contract

**Files:**
- Create: `tests/test_india_eligibility.py`
- Modify: `tests/conftest.py`, `tests/test_api_settings.py`

**Interfaces:**
- Produces the exact expected `IndiaEligibilityDecision` contract used by normalization, handoff, and APIs.
- Ensures every test defaults to disabled handoff and an isolated SQLite URL.

- [ ] Write parameterized failing tests for India, Bengaluru/Hyderabad/Telangana, India remote, multi-location containing India, `None`, blank, unknown, clearly foreign, and ambiguous non-empty values.
- [ ] Add an autouse/local fixture that sets both environment and `settings.HANDOFF_ENABLED` false, clears `JOBOPS_ENDPOINT`, uses the test session/engine, and replaces outbound `httpx.AsyncClient.post` with an `AsyncMock` that raises if called.
- [ ] Run the focused test file and confirm it fails because the classifier does not exist.
- [ ] Implement the pure classifier with explicit normalization and stable reason codes; do not call a network service.
- [ ] Re-run focused classifier tests; then run the existing settings tests.
- [ ] Commit the test harness and classifier together.

### Task 2: Persist eligibility and make exclusion observable

**Files:**
- Create: `alembic/versions/<timestamp>_add_india_eligibility.py`
- Modify: `src/job_radar/db/models/candidate.py`, `src/job_radar/db/models/handoff.py`, `tests/test_models.py`, `tests/test_normalization.py`

**Interfaces:**
- `CandidateJob` holds the current `india_eligibility_status`, `india_eligibility_classification`, `india_eligibility_reason_code`, `normalized_location`, and decision timestamp.
- Existing/legacy outbox rows can persist `exclusion_reason_code` when dispatch safety stops them.

- [ ] Write failing ORM/migration readback tests that create an India candidate, a blank candidate, a foreign candidate, and an ambiguous candidate; assert values survive a new session.
- [ ] Add nullable/backfilled-safe columns and indexes in the model and Alembic migration. Use `down_revision = "20260821_enrich_state"` unless the chain has changed.
- [ ] In upgrade, backfill existing candidates conservatively by classification; never mark a null historical location as India. In downgrade, remove the new columns/indexes only.
- [ ] Run the focused model/normalization persistence tests against in-memory SQLite and, separately, an explicit temporary database URL. Do not invoke `seed_database()` against the default database because it drops all tables.
- [ ] Commit migration, model, and persistence tests.

### Task 3: Enforce eligibility in normalization and all Job Ops boundaries

**Files:**
- Modify: `src/job_radar/services/normalization.py`, `src/job_radar/services/handoff.py`, `src/job_radar/api/v1/jobs.py`, `src/job_radar/api/v1/runs.py`
- Modify: `tests/test_normalization.py`, `tests/test_handoff.py`, `tests/test_api_runs_outcomes.py`

**Interfaces:**
- `NormalizationService.ingest_candidates(...)` persists a policy decision before any enqueue attempt.
- `HandoffProcessor.enqueue_candidate_handoff(candidate_id)` returns a result indicating queued versus excluded; it cannot create a queued row for excluded candidates.
- Dispatch rechecks the persisted/current decision before `push_candidate`.

- [ ] Write failing tests for each enqueue path: valid inline description, successful detail enrichment, re-observed candidate, manual push endpoint, and a pre-existing queued outbox row changed to ineligible.
- [ ] Remove `normalization.py`’s `"India"` default (`loc = ... else "India"`) and preserve raw missing location; update detail enrichment so a genuine India value is accepted rather than treated as a sentinel.
- [ ] Call the shared classifier after normalization and after usable detail enrichment, persist the newest decision, and enqueue only `eligible` candidates.
- [ ] Remove the Job Ops payload’s `"India"` fallback. Recheck candidate eligibility immediately before network dispatch; mark legacy disallowed rows `not_eligible` with reason and make zero HTTP calls.
- [ ] Update manual push endpoint/API serialization/run detail to expose eligibility status/classification/reason while never exposing sensitive raw provider payloads.
- [ ] Run focused normalization, handoff, API, and outbound-trap tests. Assert the trap has call count zero in all disabled-handoff and excluded cases.
- [ ] Commit this boundary change before starting provider work.

### Task 4: Make adapter routing contract-safe and preserve raw extraction data

**Files:**
- Modify: `src/job_radar/adapters/base.py`, `src/job_radar/adapters/registry.py`, `src/job_radar/adapters/families.py`, `src/job_radar/services/engine.py`
- Modify: `tests/test_adapters.py`, `tests/test_engine.py`

**Interfaces:**
- `ProviderContractUnsupported` maps to a structured board-run `parser_contract`/reason code.
- All adapter output uses truthful source location and does not apply local India exclusion.

- [ ] Write failing registry/engine tests proving an unverified new family cannot become a `GenericAdapter` and produces a held contract outcome.
- [ ] Write regression tests for existing generic/family parsing proving blank location remains `None`/blank and no parser supplies India, engineering, or full-time as an invented default.
- [ ] Replace dynamic unknown-family fallback with typed unsupported-contract handling and retain existing reviewed behavior only where explicitly configured.
- [ ] Remove Lever’s India substring rejection and Ashby/other source defaults in engine/family parsing; upstream URL filtering remains, but shared policy alone decides handoff eligibility.
- [ ] Run adapter and engine tests; commit the safe routing change.

### Task 5: Add verified-family cohorts one family at a time

**Files:**
- Modify: `src/job_radar/db/seed.py`, relevant existing adapter modules/engine/registry only when a canary proves a tenant config requirement.
- Create: `tests/fixtures/providers/workday/`, `greenhouse/`, `lever/`, `ashby/`.
- Modify: `tests/test_adapters.py`, `tests/test_engine.py`, `tests/test_models.py`.

**Cohort order:** Workday → Greenhouse → Lever → Ashby. Do not combine cohorts in one review/commit.

- [ ] For one approved board at a time, capture the standalone canary evidence listed in Section 0.1, obtain approval to use it, and freeze a scrubbed listing/detail fixture plus expected request configuration.
- [ ] Write fixture tests asserting exact source filters, repeated query/facet preservation, page offset/termination, source ID, canonical URL, raw location, and detail description.
- [ ] Add/adjust only the canary-backed tenant config and seed revision with `status="reviewed"`; never seed as enabled.
- [ ] Run the focused cohort tests and the full suite; commit exactly one provider cohort.
- [ ] Repeat until every eligible board from the table with a successful documented-family canary is represented. A failed canary remains a reviewed blocker, not a generic implementation.

### Task 6: Implement only canary-proven missing families and custom contracts

**Files:**
- Create only after approved evidence: `src/job_radar/adapters/smartrecruiters.py`, `src/job_radar/adapters/talent500.py`, or narrow `src/job_radar/adapters/custom_<board>.py` modules.
- Modify: `src/job_radar/adapters/registry.py`, `src/job_radar/services/engine.py`, `src/job_radar/db/seed.py`, provider fixtures/tests.

- [ ] Start SmartRecruiters and Talent500 as separate reviewable family tasks; each defines explicit listing/detail request models, allowed origins, source IDs, canonical URLs, raw location, and bounded pagination.
- [ ] Require a second independently canaried compatible site before generalizing a purported shared provider; otherwise keep the adapter board-specific.
- [ ] Implement each first-party custom contract in a focused module with no generic selector fallback; include fixture tests for source filter and pagination retention.
- [ ] Keep every uncertain Phenom/Eightfold/Zoho/first-party row disabled until its individual canary passes; no source-table label is an exemption.
- [ ] For the blocked duplicate-source row, accept no code/seed enablement until a corrected target is supplied and verified.
- [ ] Commit each provider/board cohort separately after focused tests and full suite pass.

### Task 7: Seed/readback, completion receipt, and rollback rehearsal

**Files:**
- Modify: `src/job_radar/db/seed.py`, `tests/test_models.py`, `tests/test_handoff.py`, `tests/test_discord_notifier.py` if reporting changes.
- Create: `docs/verification/new-boards-<date>-receipt.md` only when implementation is approved and completed.

- [ ] Add a deterministic isolated-database test that seeds into a temporary `sqlite+aiosqlite:///...` path, reads boards/revisions in a new session, and checks every source target/config status. Never point it to the application default database.
- [ ] Assert all 65 source records exist exactly once, source URLs are byte-for-byte retained, status is `draft`/`reviewed` until their contract is approved, and no duplicate source key exists.
- [ ] Run the complete suite using the mandated command; fail the release gate on any test failure, unexpected network call, or enabled unverified board.
- [ ] Produce a local completion receipt listing: exact inventory count, enabled/reviewed/blocked board counts, each canary reference/outcome, fixture names, test command/result, isolated DB path (not credentials), eligibility counts by reason, and explicit `Job Ops HTTP calls: 0` for local verification.
- [ ] Rehearse rollback locally: disable/revert one newly enabled revision to the previous reviewed revision, apply the Alembic downgrade only to the temporary database, and verify current candidates/outbox semantics remain intact according to the migration test.
- [ ] Commit docs/receipt only after approval; do not merge, push, deploy, or alter `main`.

---

## 5. Test Matrix and Mandatory Gates

| Area | Required assertions | Local gate |
| --- | --- | --- |
| Classifier | Indian city/state, explicit India remote, India-containing multi-location, null/blank/unknown eligible; foreign and ambiguous non-empty excluded with stable reason | `tests/test_india_eligibility.py` |
| Normalization | No invented India/default location; decision persisted on create/re-observe/enrichment; exclusions not enqueued | `tests/test_normalization.py` |
| Handoff | Disabled settings cause zero posts; excluded/manual/legacy queued records never post; accepted payload preserves nullable location | `tests/test_handoff.py` with `httpx.AsyncClient.post` trap |
| API | Manual push reports non-eligible outcome; run/jobs serialization exposes classification/reason | API route tests |
| Existing adapters | No regression in existing reviewed providers; raw locations and exact configurations survive parsing | `tests/test_adapters.py`, `tests/test_engine.py` |
| New provider fixture | Listing/detail schema, source ID, canonical detail URL, filter/query/facet/pagination preservation, raw location | one scrubbed fixture set per canary-approved board |
| Migration/readback | Upgrade/downgrade and fresh-session durability; isolated seed readback | model/migration tests using temp DB only |
| Inventory | 65 canonical rows, each once, source target exact, no unapproved enabled board | seed/config inventory test |
| Full suite | All tests pass through worktree imports; test-only handoff stays disabled | mandated pytest command |
| Live canary | Separate authorized run validates contract and records evidence before implementation/enablement | manual approval gate; not part of local suite |

**Mechanical local handoff safety:** Test fixtures must make `HandoffProcessor.process_pending_outbox()` and `JobOpsClient` see disabled persisted and environment settings, monkeypatch outbound `httpx.AsyncClient.post` to throw, then assert zero calls. A mock returning simulated success is insufficient on its own because it does not prove the network path was unreachable.

---

## 6. Rollback, Reporting, and Approval Gates

### Rollback

1. **Contract failure:** pause/review the affected `BoardRevision`; retain evidence/reason and revert only that provider config to `reviewed`. Do not change unrelated boards.
2. **Parser regression:** ship a focused revert of the cohort commit, mark the board `parser_contract`, and preserve fixtures for diagnosis.
3. **Eligibility regression:** disable handoff, revert the policy migration/application commit in the isolated environment, and query candidates/outbox for the durable decisions before any remediation. Never delete candidate history to hide an incorrect decision.
4. **Migration rollback:** test Alembic downgrade only against the temporary database. Production migration rollback needs a separate approved change procedure.
5. **No side effects:** local tests and rollback rehearsal use fakes/fixtures only; no Job Ops, no deployment, no canonical database.

### Completion receipt

The final local report must state: worktree and branch; plan revision; 65/65 inventory validation; source URL preservation result; approved/blocked contracts and reasons; board statuses; provider fixture coverage; India eligibility totals by classification; database readback outcome; exact pytest command and result; outbound Job Ops HTTP-call count; rollback rehearsal result; and any remaining explicit blockers (including the duplicate-source row).

### Final integration gate

Implementation completion does **not** authorize a merge, push, deployment, scheduler enablement, production configuration change, Job Ops invocation, or modification of canonical `main`. Obtain separate, explicit approval for each outward-facing action after the local completion receipt is reviewed.

---

## 7. Plan Self-Review Checklist

- [x] Section 0 indexes requirements, source inventory, adapter documentation, and current code/test boundaries.
- [x] The numbered inventory contains 65 rows and preserves every canonical source board name exactly once.
- [x] Each row identifies source target, proposed acquisition, detail strategy, filters/pagination, raw location treatment, fixture need, canary status, and blocker where applicable.
- [x] Unsupported provider assumptions are corrected rather than copied: duplicate source, GoDaddy, Zoho, VMware, and Talent500/Stratsy.
- [x] The India gate covers all boards and all automatic/manual/dispatch handoff boundaries, including blank/unknown and ambiguous location semantics.
- [x] Durable candidate eligibility and exclusion observability are specified; excluded candidates are not silently queued.
- [x] Local-only, disabled-handoff, zero-outbound-call tests and isolated database readback are mandatory.
- [x] File list, phased execution, test matrix, canary/full-suite gates, rollback, completion report, and no-merge/deploy/push approval gate are explicit.

## Concise Summary

Implement the shared India classifier and durable handoff boundary first, then make adapter routing reject unverified contracts. Integrate only one canary-backed provider or custom cohort at a time, preserve every source URL/filter exactly, keep all local tests isolated with handoff mechanically blocked, and leave unresolved contracts disabled. The required plan artifact is `IMPLEMENTATION_PLAN.md`.
