import httpx
import pytest

from job_radar.services.engine import PipelineExecutionEngine


def _job(index: int, *, location: str, title: str | None = None) -> dict:
    job_id = f"00000000-0000-0000-0000-{index:012d}"
    return {
        "id": job_id,
        "text": title or f"Technology Role {index}",
        "hostedUrl": f"https://jobs.lever.co/paytm/{job_id}",
        "categories": {
            "commitment": "Full-time Employment",
            "department": "Technology",
            "location": location,
        },
        "descriptionPlain": "Role overview with responsibilities and qualifications. " * 8,
    }


@pytest.mark.asyncio
async def test_paytm_preserves_lever_filters_and_keeps_indian_city_state_jobs(monkeypatch):
    requests: list[httpx.Request] = []
    payload = [_job(i, location="Noida, Uttar Pradesh") for i in range(1, 8)]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    class MockAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            kwargs["transport"] = transport
            super().__init__(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    try:
        engine = PipelineExecutionEngine(session_factory=None)
        candidates = await engine.fetch_lever_candidates(
            target_url=(
                "https://jobs.lever.co/paytm"
                "?department=Technology&commitment=Full-time%20Employment"
            ),
            board_name="Paytm",
        )
    finally:
        monkeypatch.setattr(httpx, "AsyncClient", original_client)

    assert len(requests) == 1
    assert requests[0].url.host == "api.lever.co"
    assert requests[0].url.path == "/v0/postings/paytm"
    assert requests[0].url.params.get("mode") == "json"
    assert requests[0].url.params.get("department") == "Technology"
    assert requests[0].url.params.get("commitment") == "Full-time Employment"
    assert len(candidates) == 7
    assert len({candidate.raw_url for candidate in candidates}) == 7
    assert all(candidate.location == "Noida, Uttar Pradesh" for candidate in candidates)


@pytest.mark.asyncio
async def test_unfiltered_lever_source_retains_explicit_india_gate(monkeypatch):
    requests: list[httpx.Request] = []
    payload = [
        _job(1, location="Pune, India", title="India Role"),
        _job(2, location="Tokyo, Japan", title="Japan Role"),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    class MockAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            kwargs["transport"] = transport
            super().__init__(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    try:
        engine = PipelineExecutionEngine(session_factory=None)
        candidates = await engine.fetch_lever_candidates(
            target_url="https://api.lever.co/v0/postings/coupa?mode=json",
            board_name="Coupa",
        )
    finally:
        monkeypatch.setattr(httpx, "AsyncClient", original_client)

    assert len(requests) == 1
    assert requests[0].url.params.get("mode") == "json"
    assert len(candidates) == 1
    assert candidates[0].title == "India Role"


@pytest.mark.asyncio
async def test_lever_preserves_repeated_approved_filters_only(monkeypatch):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    class MockAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            kwargs["transport"] = transport
            super().__init__(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    try:
        engine = PipelineExecutionEngine(session_factory=None)
        await engine.fetch_lever_candidates(
            target_url=(
                "https://jobs.lever.co/resilinc?location=India"
                "&department=Engineering&department=Platform"
                "&commitment=Full%20Time&untrusted=value"
            ),
            board_name="Resilinc",
        )
    finally:
        monkeypatch.setattr(httpx, "AsyncClient", original_client)

    request = requests[0]
    assert request.url.params.get_list("department") == ["Engineering", "Platform"]
    assert request.url.params.get("location") == "India"
    assert request.url.params.get("commitment") == "Full Time"
    assert "untrusted" not in request.url.params
