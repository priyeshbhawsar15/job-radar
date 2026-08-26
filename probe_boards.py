"""Bounded live canary runner for 65 target job boards."""

import asyncio
import json
import re
import urllib.parse
from typing import Dict, Any, List, Optional
import httpx
import html.parser

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

BOARDS_INVENTORY = [
    {"num": 1, "name": "JLL", "url": "https://jll.wd1.myworkdayjobs.com/en-US/jllcareers?locationCountry=c4f78be1a8f14da0ab49ce1162348a5e&timeType=72e81fa31e6f01cf9aa5a4251a4e4e00&jobFamilyGroup=c608fc06410f01484a9fec7aba539450&jobFamilyGroup=f134f8e1c0811001fe9e2695d0c80000", "family": "workday"},
    {"num": 2, "name": "Razorpay", "url": "https://job-boards.greenhouse.io/razorpaysoftwareprivatelimited?departments%5B%5D=4024806005", "family": "greenhouse"},
    {"num": 3, "name": "SOTI", "url": "https://soti.wd3.myworkdayjobs.com/en-US/Careers?locations=f35dd6d3a7da01adef33e8916446200f&locations=27190dd10fff1074b213f2d1500595ed&EEB_-_Job_Categories_for_External_Site_Extended=267bdbcbbd671001697698c0843a0001", "family": "workday"},
    {"num": 4, "name": "Amgen", "url": "https://amgen.wd1.myworkdayjobs.com/en-US/Careers?locations=be0893cb78ed012e9c728ee58144ec3b&jobFamilyGroup=3b16b67900e510859633b621ace7c537", "family": "workday"},
    {"num": 5, "name": "Paytm", "url": "https://jobs.lever.co/paytm?department=Technology&commitment=Full-time%20Employment", "family": "lever"},
    {"num": 6, "name": "Atlassian", "url": "https://www.atlassian.com/company/careers/all-jobs?team=Engineering&location=India&search=", "family": "custom"},
    {"num": 7, "name": "Uber", "url": "https://jobs.uber.com/en/jobs/?search=software&countries=India", "family": "custom"},
    {"num": 8, "name": "Gitlab", "url": "https://job-boards.greenhouse.io/gitlab", "family": "greenhouse"},
    {"num": 9, "name": "Hobspot", "url": "https://job-boards.greenhouse.io/hubspot", "family": "greenhouse"},
    {"num": 10, "name": "Godaddy", "url": "https://careers.godaddy/jobs/search?page=1&query=&department_uids[]=6ed98616cdc63adf0b08529f08290235&country_codes[]=IN", "family": "greenhouse"},
    {"num": 11, "name": "Phonepay", "url": "https://job-boards.greenhouse.io/phonepe?gh_src=961e65dc3us", "family": "greenhouse"},
    {"num": 12, "name": "Buffer", "url": "https://jobs.ashbyhq.com/buffer", "family": "ashby"},
    {"num": 13, "name": "Sourcegraph", "url": "https://boards-api.greenhouse.io/v1/boards/sourcegraph91/jobs?content=true", "family": "greenhouse"},
    {"num": 14, "name": "Zapier", "url": "https://jobs.ashbyhq.com/zapier", "family": "ashby"},
    {"num": 15, "name": "Automattic", "url": "https://automattic.com/work-with-us/jobs/", "family": "custom"},
    {"num": 16, "name": "Doist", "url": "https://doist.com/careers#open-roles", "family": "custom"},
    {"num": 17, "name": "Deel", "url": "https://www.deel.com/careers/?department=engineering", "family": "custom"},
    {"num": 18, "name": "Remote.com", "url": "https://job-boards.greenhouse.io/remote", "family": "greenhouse"},
    {"num": 19, "name": "Elastic", "url": "https://jobs.elastic.co/jobs/country/india?size=n_20_n", "family": "custom"},
    {"num": 20, "name": "Twilio", "url": "https://job-boards.greenhouse.io/twilio", "family": "greenhouse"},
    {"num": 21, "name": "Supabase", "url": "https://jobs.ashbyhq.com/supabase", "family": "ashby"},
    {"num": 22, "name": "Bitwarden", "url": "https://job-boards.greenhouse.io/bitwarden", "family": "greenhouse"},
    {"num": 23, "name": "Camunda", "url": "https://jobs.ashbyhq.com/camunda", "family": "ashby"},
    {"num": 24, "name": "MailerLite", "url": "https://www.mailerlite.com/jobs", "family": "custom"},
    {"num": 25, "name": "Zoho", "url": "https://www.zoho.com/careers/", "family": "zoho"},
    {"num": 26, "name": "Postman", "url": "https://job-boards.greenhouse.io/postman", "family": "greenhouse"},
    {"num": 27, "name": "BrowserStack", "url": "https://browserstack.wd3.myworkdayjobs.com/External?jobFamilyGroup=0cb9174e33c9100190f156427de80000", "family": "workday"},
    {"num": 28, "name": "Atlan", "url": "https://jobs.ashbyhq.com/atlan", "family": "ashby"},
    {"num": 29, "name": "Redis", "url": "https://jobs.ashbyhq.com/redis", "family": "ashby"},
    {"num": 30, "name": "Springworks", "url": "https://jobs.goodfit.so/careers/springworks", "family": "custom"},
    {"num": 31, "name": "Juspay", "url": "https://juspay.io/careers", "family": "custom"},
    {"num": 32, "name": "Groww", "url": "https://job-boards.eu.greenhouse.io/groww", "family": "greenhouse"},
    {"num": 33, "name": "CRED", "url": "https://jobs.lever.co/cred", "family": "lever"},
    {"num": 34, "name": "Snowflake", "url": "https://careers.snowflake.com/us/en/search-results", "family": "phenom"},
    {"num": 35, "name": "Databricks", "url": "https://job-boards.greenhouse.io/databricks", "family": "greenhouse"},
    {"num": 36, "name": "IBM", "url": "https://careers.ibm.com/en_IN/careers/search", "family": "custom"},
    {"num": 37, "name": "Okta", "url": "https://job-boards.greenhouse.io/okta", "family": "greenhouse"},
    {"num": 38, "name": "CrowdStrike", "url": "https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers?locationCountry=c4f78be1a8f14da0ab49ce1162348a5e&Job_Family=1408861ee6e201641be2c2f6b000c00b&Job_Family=cb19f044639b1001f6a02595bc920000", "family": "workday"},
    {"num": 39, "name": "Stripe", "url": "https://stripe.com/careers/search?teams=Products&locations=Asia+Pacific--India&employment_types=Full+time", "family": "custom"},
    {"num": 40, "name": "Coinbase", "url": "https://job-boards.greenhouse.io/coinbase", "family": "greenhouse"},
    {"num": 41, "name": "Salesforce", "url": "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site", "family": "workday"},
    {"num": 42, "name": "SAP", "url": "https://jobs.sap.com/search/?createNewAlert=false&q=&locationsearch=&optionsFacetsDD_department=Software-Design+and+Development&optionsFacetsDD_customfield3=&optionsFacetsDD_country=IN", "family": "phenom"},
    {"num": 43, "name": "Workday", "url": "https://workday.wd5.myworkdayjobs.com/Workday/?source=Careers_Website&Location_Country=c4f78be1a8f14da0ab49ce1162348a5e&jobFamilyGroup=8c5ce7a1cffb43e0a819c249a49fcb00", "family": "workday"},
    {"num": 44, "name": "Intuit", "url": "https://jobs.intuit.com/search-jobs?acm=9211424&alrpm=ALL&ascf=[{%22key%22:%22ALL%22,%22value%22:%22%22}]", "family": "custom"},
    {"num": 45, "name": "Nutanix", "url": "https://careers.nutanix.com/en/jobs/?search=&country=India&team=Engineering&type=Full-Time&pagesize=20#results", "family": "phenom"},
    {"num": 46, "name": "VMware", "url": "https://careers.smartrecruiters.com/Vmware2", "family": "smartrecruiters"},
    {"num": 47, "name": "NVIDIA", "url": "https://jobs.nvidia.com/careers?start=0&location=Hyderabad%2C++Telangana%2C++India&pid=893395509555&sort_by=distance&filter_distance=160&filter_include_remote=1&filter_include_relocation=0&filter_job_category=engineering", "family": "eightfold"},
    {"num": 48, "name": "Intel", "url": "https://intel.wd1.myworkdayjobs.com/External?locations=1e4a4eb3adf101f44070f976bf8184cf&jobFamilyGroup=ace7a3d23b7e01a0544279031a0ec85c", "family": "workday"},
    {"num": 49, "name": "Airbnb", "url": "https://job-boards.greenhouse.io/airbnb", "family": "greenhouse"},
    {"num": 50, "name": "Meesho", "url": "https://www.meesho.io/jobs?&t=Business%20Analytics,Backend,QA,Infrastructure,CTO%20Office,Data%20Engineering,Data%20Science,Demand,Frontend,Supply,Security", "family": "custom"},
    {"num": 51, "name": "Target", "url": "https://corporate.target.com/careers/job-search?currentPage=1&jobAreas=Target%20Tech&schedule=Full-time&country=India", "family": "phenom"},
    {"num": 52, "name": "Goldman Sachs", "url": "https://higher.gs.com/results?JOB_FUNCTION=Software%20Engineering&page=1&sort=POSTED_DATE", "family": "custom"},
    {"num": 53, "name": "Morgan Stanley", "url": "https://morganstanley.eightfold.ai/careers?source=mscom&start=0&location=India&pid=549798643496&sort_by=distance&filter_include_remote=1&filter_include_relocation=0&filter_businessarea=technology&filter_employmenttype=full+time", "family": "eightfold"},
    {"num": 54, "name": "HSBC", "url": "https://portal.careers.hsbc.com/careers?query=software&location=India&pid=563774612163818&domain=hsbc.com&sort_by=relevance&triggerGoButton=false", "family": "eightfold"},
    {"num": 55, "name": "BlackRock", "url": "https://careers.blackrock.com/search-jobs/software/India/45831/1/2/1269750/22/79/0/2", "family": "phenom"},
    {"num": 56, "name": "UiPath", "url": "https://www.uipath.com/careers/jobs", "family": "custom"},
    {"num": 57, "name": "Druva", "url": "https://job-boards.greenhouse.io/druva", "family": "greenhouse"},
    {"num": 58, "name": "Swiggy", "url": "https://careers.swiggy.com/#/careers?career_page_category=Technology", "family": "custom"},
    {"num": 59, "name": "Publicis Sapient", "url": "https://careers.publicissapient.com/job-search?q=&location_q=India&skipLocation=true&country=India&sortOrder=desc&teams=Technology+and+Engineering", "family": "phenom"},
    {"num": 60, "name": "EPAM Systems", "url": "https://careers.epam.com/en/jobs/india?city=4060741400035606933&sort_by=relevance&specialization=developer&utm_content=job-search&utm_term=start-your-search-here", "family": "custom"},
    {"num": 61, "name": "TMUS", "url": "https://talent500.com/joblist/?company=TMUS+Global+Solutions&sort_by_created_date=1&offset=0&limit=20", "family": "talent500"},
    {"num": 62, "name": "Best Buy", "url": "https://talent500.com/joblist/?company=Best+Buy&sort_by_created_date=1&offset=0&limit=20", "family": "talent500"},
    {"num": 63, "name": "Evernorth", "url": "https://talent500.com/joblist/?company=Evernorth&sort_by_created_date=1&offset=0&limit=20", "family": "talent500"},
    {"num": 64, "name": "Marriott Tech", "url": "https://talent500.com/joblist/?company=Marriott+Tech+Accelerator&sort_by_created_date=1&offset=0&limit=20", "family": "talent500"},
    {"num": 65, "name": "McD", "url": "https://talent500.com/joblist/?company=McDonalds+in+India&sort_by_created_date=1&offset=0&limit=20", "family": "talent500"},
]

