"""pytest configuration and shared fixtures."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("GROQ_API_KEY", "gsk-test-placeholder")
os.environ.setdefault("LOG_LEVEL", "WARNING")

SAMPLE_CSV = (
    b"date,region,sales,units\n"
    b"2023-01-01,North,10000,500\n"
    b"2023-01-02,South,9000,450\n"
    b"2023-01-03,East,8000,400\n"
)


import pytest


@pytest.fixture
def uploaded_session(client):
    """Upload a sample CSV and return the session ID."""
    resp = client.post(
        "/api/upload-data",
        files={"file": ("data.csv", SAMPLE_CSV, "text/csv")},
    )
    assert resp.status_code == 201
    return resp.json()["session_id"]
