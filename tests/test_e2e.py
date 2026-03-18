"""End-to-end browser tests for chatweb.ai using Playwright."""
import re

import pytest

BASE_URL = "https://chatweb.ai"

# Skip all tests if playwright is not installed
pytest.importorskip("playwright")

try:
    from playwright.sync_api import expect  # noqa: F401

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="playwright not installed",
)


# ---------------------------------------------------------------------------
# Homepage & core UI
# ---------------------------------------------------------------------------


class TestHomepage:
    """Verify the homepage loads and renders key elements."""

    def test_page_loads_with_title(self, page):
        page.goto(BASE_URL)
        expect(page).to_have_title(re.compile(r"chatweb\.ai"), timeout=15_000)

    def test_welcome_message_visible(self, page):
        page.goto(BASE_URL)
        # The chat area should be visible
        chat_wrap = page.locator("#chatWrap")
        expect(chat_wrap).to_be_visible(timeout=10_000)

    def test_chat_input_visible(self, page):
        page.goto(BASE_URL)
        chat_input = page.locator("#chatInput")
        expect(chat_input).to_be_visible(timeout=10_000)

    def test_chat_input_is_interactive(self, page):
        page.goto(BASE_URL)
        chat_input = page.locator("#chatInput")
        expect(chat_input).to_be_visible(timeout=10_000)
        chat_input.fill("Hello from Playwright")
        expect(chat_input).to_have_value("Hello from Playwright")

    def test_send_button_visible(self, page):
        page.goto(BASE_URL)
        send_btn = page.locator("#sendBtn")
        expect(send_btn).to_be_visible(timeout=10_000)


# ---------------------------------------------------------------------------
# Agent selector
# ---------------------------------------------------------------------------


class TestAgentSelector:
    """Verify the agent selector dropdown opens and lists agents."""

    def test_agent_pill_visible(self, page):
        page.goto(BASE_URL)
        pill = page.locator("#agent-pill")
        expect(pill).to_be_visible(timeout=10_000)
        # Default text
        expect(pill).to_contain_text("エージェント")

    def test_agent_selector_opens(self, page):
        page.goto(BASE_URL)
        pill = page.locator("#agent-pill")
        expect(pill).to_be_visible(timeout=10_000)
        pill.click()
        # The agent selector modal should appear
        modal = page.locator("#agent-selector-modal")
        expect(modal).to_be_visible(timeout=5_000)

    def test_agent_search_field(self, page):
        page.goto(BASE_URL)
        page.locator("#agent-pill").click()
        search = page.locator("#agent-search")
        expect(search).to_be_visible(timeout=5_000)


# ---------------------------------------------------------------------------
# Language selector
# ---------------------------------------------------------------------------


class TestLanguageSelector:
    """Verify language switching works."""

    def test_lang_button_visible(self, page):
        page.goto(BASE_URL)
        lang_btn = page.locator("#lang-btn")
        expect(lang_btn).to_be_visible(timeout=10_000)

    def test_lang_dropdown_opens(self, page):
        page.goto(BASE_URL)
        lang_btn = page.locator("#lang-btn")
        expect(lang_btn).to_be_visible(timeout=10_000)
        lang_btn.click()
        dropdown = page.locator("#lang-dropdown")
        expect(dropdown).to_be_visible(timeout=5_000)

    def test_switch_to_english(self, page):
        page.goto(BASE_URL)
        page.locator("#lang-btn").click()
        dropdown = page.locator("#lang-dropdown")
        expect(dropdown).to_be_visible(timeout=5_000)
        # Click English option
        page.locator("#lang-dropdown >> button", has_text="English").click()
        # Label should update
        expect(page.locator("#lang-label")).to_have_text("EN", timeout=5_000)


# ---------------------------------------------------------------------------
# Theme toggle
# ---------------------------------------------------------------------------


class TestThemeToggle:
    """Verify dark/light theme toggle works."""

    def test_theme_toggle_button_exists(self, page):
        """The theme toggle is inside the 'more' menu."""
        page.goto(BASE_URL)
        # The theme button contains the text "テーマ"
        theme_btn = page.locator("button.dropdown-item", has_text="テーマ")
        # It may be hidden inside a dropdown; just verify the element exists
        assert theme_btn.count() >= 1

    def test_toggle_theme_changes_class(self, page):
        """Clicking theme toggle should flip the 'dark' class on <html>."""
        page.goto(BASE_URL)
        html_el = page.locator("html")

        # Record the initial theme state
        initial_dark = page.evaluate("document.documentElement.classList.contains('dark')")

        # toggleTheme is a global function
        page.evaluate("toggleTheme()")

        after_dark = page.evaluate("document.documentElement.classList.contains('dark')")
        assert initial_dark != after_dark, "Theme class should have toggled"

        # Toggle back
        page.evaluate("toggleTheme()")
        restored = page.evaluate("document.documentElement.classList.contains('dark')")
        assert restored == initial_dark, "Theme should be restored after double toggle"


# ---------------------------------------------------------------------------
# Static page navigation (HTTP-level)
# ---------------------------------------------------------------------------


class TestStaticPages:
    """Verify key pages return HTTP 200."""

    @pytest.mark.parametrize(
        "path",
        [
            "/features",
            "/about",
            "/press-release",
        ],
    )
    def test_page_returns_200(self, page, path):
        response = page.goto(f"{BASE_URL}{path}")
        assert response is not None
        assert response.status == 200, f"{path} returned {response.status}"


# ---------------------------------------------------------------------------
# Favicon
# ---------------------------------------------------------------------------


class TestFavicon:
    """Verify favicon is served correctly."""

    def test_favicon_ico(self, page):
        response = page.goto(f"{BASE_URL}/favicon.ico")
        assert response is not None
        # Should be 200 (may redirect internally to SVG, but final status is 200)
        assert response.status == 200


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


class TestAuthEnforcement:
    """Verify unauthenticated access to protected endpoints is rejected."""

    def test_metrics_requires_auth(self, page):
        response = page.goto(f"{BASE_URL}/metrics")
        assert response is not None
        assert response.status == 401, (
            f"/metrics should return 401 for unauthenticated requests, got {response.status}"
        )
