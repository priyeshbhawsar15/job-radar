import asyncio
import os
from job_radar.db.session import AsyncSessionLocal, engine
from job_radar.db.base import Base
from job_radar.db.models.board import Board, BoardRevision
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.run import PipelineRun, BoardRun, RunRequest, ExecutionAttempt
from job_radar.db.models.handoff import HandoffOutbox, HandoffAttempt

# Baseline 37 Boards + 65 New Boards (Total 102 Boards)
INITIAL_BOARDS = [
    # --- Baseline Boards ---
    ("board-abnormalai", "Abnormal AI", "custom", "https://abnormal.ai/careers/open-roles?location=Hybrid+-+Bangalore%2C+India&category=Engineering"),
    ("board-adobe", "Adobe", "workday", "https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced?Job_Application_ID=cf0155a2a4659000ad6ec95db1160000&workerSubType=3ba4ecdf4893100b2f8d06b0870c6c8b&jobFamilyGroup=591af8b812fa10737b0e880e0e3eeee9&jobFamilyGroup=591af8b812fa10737af39db3d96eed9f&locationCountry=c4f78be1a8f14da0ab49ce1162348a5e"),
    ("board-amazon", "Amazon", "amazon_jobs", "https://www.amazon.jobs/en/search?offset=0&result_limit=10&sort=recent&category[]=software-development&distanceType=Mi&radius=24km&latitude=&longitude=&loc_group_id=&loc_query=India&base_query=software&city=&country=IND&region=&county=&query_options=&"),
    ("board-ameriprise", "Ameriprise", "ameriprise", "https://careers.ameriprise.com/search-jobs/?search=software&country=India&team=Technology&type=Full+Time&pagesize=20#results"),
    ("board-amex", "AMEX", "oracle", "https://egug.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs?keyword=Software", {
        "api_origin": "https://egug.fa.us2.oraclecloud.com",
        "site_number": "CX_1",
        "allowed_origins": [
            "https://egug.fa.us2.oraclecloud.com",
            "https://americanexpress.wd5.myworkdayjobs.com"
        ]
    }),
    ("board-apple", "Apple", "apple_jobs", "https://jobs.apple.com/en-in/search?search=Software&sort=newest&location=bangalore-metro-BANG"),
    ("board-aspora", "Aspora", "ashby", "https://jobs.ashbyhq.com/Aspora?departmentId=3790eb6b-6f6f-4d71-ad69-6a1a9fea6066&employmentType=FullTime&utm_medium=organic&utm_source=startup.jobs"),
    ("board-celonis", "Celonis", "celonis_dxp", "https://careers.celonis.com/join-us/open-positions?team=Engineering&seniority=Experienced+Professional&groupedLocation=Bangalore%2C+India"),
    ("board-cisco", "Cisco", "workday", "https://cisco.wd5.myworkdayjobs.com/en-US/Cisco_Careers?locations=026fa05becb01001f506953e0df00000&locations=6bed8334bf4b1001f4f15a1f787a0000&locations=8676de3331b41001f4eaac80a6280000&locations=ef8a5a22403d1001f4fde228ba110000&locations=662e524adea41001f4d0bd5a1ddd0000&timeType=672880041e5001a878ea77353f075800&jobFamilyGroup=2101eee3ea96016aef42a674fc016429"),
    ("board-cognite", "Cognite", "greenhouse", "https://job-boards.eu.greenhouse.io/cognite?departments[]=4059460101&offices[]=4033280101"),
    ("board-coupa", "Coupa", "lever", "https://api.lever.co/v0/postings/coupa?mode=json"),
    ("board-ebay", "eBay", "workday", "https://ebay.wd5.myworkdayjobs.com/en-US/apply?q=Software+Engineer&locations=a26d394fcb4f10011d72987ae6420000&jobFamilyGroup=faedd7c80dd5102a1e369f8dcda9ca60"),
    ("board-eisneramper", "EisnerAmper", "workday", "https://eisneramper.wd1.myworkdayjobs.com/en-US/eisneramper_external?q=software&timeType=8f3b4e5b394010017a4ab94afe3ca02f&locations=2e11502a14760101a15a94aa71a40000&locations=743b927c6e5010014fe0f4a1f4d80000&locations=ec61fb5ee07b1003fb71b0c8eab18271"),
    ("board-google", "Google", "google_careers", "https://www.google.com/about/careers/applications/jobs/results?location=India&q=%22Software%20Engineer%22&target_level=MID&employment_type=FULL_TIME&sort_by=date"),
    ("board-highradius", "HighRadius", "custom", "https://www.highradius.com/about/career/"),
    ("board-hp", "HP", "eightfold", "https://hp.eightfold.ai/careers?query=software&start=0&location=india&pid=41541191&sort_by=timestamp&filter_include_remote=1&filter_include_relocation=0&filter_seniority=experienced"),
    ("board-jiostar", "JioStar", "workday", "https://jiostar.wd102.myworkdayjobs.com/en-US/JioStar?source=jobfound.org&jobFamilyGroup=8df5dc1586541000539b236955f10000"),
    ("board-jpmc", "JPMC", "oracle", "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs?lastSelectedFacet=POSTING_DATES&location=India&locationId=300000000289360&locationLevel=country&mode=location&selectedCategoriesFacet=300000086152753&selectedPostingDatesFacet=30%3B7", {
        "api_origin": "https://jpmc.fa.oraclecloud.com",
        "site_number": "CX_1001",
        "allowed_origins": [
            "https://jpmc.fa.oraclecloud.com",
            "https://careers.jpmorganchase.com"
        ]
    }),
    ("board-mattel", "Mattel", "custom", "https://jobs.mattel.com/en/search-jobs/software/Hyderabad%2C+Telangana/2015/1/4/1269750-1254788-1269844-1269843/17x38405/78x45636/35/2"),
    ("board-meta", "Meta", "meta_careers", "https://www.metacareers.com/jobsearch/?sort_by_new=true&offices[0]=Bangalore%2C%20India&offices[1]=Hyderabad%2C%20India&offices[2]=Mumbai%2C%20India&offices[3]=New%20Delhi%2C%20India&offices[4]=Gurgaon%2C%20India&roles[0]=Full%20time%20employment"),
    ("board-microsoft", "Microsoft", "eightfold", "https://apply.careers.microsoft.com/careers?query=Software&start=0&location=india&pid=1970393556955275&sort_by=relevance&filter_include_remote=1&filter_include_relocation=0&filter_profession=software+engineering&filter_seniority=Mid-Level"),
    ("board-motorola", "Motorola Solutions", "workday", "https://motorolasolutions.wd5.myworkdayjobs.com/en-US/Careers?timeType=14bb6aa2c25e4a218b2a3faaa951e44c&jobFamilyGroup=2161bef685534428b91fad96fc9069b4&jobFamilyGroup=c3fc17b768e842e39b7192f0bf4cb0f1&locationCountry=c4f78be1a8f14da0ab49ce1162348a5e"),
    ("board-novartis", "Novartis", "custom", "https://www.novartis.com/in-en/careers/career-search?search_api_fulltext=software&country[0]=LOC_IN&op=Submit&field_job_posted_date=3"),
    ("board-oracle", "Oracle", "oracle", "https://careers.oracle.com/en/sites/jobsearch/jobs?keyword=Software+Engineer&location=India", {
        "api_origin": "https://eeho.fa.us2.oraclecloud.com",
        "site_number": "CX_45001",
        "allowed_origins": [
            "https://careers.oracle.com",
            "https://eeho.fa.us2.oraclecloud.com"
        ]
    }, {
        "oracle_listing": {
            "keyword": "Software Engineer",
            "location": "India",
            "limit": 10
        }
    }),
    ("board-philips", "Philips", "phenom", "https://www.careers.philips.com/in/en/search-results", {
        "allowed_origins": [
            "https://www.careers.philips.com"
        ]
    }),
    ("board-plane", "Plane", "ashby", "https://jobs.ashbyhq.com/plane?departmentId=0421d677-7dfa-49f4-ab71-57d3cf54cc94&locationId=fe009c8d-2efb-4677-994b-768c71c63d58&utm_medium=organic&utm_source=startup.jobs"),
    ("board-qualcomm", "Qualcomm", "eightfold", "https://careers.qualcomm.com/careers?start=0&location=india&pid=446719653366&sort_by=timestamp&filter_include_remote=0&filter_include_relocation=0&filter_job_family=software+engineering&filter_seniority=Entry%2CMid-Level"),
    ("board-rbctech", "RBCTech", "stratsy", "https://www.rbctechsolutions.com/rbctech/careers/"),
    ("board-resilinc", "Resilinc", "lever", "https://jobs.lever.co/resilinc?location=India&department=Engineering&commitment=Full%20Time"),
    ("board-solera", "Solera", "workday", "https://solera.wd5.myworkdayjobs.com/en-US/Global_Career_Site?locationCountry=c4f78be1a8f14da0ab49ce1162348a5e&timeType=4e10d1a5fccf0131793c639ceee06c00"),
    ("board-tesco", "Tesco", "avature", "https://careers.tesco.com/en_GB/careers/SearchJobs/?748_location_place=Bengaluru,%20Karnataka,%20India&748_location_radius=200&748_location_coordinates=[12.98,77.59]&12328=[587056]&12328_format=25911&59964=[4196244]&59964_format=26080&listFilterMode=1&jobSort=postedDate&jobSortDirection=ASC&jobRecordsPerPage=10&"),
    ("board-thomsonreuters", "Thomson Reuters", "workday", "https://thomsonreuters.wd5.myworkdayjobs.com/en-US/External_Career_Site?timeType=3f1eb038fd70401c97dc2b7d14b4a0fb&CF_Job_Posting_Anchor_Job_Category_EEB_Extended=9276a62d4e68100204e60c54e1cc0001&Location_Country=c4f78be1a8f14da0ab49ce1162348a5e&jobFamily=f95730d5e7cb4830b5b70285df79c8b4&jobFamily=8d930836c67610016a46e7095aa80000&jobFamily=7f024350a1b7449084d35b779d407130"),
    ("board-tp", "TP", "workday", "https://onetp.wd1.myworkdayjobs.com/en-US/Teleperformance?jobFamilyGroup=c195d27ce3d310009f09b8c364620001"),
    ("board-vanguard", "Vanguard", "workday", "https://vanguard.wd5.myworkdayjobs.com/en-US/vanguard_external"),
    ("board-walmart", "Walmart", "workday", "https://walmart.wd504.myworkdayjobs.com/en-US/WalmartExternal?timeType=b181d8271e36017533d4ca68eee44f00&jobFamilyGroup=e83ebdbd2a0a01e7e1477a8948e904c6&locationCountry=c4f78be1a8f14da0ab49ce1162348a5e&jobFamily=e83ebdbd2a0a01e6af60e95a47e972c4"),
    ("board-weave", "Weave", "ashby", "https://jobs.ashbyhq.com/weave?departmentId=18d3af43-c3c7-4437-8197-e4c649b8b8d9&employmentType=FullTime&locationId=efd16dc3-9146-410b-899f-75ca810de563&utm_medium=organic&utm_source=startup.jobs"),
    ("board-wynploy", "Wynploy", "zoho", "https://wynploy.zohorecruit.in/jobs/Careers"),

    # --- 65 New Boards ---
    ("board-jll", "JLL", "workday", "https://jll.wd1.myworkdayjobs.com/en-US/jllcareers?locationCountry=c4f78be1a8f14da0ab49ce1162348a5e&timeType=72e81fa31e6f01cf9aa5a4251a4e4e00&jobFamilyGroup=c608fc06410f01484a9fec7aba539450&jobFamilyGroup=f134f8e1c0811001fe9e2695d0c80000"),
    ("board-razorpay", "Razorpay", "greenhouse", "https://job-boards.greenhouse.io/razorpaysoftwareprivatelimited?departments%5B%5D=4024806005"),
    ("board-soti", "SOTI", "workday", "https://soti.wd3.myworkdayjobs.com/en-US/Careers?locations=f35dd6d3a7da01adef33e8916446200f&locations=27190dd10fff1074b213f2d1500595ed&EEB_-_Job_Categories_for_External_Site_Extended=267bdbcbbd671001697698c0843a0001"),
    ("board-amgen", "Amgen", "workday", "https://amgen.wd1.myworkdayjobs.com/en-US/Careers?locations=be0893cb78ed012e9c728ee58144ec3b&jobFamilyGroup=3b16b67900e510859633b621ace7c537"),
    ("board-paytm", "Paytm", "lever", "https://jobs.lever.co/paytm?department=Technology&commitment=Full-time%20Employment"),
    ("board-atlassian", "Atlassian", "custom", "https://www.atlassian.com/company/careers/all-jobs?team=Engineering&location=India&search="),
    ("board-uber", "Uber", "custom", "https://jobs.uber.com/en/jobs/?search=software&countries=India"),
    ("board-gitlab", "Gitlab", "greenhouse", "https://job-boards.greenhouse.io/gitlab"),
    ("board-hobspot", "Hobspot", "greenhouse", "https://job-boards.greenhouse.io/hubspot"),
    ("board-godaddy", "GoDaddy", "greenhouse", "https://careers.godaddy/jobs/search?page=1&query=&department_uids[]=6ed98616cdc63adf0b08529f08290235&country_codes[]=IN"),
    ("board-phonepay", "PhonePe", "greenhouse", "https://job-boards.greenhouse.io/phonepe?gh_src=961e65dc3us"),
    ("board-buffer", "Buffer", "ashby", "https://jobs.ashbyhq.com/buffer"),
    ("board-sourcegraph", "Sourcegraph", "greenhouse", "https://boards-api.greenhouse.io/v1/boards/sourcegraph91/jobs?content=true"),
    ("board-zapier", "Zapier", "ashby", "https://jobs.ashbyhq.com/zapier"),
    ("board-automattic", "Automattic", "custom", "https://automattic.com/work-with-us/jobs/"),
    ("board-doist", "Doist", "custom", "https://doist.com/careers#open-roles"),
    ("board-deel", "Deel", "custom", "https://www.deel.com/careers/?department=engineering"),
    ("board-remote", "Remote.com", "greenhouse", "https://job-boards.greenhouse.io/remote"),
    ("board-elastic", "Elastic", "custom", "https://jobs.elastic.co/jobs/country/india?size=n_20_n"),
    ("board-twilio", "Twilio", "greenhouse", "https://job-boards.greenhouse.io/twilio"),
    ("board-supabase", "Supabase", "ashby", "https://jobs.ashbyhq.com/supabase"),
    ("board-bitwarden", "Bitwarden", "greenhouse", "https://job-boards.greenhouse.io/bitwarden"),
    ("board-camunda", "Camunda", "ashby", "https://jobs.ashbyhq.com/camunda"),
    ("board-mailerlite", "MailerLite", "custom", "https://www.mailerlite.com/jobs"),
    ("board-zoho", "Zoho", "zoho", "https://www.zoho.com/careers/"),
    ("board-postman", "Postman", "greenhouse", "https://job-boards.greenhouse.io/postman"),
    ("board-browserstack", "BrowserStack", "workday", "https://browserstack.wd3.myworkdayjobs.com/External?jobFamilyGroup=0cb9174e33c9100190f156427de80000"),
    ("board-atlan", "Atlan", "ashby", "https://jobs.ashbyhq.com/atlan"),
    ("board-redis", "Redis", "ashby", "https://jobs.ashbyhq.com/redis"),
    ("board-springworks", "Springworks", "custom", "https://jobs.goodfit.so/careers/springworks"),
    ("board-juspay", "Juspay", "custom", "https://juspay.io/careers"),
    ("board-groww", "Groww", "greenhouse", "https://job-boards.eu.greenhouse.io/groww"),
    ("board-cred", "CRED", "lever", "https://jobs.lever.co/cred"),
    ("board-snowflake", "Snowflake", "phenom", "https://careers.snowflake.com/us/en/search-results"),
    ("board-databricks", "Databricks", "greenhouse", "https://job-boards.greenhouse.io/databricks"),
    ("board-ibm", "IBM", "custom", "https://careers.ibm.com/en_IN/careers/search"),
    ("board-okta", "Okta", "greenhouse", "https://job-boards.greenhouse.io/okta"),
    ("board-crowdstrike", "CrowdStrike", "workday", "https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers?locationCountry=c4f78be1a8f14da0ab49ce1162348a5e&Job_Family=1408861ee6e201641be2c2f6b000c00b&Job_Family=cb19f044639b1001f6a02595bc920000"),
    ("board-stripe", "Stripe", "custom", "https://stripe.com/careers/search?teams=Products&locations=Asia+Pacific--India&employment_types=Full+time"),
    ("board-coinbase", "Coinbase", "greenhouse", "https://job-boards.greenhouse.io/coinbase"),
    ("board-salesforce", "Salesforce", "workday", "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site"),
    ("board-sap", "SAP", "phenom", "https://jobs.sap.com/search/?createNewAlert=false&q=&locationsearch=&optionsFacetsDD_department=Software-Design+and+Development&optionsFacetsDD_customfield3=&optionsFacetsDD_country=IN"),
    ("board-workdaycorp", "Workday", "workday", "https://workday.wd5.myworkdayjobs.com/Workday/?source=Careers_Website&Location_Country=c4f78be1a8f14da0ab49ce1162348a5e&jobFamilyGroup=8c5ce7a1cffb43e0a819c249a49fcb00"),
    ("board-intuit", "Intuit", "custom", "https://jobs.intuit.com/search-jobs?acm=9211424&alrpm=ALL&ascf=[{%22key%22:%22ALL%22,%22value%22:%22%22}]"),
    ("board-nutanix", "Nutanix", "phenom", "https://careers.nutanix.com/en/jobs/?search=&country=India&team=Engineering&type=Full-Time&pagesize=20#results"),
    ("board-vmware", "VMware", "smartrecruiters", "https://careers.smartrecruiters.com/Vmware2"),
    ("board-nvidia", "NVIDIA", "eightfold", "https://jobs.nvidia.com/careers?start=0&location=Hyderabad%2C++Telangana%2C++India&pid=893395509555&sort_by=distance&filter_distance=160&filter_include_remote=1&filter_include_relocation=0&filter_job_category=engineering"),
    ("board-intel", "Intel", "workday", "https://intel.wd1.myworkdayjobs.com/External?locations=1e4a4eb3adf101f44070f976bf8184cf&jobFamilyGroup=ace7a3d23b7e01a0544279031a0ec85c"),
    ("board-airbnb", "Airbnb", "greenhouse", "https://job-boards.greenhouse.io/airbnb"),
    ("board-meesho", "Meesho", "custom", "https://www.meesho.io/jobs?&t=Business%20Analytics,Backend,QA,Infrastructure,CTO%20Office,Data%20Engineering,Data%20Science,Demand,Frontend,Supply,Security"),
    ("board-target", "Target", "phenom", "https://corporate.target.com/careers/job-search?currentPage=1&jobAreas=Target%20Tech&schedule=Full-time&country=India"),
    ("board-goldmansachs", "Goldman Sachs", "custom", "https://higher.gs.com/results?JOB_FUNCTION=Software%20Engineering&page=1&sort=POSTED_DATE"),
    ("board-morganstanley", "Morgan Stanley", "eightfold", "https://morganstanley.eightfold.ai/careers?source=mscom&start=0&location=India&pid=549798643496&sort_by=distance&filter_include_remote=1&filter_include_relocation=0&filter_businessarea=technology&filter_employmenttype=full+time"),
    ("board-hsbc", "HSBC", "eightfold", "https://portal.careers.hsbc.com/careers?query=software&location=India&pid=563774612163818&domain=hsbc.com&sort_by=relevance&triggerGoButton=false"),
    ("board-blackrock", "BlackRock", "phenom", "https://careers.blackrock.com/search-jobs/software/India/45831/1/2/1269750/22/79/0/2"),
    ("board-uipath", "UiPath", "custom", "https://www.uipath.com/careers/jobs"),
    ("board-druva", "Druva", "greenhouse", "https://job-boards.greenhouse.io/druva"),
    ("board-swiggy", "Swiggy", "custom", "https://careers.swiggy.com/#/careers?career_page_category=Technology"),
    ("board-publicissapient", "Publicis Sapient", "phenom", "https://careers.publicissapient.com/job-search?q=&location_q=India&skipLocation=true&country=India&sortOrder=desc&teams=Technology+and+Engineering"),
    ("board-epam", "EPAM Systems", "custom", "https://careers.epam.com/en/jobs/india?city=4060741400035606933&sort_by=relevance&specialization=developer&utm_content=job-search&utm_term=start-your-search-here"),
    ("board-tmus", "TMUS", "talent500", "https://talent500.com/joblist/?company=TMUS+Global+Solutions&sort_by_created_date=1&offset=0&limit=20"),
    ("board-bestbuy", "Best Buy", "talent500", "https://talent500.com/joblist/?company=Best+Buy&sort_by_created_date=1&offset=0&limit=20"),
    ("board-evernorth", "Evernorth", "talent500", "https://talent500.com/joblist/?company=Evernorth&sort_by_created_date=1&offset=0&limit=20"),
    ("board-marriotttech", "Marriott Tech", "talent500", "https://talent500.com/joblist/?company=Marriott+Tech+Accelerator&sort_by_created_date=1&offset=0&limit=20"),
    ("board-mcd", "McD", "talent500", "https://talent500.com/joblist/?company=McDonalds+in+India&sort_by_created_date=1&offset=0&limit=20"),
]

