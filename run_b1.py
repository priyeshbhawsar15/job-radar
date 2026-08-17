import asyncio
from sqlalchemy import select
from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.board import Board
from job_radar.services.engine import execution_engine

async def run_b1():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Board))
        boards = res.scalars().all()

    b_half = boards[:18]
    print('=== RUNNING BATCH 1 (' + str(len(b_half)) + ' BOARDS) ===')
    for b in b_half:
        if b.status == 'draft': continue
        res = await execution_engine.execute_board_run(b.board_id)
        print('[' + b.name + '] -> ' + res.outcome + ' (' + str(res.extracted_count) + ' jobs)')

asyncio.run(run_b1())
