import json
import pytest
import httpx
from job_radar.services.engine import PipelineExecutionEngine


@pytest.mark.asyncio
async def test_talent500_pagination_carries_cursor_and_deduplicates():
    engine = PipelineExecutionEngine(session_factory=None)

    page1_jobs = [
        {
            "id": f"job-id-{i}",
            "job_code": f"T500-{i}",
            "slug": f"job-slug-{i}",
            "title": f"Software Engineer {i}",
            "company": {"name": "TMUS Global Solutions", "slug": "tmobile"},
            "location": "Hyderabad",
            "country": {"name": "India"}
        }
        for i in range(1, 21)
    ]
    page1_payload = {
        "total": 40,
        "data": page1_jobs,
        "search_after": [0, 28.5, "cursor-uuid-1"]
    }

    page2_jobs = [
        {
            "id": f"job-id-{i}",
            "job_code": f"T500-{i}",
            "slug": f"job-slug-{i}",
            "title": f"Software Engineer {i}",
            "company": {"name": "TMUS Global Solutions", "slug": "tmobile"},
            "location": "Hyderabad",
            "country": {"name": "India"}
        }
        for i in range(21, 41)
    ]
    page2_payload = {
        "total": 40,
        "data": page2_jobs,
        "search_after": [0, 28.4, "cursor-uuid-2"]
    }

    requests_made = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_made.append(request)
        url_params = dict(request.url.params)
        offset = url_params.get("offset")
        search_after = url_params.get("search_after")

        if offset == "0":
            return httpx.Response(200, json=page1_payload, headers={"content-type": "application/json"})
        elif offset == "20":
            # Assert search_after cursor is passed in request query params
            if search_after == json.dumps([0, 28.5, "cursor-uuid-1"]):
                return httpx.Response(200, json=page2_payload, headers={"content-type": "application/json"})
            else:
                # Without search_after cursor, Talent500 repeats page 1
                return httpx.Response(200, json=page1_payload, headers={"content-type": "application/json"})

        return httpx.Response(404, json={})

    transport = httpx.MockTransport(handler)

    # Patch httpx.AsyncClient in engine to use our mock transport
    original_async_client = httpx.AsyncClient

    class CustomAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            kwargs["transport"] = transport
            super().__init__(**kwargs)

    try:
        httpx.AsyncClient = CustomAsyncClient
        target_url = "https://talent500.com/joblist/?company=TMUS+Global+Solutions&sort_by_created_date=1&offset=0&limit=20"
        candidates = await engine.fetch_talent500_candidates(
            target_url=target_url,
            board_name="TMUS",
            max_pages=2
        )
    finally:
        httpx.AsyncClient = original_async_client

    # Assert 2 requests were made
    assert len(requests_made) == 2
    p2_request_params = dict(requests_made[1].url.params)
    assert p2_request_params.get("offset") == "20"
    assert "search_after" in p2_request_params
    assert p2_request_params["search_after"] == json.dumps([0, 28.5, "cursor-uuid-1"])

    # Assert 40 unique candidates were fetched
    assert len(candidates) == 40
    ids = [c.extra_payload["talent500_id"] for c in candidates]
    assert len(set(ids)) == 40


@pytest.mark.asyncio
async def test_talent500_pagination_safety_stops():
    engine = PipelineExecutionEngine(session_factory=None)

    # Scenario: Missing search_after cursor on page 1 response
    page1_jobs = [
        {
            "id": f"job-id-{i}",
            "job_code": f"T500-{i}",
            "slug": f"job-slug-{i}",
            "title": f"Software Engineer {i}",
            "company": {"name": "TMUS", "slug": "tmobile"},
            "location": "Hyderabad",
            "country": {"name": "India"}
        }
        for i in range(1, 21)
    ]
    page1_payload_no_cursor = {
        "total": 40,
        "data": page1_jobs,
        "search_after": None
    }

    requests_made = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_made.append(request)
        return httpx.Response(200, json=page1_payload_no_cursor, headers={"content-type": "application/json"})

    transport = httpx.MockTransport(handler)

    original_async_client = httpx.AsyncClient

    class CustomAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            kwargs["transport"] = transport
            super().__init__(**kwargs)

    try:
        httpx.AsyncClient = CustomAsyncClient
        target_url = "https://talent500.com/joblist/?company=TMUS+Global+Solutions&sort_by_created_date=1&offset=0&limit=20"
        candidates = await engine.fetch_talent500_candidates(
            target_url=target_url,
            board_name="TMUS",
            max_pages=3
        )
    finally:
        httpx.AsyncClient = original_async_client

    # Should safely stop after 1 page because search_after was None
    assert len(requests_made) == 1
    assert len(candidates) == 20