BLOCKED_BOARD_IDS = {
    # Baseline draft boards (6)
    "board-highradius",
    "board-mattel",
    "board-novartis",
    "board-rbctech",
    "board-solera",
    "board-tp",

    # New draft boards (20)
    "board-soti",
    "board-atlassian",
    "board-hobspot",
    "board-zapier",
    "board-doist",
    "board-remote",
    "board-juspay",
    "board-cred",
    "board-ibm",
    "board-stripe",
    "board-workdaycorp",
    "board-uipath",
    "board-hsbc",
    "board-swiggy",
    "board-publicissapient",
    "board-tmus",
    "board-bestbuy",
    "board-evernorth",
    "board-marriotttech",
    "board-mcd",
}

def build_initial_revision_config(item: tuple) -> dict:
    """Build one initial BoardRevision config without database I/O."""
    if len(item) == 4:
        b_id, name, family, target_url = item
        family_cfg = None
        revision_extras = None
    elif len(item) == 5:
        b_id, name, family, target_url, family_cfg = item
        revision_extras = None
    elif len(item) == 6:
        b_id, name, family, target_url, family_cfg, revision_extras = item
    else:
        raise ValueError(f"Unsupported INITIAL_BOARDS tuple length: {len(item)}")

    cfg_json = {
        "target_url": target_url,
        "max_pages": 3,
        "schedule_cron": "0 */6 * * *"
    }
    if family_cfg:
        if family == "oracle":
            cfg_json["oracle_detail"] = dict(family_cfg)
        elif family == "phenom":
            cfg_json["phenom_detail"] = dict(family_cfg)

    if revision_extras:
        for key, value in revision_extras.items():
            cfg_json[key] = dict(value) if isinstance(value, dict) else value

    return cfg_json


async def seed_database():
    print("Resetting database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for item in INITIAL_BOARDS:
            b_id, name, family = item[0], item[1], item[2]
            status = "draft" if b_id in BLOCKED_BOARD_IDS else "reviewed"

            board = Board(
                board_id=b_id,
                name=name,
                family=family,
                status=status,
                consecutive_parser_failures=0
            )
            session.add(board)
            await session.flush()

            cfg_json = build_initial_revision_config(item)

            rev = BoardRevision(
                board_id=b_id,
                revision_number=1,
                status=status,
                config_json=cfg_json
            )
            session.add(rev)
            await session.flush()
            board.current_revision_id = rev.revision_id

        await session.commit()
    print(f"Database reset complete. Seeded {len(INITIAL_BOARDS)} company boards cleanly.")

if __name__ == "__main__":
    asyncio.run(seed_database())
