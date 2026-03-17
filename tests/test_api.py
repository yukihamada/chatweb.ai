"""API integration tests for chatweb.ai endpoints."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create test client. Skip if imports fail (missing env vars etc)."""
    try:
        from main import app
        return TestClient(app)
    except Exception as e:
        pytest.skip(f"Cannot create test client: {e}")


class TestHealthEndpoints:
    def test_root_returns_html(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "chatweb.ai" in r.text

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ok"
        assert d["agents"] >= 35

    def test_robots_txt(self, client):
        r = client.get("/robots.txt")
        assert r.status_code == 200
        assert "Sitemap" in r.text

    def test_sitemap_xml(self, client):
        r = client.get("/sitemap.xml")
        assert r.status_code == 200
        assert "urlset" in r.text


class TestA2A:
    def test_agent_card(self, client):
        r = client.get("/.well-known/agent-card.json")
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == "chatweb-ai"
        assert "supportedInterfaces" in d
        assert d["supportedInterfaces"][0]["protocolVersion"] == "1.0"
        assert len(d["skills"]) >= 30

    def test_a2a_send_message(self, client):
        r = client.post("/a2a", json={
            "jsonrpc": "2.0",
            "method": "GetExtendedAgentCard",
            "params": {},
            "id": "test-1"
        })
        assert r.status_code == 200
        d = r.json()
        assert d["jsonrpc"] == "2.0"
        assert "result" in d

    def test_a2a_invalid_method(self, client):
        r = client.post("/a2a", json={
            "jsonrpc": "2.0",
            "method": "InvalidMethod",
            "params": {},
            "id": "test-2"
        })
        assert r.status_code == 200
        d = r.json()
        assert "error" in d
        assert d["error"]["code"] == -32601

    def test_legacy_agent_json_redirects(self, client):
        r = client.get("/.well-known/agent.json", follow_redirects=False)
        assert r.status_code == 301


class TestCleanURLs:
    """Test all clean URL routes return 200."""

    @pytest.mark.parametrize("path", [
        "/features", "/about", "/workflow", "/api-docs",
        "/terms", "/privacy", "/press-release",
        "/guides/ai-agents", "/guides/ai-automation", "/guides/chatgpt-alternative",
        "/guides/a2a-guide",
        "/en/ai-agents", "/en/ai-automation", "/en/api-docs", "/en/press-release",
        "/launch",
        "/launch/twitter", "/launch/linkedin", "/launch/media-pitch",
        "/launch/product-hunt", "/launch/hackernews", "/launch/tech-article",
    ])
    def test_clean_url(self, client, path):
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}"


class TestAuth:
    def test_auth_me_unauthenticated(self, client):
        r = client.get("/auth/me")
        assert r.status_code == 200
        d = r.json()
        assert d["logged_in"] == False

    def test_auth_google_redirects(self, client):
        r = client.get("/auth/google", follow_redirects=False)
        assert r.status_code in (302, 307)


class TestAgentsEndpoint:
    def test_list_agents(self, client):
        r = client.get("/agents")
        assert r.status_code == 200
        d = r.json()
        assert len(d) >= 30
        # Hidden agents should not appear
        assert "critic" not in d
        assert "synthesizer" not in d

    def test_agent_has_llm_field(self, client):
        r = client.get("/agents")
        d = r.json()
        for aid, ag in d.items():
            if ag.get("is_builtin"):
                assert "llm" in ag, f"Agent {aid} missing llm field"


class TestBilling:
    def test_billing_plans(self, client):
        r = client.get("/billing/plans")
        assert r.status_code == 200


class TestReferral:
    def test_referral_requires_auth(self, client):
        r = client.get("/referral/code")
        assert r.status_code == 401
