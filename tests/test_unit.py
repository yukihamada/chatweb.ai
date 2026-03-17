"""Unit tests for chatweb.ai core functions."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestCostCalculation:
    """Test MODEL_COSTS and calculate_cost."""

    def test_calculate_cost_llama4(self):
        from main import calculate_cost
        # Llama 4 Scout: $0.11 input, $0.34 output per 1M tokens
        cost = calculate_cost("meta-llama/llama-4-scout-17b-16e-instruct", 1000, 500)
        assert cost > 0
        assert cost < 0.001  # Should be very cheap

    def test_calculate_cost_opus(self):
        from main import calculate_cost
        # Opus: $15 input, $75 output per 1M tokens
        cost = calculate_cost("claude-opus-4-6", 1000, 500)
        assert cost > 0.01  # Should be expensive

    def test_calculate_cost_unknown_model_fallback(self):
        from main import calculate_cost
        # Unknown model should fallback to Haiku pricing
        cost = calculate_cost("unknown-model", 1000, 500)
        assert cost > 0

    def test_all_models_have_costs(self):
        from main import MODEL_COSTS
        required = [
            "claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001",
            "gpt-4o", "gemini-2.0-flash",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "qwen/qwen3-32b", "llama-3.3-70b-versatile",
        ]
        for model in required:
            assert model in MODEL_COSTS, f"Missing cost for {model}"
            assert "input" in MODEL_COSTS[model]
            assert "output" in MODEL_COSTS[model]


class TestTierConfig:
    """Test TIER_CONFIG structure."""

    def test_all_tiers_exist(self):
        from main import TIER_CONFIG
        required = ["cheap", "pro", "opus", "gemini", "gemini-pro", "gpt", "deepseek", "llama"]
        for tier in required:
            assert tier in TIER_CONFIG, f"Missing tier: {tier}"

    def test_tier_has_required_fields(self):
        from main import TIER_CONFIG
        for tid, cfg in TIER_CONFIG.items():
            assert "provider" in cfg, f"Tier {tid} missing provider"
            assert "model" in cfg, f"Tier {tid} missing model"
            assert "fallback_provider" in cfg, f"Tier {tid} missing fallback_provider"
            assert "fallback_model" in cfg, f"Tier {tid} missing fallback_model"

    def test_paid_tiers_flagged(self):
        from main import TIER_CONFIG
        assert TIER_CONFIG["opus"].get("paid_only") == True
        assert TIER_CONFIG["gemini-pro"].get("paid_only") == True
        assert TIER_CONFIG["cheap"].get("paid_only") is None


class TestAgents:
    """Test AGENTS configuration."""

    def test_minimum_agent_count(self):
        from main import AGENTS
        assert len(AGENTS) >= 35, f"Only {len(AGENTS)} agents, expected 35+"

    def test_agents_have_required_fields(self):
        from main import AGENTS
        for aid, ag in AGENTS.items():
            assert "name" in ag, f"Agent {aid} missing name"
            assert "system" in ag, f"Agent {aid} missing system prompt"
            assert "description" in ag, f"Agent {aid} missing description"

    def test_hidden_agents(self):
        from main import AGENTS
        hidden_ids = [k for k, v in AGENTS.items() if v.get("hidden")]
        assert "critic" in hidden_ids
        assert "synthesizer" in hidden_ids
        assert "user_prefs" in hidden_ids

    def test_no_synapse_in_prompts(self):
        """Old brand name should not appear in agent prompts."""
        from main import AGENTS
        for aid, ag in AGENTS.items():
            prompt = ag.get("system", "").lower()
            # Allow "synapse_data" (volume name) but not "Synapse" as brand
            clean = prompt.replace("synapse_data", "")
            assert "synapseプラットフォーム" not in clean, f"Agent {aid} still references Synapse"


class TestPlanCredits:
    """Test plan credit configuration."""

    def test_plan_credits_exist(self):
        from main import _PLAN_CREDITS
        assert _PLAN_CREDITS["free"] == 2.0
        assert _PLAN_CREDITS["pro"] == 19.0
        assert _PLAN_CREDITS["team"] == 65.0
        assert _PLAN_CREDITS["enterprise"] >= 100

    def test_free_is_cheapest(self):
        from main import _PLAN_CREDITS
        assert _PLAN_CREDITS["free"] < _PLAN_CREDITS["pro"]
        assert _PLAN_CREDITS["pro"] < _PLAN_CREDITS["team"]


class TestStripThinkTags:
    """Test think tag stripping."""

    def test_strip_basic(self):
        from main import _strip_think_tags
        result = _strip_think_tags("<think>internal</think>Hello")
        assert "internal" not in result
        assert "Hello" in result

    def test_strip_multiline(self):
        from main import _strip_think_tags
        result = _strip_think_tags("<think>\nline1\nline2\n</think>\nAnswer")
        assert "line1" not in result
        assert "Answer" in result

    def test_no_think_tags(self):
        from main import _strip_think_tags
        result = _strip_think_tags("Just a normal response")
        assert result == "Just a normal response"


class TestProviderHealth:
    """Test provider health cache."""

    def test_healthy_by_default(self):
        from main import _is_provider_healthy
        assert _is_provider_healthy("some_new_provider") == True

    def test_mark_unhealthy(self):
        from main import _mark_provider_unhealthy, _is_provider_healthy, _provider_unhealthy
        _mark_provider_unhealthy("test_provider")
        assert _is_provider_healthy("test_provider") == False
        # Cleanup
        _provider_unhealthy.pop("test_provider", None)
