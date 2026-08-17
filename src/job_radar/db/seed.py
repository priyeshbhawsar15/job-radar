import asyncio
import os
from job_radar.db.session import AsyncSessionLocal, engine
from job_radar.db.base import Base
from job_radar.db.models.board import Board, BoardRevision
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.run import PipelineRun, BoardRun, RunRequest, ExecutionAttempt
from job_radar.db.models.handoff import HandoffOutbox, HandoffAttempt

INITIAL_BOARDS = [
    ("board-abnormalai", "Abnormal AI", "custom", "https://abnormal.ai/careers/jobs"),
    ("board-adobe", "Adobe", "workday", "https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced"),
    ("board-amazon", "Amazon", "amazon_jobs", "https://www.amazon.jobs/en/search"),
    ("board-ameriprise", "Ameriprise", "phenom", "https://www.ameriprise.com/careers"),
    ("board-amex", "AMEX", "oracle", "https://aexp.eightfold.ai/careers"),
    ("board-apple", "Apple", "apple_jobs", "https://jobs.apple.com/en-in/search"),
    ("board-celonis", "Celonis", "celonis_dxp", "https://www.celonis.com/careers/jobs"),
    ("board-cisco", "Cisco", "workday", "https://jobs.cisco.com"),
    ("board-cognite", "Cognite", "greenhouse", "https://www.cognite.com/careers"),
    ("board-coupa", "Coupa", "lever", "https://api.lever.co/v0/postings/coupa?mode=json"),
    ("board-eisneramper", "EisnerAmper", "workday", "https://eisneramper.wd1.myworkdayjobs.com/eisneramper_external"),
    ("board-google", "Google", "google_careers", "https://www.google.com/about/careers/applications/jobs/results"),
    ("board-googlecloud", "Google Cloud", "google_cloud_talent_solution", "https://jobs.google.com"),
    ("board-highradius", "HighRadius", "custom", "https://www.highradius.com/about/career"),
    ("board-hp", "HP", "eightfold", "https://hp.eightfold.ai/careers"),
    ("board-jiostar", "JioStar", "workday", "https://jiostar.wd3.myworkdayjobs.com/Global_Career_Site"),
    ("board-jpmc", "JPMC", "oracle", "https://jpmc.fa.oraclecloud.com"),
    ("board-mattel", "Mattel", "custom", "https://jobs.mattel.com/en/search"),
    ("board-meta", "Meta", "meta_careers", "https://www.metacareers.com/jobs"),
    ("board-microsoft", "Microsoft", "eightfold", "https://jobs.careers.microsoft.com/global/en/search"),
    ("board-motorola", "Motorola", "workday", "https://motorolasolutions.wd1.myworkdayjobs.com/Careers"),
    ("board-novartis", "Novartis", "custom", "https://www.novartis.com/careers/career-search"),
    ("board-philips", "Philips", "phenom", "https://www.careers.philips.com"),
    ("board-qualcomm", "Qualcomm", "eightfold", "https://qualcomm.eightfold.ai/careers"),
    ("board-rbctech", "RBCTech", "stratsy", "https://aligncrm.stratsy.us/api/public/opportunities"),
    ("board-solera", "Solera", "workday", "https://solera.wd5.myworkdayjobs.com/External_Career_Site"),
    ("board-tesco", "Tesco", "avature", "https://www.tesco-careers.com"),
    ("board-thomsonreuters", "Thomson Reuters", "workday", "https://thomsonreuters.wd5.myworkdayjobs.com/External_Career_Site"),
    ("board-tp", "TP", "workday", "https://teleperformance.wd3.myworkdayjobs.com/Teleperformance"),
    ("board-vanguard", "Vanguard", "google_cloud_talent_solution", "https://vanguard.jobsapi-google.m-cloud.io"),
    ("board-walmart", "Walmart", "workday", "https://walmart.wd5.myworkdayjobs.com/WalmartExternal"),
    ("board-wynploy", "Wynploy", "zoho", "https://wynploy.zohorecruit.com"),
    ("board-ebay", "eBay", "workday", "https://ebay.wd1.myworkdayjobs.com/apply")
]

async def seed_database():
    print("Resetting database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for b_id, name, family, target_url in INITIAL_BOARDS:
            board = Board(
                board_id=b_id,
                name=name,
                family=family,
                status="reviewed",
                consecutive_parser_failures=0
            )
            session.add(board)
            await session.flush()

            rev = BoardRevision(
                board_id=b_id,
                revision_number=1,
                status="reviewed",
                config_json={
                    "target_url": target_url,
                    "max_pages": 3,
                    "schedule_cron": "0 */6 * * *"
                }
            )
            session.add(rev)
            await session.flush()
            board.current_revision_id = rev.revision_id

        await session.commit()
    print("Database reset complete. Seeded company boards cleanly.")

if __name__ == "__main__":
    asyncio.run(seed_database())
