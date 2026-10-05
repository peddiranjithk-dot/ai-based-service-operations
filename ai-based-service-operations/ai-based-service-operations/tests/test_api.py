import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.pop("ANTHROPIC_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def test_flow():
    with TestClient(app) as c:
        r = c.post("/tickets", json={"customer": "Asha",
                   "message": "URGENT: our production site is down, this is unacceptable!"})
        assert r.status_code == 201
        t = r.json()
        assert t["category"] == "outage" and t["priority"] == "critical"
        assert t["team"] == "Site Reliability"

        r = c.post("/tickets", json={"customer": "Ravi", "message": "I want a refund for my invoice"})
        assert r.json()["category"] == "billing"

        assert c.get("/tickets").json()[0]["priority"] == "critical"
        assert c.patch(f"/tickets/{t['id']}/status", json={"status": "resolved"}).json()["status"] == "resolved"
        assert c.get("/stats").json()["total"] == 2
        assert c.get("/tickets/999").status_code == 404