from job_radar.services.location import is_india_eligible

async def probe_board(client: httpx.AsyncClient, item: Dict[str, Any]) -> Dict[str, Any]:
    num = item["num"]
    name = item["name"]
    target_url = item["url"]
    family = item["family"]

    result = {
        "num": num,
        "name": name,
        "target_url": target_url,
        "family": family,
        "status": "active",
        "count": 0,
        "sample_id": None,
        "sample_url": None,
        "sample_title": None,
        "sample_location": None,
        "india_eligible": True,
        "blocker": None,
        "raw_payload_sample": None
    }

    try:
        if family == "greenhouse":
            slug = None
            if "boards-api.greenhouse.io" in target_url:
                m = re.search(r"/boards/([^/]+)/jobs", target_url)
                if m: slug = m.group(1)
            elif "greenhouse.io" in target_url:
                parsed = urllib.parse.urlparse(target_url)
                slug = parsed.path.strip("/").split("/")[0]

            if not slug and "godaddy" in target_url:
                slug = "godaddy"

            if slug:
                api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
                r = await client.get(api_url, timeout=10.0)
                if r.status_code == 200:
                    data = r.json()
                    jobs = data.get("jobs", [])
                    result["count"] = len(jobs)
                    if jobs:
                        j0 = jobs[0]
                        result["sample_id"] = str(j0.get("id"))
                        result["sample_url"] = j0.get("absolute_url")
                        result["sample_title"] = j0.get("title")
                        loc_str = j0.get("location", {}).get("name") if isinstance(j0.get("location"), dict) else str(j0.get("location"))
                        result["sample_location"] = loc_str
                        result["raw_payload_sample"] = j0
                    elif len(jobs) == 0:
                        result["status"] = "active_empty"
                else:
                    result["blocker"] = f"Greenhouse API returned HTTP {r.status_code}"
                    result["status"] = "draft"
            else:
                result["blocker"] = "Could not parse Greenhouse slug"
                result["status"] = "draft"

        elif family == "ashby":
            parsed = urllib.parse.urlparse(target_url)
            slug = parsed.path.strip("/").split("/")[0]
            api_url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
            r = await client.get(api_url, timeout=10.0)
            if r.status_code == 200:
                data = r.json()
                jobs = data.get("jobs", [])
                result["count"] = len(jobs)
                if jobs:
                    j0 = jobs[0]
                    result["sample_id"] = j0.get("id")
                    result["sample_url"] = j0.get("jobUrl") or f"https://jobs.ashbyhq.com/{slug}/{j0.get('id')}"
                    result["sample_title"] = j0.get("title")
                    result["sample_location"] = j0.get("locationName")
                    result["raw_payload_sample"] = j0
                elif len(jobs) == 0:
                    result["status"] = "active_empty"
            else:
                result["blocker"] = f"Ashby API returned HTTP {r.status_code}"
                result["status"] = "draft"

        elif family == "lever":
            parsed = urllib.parse.urlparse(target_url)
            slug = parsed.path.strip("/").split("/")[0]
            api_url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
            r = await client.get(api_url, timeout=10.0)
            if r.status_code == 200:
                jobs = r.json()
                if isinstance(jobs, list):
                    result["count"] = len(jobs)
                    if jobs:
                        j0 = jobs[0]
                        result["sample_id"] = j0.get("id")
                        result["sample_url"] = j0.get("hostedUrl")
                        result["sample_title"] = j0.get("text")
                        result["sample_location"] = j0.get("categories", {}).get("location")
                        result["raw_payload_sample"] = j0
                    else:
                        result["status"] = "active_empty"
            else:
                result["blocker"] = f"Lever API returned HTTP {r.status_code}"
                result["status"] = "draft"

        elif family == "workday":
            parsed = urllib.parse.urlparse(target_url)
            tenant_host = parsed.netloc
            tenant = tenant_host.split(".")[0]
            path_parts = [p for p in parsed.path.split("/") if p]

            site = "Careers"
            if path_parts:
                last_part = path_parts[-1].split("?")[0]
                if last_part not in ("en-US", "en_US"):
                    site = last_part
                elif len(path_parts) > 1:
                    site = path_parts[1].split("?")[0]

            if "jllcareers" in target_url:
                site = "jllcareers"

            cxs_url = f"https://{tenant_host}/wday/cxs/{tenant}/{site}/jobs"

            query_params = urllib.parse.parse_qs(parsed.query)
            payload = {
                "appliedFacets": {},
                "limit": 20,
                "offset": 0,
                "searchText": ""
            }
            for k, v in query_params.items():
                if k in ("locationCountry", "locations", "jobFamilyGroup", "Job_Family", "timeType", "Location_Country"):
                    payload["appliedFacets"][k] = v

            r = await client.post(cxs_url, json=payload, timeout=10.0)
            if r.status_code == 200:
                data = r.json()
                total = data.get("total", 0)
                jobs = data.get("jobPostings", [])
                result["count"] = len(jobs)
                if jobs:
                    j0 = jobs[0]
                    result["sample_id"] = j0.get("bulletFields", [None])[0] or j0.get("title")
                    sub_path = j0.get("externalPath")
                    result["sample_url"] = f"https://{tenant_host}/en-US/{site}{sub_path}" if sub_path else target_url
                    result["sample_title"] = j0.get("title")
                    result["sample_location"] = j0.get("locationsText")
                    result["raw_payload_sample"] = j0
                elif total == 0 or len(jobs) == 0:
                    result["status"] = "active_empty"
            else:
                result["blocker"] = f"Workday CXS API returned HTTP {r.status_code}"
                result["status"] = "draft"

        elif family == "smartrecruiters":
            parsed = urllib.parse.urlparse(target_url)
            company_slug = parsed.path.strip("/").split("/")[0]
            api_url = f"https://api.smartrecruiters.com/v1/companies/{company_slug}/postings"
            r = await client.get(api_url, timeout=10.0)
            if r.status_code == 200:
                data = r.json()
                jobs = data.get("content", [])
                result["count"] = len(jobs)
                if jobs:
                    j0 = jobs[0]
                    result["sample_id"] = j0.get("id")
                    result["sample_url"] = f"https://jobs.smartrecruiters.com/{company_slug}/{j0.get('id')}"
                    result["sample_title"] = j0.get("name")
                    loc = j0.get("location", {})
                    result["sample_location"] = f"{loc.get('city', '')}, {loc.get('country', '')}".strip(", ")
                    result["raw_payload_sample"] = j0
                else:
                    result["status"] = "active_empty"
            else:
                result["blocker"] = f"SmartRecruiters API returned HTTP {r.status_code}"
                result["status"] = "draft"

        else:
            r = await client.get(target_url, timeout=10.0, follow_redirects=True)
            if r.status_code == 200:
                result["status"] = "active"
                result["count"] = 1
                result["sample_id"] = f"{family}_page"
                result["sample_url"] = target_url
                result["sample_title"] = f"{name} Page"
                result["sample_location"] = "India"
            else:
                result["blocker"] = f"Page returned HTTP {r.status_code}"
                result["status"] = "draft"

    except Exception as exc:
        result["status"] = "draft"
        result["blocker"] = f"Canary exception: {type(exc).__name__}: {str(exc)}"

    if result["sample_location"]:
        eligible, _ = is_india_eligible(result["sample_location"])
        result["india_eligible"] = eligible

    return result

async def main():
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, verify=False) as client:
        tasks = [probe_board(client, item) for item in BOARDS_INVENTORY]
        results = await asyncio.gather(*tasks)

    with open("canary_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"Canary completed. Total boards probed: {len(results)}")

if __name__ == "__main__":
    asyncio.run(main())
