import asyncio
from job_radar.db.session import AsyncSessionLocal, engine
from job_radar.db.base import Base
from job_radar.db.models.board import Board, BoardRevision
import job_radar.db.models  # Ensure all models are registered

async def seed_boards():
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

  async with AsyncSessionLocal() as session:
    # Check if boards exist
    res = await session.execute(Board.__table__.select())
    if res.fetchone():
      print("Database already seeded.")
      return

    boards_data = [
      {
        "board_id": "board-greenhouse-01",
        "name": "Stripe Engineering",
        "family": "greenhouse",
        "target_url": "https://boards.greenhouse.io/stripe",
        "schedule_cron": "0 */6 * * *",
        "status": "active"
      },
      {
        "board_id": "board-lever-02",
        "name": "Datadog Product & Eng",
        "family": "lever",
        "target_url": "https://jobs.lever.co/datadog",
        "schedule_cron": "0 */12 * * *",
        "status": "active"
      },
      {
        "board_id": "board-ashby-03",
        "name": "Linear Core Team",
        "family": "ashby",
        "target_url": "https://jobs.ashbyhq.com/linear",
        "schedule_cron": "0 0 * * *",
        "status": "active"
      },
      {
        "board_id": "board-workday-04",
        "name": "Vercel Infrastructure",
        "family": "workday",
        "target_url": "https://vercel.wd1.myworkdayjobs.com/Careers",
        "schedule_cron": "0 */4 * * *",
        "status": "active"
      }
    ]

    for data in boards_data:
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
    print("Default job boards seeded successfully.")

if __name__ == "__main__":
  asyncio.run(seed_boards())
