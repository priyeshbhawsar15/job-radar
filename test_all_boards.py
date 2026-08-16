import asyncio
import json
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.board import Board
from job_radar.services.engine import execution_engine

logger = logging.getLogger(__name__)

async def run_board_tests():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Board).options(selectinload(Board.current_revision)))
        boards = res.scalars().all()

    print("=== STARTING SYSTEMATIC TEST OF " + str(len(boards)) + " BOARDS ===")

    results = []

    for b in boards:
        board_id = b.board_id
        board_name = b.name
        family = b.family
        is_manual = False

        if b.current_revision and isinstance(b.current_revision.config_json, dict):
            cfg = b.current_revision.config_json
            if cfg.get("manual_only") or cfg.get("selector_config", {}).get("manual_only"):
                is_manual = True

        if b.status == "draft" or is_manual:
            print("[" + board_name + "] (" + family + ") -> SKIPPED (Manual-only policy / Draft status)")
            results.append({
                "board_id": board_id,
                "name": board_name,
                "family": family,
                "status": "skipped_manual_policy",
                "extracted": 0,
                "notes": "Manual-only policy (robots/public access constraint)"
            })
            continue

        print("Testing [" + board_name + "] (" + family + ")...")
        try:
            run_res = await execution_engine.execute_board_run(board_id)
            extracted = run_res.extracted_count
            outcome = run_res.outcome
            error_code = run_res.error_code

            if outcome == "success" and extracted > 0:
                print("  ✓ SUCCESS: Extracted " + str(extracted) + " jobs")
                results.append({
                    "board_id": board_id,
                    "name": board_name,
                    "family": family,
                    "status": "success",
                    "extracted": extracted,
                    "notes": "Extracted " + str(extracted) + " candidates"
                })
            else:
                note = "Outcome: " + str(outcome) + ", extracted: " + str(extracted) + ", error: " + str(error_code)
                print("  ✗ ISSUE: " + note)
                results.append({
                    "board_id": board_id,
                    "name": board_name,
                    "family": family,
                    "status": "issue",
                    "extracted": extracted,
                    "notes": note
                })
        except Exception as e:
            print("  ✗ EXCEPTION: " + str(e))
            results.append({
                "board_id": board_id,
                "name": board_name,
                "family": family,
                "status": "error",
                "extracted": 0,
                "notes": str(e)
            })

        await asyncio.sleep(0.5)

    print("=== INITIAL BOARD TEST RUN COMPLETE ===")
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_board_tests())
