import asyncio
from job_radar.db.session import AsyncSessionLocal, engine
from job_radar.db.base import Base
from job_radar.db.models.board import Board, BoardRevision
import job_radar.db.models

async def seed_boards():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        boards_data = [
            {
                "board_id": "board-coupa-01",
                "name": "Coupa Software",
                "family": "lever",
                "target_url": "https://api.lever.co/v0/postings/coupa?mode=json",
                "schedule_cron": "0 */6 * * *",
                "status": "active"
            },
            {
                "board_id": "board-stripe-02",
                "name": "Stripe",
                "family": "greenhouse",
                "target_url": "https://boards-api.greenhouse.io/v1/boards/stripe/jobs",
                "schedule_cron": "0 */6 * * *",
                "status": "active"
            },
            {
                "board_id": "board-linear-03",
                "name": "Linear",
                "family": "ashby",
                "target_url": "https://api.ashbyhq.com/posting-api/job-board/linear",
                "schedule_cron": "0 */12 * * *",
                "status": "active"
            },
            {
                "board_id": "board-datadog-04",
                "name": "Datadog",
                "family": "lever",
                "target_url": "https://api.lever.co/v0/postings/datadog?mode=json",
                "schedule_cron": "0 */6 * * *",
                "status": "active"
            }
        ]

        for data in boards_data:
            res = await session.execute(Board.__table__.select().where(Board.board_id == data["board_id"]))
            if res.fetchone():
                continue

            b = Board(
                board_id=data["board_id"],
                name=data["name"],
                family=data["family"],
                status=data["status"]
            )
            rev = BoardRevision(
                board_id=data["board_id"],
                revision_number=1,
                status="reviewed",
                config_json={
                    "target_url": data["target_url"],
                    "schedule_cron": data["schedule_cron"]
                }
            )
            b.current_revision = rev
            session.add(b)
            session.add(rev)

        await session.commit()
        print("Job Radar seed complete.")

if __name__ == "__main__":
    asyncio.run(seed_boards())
