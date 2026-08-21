import asyncio
import os
from job_radar.db.session import AsyncSessionLocal, engine
from job_radar.db.base import Base
from job_radar.db.models.board import Board, BoardRevision
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.run import PipelineRun, BoardRun, RunRequest, ExecutionAttempt
from job_radar.db.models.handoff import HandoffOutbox, HandoffAttempt

INITIAL_BOARDS = [
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
    ("board-wynploy", "Wynploy", "zoho", "https://wynploy.zohorecruit.in/jobs/Careers")
]

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

            board = Board(
                board_id=b_id,
                name=name,
                family=family,
                status="reviewed",
                consecutive_parser_failures=0
            )
            session.add(board)
            await session.flush()

            cfg_json = build_initial_revision_config(item)

            rev = BoardRevision(
                board_id=b_id,
                revision_number=1,
                status="reviewed",
                config_json=cfg_json
            )
            session.add(rev)
            await session.flush()
            board.current_revision_id = rev.revision_id

        await session.commit()
    print("Database reset complete. Seeded company boards cleanly.")

if __name__ == "__main__":
    asyncio.run(seed_database())
