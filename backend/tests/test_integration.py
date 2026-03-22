"""
Integration tests for PoetryForYou API.
Tests the full FastAPI endpoints with a test database.

IMPORTANT: DATABASE_URL must be set BEFORE importing app modules,
because db.py creates the engine at import time.
"""
import os
import tempfile

# Create a writable temporary SQLite DB BEFORE any app imports
_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db_path = _test_db.name
_test_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"

import pytest
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.main import app
from app.db import engine
from sqlmodel import SQLModel


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create fresh test database for each test."""
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


# ─────────── Test 1: Health Endpoint ─────────── #

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True}


# ─────────── Test 2: Start Onboarding ─────────── #

class TestStartOnboarding:
    def test_start_creates_user(self, client):
        response = client.post("/message", json={
            "telegram_id": 111111,
            "text": "/start"
        })
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "onboarding" in data.get("stage", "") or "onboarding" in data.get("intent", "")

    def test_start_returns_language_options(self, client):
        response = client.post("/message", json={
            "telegram_id": 222222,
            "text": "/start"
        })
        data = response.json()
        suggested = data["reply"]["suggested_replies"]
        assert "ru" in suggested
        assert "en" in suggested


# ─────────── Test 3: Full Onboarding Flow ─────────── #

class TestFullOnboarding:
    def test_onboarding_completes(self, client):
        # Step 1: /start
        client.post("/message", json={
            "telegram_id": 333333,
            "text": "/start"
        })

        # Step 2: Pick language
        response = client.post("/message", json={
            "telegram_id": 333333,
            "text": "ru"
        })
        data = response.json()
        assert data["stage"] == "idle"


# ─────────── Test 4: Library Browsing ─────────── #

class TestLibraryBrowsing:
    def test_library_after_onboarding(self, client):
        # Onboard first
        client.post("/message", json={"telegram_id": 444444, "text": "/start"})
        client.post("/message", json={"telegram_id": 444444, "text": "en"})

        # Browse library
        response = client.post("/message", json={
            "telegram_id": 444444,
            "text": "/library"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "library"


# ─────────── Test 5: Error Handling ─────────── #

class TestErrorHandling:
    def test_missing_text_returns_400(self, client):
        response = client.post("/message", json={
            "telegram_id": 555555
        })
        assert response.status_code == 400

    def test_help_command(self, client):
        # Onboard first
        client.post("/message", json={"telegram_id": 666666, "text": "/start"})
        client.post("/message", json={"telegram_id": 666666, "text": "en"})

        # Ask for help
        response = client.post("/message", json={
            "telegram_id": 666666,
            "text": "/help"
        })
        assert response.status_code == 200
        data = response.json()
        assert "/learn" in data["reply"]["text"] or "/library" in data["reply"]["text"]


def teardown_module():
    """Clean up temp DB file."""
    try:
        os.remove(_test_db_path)
    except OSError:
        pass
