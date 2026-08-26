# Adapters Master Index & Data Contracts

This index maps every active company board in **Job Radar** (under `## Company` in `10 Personal/Career/Job Boards.md`) to its dedicated provider adapter document.

Each linked document provides:
1. **Job Listing Acquisition Logic:** Endpoints, HTTP methods, headers, payload/query structures, and pagination mechanics.
2. **Job Details Extraction Logic:** Primary APIs, DOM/JSON-LD fallback selectors, structured script hydration paths, and sanitization/cleaning rules.

---

## Adapter Families & Company Mapping

| Company Board | Adapter Family ID | Dedicated Adapter Contract Document |
| :--- | :--- | :--- |
| **Abnormal AI** | `custom` | [[20 Projects/Job Radar/Adapters/[Adapter] Custom Boards\|[Adapter] Custom Boards]] |
| **Adobe** | `workday` | [[20 Projects/Job Radar/Adapters/[Adapter] Workday\|[Adapter] Workday]] |
| **Amazon** | `amazon_jobs` | [[20 Projects/Job Radar/Adapters/[Adapter] Amazon\|[Adapter] Amazon]] |
| **Ameriprise** | `phenom` | [[20 Projects/Job Radar/Adapters/[Adapter] Phenom\|[Adapter] Phenom]] |
| **Amex** | `oracle` | [[20 Projects/Job Radar/Adapters/[Adapter] Oracle HCM\|[Adapter] Oracle HCM]] |
| **Apple** | `apple_jobs` | [[20 Projects/Job Radar/Adapters/[Adapter] Apple\|[Adapter] Apple]] |
| **Aspora** | `ashbyhq` | [[20 Projects/Job Radar/Adapters/[Adapter] Ashby\|[Adapter] Ashby]] |
| **Best Buy** | `talent500` | [[20 Projects/Job Radar/Adapters/[Adapter] Talent500\|[Adapter] Talent500]] |
| **Celonis** | `custom` | [[20 Projects/Job Radar/Adapters/[Adapter] Custom Boards\|[Adapter] Custom Boards]] |
| **Cisco** | `workday` | [[20 Projects/Job Radar/Adapters/[Adapter] Workday\|[Adapter] Workday]] |
| **Cognite** | `greenhouse` | [[20 Projects/Job Radar/Adapters/[Adapter] Greenhouse\|[Adapter] Greenhouse]] |
| **Coupa** | `custom` | [[20 Projects/Job Radar/Adapters/[Adapter] Custom Boards\|[Adapter] Custom Boards]] |
| **eBay** | `workday` | [[20 Projects/Job Radar/Adapters/[Adapter] Workday\|[Adapter] Workday]] |
| **EisnerAmper** | `workday` | [[20 Projects/Job Radar/Adapters/[Adapter] Workday\|[Adapter] Workday]] |
| **Evernorth** | `talent500` | [[20 Projects/Job Radar/Adapters/[Adapter] Talent500\|[Adapter] Talent500]] |
| **Google** | `google_careers` | [[20 Projects/Job Radar/Adapters/[Adapter] Google Careers\|[Adapter] Google Careers]] |
| **HighRadius** | `custom` | [[20 Projects/Job Radar/Adapters/[Adapter] Custom Boards\|[Adapter] Custom Boards]] |
| **HP** | `eightfold` | [[20 Projects/Job Radar/Adapters/[Adapter] Eightfold\|[Adapter] Eightfold]] |
| **JioStar** | `workday` | [[20 Projects/Job Radar/Adapters/[Adapter] Workday\|[Adapter] Workday]] |
| **JPMC** | `oracle` | [[20 Projects/Job Radar/Adapters/[Adapter] Oracle HCM\|[Adapter] Oracle HCM]] |
| **Marriott Tech** | `talent500` | [[20 Projects/Job Radar/Adapters/[Adapter] Talent500\|[Adapter] Talent500]] |
| **Mattel** | `custom` | [[20 Projects/Job Radar/Adapters/[Adapter] Custom Boards\|[Adapter] Custom Boards]] |
| **McD** | `talent500` | [[20 Projects/Job Radar/Adapters/[Adapter] Talent500\|[Adapter] Talent500]] |
| **Meta** | `meta_careers` | [[20 Projects/Job Radar/Adapters/[Adapter] Meta Careers\|[Adapter] Meta Careers]] |
| **Microsoft** | `eightfold` | [[20 Projects/Job Radar/Adapters/[Adapter] Eightfold\|[Adapter] Eightfold]] |
| **Motorola Solutions** | `workday` | [[20 Projects/Job Radar/Adapters/[Adapter] Workday\|[Adapter] Workday]] |
| **Novartis** | `custom` | [[20 Projects/Job Radar/Adapters/[Adapter] Custom Boards\|[Adapter] Custom Boards]] |
| **Oracle** | `oracle` | [[20 Projects/Job Radar/Adapters/[Adapter] Oracle HCM\|[Adapter] Oracle HCM]] |
| **Philips** | `phenom` | [[20 Projects/Job Radar/Adapters/[Adapter] Phenom\|[Adapter] Phenom]] |
| **Plane** | `ashbyhq` | [[20 Projects/Job Radar/Adapters/[Adapter] Ashby\|[Adapter] Ashby]] |
| **Qualcomm** | `eightfold` | [[20 Projects/Job Radar/Adapters/[Adapter] Eightfold\|[Adapter] Eightfold]] |
| **RBCTech** | `stratsy` | [[20 Projects/Job Radar/Adapters/[Adapter] Stratsy\|[Adapter] Stratsy]] |
| **Regal Rexnord** | `workday` | [[20 Projects/Job Radar/Adapters/[Adapter] Workday\|[Adapter] Workday]] |
| **Resilinc** | `lever` | [[20 Projects/Job Radar/Adapters/[Adapter] Lever\|[Adapter] Lever]] |
| **Solera** | `workday` | [[20 Projects/Job Radar/Adapters/[Adapter] Workday\|[Adapter] Workday]] |
| **Tesco** | `avature` | [[20 Projects/Job Radar/Adapters/[Adapter] Avature\|[Adapter] Avature]] |
| **Thomson Reuters** | `workday` | [[20 Projects/Job Radar/Adapters/[Adapter] Workday\|[Adapter] Workday]] |
| **TMUS** | `talent500` | [[20 Projects/Job Radar/Adapters/[Adapter] Talent500\|[Adapter] Talent500]] |
| **TP** | `workday` | [[20 Projects/Job Radar/Adapters/[Adapter] Workday\|[Adapter] Workday]] |
| **Vanguard** | `google_cloud_talent_solution` | [[20 Projects/Job Radar/Adapters/[Adapter] Google Cloud Talent Solution\|[Adapter] Google Cloud Talent Solution]] |
| **Walmart** | `workday` | [[20 Projects/Job Radar/Adapters/[Adapter] Workday\|[Adapter] Workday]] |
| **Weave** | `ashbyhq` | [[20 Projects/Job Radar/Adapters/[Adapter] Ashby\|[Adapter] Ashby]] |
| **Wynploy** | `zoho` | [[20 Projects/Job Radar/Adapters/[Adapter] Zoho Recruit\|[Adapter] Zoho Recruit]] |
