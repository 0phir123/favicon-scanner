# tests/test_fastapi_api.py
from fastapi.testclient import TestClient

from app.adapters.api.fastapi_app import app

client = TestClient(app)


def test_post_scan_returns_id_and_status():
    r = client.post("/scan", json={"targets": ["example.com"], "ports": [80]})
    # Non-blocking implementations often return 202; your app currently returns 200.
    assert r.status_code in {200, 202}
    data = r.json()
    # The response should always include an id we can poll later
    assert isinstance(data.get("scan_id"), str) and data["scan_id"]
    # And a status indicator
    assert data.get("status") in {"pending", "done"}
    # Optional metadata if your app includes it
    if "job_id" in data:
        assert isinstance(data["job_id"], str)


def test_get_unknown_scan_returns_404():
    r = client.get("/scan/notfound")
    assert r.status_code == 404
