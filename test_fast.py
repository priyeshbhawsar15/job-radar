import asyncio
import json
import logging
from sqlalchemy import select
from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob
from job_radar.services.engine import execution_engine

logging.basicConfig(level=logging.INFO)

async def test_all_37_boards():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Board))
        boards = res.scalars().all()

    print('=== TESTING ALL 37 BOARDS END-TO-END ===')
    results = []

    for b in boards:
        if b.status == 'draft':
            print('[' + b.name + '] SKIPPED (Manual-only policy)')
            continue

        print('[' + b.name + '] (' + b.family + ') Running pipeline extraction...')
        try:
            run_res = await execution_engine.execute_board_run(b.board_id)
            print('  -> Outcome: ' + str(run_res.outcome) + ' | Extracted: ' + str(run_res.extracted_count))
            results.append({
                'board_id': b.board_id,
                'name': b.name,
                'family': b.family,
                'outcome': run_res.outcome,
                'extracted': run_res.extracted_count
            })
        except Exception as e:
            print('  -> ERROR: ' + str(e))
            results.append({
                'board_id': b.board_id,
                'name': b.name,
                'family': b.family,
                'outcome': 'error',
                'extracted': 0,
                'error': str(e)
            })

    async with AsyncSessionLocal() as session:
        cand_res = await session.execute(select(CandidateJob))
        cands = cand_res.scalars().all()

    print('=== SYSTEM END-TO-END SUMMARY ===')
    succeeded = [r for r in results if r['extracted'] > 0]
    print('Total Boards Tested: ' + str(len(results)))
    print('Successfully Extracting Boards: ' + str(len(succeeded)))
    print('Total Enriched Candidates in DB: ' + str(len(cands)))

if __name__ == '__main__':
    asyncio.run(test_all_37_boards())
