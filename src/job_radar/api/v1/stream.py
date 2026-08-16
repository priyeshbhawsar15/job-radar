import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


@router.get("/stream")
async def sse_event_stream(request: Request):
    """Server-Sent Events endpoint for live operator updates."""
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break

            # Send heartbeat / pulse telemetry event
            payload = {
                "event_type": "heartbeat",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system_status": "ready",
                "active_runs_count": 0
            }
            yield {
                "event": "message",
                "data": json.dumps(payload)
            }
            await asyncio.sleep(5)

    return EventSourceResponse(event_generator())
