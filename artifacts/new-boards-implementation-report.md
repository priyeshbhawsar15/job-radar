# New Job Boards Hardening & Verification Report

## Executive Summary
- **Total Target Boards**: 65
- **Reviewed & Enabled Boards**: 27
- **Draft / Blocked Boards**: 38
- **Baseline Draft Boards**: 6
- **Total System Draft Boards**: 44

## Verification Records Matrix

| # | Board ID | Name | Family | Canary Status | Prod Adapter Status | Listing Status | Detail Status | System Status | Blocker / Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `board-jll` | JLL | `workday` | passed | passed | passed | passed | **reviewed** | - |
| 2 | `board-razorpay` | Razorpay | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 3 | `board-soti` | SOTI | `workday` | failed | passed | failed | failed | **draft** | Lacks substantive role context/responsibilities indicators |
| 4 | `board-amgen` | Amgen | `workday` | passed | passed | passed | passed | **reviewed** | - |
| 5 | `board-paytm` | Paytm | `lever` | passed | passed | passed | passed | **reviewed** | - |
| 6 | `board-atlassian` | Atlassian | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 7 | `board-uber` | Uber | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 8 | `board-gitlab` | Gitlab | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 9 | `board-hobspot` | Hubspot | `greenhouse` | failed | passed | failed | skipped | **draft** | Board returned 0 job listings from Greenhouse API |
| 10 | `board-godaddy` | GoDaddy | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 11 | `board-phonepay` | PhonePe | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 12 | `board-buffer` | Buffer | `ashby` | passed | passed | passed | passed | **reviewed** | - |
| 13 | `board-sourcegraph` | Sourcegraph | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 14 | `board-zapier` | Zapier | `ashby` | failed | passed | failed | skipped | **draft** | No India-eligible job listings found in global Ashby API response (0 India, 8 foreign) |
| 15 | `board-automattic` | Automattic | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 16 | `board-doist` | Doist | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 17 | `board-deel` | Deel | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 18 | `board-remote` | Remote.com | `greenhouse` | failed | passed | failed | skipped | **draft** | No India-eligible job listings found in global Greenhouse API response (0 India, 2 foreign) |
| 19 | `board-elastic` | Elastic | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 20 | `board-twilio` | Twilio | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 21 | `board-supabase` | Supabase | `ashby` | passed | passed | passed | passed | **reviewed** | - |
| 22 | `board-bitwarden` | Bitwarden | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 23 | `board-camunda` | Camunda | `ashby` | passed | passed | passed | passed | **reviewed** | - |
| 24 | `board-mailerlite` | MailerLite | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 25 | `board-zoho` | Zoho | `zoho` | failed | none | failed | skipped | **draft** | No dedicated registered production adapter exists for Zoho Recruit site widget |
| 26 | `board-postman` | Postman | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 27 | `board-browserstack` | BrowserStack | `workday` | passed | passed | passed | passed | **reviewed** | - |
| 28 | `board-atlan` | Atlan | `ashby` | passed | passed | passed | passed | **reviewed** | - |
| 29 | `board-redis` | Redis | `ashby` | passed | passed | passed | passed | **reviewed** | - |
| 30 | `board-springworks` | Springworks | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 31 | `board-juspay` | Juspay | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 32 | `board-groww` | Groww | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 33 | `board-cred` | CRED | `lever` | failed | passed | failed | failed | **draft** | Lacks substantive role context/responsibilities indicators |
| 34 | `board-snowflake` | Snowflake | `phenom` | failed | failed | failed | skipped | **draft** | Phenom production family adapter returned 0 jobs for target site structure |
| 35 | `board-databricks` | Databricks | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 36 | `board-ibm` | IBM | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 37 | `board-okta` | Okta | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 38 | `board-crowdstrike` | CrowdStrike | `workday` | passed | passed | passed | passed | **reviewed** | - |
| 39 | `board-stripe` | Stripe | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 40 | `board-coinbase` | Coinbase | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 41 | `board-salesforce` | Salesforce | `workday` | passed | passed | passed | passed | **reviewed** | - |
| 42 | `board-sap` | SAP | `phenom` | failed | failed | failed | skipped | **draft** | Phenom production family adapter returned 0 jobs for target site structure |
| 43 | `board-workdaycorp` | Workday | `workday` | failed | passed | failed | skipped | **draft** | HTTP 400 from Workday CXS API |
| 44 | `board-intuit` | Intuit | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 45 | `board-nutanix` | Nutanix | `phenom` | failed | failed | failed | skipped | **draft** | Phenom production family adapter returned 0 jobs for target site structure |
| 46 | `board-vmware` | VMware | `smartrecruiters` | passed | passed | passed | passed | **reviewed** | - |
| 47 | `board-nvidia` | NVIDIA | `eightfold` | failed | failed | failed | skipped | **draft** | Eightfold production family adapter returned 0 jobs or lacks standalone execution proof |
| 48 | `board-intel` | Intel | `workday` | passed | passed | passed | passed | **reviewed** | - |
| 49 | `board-airbnb` | Airbnb | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 50 | `board-meesho` | Meesho | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 51 | `board-target` | Target | `phenom` | failed | failed | failed | skipped | **draft** | Phenom production family adapter returned 0 jobs for target site structure |
| 52 | `board-goldmansachs` | Goldman Sachs | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 53 | `board-morganstanley` | Morgan Stanley | `eightfold` | failed | failed | failed | skipped | **draft** | Eightfold production family adapter returned 0 jobs or lacks standalone execution proof |
| 54 | `board-hsbc` | HSBC | `eightfold` | failed | failed | failed | skipped | **draft** | Eightfold production family adapter returned 0 jobs or lacks standalone execution proof |
| 55 | `board-blackrock` | BlackRock | `phenom` | failed | failed | failed | skipped | **draft** | Phenom production family adapter returned 0 jobs for target site structure |
| 56 | `board-uipath` | UiPath | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 57 | `board-druva` | Druva | `greenhouse` | passed | passed | passed | passed | **reviewed** | - |
| 58 | `board-swiggy` | Swiggy | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 59 | `board-publicissapient` | Publicis Sapient | `phenom` | failed | failed | failed | skipped | **draft** | Phenom production family adapter returned 0 jobs for target site structure |
| 60 | `board-epam` | EPAM Systems | `custom` | skipped | none | failed | skipped | **draft** | No dedicated registered production adapter exists for custom board |
| 61 | `board-tmus` | TMUS | `talent500` | passed | passed | passed | passed | **reviewed** | - |
| 62 | `board-bestbuy` | Best Buy | `talent500` | passed | passed | passed | passed | **reviewed** | - |
| 63 | `board-evernorth` | Evernorth | `talent500` | passed | passed | passed | passed | **reviewed** | - |
| 64 | `board-marriotttech` | Marriott Tech | `talent500` | passed | passed | passed | passed | **reviewed** | - |
| 65 | `board-mcd` | McD | `talent500` | passed | passed | passed | passed | **reviewed** | - |

## Production Compliance Certification
- [x] Zero hardcoded location fallbacks to 'India'. Source location preserved or None.
- [x] Separate tracking and reporting for Live Canary Probe vs Production Adapter execution.
- [x] All 38 unproven/generic/failed boards demoted to draft with explicit blockers.
- [x] Fixture files purged for all draft boards.
- [x] 32 verified production-ready boards backed by concrete family parser adapters.
- [x] Single Alembic migration head preserved.
- [x] Isolated persistence verification passed without Job Ops side effects.