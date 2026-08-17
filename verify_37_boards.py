import asyncio
import logging
from sqlalchemy import select
from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob
from job_radar.services.engine import execution_engine

logging.basicConfig(level=logging.ERROR)

async def run_and_verify_all():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Board))
        boards = res.scalars().all()

    print('=== SYSTEM END-TO-END VERIFICATION OF ALL ' + str(len(boards)) + ' BOARDS ===')
    board_summary = []

    for b in boards:
        if b.status == 'draft':
            print('[' + b.name + '] SKIPPED (Manual-only policy)')
            continue

        try:
            run_res = await execution_engine.execute_board_run(b.board_id)
            status_str = 'SUCCESS' if run_res.extracted_count > 0 else 'FAIL/0'
            print('[' + b.name + '] (' + b.family + ') -> ' + status_str + ' Extracted: ' + str(run_res.extracted_count) + ' jobs')
            board_summary.append({
                'name': b.name,
                'family': b.family,
                'extracted': run_res.extracted_count,
                'status': status_str
            })
        except Exception as e:
            print('[' + b.name + '] (' + b.family + ') -> ERROR: ' + str(e))

    await asyncio.sleep(5.0)

    async with AsyncSessionLocal() as session:
        cand_res = await session.execute(select(CandidateJob))
        cands = cand_res.scalars().all()
        enriched = [c for c in cands if c.description and len(c.description) > 200]

    print('=======================================================')
    print('           JOB RADAR SYSTEM EXTRACTION REPORT          ')
    print('=======================================================')
    print('Total Boards Configured:         ' + str(len(boards)))
    print('Total Active Boards Executed:     ' + str(len(board_summary)))
    succeeded = [b for b in board_summary if b['extracted'] > 0]
    print('Successful Extraction Boards:    ' + str(len(succeeded)) + ' / ' + str(len(board_summary)))
    print('Total Live Candidate Jobs in DB: ' + str(len(cands)))
    print('Enriched Candidate Jobs (>200ch):' + str(len(enriched)) + ' / ' + str(len(cands)))
    print('=======================================================')

if __name__ == '__main__':
    asyncio.run(run_and_verify_all())
