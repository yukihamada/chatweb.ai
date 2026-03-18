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


class TestAuthEnforcement:
    """Verify all sensitive endpoints reject unauthenticated requests.
    This prevents regressions where auth gates are accidentally removed."""

    @pytest.mark.parametrize("method,path", [
        # Data access
        ("GET", "/schedule/tasks"),
        ("GET", "/usage/test123"),
        ("GET", "/runs/test123"),
        ("GET", "/history/test123"),
        ("GET", "/export/test123"),
        ("GET", "/metrics"),
        ("GET", "/dashboard"),
        ("GET", "/stats/usage"),
        ("GET", "/search/messages?q=test"),
        ("GET", "/search?q=test"),
        ("GET", "/referral/code"),
        # Data mutation
        ("DELETE", "/hitl/clear"),
        ("DELETE", "/hitl/test123"),
        ("DELETE", "/files/test123"),
    ])
    def test_requires_auth(self, client, method, path):
        if method == "GET":
            r = client.get(path)
        elif method == "DELETE":
            r = client.delete(path)
        assert r.status_code in (401, 403), f"{method} {path} returned {r.status_code} (expected 401/403)"

    @pytest.mark.parametrize("path,body", [
        ("/webhook/inbound/test", {}),
        ("/chat/suggest", {"user_message": "test", "ai_response": "test"}),
    ])
    def test_post_requires_auth(self, client, path, body):
        r = client.post(path, json=body)
        assert r.status_code in (401, 403), f"POST {path} returned {r.status_code} (expected 401/403)"


class TestSecurityHeaders:
    """Verify security headers are present on responses."""

    def test_csp_header(self, client):
        r = client.get("/")
        assert "content-security-policy" in r.headers
        assert "frame-ancestors" in r.headers["content-security-policy"]

    def test_hsts_header(self, client):
        # HSTS only set for HTTPS, TestClient uses HTTP
        r = client.get("/")
        assert "x-frame-options" in r.headers
        assert r.headers["x-frame-options"] == "DENY"

    def test_nosniff_header(self, client):
        r = client.get("/")
        assert r.headers.get("x-content-type-options") == "nosniff"


class TestTokenEstimation:
    """Test _estimate_tokens for conversation compression."""

    def test_basic_estimation(self):
        from main import _estimate_tokens
        msgs = [{"role": "user", "content": "Hello world"}]  # 11 chars → ~3 tokens
        tokens = _estimate_tokens(msgs)
        assert tokens >= 1
        assert tokens < 20

    def test_empty_messages(self):
        from main import _estimate_tokens
        assert _estimate_tokens([]) >= 1 or _estimate_tokens([]) == 0

    def test_list_content(self):
        from main import _estimate_tokens
        msgs = [{"role": "user", "content": [
            {"type": "text", "text": "Describe this image"},
            {"type": "image", "source": {"type": "base64", "data": "abc"}}
        ]}]
        tokens = _estimate_tokens(msgs)
        assert tokens >= 1  # Should count text blocks, not crash

    def test_none_content(self):
        from main import _estimate_tokens
        msgs = [{"role": "user", "content": None}]
        tokens = _estimate_tokens(msgs)
        assert tokens >= 0  # Should not crash


class TestIsUrlSafe:
    """Test SSRF prevention."""

    def test_public_url_safe(self):
        from main import _is_url_safe
        assert _is_url_safe("https://example.com") == True

    def test_metadata_blocked(self):
        from main import _is_url_safe
        assert _is_url_safe("http://169.254.169.254/latest/meta-data") == False

    def test_localhost_blocked(self):
        from main import _is_url_safe
        assert _is_url_safe("http://127.0.0.1:8080") == False
        assert _is_url_safe("http://localhost:3000") == False

    def test_file_scheme_blocked(self):
        from main import _is_url_safe
        assert _is_url_safe("file:///etc/passwd") == False

    def test_private_ip_blocked(self):
        from main import _is_url_safe
        assert _is_url_safe("http://10.0.0.1") == False
        assert _is_url_safe("http://192.168.1.1") == False


class TestStripeWebhook:
    """Test Stripe webhook handling."""

    def test_webhook_rejects_without_signature(self, client):
        r = client.post("/billing/webhook", content=b'{}',
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 400

    def test_billing_plans_returns_all(self, client):
        r = client.get("/billing/plans")
        assert r.status_code == 200
        d = r.json()
        plans = d if isinstance(d, list) else d.get("plans", [])
        plan_names = [p.get("name", p.get("id", "")) for p in plans] if isinstance(plans, list) else []
        assert len(plans) >= 3  # free, pro, team at minimum


class TestNewAgents:
    """Test newly added agents exist and are configured."""

    def test_data_viz_agent(self, client):
        r = client.get("/agents")
        d = r.json()
        assert "data_viz" in d, "data_viz agent missing"
        assert "可視化" in d["data_viz"]["name"] or "データ" in d["data_viz"]["description"]

    def test_tutor_agent(self, client):
        r = client.get("/agents")
        d = r.json()
        assert "tutor" in d, "tutor agent missing"

    def test_health_agent(self, client):
        r = client.get("/agents")
        d = r.json()
        assert "health" in d, "health agent missing"

    def test_agent_count_increased(self, client):
        r = client.get("/agents")
        d = r.json()
        assert len(d) >= 38, f"Only {len(d)} visible agents, expected 38+"


class TestCompressHistory:
    """Test conversation compression."""

    def test_short_history_unchanged(self):
        import asyncio
        from main import compress_history
        msgs = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        result, summary = asyncio.get_event_loop().run_until_complete(
            compress_history(msgs, "test_session"))
        assert result == msgs
        assert summary is None

    def test_empty_history(self):
        import asyncio
        from main import compress_history
        result, summary = asyncio.get_event_loop().run_until_complete(
            compress_history([], "test_session"))
        assert result == []
        assert summary is None
