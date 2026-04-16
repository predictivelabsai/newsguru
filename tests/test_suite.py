"""
NewsGuru Test Suite

Basic smoke tests for the NewsGuru application.

Usage:
    python -m pytest tests/test_suite.py -v
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from starlette.testclient import TestClient


def get_app():
    """Import the FastHTML app."""
    os.environ.setdefault("DB_URL", "postgresql://finespresso:mlfpass2026@72.62.114.124:5432/finespresso_db")
    os.environ.setdefault("XAI_API_KEY", "test-key")
    from main import app
    return app


class TestHomePage:
    def setup_method(self):
        self.client = TestClient(get_app())

    def test_homepage_returns_200(self):
        resp = self.client.get("/")
        assert resp.status_code == 200

    def test_homepage_has_topic_cards(self):
        resp = self.client.get("/")
        assert "News &amp; Politics" in resp.text or "Business &amp; Tech" in resp.text

    def test_homepage_has_live_feed(self):
        resp = self.client.get("/")
        assert "Live Feed" in resp.text

    def test_homepage_has_config_sources(self):
        resp = self.client.get("/")
        assert "Configure Sources" in resp.text


class TestAuthPages:
    def setup_method(self):
        self.client = TestClient(get_app())

    def test_login_page(self):
        resp = self.client.get("/login")
        assert resp.status_code == 200
        assert "Sign in" in resp.text or "Sign In" in resp.text

    def test_register_page(self):
        resp = self.client.get("/register")
        assert resp.status_code == 200
        assert "Create" in resp.text


class TestChatPage:
    def setup_method(self):
        self.client = TestClient(get_app())

    def test_chat_politics(self):
        resp = self.client.get("/chat/politics")
        assert resp.status_code == 200
        assert "Politics" in resp.text

    def test_chat_technology(self):
        resp = self.client.get("/chat/technology")
        assert resp.status_code == 200

    def test_chat_invalid_topic_redirects(self):
        resp = self.client.get("/chat/nonexistent", follow_redirects=False)
        assert resp.status_code == 303


class TestAPIEndpoints:
    def setup_method(self):
        self.client = TestClient(get_app())

    def test_trending(self):
        resp = self.client.get("/api/trending")
        assert resp.status_code == 200

    def test_journalists(self):
        resp = self.client.get("/api/journalists")
        assert resp.status_code == 200

    def test_sources(self):
        resp = self.client.get("/api/sources")
        assert resp.status_code == 200


class TestSSEEndpoints:
    def setup_method(self):
        self.client = TestClient(get_app())

    def test_feed_endpoint_exists(self):
        # SSE endpoints return streaming responses
        resp = self.client.get("/sse/feed", timeout=2)
        assert resp.status_code == 200

    def test_feed_topic_endpoint_exists(self):
        resp = self.client.get("/sse/feed/technology", timeout=2)
        assert resp.status_code == 200
